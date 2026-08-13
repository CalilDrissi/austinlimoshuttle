"""
Tests for the user model.

The emphasis is on the two legacy failure modes: case-sensitive email identity
(the old system compared with BINARY, so Jo@x.com and jo@x.com were different
accounts) and passwords that must never be storable in a recoverable form.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

User = get_user_model()


@pytest.mark.django_db
class TestUserCreation:
    def test_create_user_normalises_email_to_lowercase(self):
        user = User.objects.create_user(email="John.Smith@Example.COM")
        assert user.email == "john.smith@example.com"

    def test_direct_construction_also_normalises(self):
        """Imports and factories bypass the manager, so save() must normalise too."""
        user = User(email="  Mixed@Case.Com  ")
        user.save()
        assert user.email == "mixed@case.com"

    def test_email_is_unique_case_insensitively_after_normalisation(self):
        User.objects.create_user(email="dup@example.com")
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="DUP@EXAMPLE.COM")

    def test_email_is_required(self):
        with pytest.raises(ValueError, match="email address is required"):
            User.objects.create_user(email="")

    def test_superuser_flags(self):
        admin = User.objects.create_superuser(email="boss@example.com", password="x9dK2mQ7pL")
        assert admin.is_staff and admin.is_superuser

    def test_superuser_rejects_contradictory_flags(self):
        with pytest.raises(ValueError):
            User.objects.create_superuser(
                email="bad@example.com", password="x9dK2mQ7pL", is_staff=False
            )


@pytest.mark.django_db
class TestPasswordHandling:
    def test_password_is_hashed_never_stored_plaintext(self):
        raw = "correct-horse-battery"
        user = User.objects.create_user(email="hash@example.com", password=raw)
        assert user.password != raw
        assert user.check_password(raw)

    def test_imported_accounts_have_no_usable_password(self):
        """
        Legacy passwords were plaintext and are deliberately discarded. Imported
        accounts must be unable to authenticate until the customer resets.
        """
        user = User.objects.create_user(email="legacy@example.com", password=None)
        assert not user.has_usable_password()
        assert not user.check_password("")

    def test_model_has_no_field_that_could_hold_a_recoverable_password(self):
        field_names = {f.name for f in User._meta.get_fields()}
        for forbidden in ("plain_password", "password_plain", "legacy_password"):
            assert forbidden not in field_names


@pytest.mark.django_db
class TestUserDisplay:
    def test_full_name(self):
        user = User.objects.create_user(
            email="jane@example.com", first_name="Jane", last_name="Doe"
        )
        assert user.get_full_name() == "Jane Doe"
        assert str(user) == "Jane Doe <jane@example.com>"

    def test_str_falls_back_to_email_when_unnamed(self):
        user = User.objects.create_user(email="anon@example.com")
        assert str(user) == "anon@example.com"

    def test_short_name_falls_back_to_email(self):
        user = User.objects.create_user(email="anon2@example.com")
        assert user.get_short_name() == "anon2@example.com"


@pytest.mark.django_db
class TestLegacyTraceability:
    def test_legacy_member_id_is_unique(self):
        User.objects.create_user(email="a@example.com", legacy_member_id=42)
        with pytest.raises(IntegrityError):
            User.objects.create_user(email="b@example.com", legacy_member_id=42)

    def test_legacy_member_id_is_optional(self):
        user = User.objects.create_user(email="new@example.com")
        assert user.legacy_member_id is None
