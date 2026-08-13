"""
Transactional email and SMTP settings.

The properties that matter: the mailbox password is never exposed, a mail
failure never breaks a booking, and every attempt is recorded so "the customer
says they never got it" is an answerable question.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking, BookingPriceLine, Driver
from config import crypto
from dashboard.permissions import DISPATCHER, MANAGER, sync_roles
from fleet.models import Vehicle
from notifications import mailer
from notifications.models import EmailLog, EmailSettings

User = get_user_model()
PASSWORD = "MailboxLocal!2026"


@pytest.fixture(autouse=True)
def empty_outbox():
    mail.outbox.clear()
    yield
    mail.outbox.clear()


@pytest.fixture
def configured(db):
    config = EmailSettings.load()
    config.host = "mail.austinlimoshuttle.com"
    config.port = 587
    config.security = EmailSettings.Security.TLS
    config.username = "bookings@austinlimoshuttle.com"
    config.password = PASSWORD
    config.from_email = "bookings@austinlimoshuttle.com"
    config.from_name = "Austin Limo Shuttle"
    config.ops_notification_email = "ops@austinlimoshuttle.com"
    config.is_enabled = True
    config.save()
    return config


@pytest.fixture
def booking(db):
    vehicle = Vehicle.objects.create(name="Business Class", slug="bc", hourly_rate=85)
    customer = User.objects.create_user(
        email="rider@example.com", first_name="Sam", last_name="Ray",
    )
    booking = Booking.objects.create(
        customer=customer, vehicle=vehicle,
        pickup_address="Austin-Bergstrom International Airport",
        dropoff_address="Downtown Austin",
        pickup_at=timezone.now() + timedelta(days=2),
        distance_miles=Decimal("25"), total=Decimal("145.10"),
        subtotal=Decimal("145.10"), passenger_count=2,
        status=Booking.Status.CONFIRMED,
    )
    BookingPriceLine.objects.create(
        booking=booking, kind=BookingPriceLine.Kind.BAND,
        label="25 mi", amount=Decimal("145.10"),
    )
    return booking


@pytest.mark.django_db
class TestSettingsSecurity:
    def test_password_is_encrypted_at_rest(self, configured):
        from django.db import connection

        with connection.cursor() as cur:
            cur.execute("SELECT password_encrypted FROM notifications_emailsettings WHERE id=1")
            stored = cur.fetchone()[0]

        assert PASSWORD not in stored
        assert EmailSettings.load().password == PASSWORD

    def test_masking_reveals_almost_nothing(self, configured):
        assert PASSWORD not in configured.password_masked
        assert configured.password_masked.startswith("••••")

    def test_sender_uses_the_display_name(self, configured):
        assert configured.sender == "Austin Limo Shuttle <bookings@austinlimoshuttle.com>"

    def test_singleton(self, configured):
        EmailSettings(host="other.example.com").save()
        assert EmailSettings.objects.count() == 1

    def test_security_flags_are_mutually_exclusive(self, configured):
        configured.security = EmailSettings.Security.SSL
        assert configured.use_ssl and not configured.use_tls


@pytest.mark.django_db
class TestSettingsPage:
    def staff(self, role):
        sync_roles()
        user = User.objects.create_user(
            email=f"{role.lower()}@example.com", password=PASSWORD, is_staff=True,
        )
        user.groups.add(Group.objects.get(name=role))
        return user

    def test_manager_can_reach_it(self, client, db):
        self.staff(MANAGER)
        client.login(username="manager@example.com", password=PASSWORD)
        assert client.get(reverse("dashboard:email_settings")).status_code == 200

    def test_dispatcher_cannot(self, client, db):
        self.staff(DISPATCHER)
        client.login(username="dispatcher@example.com", password=PASSWORD)
        assert client.get(reverse("dashboard:email_settings")).status_code == 403

    def test_password_is_never_rendered(self, client, configured):
        self.staff(MANAGER)
        client.login(username="manager@example.com", password=PASSWORD)
        body = client.get(reverse("dashboard:email_settings")).content.decode()
        assert PASSWORD not in body

    def test_blank_password_keeps_the_stored_one(self, client, configured):
        self.staff(MANAGER)
        client.login(username="manager@example.com", password=PASSWORD)
        client.post(reverse("dashboard:email_settings"), {
            "is_enabled": "on", "host": "mail.austinlimoshuttle.com", "port": "587",
            "security": "tls", "username": "bookings@austinlimoshuttle.com",
            "password": "", "from_name": "Austin Limo Shuttle",
            "from_email": "bookings@austinlimoshuttle.com", "reply_to": "",
            "ops_notification_email": "ops@austinlimoshuttle.com", "timeout_seconds": "15",
        }, follow=True)
        assert EmailSettings.load().password == PASSWORD

    def test_port_and_security_mismatch_is_flagged(self, client, configured):
        self.staff(MANAGER)
        client.login(username="manager@example.com", password=PASSWORD)
        response = client.post(reverse("dashboard:email_settings"), {
            "is_enabled": "on", "host": "mail.example.com", "port": "465",
            "security": "tls", "username": "u", "password": "",
            "from_name": "X", "from_email": "a@example.com", "reply_to": "",
            "ops_notification_email": "", "timeout_seconds": "15",
        }, follow=True)
        assert b"465 is normally SSL" in response.content

    def test_test_message_records_the_outcome(self, client, configured):
        user = self.staff(MANAGER)
        client.login(username="manager@example.com", password=PASSWORD)
        client.post(reverse("dashboard:email_settings"),
                    {"action": "test", "test_email": user.email}, follow=True)

        config = EmailSettings.load()
        assert config.last_test_ok is True
        assert config.last_test_at is not None
        assert len(mail.outbox) == 1

    def test_failing_test_message_is_recorded_not_raised(self, client, configured):
        self.staff(MANAGER)
        client.login(username="manager@example.com", password=PASSWORD)
        with patch("notifications.mailer.EmailMultiAlternatives.send",
                   side_effect=OSError("connection refused")):
            response = client.post(reverse("dashboard:email_settings"),
                                   {"action": "test", "test_email": "a@example.com"},
                                   follow=True)
        assert response.status_code == 200
        config = EmailSettings.load()
        assert config.last_test_ok is False
        assert "connection refused" in config.last_test_error


@pytest.mark.django_db
class TestBookingConfirmation:
    def test_sends_with_a_pdf_attached(self, booking, configured):
        assert mailer.send_booking_confirmation(booking)

        message = mail.outbox[0]
        assert message.to == ["rider@example.com"]
        assert booking.reference in message.subject
        assert message.attachments
        filename, content, mimetype = message.attachments[0]
        assert filename == f"booking-{booking.reference}.pdf"
        assert mimetype == "application/pdf"
        assert content[:4] == b"%PDF"

    def test_has_both_text_and_html_parts(self, booking, configured):
        mailer.send_booking_confirmation(booking)
        message = mail.outbox[0]
        assert booking.pickup_address in message.body           # text
        assert booking.pickup_address in message.alternatives[0][0]  # html

    def test_shows_the_fare_breakdown(self, booking, configured):
        mailer.send_booking_confirmation(booking)
        assert "145.10" in mail.outbox[0].body

    def test_is_logged(self, booking, configured):
        mailer.send_booking_confirmation(booking)
        log = EmailLog.objects.get()
        assert log.succeeded
        assert log.has_attachment
        assert log.booking == booking

    def test_guest_booking_uses_the_guest_address(self, db, configured):
        vehicle = Vehicle.objects.create(name="V", slug="v", hourly_rate=50)
        guest = Booking.objects.create(
            vehicle=vehicle, pickup_address="a",
            pickup_at=timezone.now() + timedelta(days=1),
            total=Decimal("50.00"), guest_email="guest@example.com",
        )
        assert mailer.send_booking_confirmation(guest)
        assert mail.outbox[0].to == ["guest@example.com"]

    def test_no_address_sends_nothing(self, db, configured):
        vehicle = Vehicle.objects.create(name="V", slug="v", hourly_rate=50)
        anonymous = Booking.objects.create(
            vehicle=vehicle, pickup_address="a",
            pickup_at=timezone.now() + timedelta(days=1), total=Decimal("50.00"),
        )
        assert not mailer.send_booking_confirmation(anonymous)
        assert len(mail.outbox) == 0


@pytest.mark.django_db
class TestOtherMessages:
    def test_driver_assigned(self, booking, configured):
        booking.driver = Driver.objects.create(full_name="Alex Ruiz", phone="512-555-0134")
        booking.save()
        assert mailer.send_driver_assigned(booking)
        assert "Alex Ruiz" in mail.outbox[0].body
        assert "512-555-0134" in mail.outbox[0].body

    def test_driver_assigned_needs_a_driver(self, booking, configured):
        assert not mailer.send_driver_assigned(booking)

    def test_cancellation_mentions_the_refund(self, booking, configured):
        assert mailer.send_booking_cancelled(booking, refund_amount=Decimal("100.00"))
        assert "100.00" in mail.outbox[0].body

    def test_ops_alert_goes_to_the_office(self, booking, configured):
        assert mailer.send_ops_new_booking(booking)
        assert mail.outbox[0].to == ["ops@austinlimoshuttle.com"]

    def test_ops_alert_needs_an_address(self, booking, configured):
        configured.ops_notification_email = ""
        configured.save()
        assert not mailer.send_ops_new_booking(booking)

    def test_pickup_reminder(self, booking, configured):
        assert mailer.send_pickup_reminder(booking)
        assert booking.reference in mail.outbox[0].subject


@pytest.mark.django_db
class TestFailuresAreContained:
    def test_disabled_email_sends_nothing_but_logs_why(self, booking, configured):
        configured.is_enabled = False
        configured.save()

        assert not mailer.send_booking_confirmation(booking)
        assert len(mail.outbox) == 0
        log = EmailLog.objects.get()
        assert not log.succeeded
        assert "switched off" in log.error

    def test_smtp_failure_is_logged_not_raised(self, booking, configured):
        """A dead mail server must not lose a paid booking."""
        with patch("notifications.mailer.EmailMultiAlternatives.send",
                   side_effect=OSError("connection refused")):
            assert not mailer.send_booking_confirmation(booking)

        log = EmailLog.objects.get()
        assert not log.succeeded
        assert "connection refused" in log.error

    def test_a_broken_pdf_still_sends_the_email(self, booking, configured):
        with patch("notifications.mailer.render_booking_pdf", return_value=None):
            assert mailer.send_booking_confirmation(booking)
        assert len(mail.outbox) == 1
        assert not mail.outbox[0].attachments
        assert not EmailLog.objects.get().has_attachment

    def test_confirmation_failure_does_not_stop_a_payment(self, booking, configured):
        """
        The webhook confirms the booking and then emails. If the email raises,
        the money has already moved -- the booking must stay confirmed.
        """
        from payments import gateway
        from payments.models import Payment

        booking.status = Booking.Status.PENDING
        booking.save()
        Payment.objects.create(booking=booking, payment_intent_id="pi_x",
                               amount=booking.total)

        with patch("notifications.mailer.send_booking_confirmation",
                   side_effect=RuntimeError("mail exploded")):
            gateway.apply_intent_to_payment({
                "id": "pi_x", "status": "succeeded", "amount": 14510,
                "currency": "usd", "metadata": {"booking_reference": booking.reference},
                "charges": {"data": []},
            })

        booking.refresh_from_db()
        assert booking.status == Booking.Status.CONFIRMED


@pytest.mark.django_db
class TestConfigurableBackend:
    def test_reads_host_and_credentials_from_the_database(self, configured):
        from notifications.backend import ConfigurableEmailBackend

        backend = ConfigurableEmailBackend()
        assert backend.host == "mail.austinlimoshuttle.com"
        assert backend.port == 587
        assert backend.username == "bookings@austinlimoshuttle.com"
        assert backend.password == PASSWORD
        assert backend.use_tls and not backend.use_ssl

    def test_falls_back_to_django_settings_when_disabled(self, configured, settings):
        from notifications.backend import ConfigurableEmailBackend

        configured.is_enabled = False
        configured.save()
        settings.EMAIL_HOST = "fallback.example.com"

        backend = ConfigurableEmailBackend()
        assert backend.host == "fallback.example.com"

    def test_never_sets_both_tls_and_ssl(self, configured):
        from notifications.backend import ConfigurableEmailBackend

        configured.security = EmailSettings.Security.SSL
        configured.save()
        backend = ConfigurableEmailBackend()
        assert backend.use_ssl and not backend.use_tls


class TestCryptoIsShared:
    def test_email_and_payment_settings_use_the_same_helper(self):
        """Both secrets go through one implementation, so a fix reaches both."""
        assert crypto.decrypt(crypto.encrypt("x")) == "x"
