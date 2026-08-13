"""
PayPal credential storage and the settings page.

Same properties as the Stripe page: the secret is encrypted, never rendered,
and unreachable by a Dispatcher. The difference worth testing separately is the
credential check — PayPal ids carry no sandbox/live prefix, so a mismatched pair
can only be caught by authenticating.
"""

from unittest.mock import patch

import pytest
import requests
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from dashboard.permissions import DISPATCHER, EDITOR, MANAGER, sync_roles
from payments import paypal
from payments.models import PayPalSettings

User = get_user_model()

CLIENT_ID = "AYSq3RDGsmBLJE-otTkBtM-jBRd1TCQwFf9RGfwddNXWz0uFU9ztymylOhRS"
CLIENT_SECRET = "EGnHDxD_qRPdaLdZz8iCr8N7_MzF-YHPTkjs6NKYQvQSBngp4PTTVWkPZRbL"
WEBHOOK_ID = "8SW40482T02784321"
PASSWORD = "PayPalLocal!2026"


@pytest.fixture
def roles(db):
    sync_roles()


def staff(role):
    user = User.objects.create_user(
        email=f"{role.lower()}@example.com", password=PASSWORD, is_staff=True,
    )
    user.groups.add(Group.objects.get(name=role))
    return user


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.ok = status_code < 400

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


@pytest.mark.django_db
class TestModel:
    def test_secret_is_encrypted_at_rest(self):
        obj = PayPalSettings.load()
        obj.client_secret = CLIENT_SECRET
        obj.save()

        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("SELECT client_secret_encrypted FROM payments_paypalsettings WHERE id=1")
            stored = cur.fetchone()[0]

        assert CLIENT_SECRET not in stored
        assert PayPalSettings.load().client_secret == CLIENT_SECRET

    def test_masking_hides_the_secret(self):
        obj = PayPalSettings.load()
        obj.client_secret = CLIENT_SECRET
        assert CLIENT_SECRET not in obj.client_secret_masked
        assert obj.client_secret_masked.endswith(CLIENT_SECRET[-4:])

    def test_client_id_is_truncated_for_display_but_not_hidden(self):
        obj = PayPalSettings.load()
        obj.client_id = CLIENT_ID
        assert obj.client_id_masked.startswith(CLIENT_ID[:10])
        assert len(obj.client_id_masked) < len(CLIENT_ID)

    def test_api_base_follows_the_mode(self):
        obj = PayPalSettings.load()
        assert "sandbox" in obj.api_base
        obj.mode = PayPalSettings.Mode.LIVE
        assert "sandbox" not in obj.api_base
        assert obj.is_live

    def test_singleton(self):
        PayPalSettings.load()
        PayPalSettings(client_id="other").save()
        assert PayPalSettings.objects.count() == 1

    def test_cannot_be_deleted(self):
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            PayPalSettings.load().delete()

    def test_is_configured_requires_both_credentials_and_the_switch(self):
        obj = PayPalSettings.load()
        assert not obj.is_configured
        obj.client_id = CLIENT_ID
        obj.client_secret = CLIENT_SECRET
        obj.save()
        assert not obj.is_configured  # still disabled
        obj.is_enabled = True
        obj.save()
        assert obj.is_configured


@pytest.mark.django_db
class TestCredentialVerification:
    @pytest.fixture
    def configured(self):
        obj = PayPalSettings.load()
        obj.client_id = CLIENT_ID
        obj.client_secret = CLIENT_SECRET
        obj.save()
        return obj

    def test_successful_authentication(self, configured):
        with patch("payments.paypal.requests.post",
                   return_value=FakeResponse({"access_token": "A21AA"})):
            ok, message = paypal.verify_credentials(configured)
        assert ok
        assert "Sandbox" in message
        configured.refresh_from_db()
        assert configured.last_test_ok is True

    def test_rejected_credentials_explain_the_likely_cause(self, configured):
        """401 usually means live credentials against sandbox, or the reverse."""
        with patch("payments.paypal.requests.post",
                   return_value=FakeResponse({"error": "invalid_client"}, 401)):
            ok, message = paypal.verify_credentials(configured)
        assert not ok
        assert "sandbox" in message.lower()
        configured.refresh_from_db()
        assert configured.last_test_ok is False
        assert configured.last_test_error

    def test_hits_the_environment_that_is_selected(self, configured):
        configured.mode = PayPalSettings.Mode.LIVE
        configured.save()
        with patch("payments.paypal.requests.post",
                   return_value=FakeResponse({"access_token": "A21AA"})) as mock_post:
            paypal.verify_credentials(configured)
        url = mock_post.call_args.args[0]
        assert "sandbox" not in url

    def test_timeout_is_reported_not_raised(self, configured):
        with patch("payments.paypal.requests.post", side_effect=requests.Timeout()):
            ok, message = paypal.verify_credentials(configured)
        assert not ok
        assert "did not respond" in message

    def test_network_failure_is_reported_not_raised(self, configured):
        with patch("payments.paypal.requests.post", side_effect=requests.ConnectionError()):
            ok, _ = paypal.verify_credentials(configured)
        assert not ok

    def test_unreadable_reply_is_reported(self, configured):
        with patch("payments.paypal.requests.post", return_value=FakeResponse(None)):
            ok, _ = paypal.verify_credentials(configured)
        assert not ok

    def test_missing_credentials_fail_without_calling_paypal(self):
        blank = PayPalSettings.load()
        with patch("payments.paypal.requests.post") as mock_post:
            ok, message = paypal.verify_credentials(blank)
        mock_post.assert_not_called()
        assert not ok
        assert "required" in message

    def test_the_secret_is_never_in_the_url(self, configured):
        """It must travel as HTTP basic auth, not a query string that gets logged."""
        with patch("payments.paypal.requests.post",
                   return_value=FakeResponse({"access_token": "A21AA"})) as mock_post:
            paypal.verify_credentials(configured)
        url = mock_post.call_args.args[0]
        assert CLIENT_SECRET not in url
        assert mock_post.call_args.kwargs["auth"] == (CLIENT_ID, CLIENT_SECRET)


