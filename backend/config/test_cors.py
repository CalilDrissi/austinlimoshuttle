"""
Cross-origin access for the Next.js frontend.

Server-rendered pages reach this API from Node and never trigger CORS, so a
missing configuration stays invisible until the booking funnel calls the API
from a browser. These tests make it visible immediately.

The security-relevant assertion is the last one: credentials are allowed, and a
wildcard origin combined with credentials would let any site issue authenticated
requests as a signed-in customer.
"""

import pytest
from django.conf import settings
from django.urls import reverse

ALLOWED = "http://localhost:3000"
FOREIGN = "https://evil.example.com"


@pytest.mark.django_db
class TestCorsHeaders:
    def test_allowed_origin_gets_the_header(self, client):
        response = client.get(reverse("api:vehicles"), HTTP_ORIGIN=ALLOWED)
        assert response.headers.get("Access-Control-Allow-Origin") == ALLOWED

    def test_credentials_are_permitted(self, client):
        """Session cookies must travel with API requests from the frontend."""
        response = client.get(reverse("api:vehicles"), HTTP_ORIGIN=ALLOWED)
        assert response.headers.get("Access-Control-Allow-Credentials") == "true"

    def test_unknown_origin_gets_nothing(self, client):
        response = client.get(reverse("api:vehicles"), HTTP_ORIGIN=FOREIGN)
        assert "Access-Control-Allow-Origin" not in response.headers

    def test_preflight_is_answered(self, client):
        """A POST with a JSON body triggers a preflight before the real request."""
        response = client.options(
            reverse("api:quotes"),
            HTTP_ORIGIN=ALLOWED,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="content-type,x-csrftoken",
        )
        assert response.status_code in (200, 204)
        assert response.headers.get("Access-Control-Allow-Origin") == ALLOWED

    def test_csrf_header_is_permitted_on_preflight(self, client):
        """Django rejects session-authenticated writes without X-CSRFToken."""
        response = client.options(
            reverse("api:quotes"),
            HTTP_ORIGIN=ALLOWED,
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
            HTTP_ACCESS_CONTROL_REQUEST_HEADERS="x-csrftoken",
        )
        allowed = (response.headers.get("Access-Control-Allow-Headers") or "").lower()
        assert "x-csrftoken" in allowed


class TestCorsConfiguration:
    def test_origins_are_explicit_never_wildcarded(self):
        """
        A wildcard origin with credentials is refused by browsers and unsafe:
        it would let any site make authenticated requests as a signed-in
        customer.
        """
        assert getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False) is False
        assert "*" not in settings.CORS_ALLOWED_ORIGINS
        assert settings.CORS_ALLOWED_ORIGINS

    def test_middleware_precedes_common_middleware(self):
        """
        CorsMiddleware must run before CommonMiddleware, or a preflight can be
        redirected before the CORS headers are attached.
        """
        order = settings.MIDDLEWARE
        assert order.index("corsheaders.middleware.CorsMiddleware") < order.index(
            "django.middleware.common.CommonMiddleware"
        )
