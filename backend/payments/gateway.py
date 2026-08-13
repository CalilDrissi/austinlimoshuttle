"""
Stripe gateway.

Card details never pass through here. The browser sends them straight to Stripe
Elements; we handle a PaymentIntent and, afterwards, a brand and a last-4 that
Stripe gives back for display. That is what takes this application out of PCI
scope, and it is why the legacy failure -- 3,416 card numbers in the database --
cannot recur regardless of what anyone writes later.

Credentials come from `PaymentSettings`, managed in the dashboard and encrypted
at rest. They are read per call rather than cached at import, so changing them
in the settings page takes effect immediately.
"""

from __future__ import annotations

import logging
from decimal import Decimal

import stripe
from django.utils import timezone

from bookings.models import Booking, BookingStatusChange

from .models import Payment, PaymentSettings, Refund

logger = logging.getLogger(__name__)

CENTS = Decimal("100")

# Stripe status -> our status. Anything unmapped is recorded verbatim so an
# unexpected value is visible rather than silently coerced to "succeeded".
STATUS_MAP = {
    "requires_payment_method": Payment.Status.REQUIRES_PAYMENT_METHOD,
    "requires_confirmation": Payment.Status.REQUIRES_PAYMENT_METHOD,
    "requires_action": Payment.Status.REQUIRES_ACTION,
    "processing": Payment.Status.PROCESSING,
    "succeeded": Payment.Status.SUCCEEDED,
    "canceled": Payment.Status.CANCELLED,
}


class PaymentConfigurationError(Exception):
    """Stripe is not configured, or is misconfigured."""


class PaymentGatewayError(Exception):
    """Stripe rejected the request or could not be reached."""


def _settings() -> PaymentSettings:
    config = PaymentSettings.load()

    if not config.is_enabled:
        raise PaymentConfigurationError(
            "Card payments are switched off. A manager can enable them in "
            "Dashboard → Settings."
        )
    secret = config.secret_key
    if not secret:
        raise PaymentConfigurationError(
            "No Stripe secret key is configured. Add one in Dashboard → Settings."
        )
    if not config.key_mode_matches:
        # Live mode with test keys takes no money while reporting success.
        raise PaymentConfigurationError(
            f"The stored Stripe key does not match {config.get_mode_display()}. "
            "Correct it in Dashboard → Settings before taking payments."
        )
    return config


def _client(config: PaymentSettings) -> stripe.StripeClient:
    return stripe.StripeClient(api_key=config.secret_key)


def to_cents(amount: Decimal) -> int:
    """Stripe works in the smallest currency unit."""
    return int((Decimal(amount) * CENTS).quantize(Decimal("1")))


def publishable_key() -> str:
    """The key the browser needs. Safe to expose -- that is its purpose."""
    config = PaymentSettings.load()
    return config.publishable_key if config.is_enabled else ""


def create_payment_intent(booking, *, idempotency_suffix: str = "") -> Payment:
    """
    Create (or reuse) a PaymentIntent for a booking.

    The amount comes from `booking.total`, which the pricing engine computed
    server-side. Nothing a client sent is used here.
    """
    config = _settings()

    if booking.total <= 0:
        raise PaymentGatewayError("This booking has no amount to charge.")

    # Reuse a live intent rather than stacking up abandoned ones on retries.
    existing = booking.payments.filter(
        provider=Payment.Provider.STRIPE,
        status__in=[
            Payment.Status.REQUIRES_PAYMENT_METHOD,
            Payment.Status.REQUIRES_ACTION,
            Payment.Status.PROCESSING,
        ],
    ).first()
    if existing and existing.amount == booking.total:
        return existing

    client = _client(config)
    # A stable key means a retried request returns the same intent instead of
    # charging twice.
    idempotency_key = f"booking-{booking.reference}-{booking.total}{idempotency_suffix}"

    try:
        intent = client.payment_intents.create(
            params={
                "amount": to_cents(booking.total),
                "currency": booking.currency.lower(),
                "automatic_payment_methods": {"enabled": True},
                "description": f"Booking {booking.reference}",
                "statement_descriptor_suffix": config.statement_descriptor or None,
                "metadata": {
                    "booking_reference": booking.reference,
                    "booking_id": str(booking.pk),
                    "pickup_at": booking.pickup_at.isoformat(),
                },
            },
            options={"idempotency_key": idempotency_key},
        )
    except stripe.StripeError as exc:
        logger.error("Stripe intent creation failed for %s: %s", booking.reference, exc)
        raise PaymentGatewayError(
            getattr(exc, "user_message", None) or "The payment could not be started."
        ) from exc

    payment, _ = Payment.objects.update_or_create(
        payment_intent_id=intent.id,
        defaults={
            "booking": booking,
            "provider": Payment.Provider.STRIPE,
            "amount": booking.total,
            "currency": booking.currency,
            "status": STATUS_MAP.get(intent.status, Payment.Status.UNKNOWN),
        },
    )
    return payment


def client_secret_for(payment: Payment) -> str:
    """
    Fetch the intent's client secret.

    Deliberately not stored: it is a short-lived credential for one checkout,
    and a database column holding it is a database column that can leak it.
    """
    config = _settings()
    try:
        intent = _client(config).payment_intents.retrieve(payment.payment_intent_id)
    except stripe.StripeError as exc:
        raise PaymentGatewayError("The payment could not be started.") from exc
    return intent.client_secret


