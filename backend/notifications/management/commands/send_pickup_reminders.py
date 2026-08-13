"""
Email customers whose pickup is coming up.

Invoked by cron -- shared hosting has no worker process, so a scheduled
management command is the only mechanism available.

Deduplication uses `EmailLog`: a booking that already has a successful
PICKUP_REMINDER row is skipped. That means the command is safe to run more often
than the window, and safe to re-run after a partial failure. Cron will
eventually double-fire; this is what stops customers getting two reminders.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.models import Booking
from notifications import mailer
from notifications.models import EmailLog


class Command(BaseCommand):
    help = "Send pickup reminders for bookings within the reminder window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours", type=int, default=24,
            help="Send to bookings with a pickup within this many hours (default 24).",
        )
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report who would be emailed without sending.",
        )

    def handle(self, *args, **options):
        hours = options["hours"]
        now = timezone.now()
        horizon = now + timedelta(hours=hours)

        # Only future pickups: a booking whose time has passed does not need
        # telling about it, and a wide window after a cron outage would
        # otherwise mail people about yesterday.
        candidates = (
            Booking.objects.for_dispatch()
            .filter(
                pickup_at__gte=now,
                pickup_at__lte=horizon,
                status__in=[Booking.Status.CONFIRMED, Booking.Status.PENDING],
            )
            .order_by("pickup_at")
        )

        already_sent = set(
            EmailLog.objects.filter(
                kind=EmailLog.Kind.PICKUP_REMINDER, succeeded=True,
                booking__in=candidates,
            ).values_list("booking_id", flat=True)
        )

        due = [b for b in candidates if b.pk not in already_sent and b.contact_email]
        skipped_no_email = sum(
            1 for b in candidates if b.pk not in already_sent and not b.contact_email
        )

        self.stdout.write(
            f"within {hours}h: {candidates.count()} · "
            f"already reminded: {len(already_sent)} · "
            f"no contact address: {skipped_no_email} · "
            f"to send: {len(due)}"
        )

        if options["dry_run"]:
            for booking in due[:25]:
                self.stdout.write(
                    f"  would remind {booking.reference} "
                    f"({booking.pickup_at:%a %d %b %H:%M}) -> {booking.contact_email}"
                )
            self.stdout.write(self.style.WARNING("dry run — nothing sent"))
            return

        sent = failed = 0
        for booking in due:
            if mailer.send_pickup_reminder(booking):
                sent += 1
            else:
                failed += 1

        self.stdout.write(self.style.SUCCESS(f"sent: {sent}"))
        if failed:
            self.stdout.write(self.style.ERROR(f"failed: {failed} (see EmailLog)"))
