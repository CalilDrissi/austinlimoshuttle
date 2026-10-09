"""
Bookings -- the core business record.

Replaces `limousin_order` (2,217 rows) and `limousin_orderdetails` (2,488).

Deliberate differences from the legacy schema:
  * No card columns. Legacy held the PAN, expiry, cardholder name and CVV in
    plaintext across both tables. Nothing here can store them.
  * `pickup_at` is a real timezone-aware datetime. Legacy stored a formatted
    English string ("Fri, 21 Sep 2018, 2:30 PM") which cannot be sorted or
    ranged in SQL.
  * Status is a readable word, not an opaque letter (P/N/D/C/DL, one of which
    was never used).
  * Driver is a foreign key, not free text typed onto every booking.
  * The fare breakdown is persisted as price lines, so a disputed charge can be
    explained years later. Legacy stored only the final number.
"""

from __future__ import annotations

import secrets
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I/O/0/1
REFERENCE_LENGTH = 8


def generate_reference() -> str:
    return "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(REFERENCE_LENGTH))


class Driver(models.Model):
    """A chauffeur available for assignment."""

    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True, help_text="Internal only.")

    # Login for the mobile driver app. Null until an account is provisioned:
    # most of a driver's life (assignment, payout) is staff-managed and needs no
    # login. SET_NULL so deleting the account never erases the driver record the
    # booking history points at.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="driver_profile",
        help_text="Login account for the driver app. Blank = no app access yet.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self):
        return self.full_name


class BookingQuerySet(models.QuerySet):
    def upcoming(self):
        return self.filter(pickup_at__gte=timezone.now()).exclude(
            status=Booking.Status.CANCELLED
        )

    def for_dispatch(self):
        return self.select_related("vehicle", "driver", "customer")


class Booking(models.Model):
    """A single journey."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending payment"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        NO_SHOW = "no_show", "No-show"
        CANCELLED = "cancelled", "Cancelled"

    class TripType(models.TextChoices):
        TRANSFER = "transfer", "Point-to-point transfer"
        HOURLY = "hourly", "Hourly hire"

    reference = models.CharField(
        max_length=16, unique=True, default=generate_reference, db_index=True,
        help_text="Customer-facing booking code.",
    )

    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="bookings",
        help_text="Null for guest bookings. Deleting an account must not erase "
                  "booking history.",
    )
    vehicle = models.ForeignKey(
        "fleet.Vehicle", on_delete=models.PROTECT, related_name="bookings",
        help_text="PROTECT: a vehicle with bookings can be deactivated, not deleted.",
    )
    driver = models.ForeignKey(
        Driver, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bookings",
    )

    trip_type = models.CharField(
        max_length=10, choices=TripType.choices, default=TripType.TRANSFER,
    )
    city_route = models.ForeignKey(
        "pricing.CityRoute", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="bookings",
        help_text="Set when the fare came from a fixed city-to-city route.",
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True,
    )

    # -- itinerary --------------------------------------------------------
    pickup_address = models.CharField(max_length=255)
    pickup_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    pickup_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    dropoff_address = models.CharField(max_length=255, blank=True)
    dropoff_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    dropoff_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    pickup_at = models.DateTimeField(db_index=True)

    distance_miles = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
        help_text="From the Distance Matrix API. Null for hourly hire.",
    )
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    hours = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Booked hours, for hourly hire.",
    )

    passenger_count = models.PositiveSmallIntegerField(default=1)
    luggage_count = models.PositiveSmallIntegerField(default=0)

    flight_number = models.CharField(max_length=32, blank=True)
    pickup_sign = models.CharField(
        max_length=120, blank=True, help_text="Name shown on the placard.",
    )
    meet_and_greet = models.BooleanField(default=False)
    notes = models.TextField(blank=True, help_text="Customer instructions.")

    guest_email = models.EmailField(
        blank=True,
        help_text="Contact address for a booking made without an account. "
                  "Without it a guest can never receive their own confirmation.",
    )
    guest_phone = models.CharField(max_length=32, blank=True)

    # -- money -------------------------------------------------------------
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    surcharge_total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=3, default="USD")

    vehicle_name_snapshot = models.CharField(
        max_length=120, blank=True,
        help_text="Vehicle name as sold. Deliberate denormalisation: renaming "
                  "the fleet must not rewrite history.",
    )

    # -- cancellation ------------------------------------------------------
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True)
    cancellation_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
    )

    legacy_order_id = models.IntegerField(
        null=True, blank=True, unique=True, db_index=True,
        help_text="`limousin_order.id`.",
    )

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = BookingQuerySet.as_manager()

    class Meta:
        ordering = ["-pickup_at"]
        indexes = [
            models.Index(fields=["status", "pickup_at"]),
            models.Index(fields=["pickup_at", "status"], name="booking_dispatch_idx"),
        ]

    def __str__(self):
        return f"{self.reference} — {self.pickup_at:%d %b %Y %H:%M}"

    def save(self, *args, **kwargs):
        if not self.vehicle_name_snapshot and self.vehicle_id:
            self.vehicle_name_snapshot = self.vehicle.name
        super().save(*args, **kwargs)

    @property
    def is_cancellable(self) -> bool:
        if self.status in {self.Status.CANCELLED, self.Status.COMPLETED}:
            return False
        return self.pickup_at > timezone.now()

    @property
    def amendment_deadline(self):
        """
        Latest moment a customer may change this booking's details online.

        The window (hours before pickup) is set by the office in pricing
        settings, so "3 days before" vs "6 hours before" is a config change.
        """
        from datetime import timedelta

        from pricing.models import PricingSettings

        hours = PricingSettings.load().amendment_window_hours
        return self.pickup_at - timedelta(hours=hours)

    @property
    def is_amendable(self) -> bool:
        """Whether the customer can still edit non-price details online."""
        if self.status in {self.Status.CANCELLED, self.Status.COMPLETED}:
            return False
        return timezone.now() < self.amendment_deadline

    @property
    def contact_email(self) -> str:
        """Where correspondence for this booking goes."""
        if self.customer and self.customer.email:
            return self.customer.email
        return self.guest_email

    @property
    def contact_phone(self) -> str:
        """The booker's phone -- account phone for customers, guest phone otherwise."""
        if self.customer and self.customer.phone:
            return self.customer.phone
        return self.guest_phone

    @property
    def customer_name(self) -> str:
        if self.customer:
            return self.customer.get_full_name() or self.customer.email
        return self.pickup_sign or "Guest"


class BookingPriceLine(models.Model):
    """
    One component of a booking's fare.

    Persisting the breakdown is what lets staff answer "why was I charged this?"
    long after the rate card has changed.
    """

    class Kind(models.TextChoices):
        BASE = "base", "Base fare"
        BAND = "band", "Distance band"
        SURCHARGE = "surcharge", "Surcharge"
        MEET_GREET = "meet_greet", "Meet and greet"
        MINIMUM = "minimum_adjustment", "Minimum fare adjustment"
        TAX = "tax", "Tax"

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="price_lines",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    label = models.CharField(max_length=160)
    amount = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Signed: adjustments may be negative.",
    )
    ordering = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["booking", "ordering", "id"]

    def __str__(self):
        return f"{self.label}: {self.amount}"


class BookingStatusChange(models.Model):
    """
    Audit trail for status transitions.

    Impossible in the legacy system, which had a single shared admin login -- no
    action could be attributed to a person.
    """

    booking = models.ForeignKey(
        Booking, on_delete=models.CASCADE, related_name="status_changes",
    )
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="booking_status_changes",
    )
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"{self.booking.reference}: {self.from_status or '—'} → {self.to_status}"
