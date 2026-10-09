"""
Text pickup reminders for confirmed bookings entering the reminder window.

Designed for cron (e.g. every 15 minutes). Idempotent: a booking that already
has a successful reminder in SmsLog is skipped, so running it often -- or twice
after a partial failure -- never double-texts a customer.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.models import Booking
from notifications import sms
from notifications.models import SmsLog, SmsSettings


class Command(BaseCommand):
    help = "Send SMS pickup reminders for bookings within the configured lead window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report who would be texted without sending.",
        )

    def handle(self, *args, **options):
        config = SmsSettings.load()
        if not config.is_configured or not config.reminder_enabled:
            self.stdout.write("SMS reminders are off or not configured — nothing to do.")
            return
        if not config.reminder_lead_hours:
            self.stdout.write("reminder_lead_hours is 0 — reminders disabled.")
            return

        now = timezone.now()
        horizon = now + timedelta(hours=config.reminder_lead_hours)
        candidates = (
            Booking.objects.for_dispatch()
            .filter(pickup_at__gte=now, pickup_at__lte=horizon,
                    status=Booking.Status.CONFIRMED)
            .order_by("pickup_at")
        )
        already = set(
            SmsLog.objects.filter(
                kind=SmsLog.Kind.REMINDER, succeeded=True, booking__in=candidates,
            ).values_list("booking_id", flat=True)
        )

        sent = skipped = 0
        for booking in candidates:
            if booking.id in already or not booking.contact_phone:
                skipped += 1
                continue
            if options["dry_run"]:
                self.stdout.write(
                    f"would remind {booking.reference} ({booking.contact_phone}) "
                    f"pickup {timezone.localtime(booking.pickup_at):%Y-%m-%d %H:%M}"
                )
                continue
            if sms.send_pickup_reminder(booking):
                sent += 1
            else:
                skipped += 1

        verb = "would send" if options["dry_run"] else "sent"
        self.stdout.write(f"Reminders {verb}: {sent}; skipped: {skipped}.")
