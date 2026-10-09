"""
Distance lookup.

Every test stubs the HTTP call: the suite must never touch the network or spend
the client's Google billing. The behaviour that matters is what happens when the
lookup fails -- it must fail the quote, never fall back to something a client
supplied.
"""

from decimal import Decimal
from unittest.mock import patch

import pytest
import requests
from django.core.cache import cache

from pricing.distance import DistanceLookupError, lookup

# lookup() reads the Maps key from SiteSettings (DB-backed, admin-configurable),
# so these tests need database access even though they stub the network call.
pytestmark = pytest.mark.django_db

OK_PAYLOAD = {
    "status": "OK",
    "origin_addresses": ["3600 Presidential Blvd, Austin, TX 78719, USA"],
    "destination_addresses": ["Downtown, Austin, TX, USA"],
    "rows": [{"elements": [{
        "status": "OK",
        "distance": {"text": "11.3 mi", "value": 18186},
        "duration": {"text": "18 mins", "value": 1080},
    }]}],
}


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def api_key(settings):
    """
    Configure a dummy key.

    `override_settings` only decorates SimpleTestCase subclasses, so plain
    pytest classes use the `settings` fixture instead.
    """
    settings.GOOGLE_MAPS_API_KEY = "test-key"
    return settings


class TestSuccessfulLookup:
    def test_converts_metres_to_miles(self, api_key):
        with patch("pricing.distance.requests.get", return_value=FakeResponse(OK_PAYLOAD)):
            journey = lookup("ABIA", "Downtown Austin")
        # 18186 m / 1609.344 = 11.300 mi
        assert journey.distance_miles == Decimal("11.300")

    def test_does_not_parse_the_display_string(self, api_key):
        """
        "11.3 mi" is rounded for humans and locale-dependent. The metre value is
        authoritative, so a payload whose text disagrees must follow the number.
        """
        payload = {**OK_PAYLOAD}
        payload["rows"] = [{"elements": [{
            "status": "OK",
            "distance": {"text": "99 mi", "value": 18186},
            "duration": {"text": "18 mins", "value": 1080},
        }]}]
        with patch("pricing.distance.requests.get", return_value=FakeResponse(payload)):
            journey = lookup("a", "b")
        assert journey.distance_miles == Decimal("11.300")

    def test_rounds_duration_to_whole_minutes(self, api_key):
        with patch("pricing.distance.requests.get", return_value=FakeResponse(OK_PAYLOAD)):
            journey = lookup("a", "b")
        assert journey.duration_minutes == 18

    def test_returns_the_addresses_google_resolved(self, api_key):
        with patch("pricing.distance.requests.get", return_value=FakeResponse(OK_PAYLOAD)):
            journey = lookup("abia", "downtown")
        assert "Presidential" in journey.resolved_origin

    def test_result_is_cached(self, api_key):
        with patch("pricing.distance.requests.get",
                   return_value=FakeResponse(OK_PAYLOAD)) as mock_get:
            lookup("ABIA", "Downtown Austin")
            lookup("ABIA", "Downtown Austin")
        assert mock_get.call_count == 1

    def test_cache_key_ignores_case_and_padding(self, api_key):
        with patch("pricing.distance.requests.get",
                   return_value=FakeResponse(OK_PAYLOAD)) as mock_get:
            lookup("ABIA", "Downtown Austin")
            lookup("  abia  ", "downtown austin")
        assert mock_get.call_count == 1

    def test_different_journeys_are_cached_separately(self, api_key):
        with patch("pricing.distance.requests.get",
                   return_value=FakeResponse(OK_PAYLOAD)) as mock_get:
            lookup("ABIA", "Downtown")
            lookup("ABIA", "Round Rock")
        assert mock_get.call_count == 2


class TestFailuresAreHardFailures:
    """
    A fallback to a client-supplied distance would reintroduce exactly the hole
    this module closes -- anyone wanting the cheap fare need only make the
    lookup fail.
    """

    def test_timeout_raises(self, api_key):
        with patch("pricing.distance.requests.get", side_effect=requests.Timeout()), \
             pytest.raises(DistanceLookupError, match="did not respond"):
            lookup("a", "b")

    def test_connection_error_raises(self, api_key):
        with patch("pricing.distance.requests.get",
                   side_effect=requests.ConnectionError()), \
             pytest.raises(DistanceLookupError):
            lookup("a", "b")

    def test_http_error_raises(self, api_key):
        with patch("pricing.distance.requests.get",
                   return_value=FakeResponse({}, status_code=500)), \
             pytest.raises(DistanceLookupError):
            lookup("a", "b")

    def test_unreadable_body_raises(self, api_key):
        class Broken(FakeResponse):
            def json(self):
                raise ValueError("not json")

        with patch("pricing.distance.requests.get", return_value=Broken({})), \
             pytest.raises(DistanceLookupError, match="unreadable"):
            lookup("a", "b")

    def test_request_denied_raises(self, api_key):
        """A browser-referrer-restricted key produces REQUEST_DENIED."""
        payload = {"status": "REQUEST_DENIED",
                   "error_message": "API keys with referer restrictions..."}
        with patch("pricing.distance.requests.get", return_value=FakeResponse(payload)), \
             pytest.raises(DistanceLookupError):
            lookup("a", "b")

    def test_zero_results_explains_itself(self, api_key):
        payload = {"status": "OK", "rows": [{"elements": [{"status": "ZERO_RESULTS"}]}]}
        with patch("pricing.distance.requests.get", return_value=FakeResponse(payload)), \
             pytest.raises(DistanceLookupError, match="No driving route"):
            lookup("a", "b")

    def test_unknown_address_explains_itself(self, api_key):
        payload = {"status": "OK", "rows": [{"elements": [{"status": "NOT_FOUND"}]}]}
        with patch("pricing.distance.requests.get", return_value=FakeResponse(payload)), \
             pytest.raises(DistanceLookupError, match="could not be found"):
            lookup("a", "b")

    def test_blank_addresses_are_rejected_without_calling_the_api(self, api_key):
        with patch("pricing.distance.requests.get") as mock_get:
            with pytest.raises(DistanceLookupError, match="required"):
                lookup("", "Downtown")
        mock_get.assert_not_called()

    def test_failure_is_not_cached(self, api_key):
        """A transient failure must not poison the cache for a week."""
        with patch("pricing.distance.requests.get", side_effect=requests.Timeout()), \
             pytest.raises(DistanceLookupError):
            lookup("ABIA", "Downtown")

        with patch("pricing.distance.requests.get",
                   return_value=FakeResponse(OK_PAYLOAD)) as mock_get:
            journey = lookup("ABIA", "Downtown")
        assert mock_get.call_count == 1
        assert journey.distance_miles == Decimal("11.300")


class TestConfiguration:
    def test_missing_key_fails_loudly_without_calling_the_api(self, settings):
        settings.GOOGLE_MAPS_API_KEY = ""
        with patch("pricing.distance.requests.get") as mock_get:
            with pytest.raises(DistanceLookupError, match="not configured"):
                lookup("a", "b")
        mock_get.assert_not_called()

    def test_the_key_is_sent_as_a_parameter_not_embedded_in_the_url(self, settings):
        settings.GOOGLE_MAPS_API_KEY = "secret-key-value"
        with patch("pricing.distance.requests.get",
                   return_value=FakeResponse(OK_PAYLOAD)) as mock_get:
            lookup("a", "b")
        _, kwargs = mock_get.call_args
        assert kwargs["params"]["key"] == "secret-key-value"
        assert kwargs["timeout"] > 0
