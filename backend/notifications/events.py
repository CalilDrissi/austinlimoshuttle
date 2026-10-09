"""
One place that fires every notification for a booking event, so email and SMS
stay in lock-step no matter which path confirmed the booking (Stripe webhook,
cash, or a manual back-office booking).

Each channel is independent and self-contained: a failure in one never raises
and never stops the others -- a notification outage must not break a booking.
"""

import logging

logger = logging.getLogger(__name__)


def _safe(fn, booking):
    try:
        fn(booking)
    except Exception:
        logger.exception("Notification %s failed for %s",
                         getattr(fn, "__name__", fn), booking.reference)


def booking_confirmed(booking, *, notify_ops: bool = True) -> None:
    """
    Customer confirmation by email AND SMS, plus the office alert.

    `notify_ops=False` for manual back-office bookings -- the staff member who
    just created it doesn't need a "new booking" alert about their own entry.
    """
    from . import mailer, sms

    _safe(mailer.send_booking_confirmation, booking)
    _safe(sms.send_booking_confirmation, booking)
    if notify_ops:
        _safe(mailer.send_ops_new_booking, booking)
