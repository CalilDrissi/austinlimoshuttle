"""
Scheduled commands.

Both run from cron, which means they will double-fire, fire late after an
outage, and occasionally fire twice at once. The tests are mostly about those
conditions rather than the happy path.
"""

from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from bookings.models import Booking
from fleet.models import Vehicle
from notifications.models import EmailLog, EmailSettings
from payments.models import Payment, WebhookEvent

User = get_user_model()


@pytest.fixture(autouse=True)
def empty_outbox():
    mail.outbox.clear()
    yield
    mail.outbox.clear()


@pytest.fixture
def email_on(db):
    config = EmailSettings.load()
    config.host = "mail.example.com"
    config.from_email = "bookings@example.com"
    config.is_enabled = True
    config.save()
    return config


@pytest.fixture
def vehicle(db):
    return Vehicle.objects.create(name="Business Class", slug="bc", hourly_rate=85)


def make_booking(vehicle, *, hours_ahead=12, status=Booking.Status.CONFIRMED,
                 email="rider@example.com", **kwargs):
    customer = None
    if email:
        customer, _ = User.objects.get_or_create(email=email)
    return Booking.objects.create(
        customer=customer, vehicle=vehicle, pickup_address="ABIA",
        dropoff_address="Downtown",
        pickup_at=timezone.now() + timedelta(hours=hours_ahead),
        total=Decimal("95.00"), status=status, **kwargs,
    )


def run(command, **kwargs):
    out = StringIO()
    call_command(command, stdout=out, **kwargs)
    return out.getvalue()


@pytest.mark.django_db
class TestPickupReminders:
    def test_sends_within_the_window(self, vehicle, email_on):
        booking = make_booking(vehicle, hours_ahead=12)
        run("send_pickup_reminders")
        assert len(mail.outbox) == 1
        assert booking.reference in mail.outbox[0].subject

    def test_ignores_bookings_beyond_the_window(self, vehicle, email_on):
        make_booking(vehicle, hours_ahead=72)
        run("send_pickup_reminders")
        assert len(mail.outbox) == 0

    def test_ignores_pickups_already_in_the_past(self, vehicle, email_on):
        """After a cron outage, a wide window must not mail about yesterday."""
        make_booking(vehicle, hours_ahead=-5)
        run("send_pickup_reminders")
        assert len(mail.outbox) == 0

    def test_ignores_cancelled_bookings(self, vehicle, email_on):
        make_booking(vehicle, hours_ahead=12, status=Booking.Status.CANCELLED)
        run("send_pickup_reminders")
        assert len(mail.outbox) == 0

    def test_running_twice_does_not_send_twice(self, vehicle, email_on):
        """Cron will double-fire. This is what stops a duplicate reminder."""
        make_booking(vehicle, hours_ahead=12)
        run("send_pickup_reminders")
        run("send_pickup_reminders")
        assert len(mail.outbox) == 1

    def test_a_failed_send_is_retried_next_run(self, vehicle, email_on):
        """Dedupe keys on *successful* sends, so a failure is not swallowed."""
        from unittest.mock import patch

        make_booking(vehicle, hours_ahead=12)
        with patch("notifications.mailer.EmailMultiAlternatives.send",
                   side_effect=OSError("smtp down")):
            run("send_pickup_reminders")
        assert len(mail.outbox) == 0

        run("send_pickup_reminders")
        assert len(mail.outbox) == 1

    def test_skips_bookings_with_no_contact_address(self, vehicle, email_on):
        make_booking(vehicle, hours_ahead=12, email=None)
        output = run("send_pickup_reminders")
        assert len(mail.outbox) == 0
        assert "no contact address: 1" in output

    def test_guest_bookings_are_reminded(self, vehicle, email_on):
        make_booking(vehicle, hours_ahead=12, email=None,
                     guest_email="guest@example.com")
        run("send_pickup_reminders")
        assert mail.outbox[0].to == ["guest@example.com"]

    def test_dry_run_sends_nothing(self, vehicle, email_on):
        make_booking(vehicle, hours_ahead=12)
        output = run("send_pickup_reminders", dry_run=True)
        assert "would remind" in output
        assert len(mail.outbox) == 0

    def test_window_is_configurable(self, vehicle, email_on):
        make_booking(vehicle, hours_ahead=40)
        run("send_pickup_reminders")
        assert len(mail.outbox) == 0
        run("send_pickup_reminders", hours=48)
        assert len(mail.outbox) == 1


