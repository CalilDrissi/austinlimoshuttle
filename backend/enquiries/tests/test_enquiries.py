"""Enquiry model behaviour."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from enquiries.models import ContactMessage

User = get_user_model()


def make(**kwargs):
    defaults = {
        "name": "Jo Rivera", "email": "jo@example.com", "message": "Do you serve ATX?",
        "created_at": timezone.now(),
    }
    return ContactMessage.objects.create(**{**defaults, **kwargs})


@pytest.mark.django_db
class TestContactMessage:
    def test_defaults_to_general_and_unread(self):
        msg = make()
        assert msg.nature == ContactMessage.Nature.GENERAL
        assert msg.is_read is False
        assert msg.is_answered is False

    def test_three_legacy_tables_share_one_model(self):
        make(nature=ContactMessage.Nature.GENERAL, email="a@example.com")
        make(nature=ContactMessage.Nature.SERVICE, email="b@example.com")
        make(nature=ContactMessage.Nature.CORPORATE, email="c@example.com",
             company_name="Acme")
        assert ContactMessage.objects.count() == 3
        assert ContactMessage.objects.filter(
            nature=ContactMessage.Nature.CORPORATE,
        ).first().company_name == "Acme"

    def test_marking_replied(self):
        staff = User.objects.create_user(email="ops@example.com", is_staff=True)
        msg = make()
        msg.reply_body = "Yes, we do."
        msg.replied_at = timezone.now()
        msg.replied_by = staff
        msg.save()
        assert msg.is_answered

    def test_legacy_rows_cannot_be_imported_twice(self):
        make(legacy_table="limousin_contact_us", legacy_row_id=7)
        with pytest.raises(IntegrityError):
            make(legacy_table="limousin_contact_us", legacy_row_id=7,
                 email="other@example.com")

    def test_new_enquiries_are_not_constrained_by_the_legacy_key(self):
        """The uniqueness constraint applies only to imported rows."""
        make(email="x@example.com")
        make(email="y@example.com")
        assert ContactMessage.objects.filter(legacy_row_id__isnull=True).count() == 2

    def test_ordering_is_newest_first(self):
        from datetime import timedelta

        older = make(email="old@example.com",
                     created_at=timezone.now() - timedelta(days=5))
        newer = make(email="new@example.com", created_at=timezone.now())
        assert list(ContactMessage.objects.all()) == [newer, older]
