"""
Housekeeping for tables that grow without bound.

Run weekly from cron. Nothing here touches a booking, a payment or a customer --
those are business records and are kept indefinitely.

What it does prune:

  * `WebhookEvent`   -- replay-protection ids. Stripe never retries an event for
                        months, so rows older than the retention window can go.
  * `EmailLog`       -- delivery history. Useful for answering "did they get it?"
                        for a while, not for ever.

And one operational tidy-up: bookings left `pending` long after their pickup
time. Those are abandoned checkouts -- a quote was taken, a booking row created,
and the customer never paid. Left alone they clutter the dispatch board for ever
and inflate the "awaiting payment" counter.
"""

from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from bookings.models import Booking, BookingStatusChange
from notifications.models import EmailLog
from payments.models import Payment, WebhookEvent


class Command(BaseCommand):
    help = "Prune webhook ids and email logs; close abandoned unpaid bookings."

    def add_arguments(self, parser):
        parser.add_argument("--webhook-days", type=int, default=90)
        parser.add_argument("--email-log-days", type=int, default=180)
        parser.add_argument(
            "--abandon-after-hours", type=int, default=48,
            help="Cancel bookings still unpaid this long after their pickup time.",
        )
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        now = timezone.now()

        webhook_cutoff = now - timedelta(days=options["webhook_days"])
        stale_webhooks = WebhookEvent.objects.filter(received_at__lt=webhook_cutoff)

        email_cutoff = now - timedelta(days=options["email_log_days"])
        stale_logs = EmailLog.objects.filter(sent_at__lt=email_cutoff)

        abandoned_cutoff = now - timedelta(hours=options["abandon_after_hours"])
        abandoned = Booking.objects.filter(
            status=Booking.Status.PENDING, pickup_at__lt=abandoned_cutoff,
        ).exclude(
            # Never touch anything that has money against it, whatever its status.
            payments__status=Payment.Status.SUCCEEDED,
        )

        self.stdout.write(f"webhook ids older than {options['webhook_days']}d : "
                          f"{stale_webhooks.count()}")
        self.stdout.write(f"email logs older than {options['email_log_days']}d  : "
                          f"{stale_logs.count()}")
        self.stdout.write(f"abandoned unpaid bookings          : {abandoned.count()}")

        if dry_run:
            for booking in abandoned[:20]:
                self.stdout.write(
                    f"  would abandon {booking.reference} "
                    f"(pickup {booking.pickup_at:%d %b %Y %H:%M})"
                )
            self.stdout.write(self.style.WARNING("dry run — nothing changed"))
            return

        webhook_count = stale_webhooks.count()
        stale_webhooks.delete()

        log_count = stale_logs.count()
        stale_logs.delete()

        abandoned_count = 0
        for booking in list(abandoned):
            BookingStatusChange.objects.create(
                booking=booking,
                from_status=booking.status,
                to_status=Booking.Status.CANCELLED,
                note="Automatically closed: never paid, pickup time passed.",
            )
            booking.status = Booking.Status.CANCELLED
            booking.cancelled_at = now
            booking.cancellation_reason = "Payment was never completed."
            booking.save(update_fields=[
                "status", "cancelled_at", "cancellation_reason", "updated_at",
            ])
            abandoned_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"removed {webhook_count} webhook ids, {log_count} email logs; "
            f"closed {abandoned_count} abandoned bookings"
        ))
