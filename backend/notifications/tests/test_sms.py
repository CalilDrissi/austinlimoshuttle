"""SMS gateway, confirmation hook, and the reminder command."""

from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from django.core.management import call_command
from django.utils import timezone

from bookings.models import Booking
from fleet.models import Vehicle
from notifications import sms
from notifications.models import SmsLog, SmsSettings
from notifications.phone import to_e164


@pytest.mark.parametrize("raw,expected", [
    ("(512) 555-0142", "+15125550142"),
    ("512-555-0142", "+15125550142"),
    ("5125550142", "+15125550142"),
    ("1 512 555 0142", "+15125550142"),
    ("+15125550142", "+15125550142"),
    ("", None),
    ("nope", None),
])
def test_to_e164(raw, expected):
    assert to_e164(raw) == expected


@pytest.fixture
def vehicle(db):
    return Vehicle.objects.create(name="Business Class", slug="bc", hourly_rate=85)


@pytest.fixture
def sms_on(db):
    s = SmsSettings.load()
    s.is_enabled = True
    s.account_sid = "AC_test"
    s.auth_token = "secret-token"
    s.from_number = "+15125550100"
    s.save()
    return s


def make_booking(vehicle, *, hours_ahead=12, phone="+15125550142",
                 status=Booking.Status.CONFIRMED):
    return Booking.objects.create(
        vehicle=vehicle, pickup_address="ABIA", dropoff_address="Downtown",
        pickup_at=timezone.now() + timedelta(hours=hours_ahead),
        total=Decimal("95.00"), status=status, guest_phone=phone,
    )


def ok_response():
    return Mock(status_code=201, json=Mock(return_value={"sid": "SM123"}))


@pytest.mark.django_db
class TestSmsGateway:
    def test_noop_when_not_configured(self, vehicle):
        with patch("notifications.sms.requests.post") as post:
            assert sms.send_booking_confirmation(make_booking(vehicle)) is False
            post.assert_not_called()
        assert not SmsLog.objects.exists()

    def test_confirmation_sends_and_logs(self, vehicle, sms_on):
        with patch("notifications.sms.requests.post", return_value=ok_response()) as post:
            assert sms.send_booking_confirmation(make_booking(vehicle)) is True
            post.assert_called_once()
            # amount/price are never trusted from the client -- here just check wiring
            assert post.call_args.kwargs["data"]["To"] == "+15125550142"
        log = SmsLog.objects.get()
        assert log.succeeded and log.kind == SmsLog.Kind.CONFIRMATION and log.provider_sid == "SM123"

    def test_confirmation_respects_toggle(self, vehicle, sms_on):
        sms_on.confirmation_enabled = False
        sms_on.save()
        with patch("notifications.sms.requests.post") as post:
            assert sms.send_booking_confirmation(make_booking(vehicle)) is False
            post.assert_not_called()

    def test_bad_number_is_logged_not_sent(self, vehicle, sms_on):
        with patch("notifications.sms.requests.post") as post:
            assert sms.send_booking_confirmation(make_booking(vehicle, phone="xx")) is False
            post.assert_not_called()
        assert SmsLog.objects.filter(succeeded=False, error__icontains="phone").exists()


@pytest.mark.django_db
class TestReminderCommand:
    def _run(self):
        out = StringIO()
        call_command("send_booking_reminders", stdout=out)
        return out.getvalue()

    def test_sends_once_and_dedupes(self, vehicle, sms_on):
        make_booking(vehicle, hours_ahead=12)  # within default 24h window
        with patch("notifications.sms.requests.post", return_value=ok_response()) as post:
            self._run()
            assert post.call_count == 1
            # Second run must not double-text.
            self._run()
            assert post.call_count == 1
        assert SmsLog.objects.filter(kind=SmsLog.Kind.REMINDER, succeeded=True).count() == 1

    def test_skips_outside_window(self, vehicle, sms_on):
        make_booking(vehicle, hours_ahead=72)  # beyond 24h
        with patch("notifications.sms.requests.post") as post:
            self._run()
            post.assert_not_called()

    def test_off_when_disabled(self, vehicle, sms_on):
        sms_on.reminder_enabled = False
        sms_on.save()
        make_booking(vehicle, hours_ahead=12)
        with patch("notifications.sms.requests.post") as post:
            self._run()
            post.assert_not_called()