@pytest.mark.django_db
class TestSettingsPage:
    @pytest.fixture
    def manager_client(self, client, roles):
        staff(MANAGER)
        client.login(username="manager@example.com", password=PASSWORD)
        return client

    def post(self, client, **overrides):
        data = {
            "mode": "sandbox", "is_enabled": "on", "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET, "webhook_id": WEBHOOK_ID,
            "brand_name": "Austin Limo Shuttle",
        }
        data.update(overrides)
        return client.post(reverse("dashboard:paypal_settings"), data, follow=True)

    def test_dispatcher_cannot_reach_it(self, client, roles):
        staff(DISPATCHER)
        client.login(username="dispatcher@example.com", password=PASSWORD)
        assert client.get(reverse("dashboard:paypal_settings")).status_code == 403

    def test_editor_cannot_reach_it(self, client, roles):
        staff(EDITOR)
        client.login(username="editor@example.com", password=PASSWORD)
        assert client.get(reverse("dashboard:paypal_settings")).status_code == 403

    def test_manager_can(self, manager_client):
        assert manager_client.get(reverse("dashboard:paypal_settings")).status_code == 200

    def test_saving_encrypts_and_attributes(self, manager_client):
        self.post(manager_client)
        obj = PayPalSettings.load()
        assert obj.client_secret == CLIENT_SECRET
        assert obj.client_id == CLIENT_ID
        assert obj.updated_by.email == "manager@example.com"

    def test_secret_is_never_rendered_back(self, manager_client):
        self.post(manager_client)
        body = manager_client.get(reverse("dashboard:paypal_settings")).content.decode()
        assert CLIENT_SECRET not in body
        assert "••••" in body

    def test_blank_secret_keeps_the_stored_one(self, manager_client):
        self.post(manager_client)
        self.post(manager_client, client_secret="")
        assert PayPalSettings.load().client_secret == CLIENT_SECRET

    def test_a_stripe_key_pasted_here_is_refused(self, manager_client):
        response = self.post(manager_client, client_id="sk_live_example0000")
        assert b"looks like a Stripe key" in response.content
        assert not PayPalSettings.load().client_id

    def test_enabling_without_credentials_is_refused(self, manager_client):
        response = self.post(manager_client, client_id="", client_secret="")
        assert not PayPalSettings.load().is_enabled
        assert b"required before enabling" in response.content

    def test_test_button_records_the_outcome(self, manager_client):
        self.post(manager_client)
        with patch("payments.paypal.requests.post",
                   return_value=FakeResponse({"access_token": "A21AA"})):
            manager_client.post(reverse("dashboard:paypal_settings"),
                                {"action": "test"}, follow=True)
        assert PayPalSettings.load().last_test_ok is True

    def test_page_states_the_flow_is_not_wired_up(self, manager_client):
        """
        An administrator entering live credentials must not assume PayPal is
        taking payments. Saying so on the page is cheaper than the support call.
        """
        body = manager_client.get(reverse("dashboard:paypal_settings")).content.decode()
        assert "not wired up" in body

    def test_nav_shows_paypal_to_a_manager_only(self, client, roles):
        staff(MANAGER)
        client.login(username="manager@example.com", password=PASSWORD)
        assert reverse("dashboard:paypal_settings") in \
            client.get(reverse("dashboard:home")).content.decode()

        client.logout()
        staff(DISPATCHER)
        client.login(username="dispatcher@example.com", password=PASSWORD)
        assert reverse("dashboard:paypal_settings") not in \
            client.get(reverse("dashboard:home")).content.decode()
