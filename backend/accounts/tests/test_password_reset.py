"""
Password reset.

Uses Django's built-in views, so these tests cover the wiring and our templates
rather than re-testing the framework: that the flow works end to end for a
migrated account, and that it does not disclose who is registered.

No bulk mailing exists by design -- migrated customers set a password through
the ordinary "forgot password" link whenever they next book.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.urls import reverse

User = get_user_model()


@pytest.fixture(autouse=True)
def clear_state():
    mail.outbox.clear()
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def migrated(db):
    """A migrated legacy account: exists, active, cannot sign in."""
    user = User.objects.create_user(
        email="rider@example.com", first_name="Sam", legacy_member_id=101,
    )
    user.set_unusable_password()
    user.save()
    return user


def reset_link(message) -> str:
    for line in message.body.splitlines():
        if "/reset/" in line:
            return line.strip()
    raise AssertionError("no reset link in the email")


@pytest.mark.django_db
class TestResetFlow:
    def test_full_journey_from_unusable_password_to_signed_in(self, client, migrated):
        # 1. request
        response = client.post(reverse("accounts:password_reset"),
                               {"email": "rider@example.com"})
        assert response.status_code == 302
        assert len(mail.outbox) == 1

        # 2. follow the link
        link = reset_link(mail.outbox[0])
        path = link.split("://", 1)[1].split("/", 1)[1]
        response = client.get(f"/{path}", follow=True)
        assert response.status_code == 200

        # 3. set a password
        form_url = response.redirect_chain[-1][0] if response.redirect_chain else f"/{path}"
        response = client.post(form_url, {
            "new_password1": "a-brand-new-passphrase-2026",
            "new_password2": "a-brand-new-passphrase-2026",
        }, follow=True)
        assert response.status_code == 200

        migrated.refresh_from_db()
        assert migrated.has_usable_password()
        assert client.login(username="rider@example.com",
                            password="a-brand-new-passphrase-2026")

    def test_link_cannot_be_reused(self, client, migrated):
        client.post(reverse("accounts:password_reset"), {"email": "rider@example.com"})
        link = reset_link(mail.outbox[0])
        path = "/" + link.split("://", 1)[1].split("/", 1)[1]

        first = client.get(path, follow=True)
        form_url = first.redirect_chain[-1][0]
        client.post(form_url, {"new_password1": "first-passphrase-here-2026",
                               "new_password2": "first-passphrase-here-2026"}, follow=True)

        # The same link again must not offer the form.
        second = client.get(path, follow=True)
        assert b"expired" in second.content.lower()

    def test_weak_password_is_refused(self, client, migrated):
        client.post(reverse("accounts:password_reset"), {"email": "rider@example.com"})
        path = "/" + reset_link(mail.outbox[0]).split("://", 1)[1].split("/", 1)[1]
        form_url = client.get(path, follow=True).redirect_chain[-1][0]

        client.post(form_url, {"new_password1": "12345678", "new_password2": "12345678"})
        migrated.refresh_from_db()
        assert not migrated.has_usable_password()

    def test_unknown_address_sends_nothing_but_looks_identical(self, client, migrated):
        known = client.post(reverse("accounts:password_reset"),
                            {"email": "rider@example.com"})
        mail.outbox.clear()
        unknown = client.post(reverse("accounts:password_reset"),
                              {"email": "nobody@example.com"})

        assert known.status_code == unknown.status_code == 302
        assert known["Location"] == unknown["Location"]
        assert len(mail.outbox) == 0

    def test_email_contains_a_working_absolute_link(self, client, migrated):
        client.post(reverse("accounts:password_reset"), {"email": "rider@example.com"})
        body = mail.outbox[0].body
        assert "/reset/" in body
        assert "://" in body

    def test_email_has_a_plain_text_and_html_part(self, client, migrated):
        client.post(reverse("accounts:password_reset"), {"email": "rider@example.com"})
        message = mail.outbox[0]
        assert message.body                      # text/plain
        assert message.alternatives              # text/html
        assert "Set your password" in message.alternatives[0][0]


@pytest.mark.django_db
class TestResetApiEndpoint:
    def test_sends_a_reset_email(self, client, migrated):
        response = client.post(reverse("api:password_reset"),
                               {"email": "rider@example.com"},
                               content_type="application/json")
        assert response.status_code == 202
        assert len(mail.outbox) == 1

    def test_unknown_address_gets_the_same_answer(self, client, migrated):
        known = client.post(reverse("api:password_reset"),
                            {"email": "rider@example.com"},
                            content_type="application/json")
        unknown = client.post(reverse("api:password_reset"),
                              {"email": "nobody@example.com"},
                              content_type="application/json")
        assert known.status_code == unknown.status_code == 202
        assert known.json() == unknown.json()

    def test_malformed_address_does_not_error(self, client):
        response = client.post(reverse("api:password_reset"), {"email": "not-an-email"},
                               content_type="application/json")
        assert response.status_code == 202
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class TestMigratedAccountsCanResetAtAll:
    """
    Django's stock PasswordResetForm filters out accounts with an unusable
    password. Every migrated customer has one by design, so under the default
    form none of the 1,251 could ever recover their account -- "forgot password"
    would silently send nothing, for ever.
    """

    def test_stock_django_form_would_exclude_them(self, migrated):
        from django.contrib.auth.forms import PasswordResetForm

        stock = PasswordResetForm(data={"email": "rider@example.com"})
        assert stock.is_valid()
        assert list(stock.get_users("rider@example.com")) == []

    def test_our_form_includes_them(self, migrated):
        from accounts.forms import MigrationPasswordResetForm

        form = MigrationPasswordResetForm(data={"email": "rider@example.com"})
        assert form.is_valid()
        assert [u.pk for u in form.get_users("rider@example.com")] == [migrated.pk]

    def test_inactive_accounts_are_still_excluded(self, migrated):
        from accounts.forms import MigrationPasswordResetForm

        migrated.is_active = False
        migrated.save()
        form = MigrationPasswordResetForm(data={"email": "rider@example.com"})
        assert form.is_valid()
        assert list(form.get_users("rider@example.com")) == []