@pytest.mark.django_db
class TestCleanup:
    def test_prunes_old_webhook_ids(self, db):
        old = WebhookEvent.objects.create(event_id="evt_old", event_type="x")
        WebhookEvent.objects.filter(pk=old.pk).update(
            received_at=timezone.now() - timedelta(days=200),
        )
        WebhookEvent.objects.create(event_id="evt_new", event_type="x")

        run("cleanup_stale_data")
        assert list(WebhookEvent.objects.values_list("event_id", flat=True)) == ["evt_new"]

    def test_prunes_old_email_logs(self, db):
        old = EmailLog.objects.create(kind=EmailLog.Kind.TEST, to_email="a@example.com",
                                      subject="old", succeeded=True)
        EmailLog.objects.filter(pk=old.pk).update(
            sent_at=timezone.now() - timedelta(days=400),
        )
        EmailLog.objects.create(kind=EmailLog.Kind.TEST, to_email="b@example.com",
                                subject="new", succeeded=True)

        run("cleanup_stale_data")
        assert EmailLog.objects.count() == 1

    def test_closes_bookings_never_paid(self, vehicle):
        abandoned = make_booking(vehicle, hours_ahead=-100, status=Booking.Status.PENDING)
        run("cleanup_stale_data")

        abandoned.refresh_from_db()
        assert abandoned.status == Booking.Status.CANCELLED
        assert "never completed" in abandoned.cancellation_reason

    def test_closing_is_audited(self, vehicle):
        abandoned = make_booking(vehicle, hours_ahead=-100, status=Booking.Status.PENDING)
        run("cleanup_stale_data")
        change = abandoned.status_changes.get()
        assert change.to_status == Booking.Status.CANCELLED
        assert change.changed_by is None  # automated, not a person

    def test_never_touches_a_paid_booking(self, vehicle):
        """
        Belt and braces: a booking left `pending` with a successful payment is a
        bug elsewhere, and closing it would compound the problem.
        """
        paid = make_booking(vehicle, hours_ahead=-100, status=Booking.Status.PENDING)
        Payment.objects.create(booking=paid, amount=Decimal("95.00"),
                               status=Payment.Status.SUCCEEDED)

        run("cleanup_stale_data")
        paid.refresh_from_db()
        assert paid.status == Booking.Status.PENDING

    def test_leaves_future_unpaid_bookings_alone(self, vehicle):
        pending = make_booking(vehicle, hours_ahead=48, status=Booking.Status.PENDING)
        run("cleanup_stale_data")
        pending.refresh_from_db()
        assert pending.status == Booking.Status.PENDING

    def test_never_deletes_a_booking_or_a_payment(self, vehicle):
        booking = make_booking(vehicle, hours_ahead=-100, status=Booking.Status.PENDING)
        Payment.objects.create(booking=booking, amount=Decimal("95.00"),
                               status=Payment.Status.FAILED)
        run("cleanup_stale_data")
        assert Booking.objects.filter(pk=booking.pk).exists()
        assert Payment.objects.count() == 1

    def test_dry_run_changes_nothing(self, vehicle, db):
        abandoned = make_booking(vehicle, hours_ahead=-100, status=Booking.Status.PENDING)
        old = WebhookEvent.objects.create(event_id="evt_old", event_type="x")
        WebhookEvent.objects.filter(pk=old.pk).update(
            received_at=timezone.now() - timedelta(days=200),
        )

        output = run("cleanup_stale_data", dry_run=True)
        assert "would abandon" in output
        abandoned.refresh_from_db()
        assert abandoned.status == Booking.Status.PENDING
        assert WebhookEvent.objects.count() == 1