def verify_webhook(payload: bytes, signature: str):
    """
    Verify a webhook signature and return the event.

    Unsigned or badly-signed payloads are rejected. Without this, anyone who
    knows the URL could post `payment_intent.succeeded` and confirm bookings
    without paying.
    """
    config = PaymentSettings.load()
    secret = config.webhook_secret
    if not secret:
        raise PaymentConfigurationError(
            "No webhook signing secret is configured; incoming events cannot be "
            "verified and are refused."
        )
    if not signature:
        raise PaymentGatewayError("Missing Stripe signature header.")

    try:
        return stripe.Webhook.construct_event(payload, signature, secret)
    except ValueError as exc:
        raise PaymentGatewayError("Malformed webhook payload.") from exc
    except stripe.SignatureVerificationError as exc:
        logger.warning("Rejected a webhook with an invalid signature.")
        raise PaymentGatewayError("Invalid webhook signature.") from exc


def refund(payment: Payment, *, amount: Decimal | None = None, reason: str = "",
           created_by=None):
    """
    Refund a payment, in full or in part.

    Partial refunds cover a cancellation net of its fee.
    """
    config = _settings()

    if payment.status != Payment.Status.SUCCEEDED:
        raise PaymentGatewayError("Only a successful payment can be refunded.")

    already = sum((r.amount for r in payment.refunds.all()), Decimal("0.00"))
    remaining = payment.amount - already
    amount = Decimal(amount) if amount is not None else remaining

    if amount <= 0:
        raise PaymentGatewayError("A refund must be greater than zero.")
    if amount > remaining:
        raise PaymentGatewayError(
            f"Only {remaining} {payment.currency} remains available to refund."
        )

    try:
        stripe_refund = _client(config).refunds.create(params={
            "payment_intent": payment.payment_intent_id,
            "amount": to_cents(amount),
            "metadata": {"booking_reference": payment.booking.reference},
        })
    except stripe.StripeError as exc:
        logger.error("Stripe refund failed for %s: %s", payment.booking.reference, exc)
        raise PaymentGatewayError(
            getattr(exc, "user_message", None) or "The refund could not be processed."
        ) from exc

    return Refund.objects.create(
        payment=payment,
        stripe_refund_id=stripe_refund.id,
        amount=amount,
        reason=reason,
        created_by=created_by,
    )


def apply_intent_to_payment(intent) -> Payment | None:
    """
    Bring a Payment (and its Booking) into line with a Stripe intent.

    Called from the webhook, which is the authoritative source: the browser's
    return from checkout is a hint, not proof. The legacy system trusted the
    browser.
    """
    payment = Payment.objects.filter(payment_intent_id=intent["id"]).first()
    if payment is None:
        reference = (intent.get("metadata") or {}).get("booking_reference")
        booking = Booking.objects.filter(reference=reference).first() if reference else None
        if booking is None:
            logger.warning("Webhook for unknown intent %s", intent["id"])
            return None
        payment = Payment.objects.create(
            booking=booking,
            provider=Payment.Provider.STRIPE,
            payment_intent_id=intent["id"],
            amount=Decimal(intent["amount"]) / CENTS,
            currency=(intent.get("currency") or "usd").upper(),
        )

    payment.status = STATUS_MAP.get(intent.get("status"), Payment.Status.UNKNOWN)

    charges = (intent.get("charges") or {}).get("data") or []
    if charges:
        charge = charges[0]
        payment.charge_id = charge.get("id", "")
        payment.receipt_url = charge.get("receipt_url") or ""
        details = (charge.get("payment_method_details") or {}).get("card") or {}
        payment.card_brand = (details.get("brand") or "")[:20]
        # Last four only. There is no field here that could hold more.
        payment.card_last4 = (details.get("last4") or "")[:4]

    if error := intent.get("last_payment_error"):
        payment.error_message = error.get("message", "")[:500]

    payment.save()

    booking = payment.booking
    if (
        payment.status == Payment.Status.SUCCEEDED
        and booking.status == Booking.Status.PENDING
    ):
        BookingStatusChange.objects.create(
            booking=booking,
            from_status=booking.status,
            to_status=Booking.Status.CONFIRMED,
            note=f"Payment confirmed by Stripe ({payment.payment_intent_id})",
        )
        booking.status = Booking.Status.CONFIRMED
        booking.save(update_fields=["status", "updated_at"])
        logger.info("Booking %s confirmed by payment %s", booking.reference,
                    payment.payment_intent_id)

        # Notifications must never break the confirmation: the money has already
        # moved, and losing the booking to save an email is the wrong trade.
        # mailer never raises, but the import is local so a broken notifications
        # app cannot take the payment path down with it.
        try:
            from notifications import mailer

            mailer.send_booking_confirmation(booking)
            mailer.send_ops_new_booking(booking)
        except Exception:
            logger.exception("Confirmation email failed for %s", booking.reference)

    return payment


def record_refund_from_charge(charge) -> None:
    """
    Record a refund issued outside this application.

    Staff can refund directly in the Stripe dashboard; without this the two
    systems would disagree about what a customer was charged.
    """
    payment = Payment.objects.filter(charge_id=charge.get("id")).first()
    if payment is None:
        intent_id = charge.get("payment_intent")
        payment = Payment.objects.filter(payment_intent_id=intent_id).first()
    if payment is None:
        return

    for entry in (charge.get("refunds") or {}).get("data", []):
        if Refund.objects.filter(stripe_refund_id=entry["id"]).exists():
            continue
        Refund.objects.create(
            payment=payment,
            stripe_refund_id=entry["id"],
            amount=Decimal(entry["amount"]) / CENTS,
            reason=entry.get("reason") or "Refunded in Stripe",
            created_by=None,
        )
        logger.info("Recorded external refund %s for %s", entry["id"],
                    payment.booking.reference)


def mark_settings_verified(config: PaymentSettings) -> None:
    config.updated_at = timezone.now()
    config.save(update_fields=["updated_at"])
