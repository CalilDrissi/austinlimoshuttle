"""
Stripe credential storage and the dashboard settings page.

The properties that matter: a secret key is never rendered back to a browser,
never stored in plaintext, and cannot be reached by a Dispatcher. Mode/key
mismatches are refused because they fail silently in production -- live mode
with test keys takes no money and reports success.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from config import crypto
from dashboard.permissions import DISPATCHER, EDITOR, MANAGER, sync_roles
from payments.models import PaymentSettings

User = get_user_model()

LIVE_SECRET = "sk_live_example0000abcd"
TEST_SECRET = "sk_test_example0000wxyz"
LIVE_PUBLISHABLE = "pk_live_51ABCDEFexamplepublishable"
TEST_PUBLISHABLE = "pk_test_51ABCDEFexamplepublishable"
WEBHOOK = "whsec_ABCDEFexamplewebhooksecret00"


@pytest.fixture
def roles(db):
    sync_roles()


def staff(role, password="SettingsLocal!2026"):
    user = User.objects.create_user(
        email=f"{role.lower()}@example.com", password=password, is_staff=True,
    )
    user.groups.add(Group.objects.get(name=role))
    return user


class TestEncryption:
    def test_round_trip(self):
        assert crypto.decrypt(crypto.encrypt(LIVE_SECRET)) == LIVE_SECRET

    def test_ciphertext_does_not_contain_the_secret(self):
        assert LIVE_SECRET not in crypto.encrypt(LIVE_SECRET)

    def test_same_value_encrypts_differently_each_time(self):
        """Fernet includes a random IV; identical plaintexts must not match."""
        assert crypto.encrypt(LIVE_SECRET) != crypto.encrypt(LIVE_SECRET)

    def test_empty_stays_empty(self):
        assert crypto.encrypt("") == ""
        assert crypto.decrypt("") is None

    def test_unreadable_value_returns_none_rather_than_raising(self):
        """A changed DJANGO_SECRET_KEY must degrade, not 500 every page."""
        assert crypto.decrypt("not-a-valid-fernet-token") is None

    def test_a_different_secret_key_cannot_decrypt(self, settings):
        token = crypto.encrypt(LIVE_SECRET)
        settings.SECRET_KEY = "an-entirely-different-secret-key-value"
        assert crypto.decrypt(token) is None

    def test_mask_reveals_only_the_prefix_and_last_four(self):
        masked = crypto.mask(LIVE_SECRET)
        assert masked.startswith("sk_live_")
        assert masked.endswith(LIVE_SECRET[-4:])
        assert LIVE_SECRET not in masked


@pytest.mark.django_db
class TestPaymentSettingsModel:
    def test_secret_is_not_stored_in_plaintext(self):
        obj = PaymentSettings.load()
        obj.secret_key = LIVE_SECRET
        obj.save()

        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("SELECT secret_key_encrypted FROM payments_paymentsettings WHERE id=1")
            stored = cur.fetchone()[0]

        assert LIVE_SECRET not in stored
        assert PaymentSettings.load().secret_key == LIVE_SECRET

    def test_singleton(self):
        PaymentSettings.load()
        other = PaymentSettings(mode=PaymentSettings.Mode.LIVE)
        other.save()
        assert PaymentSettings.objects.count() == 1

    def test_cannot_be_deleted(self):
        from django.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            PaymentSettings.load().delete()

    def test_is_configured_requires_keys_and_the_switch(self):
        obj = PaymentSettings.load()
        assert not obj.is_configured

        obj.publishable_key = TEST_PUBLISHABLE
        obj.secret_key = TEST_SECRET
        obj.save()
        assert not obj.is_configured  # still disabled

        obj.is_enabled = True
        obj.save()
        assert obj.is_configured

    def test_detects_a_mode_key_mismatch(self):
        obj = PaymentSettings.load()
        obj.mode = PaymentSettings.Mode.LIVE
        obj.secret_key = TEST_SECRET
        obj.save()
        assert not obj.key_mode_matches


@pytest.mark.django_db
class TestAccessControl:
    def test_dispatcher_cannot_reach_payment_settings(self, client, roles):
        staff(DISPATCHER)
        client.login(username="dispatcher@example.com", password="SettingsLocal!2026")
        assert client.get(reverse("dashboard:payment_settings")).status_code == 403

    def test_editor_cannot_reach_payment_settings(self, client, roles):
        staff(EDITOR)
        client.login(username="editor@example.com", password="SettingsLocal!2026")
        assert client.get(reverse("dashboard:payment_settings")).status_code == 403

    def test_manager_can(self, client, roles):
        staff(MANAGER)
        client.login(username="manager@example.com", password="SettingsLocal!2026")
        assert client.get(reverse("dashboard:payment_settings")).status_code == 200

    def test_anonymous_is_redirected(self, client, roles):
        response = client.get(reverse("dashboard:payment_settings"))
        assert response.status_code == 302

    def test_settings_link_is_hidden_from_a_dispatcher(self, client, roles):
        staff(DISPATCHER)
        client.login(username="dispatcher@example.com", password="SettingsLocal!2026")
        body = client.get(reverse("dashboard:home")).content.decode()
        assert reverse("dashboard:payment_settings") not in body

    def test_settings_link_is_shown_to_a_manager(self, client, roles):
        staff(MANAGER)
        client.login(username="manager@example.com", password="SettingsLocal!2026")
        body = client.get(reverse("dashboard:home")).content.decode()
        assert reverse("dashboard:payment_settings") in body


@pytest.mark.django_db
class TestSecretIsNeverRendered:
    @pytest.fixture
    def manager_client(self, client, roles):
        staff(MANAGER)
        client.login(username="manager@example.com", password="SettingsLocal!2026")
        return client

    def test_stored_secret_does_not_appear_in_the_page(self, manager_client):
        obj = PaymentSettings.load()
        obj.secret_key = TEST_SECRET
        obj.webhook_secret = WEBHOOK
        obj.save()

        body = manager_client.get(reverse("dashboard:payment_settings")).content.decode()
        assert TEST_SECRET not in body
        assert WEBHOOK not in body

    def test_masked_form_is_shown_instead(self, manager_client):
        obj = PaymentSettings.load()
        obj.secret_key = TEST_SECRET
        obj.save()
        body = manager_client.get(reverse("dashboard:payment_settings")).content.decode()
        assert "••••" in body
        assert TEST_SECRET[-4:] in body


@pytest.mark.django_db
class TestSettingsForm:
    @pytest.fixture
    def manager_client(self, client, roles):
        staff(MANAGER)
        client.login(username="manager@example.com", password="SettingsLocal!2026")
        return client

    def post(self, client, **overrides):
        data = {
            "mode": "test",
            "publishable_key": TEST_PUBLISHABLE,
            "secret_key": TEST_SECRET,
            "webhook_secret": WEBHOOK,
            "statement_descriptor": "AUSTIN LIMO",
            "is_enabled": "on",
        }
        data.update(overrides)
        return client.post(reverse("dashboard:payment_settings"), data, follow=True)

    def test_saving_encrypts_and_records_who(self, manager_client):
        self.post(manager_client)
        obj = PaymentSettings.load()
        assert obj.secret_key == TEST_SECRET
        assert obj.webhook_secret == WEBHOOK
        assert obj.updated_by.email == "manager@example.com"
        assert obj.is_configured

    def test_blank_secret_keeps_the_existing_one(self, manager_client):
        self.post(manager_client)
        self.post(manager_client, secret_key="", webhook_secret="")
        obj = PaymentSettings.load()
        assert obj.secret_key == TEST_SECRET
        assert obj.webhook_secret == WEBHOOK

    def test_live_mode_with_a_test_key_is_refused(self, manager_client):
        """Silent failure in production: the checkout works and no money moves."""
        response = self.post(manager_client, mode="live",
                             publishable_key=LIVE_PUBLISHABLE, secret_key=TEST_SECRET)
        assert PaymentSettings.load().mode == "test"
        assert b"test key" in response.content.lower()

    def test_test_mode_with_a_live_key_is_refused(self, manager_client):
        """The reverse: testing would charge real cards."""
        response = self.post(manager_client, mode="test",
                             publishable_key=TEST_PUBLISHABLE, secret_key=LIVE_SECRET)
        assert not PaymentSettings.load().has_secret_key
        assert b"live" in response.content.lower()

    def test_a_secret_key_pasted_into_the_publishable_field_is_refused(self, manager_client):
        response = self.post(manager_client, publishable_key=TEST_SECRET)
        assert b"secret key and must not go here" in response.content
        assert not PaymentSettings.load().publishable_key

    def test_enabling_without_keys_is_refused(self, manager_client):
        response = self.post(manager_client, publishable_key="", secret_key="")
        assert not PaymentSettings.load().is_enabled
        assert b"required before enabling" in response.content

    def test_malformed_webhook_secret_is_refused(self, manager_client):
        self.post(manager_client, webhook_secret="not-a-webhook-secret")
        assert not PaymentSettings.load().has_webhook_secret

    def test_can_disable_without_losing_the_keys(self, manager_client):
        self.post(manager_client)
        manager_client.post(reverse("dashboard:payment_settings"), {
            "mode": "test", "publishable_key": TEST_PUBLISHABLE,
            "secret_key": "", "webhook_secret": "", "statement_descriptor": "",
        }, follow=True)
        obj = PaymentSettings.load()
        assert not obj.is_enabled
        assert obj.secret_key == TEST_SECRET  # retained
