"""
Payment records.

Replaces `limousin_orderdetails`, which despite its name was not a line-items
table -- a limousine booking has one item. It was the payment record, and it
held the card number, expiry, cardholder name and CVV in plaintext.

This module stores Stripe references and nothing else. There is deliberately no
field capable of holding a card number, an expiry date or a security code, so
the class of defect that produced 3,416 exposed card records cannot recur.

Stripe API wiring is out of scope for this build; these models exist now because
the historical import needs somewhere to record what was paid.
"""

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

from config import crypto


class Payment(models.Model):
    """A payment attempt against a booking."""

    class Provider(models.TextChoices):
        STRIPE = "stripe", "Stripe"
        LEGACY = "legacy", "Legacy (pre-migration)"

    class Status(models.TextChoices):
        REQUIRES_PAYMENT_METHOD = "requires_payment_method", "Awaiting payment method"
        REQUIRES_ACTION = "requires_action", "Requires customer action (3-D Secure)"
        PROCESSING = "processing", "Processing"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        UNKNOWN = "unknown", "Unknown (historical record)"

    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.PROTECT, related_name="payments",
        help_text="PROTECT: financial records are never cascade-deleted.",
    )
    provider = models.CharField(
        max_length=12, choices=Provider.choices, default=Provider.STRIPE,
    )

    payment_intent_id = models.CharField(
        max_length=64, blank=True, db_index=True,
        help_text="Stripe PaymentIntent. Empty for imported historical records, "
                  "which predate this integration.",
    )
    charge_id = models.CharField(max_length=64, blank=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="USD")
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.REQUIRES_PAYMENT_METHOD,
        db_index=True,
    )

    # Display-only, supplied by Stripe. Never sufficient to transact.
    card_brand = models.CharField(max_length=20, blank=True)
    card_last4 = models.CharField(
        max_length=4, blank=True,
        validators=[RegexValidator(r"^\d{0,4}$", "Last four digits only.")],
        help_text="Last four digits only — never the full number.",
    )

    receipt_url = models.URLField(blank=True)
    error_message = models.TextField(blank=True)

    legacy_orderdetail_id = models.IntegerField(
        null=True, blank=True, unique=True, db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(card_last4="") | models.Q(card_last4__regex=r"^\d{4}$"),
                name="card_last4_is_four_digits_or_blank",
            ),
        ]

    def __str__(self):
        return f"{self.booking.reference} — {self.amount} {self.currency} ({self.status})"

    @property
    def masked_card(self) -> str:
        if not self.card_last4:
            return ""
        brand = self.card_brand.title() if self.card_brand else "Card"
        return f"{brand} •••• {self.card_last4}"


class Refund(models.Model):
    """A full or partial refund, e.g. a cancellation net of the fee."""

    payment = models.ForeignKey(
        Payment, on_delete=models.PROTECT, related_name="refunds",
    )
    stripe_refund_id = models.CharField(max_length=64, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=160, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="refunds_issued",
        help_text="Which staff member issued it.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Refund {self.amount} on {self.payment.booking.reference}"


class PaymentSettings(models.Model):
    """
    Stripe credentials, managed from the dashboard rather than the environment.

    Singleton. The secret and webhook signing keys are encrypted at rest (see
    config/crypto.py) and are never rendered back to a browser -- the settings
    form shows a masked summary and accepts a replacement, but cannot reveal
    what is stored.

    Publishable keys are deliberately NOT encrypted: they are designed to be
    embedded in a public web page, so encrypting them would imply a
    confidentiality they do not have.
    """

    class Mode(models.TextChoices):
        TEST = "test", "Test mode"
        LIVE = "live", "Live mode"

    mode = models.CharField(
        max_length=4, choices=Mode.choices, default=Mode.TEST,
        help_text="Live mode charges real cards.",
    )

    publishable_key = models.CharField(
        max_length=255, blank=True,
        help_text="Safe to expose — this is sent to the browser.",
    )
    _secret_key = models.TextField(
        "secret key", blank=True, db_column="secret_key_encrypted",
        help_text="Encrypted at rest.",
    )
    _webhook_secret = models.TextField(
        "webhook signing secret", blank=True, db_column="webhook_secret_encrypted",
        help_text="Encrypted at rest.",
    )

    statement_descriptor = models.CharField(
        max_length=22, blank=True,
        help_text="What appears on the customer's card statement (max 22 chars).",
    )

    is_enabled = models.BooleanField(
        default=False,
        help_text="Turn off to stop taking card payments without deleting the keys.",
    )

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )

    class Meta:
        verbose_name = "payment settings"
        verbose_name_plural = "payment settings"

    def __str__(self):
        return f"Stripe ({self.get_mode_display()})"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Payment settings cannot be deleted.")

    @classmethod
    def load(cls) -> "PaymentSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    # -- secrets ----------------------------------------------------------

    @property
    def secret_key(self) -> str | None:
        return crypto.decrypt(self._secret_key)

    @secret_key.setter
    def secret_key(self, value: str | None) -> None:
        self._secret_key = crypto.encrypt(value)

    @property
    def webhook_secret(self) -> str | None:
        return crypto.decrypt(self._webhook_secret)

    @webhook_secret.setter
    def webhook_secret(self, value: str | None) -> None:
        self._webhook_secret = crypto.encrypt(value)

    # -- display ----------------------------------------------------------

    @property
    def secret_key_masked(self) -> str:
        return crypto.mask(self.secret_key)

    @property
    def webhook_secret_masked(self) -> str:
        return crypto.mask(self.webhook_secret)

    @property
    def has_secret_key(self) -> bool:
        return bool(self._secret_key)

    @property
    def has_webhook_secret(self) -> bool:
        return bool(self._webhook_secret)

    @property
    def is_configured(self) -> bool:
        """Whether a charge could actually be attempted."""
        return bool(self.publishable_key and self.secret_key and self.is_enabled)

    @property
    def key_mode_matches(self) -> bool:
        """
        Whether the stored keys agree with the selected mode.

        Selecting Live mode while holding test keys is a silent failure --
        payments appear to work and no money moves.
        """
        secret = self.secret_key or ""
        expected = "sk_live_" if self.mode == self.Mode.LIVE else "sk_test_"
        if not secret:
            return True
        return secret.startswith(expected)


class WebhookEvent(models.Model):
    """
    A Stripe event we have already processed.

    Stripe retries webhooks until it gets a 2xx, and may deliver the same event
    more than once even on success. Recording the id makes processing idempotent:
    without it, a retried `charge.refunded` records the refund twice and the
    booking's financial history stops matching Stripe's.
    """

    event_id = models.CharField(max_length=80, unique=True, db_index=True)
    event_type = models.CharField(max_length=80)
    received_at = models.DateTimeField(auto_now_add=True)
    payload_summary = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-received_at"]

    def __str__(self):
        return f"{self.event_type} ({self.event_id})"
