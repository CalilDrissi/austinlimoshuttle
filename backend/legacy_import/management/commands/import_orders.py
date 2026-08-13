"""
Import bookings and their historical payment records.

Card columns are never selected. `limousin_order` holds `card_number`,
`expiration_date` and `name_on_card`; `limousin_orderdetails` additionally holds
`securitycode`. None of them appear in any query below, and the target models
have no field that could receive them.

Two legacy quirks drive the parsing:

  * `pickup_date` is a formatted English string -- "Fri, 21 Sep 2018, 2:30 PM".
    Rows where an admin typed the date by hand do not parse and are quarantined
    rather than guessed at.
  * Trip type is implicit. Transfers carry `distance` (miles) and a `duration`
    like "40 mins"; hourly hires have `distance` NULL and `duration` as a bare
    number of hours. That difference is the only signal available.
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib.auth import get_user_model
from django.utils import timezone

from bookings.models import Booking, Driver
from fleet.models import Vehicle
from legacy_import.base import ImportReport, LegacyImportCommand
from legacy_import.legacy_db import fetch_all
from legacy_import.text import clean, clean_phone
from payments.models import Payment

# "Fri, 21 Sep 2018, 2:30 PM"
PICKUP_DATE_FORMATS = [
    "%a, %d %b %Y, %I:%M %p",
    "%a, %d %b %Y, %H:%M",
    "%d %b %Y, %I:%M %p",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]

STATUS_MAP = {
    "D": Booking.Status.COMPLETED,   # 2,056 rows
    "C": Booking.Status.CANCELLED,   # 149
    "P": Booking.Status.PENDING,     # 9, all 2026
    "DL": Booking.Status.CANCELLED,  # 3 -- "deleted"; keep the record, mark cancelled
    "N": Booking.Status.PENDING,     # schema default, unused in practice
}

_DURATION_MINS = re.compile(r"(\d+(?:\.\d+)?)\s*min", re.I)
_DURATION_HOURS = re.compile(r"(\d+(?:\.\d+)?)\s*(?:hour|hr)", re.I)


class Command(LegacyImportCommand):
    help = "Import bookings from limousin_order. Card data is never read."
    label = "Bookings"

    def run_import(self, report: ImportReport) -> None:
        vehicles = {v.legacy_car_id: v for v in Vehicle.objects.all()}
        fallback_vehicle = (
            Vehicle.objects.filter(is_active=True).order_by("display_order").first()
        )
        if fallback_vehicle is None:
            report.skip("no vehicles imported — run import_fleet first")
            return

        User = get_user_model()
        members = {
            u.legacy_member_id: u
            for u in User.objects.filter(legacy_member_id__isnull=False)
        }

        rows = self.apply_limit(fetch_all("""
            SELECT id, pickup_location, destination, pickup_date, duration, distance,
                   type_vehicle, price, flight_number, pickup_sign, reference_number,
                   additional_comments, driver_name, driver_phone, member_id,
                   member_name, car_id, car_name, cancel_cas, cancel_message,
                   cancel_coss, date, orderNum, order_date, item_name, status
            FROM limousin_order
            ORDER BY id
        """))

        # `orderNum` is not unique in the legacy data: 2 values are shared by
        # two bookings each, and one row has none at all. `reference` is unique
        # here, so collisions get the legacy id appended rather than being
        # dropped -- the customer-facing code stays recognisable and traceable.
        used_references: set[str] = set(
            Booking.objects.exclude(reference="").values_list("reference", flat=True)
        )

        for row in rows:
            pickup_at = self._parse_pickup(row)
            if pickup_at is None:
                report.skip(
                    f"order id={row['id']}: unparseable pickup date "
                    f"{row.get('pickup_date')!r}"
                )
                continue

            vehicle = vehicles.get(self._as_int(row.get("car_id"))) or fallback_vehicle
            distance = self._as_decimal(row.get("distance"))
            hours = self._hours(row.get("duration"), distance)
            trip_type = (
                Booking.TripType.HOURLY
                if distance is None and hours is not None
                else Booking.TripType.TRANSFER
            )

            total = self._as_decimal(row.get("price")) or Decimal("0.00")
            status = STATUS_MAP.get((row.get("status") or "").strip(), Booking.Status.PENDING)

            defaults = {
                "reference": self._reference(row, used_references),
                "customer": members.get(self._as_int(row.get("member_id"))),
                "vehicle": vehicle,
                "trip_type": trip_type,
                "status": status,
                "pickup_address": clean(row.get("pickup_location"), max_length=255),
                "dropoff_address": clean(row.get("destination"), max_length=255),
                "pickup_at": pickup_at,
                "distance_miles": distance,
                "duration_minutes": self._minutes(row.get("duration")),
                "hours": hours,
                "flight_number": clean(row.get("flight_number"), max_length=32),
                "pickup_sign": clean(row.get("pickup_sign"), max_length=120),
                "notes": clean(row.get("additional_comments")),
                "subtotal": total,
                "total": total,
                "currency": "USD",
                "vehicle_name_snapshot": clean(row.get("car_name"), max_length=120)
                                          or vehicle.name,
                "created_at": self._aware(row.get("order_date")) or pickup_at,
            }

            if status == Booking.Status.CANCELLED:
                defaults["cancelled_at"] = self._aware(row.get("order_date")) or pickup_at
                defaults["cancellation_reason"] = (
                    clean(row.get("cancel_message")) or clean(row.get("cancel_cas"))
                )
                defaults["cancellation_fee"] = (
                    self._as_decimal(row.get("cancel_coss")) or Decimal("0.00")
                )

            booking, created = Booking.objects.update_or_create(
                legacy_order_id=row["id"], defaults=defaults,
            )

            # created_at is auto_now_add, so it ignores the value above on
            # insert. Set it explicitly or every historical booking claims to
            # have been made today.
            if created and defaults["created_at"]:
                Booking.objects.filter(pk=booking.pk).update(
                    created_at=defaults["created_at"]
                )

            self._attach_driver(booking, row)

            report.created += int(created)
            report.updated += int(not created)

        self._import_payments(report)

    # -- payments ----------------------------------------------------------

    def _import_payments(self, report: ImportReport) -> None:
        """
        Historical payment records.

        No card columns are selected. These predate Stripe PaymentIntents, so
        there is no intent id to record -- only what was charged and when.
        """
        bookings = {b.legacy_order_id: b for b in Booking.objects.all()}

        rows = fetch_all("""
            SELECT id, order_id, qnt, vat, shipping, date
            FROM limousin_orderdetails
            ORDER BY id
        """)

        for row in rows:
            booking = bookings.get(row.get("order_id"))
            if booking is None:
                report.skip(
                    f"orderdetail id={row['id']}: no booking for order_id="
                    f"{row.get('order_id')}"
                )
                continue

            Payment.objects.update_or_create(
                legacy_orderdetail_id=row["id"],
                defaults={
                    "booking": booking,
                    "provider": Payment.Provider.LEGACY,
                    "amount": booking.total,
                    "currency": "USD",
                    # Legacy recorded no payment outcome, only that a row existed.
                    "status": (
                        Payment.Status.SUCCEEDED
                        if booking.status in {
                            Booking.Status.COMPLETED, Booking.Status.CONFIRMED
                        }
                        else Payment.Status.UNKNOWN
                    ),
                },
            )

    # -- helpers -----------------------------------------------------------

    def _attach_driver(self, booking: Booking, row: dict) -> None:
        """Legacy typed driver names onto the order; promote them to real rows."""
        name = clean(row.get("driver_name"), max_length=150)
        if not name or name.lower() in {"n/a", "na", "none", "-"}:
            return

        driver, _ = Driver.objects.get_or_create(
            full_name=name,
            defaults={"phone": clean_phone(row.get("driver_phone"))},
        )
        if booking.driver_id != driver.pk:
            booking.driver = driver
            booking.save(update_fields=["driver"])

    def _parse_pickup(self, row: dict):
        raw = clean(row.get("pickup_date"))
        if not raw:
            return None
        for fmt in PICKUP_DATE_FORMATS:
            try:
                naive = datetime.strptime(raw, fmt)
            except ValueError:
                continue
            return timezone.make_aware(naive, timezone.get_default_timezone())
        return None

    @staticmethod
    def _reference(row: dict, used: set[str]) -> str:
        """
        Derive a unique customer-facing reference.

        Legacy kept two competing columns (`orderNum`, `reference_number`) and
        guaranteed uniqueness on neither.
        """
        candidate = ""
        for key in ("orderNum", "reference_number"):
            value = clean(row.get(key), max_length=16)
            if value:
                candidate = value
                break

        if not candidate:
            candidate = f"L{row['id']:06d}"

        if candidate in used:
            candidate = f"{candidate}-{row['id']}"[:16]

        used.add(candidate)
        return candidate

    @staticmethod
    def _minutes(duration) -> int | None:
        text = clean(duration)
        if not text:
            return None
        if match := _DURATION_MINS.search(text):
            return int(float(match.group(1)))
        if match := _DURATION_HOURS.search(text):
            return int(float(match.group(1)) * 60)
        return None

    @staticmethod
    def _hours(duration, distance) -> Decimal | None:
        """
        A bare number in `duration` with no distance means hourly hire.

        Legacy: `$standard_fare = $_SESSION['duration'] * product_price_hr`.
        """
        if distance is not None:
            return None
        text = clean(duration)
        if not text or not re.fullmatch(r"\d+(\.\d+)?", text):
            return None
        try:
            return Decimal(text).quantize(Decimal("0.01"))
        except InvalidOperation:
            return None

    @staticmethod
    def _as_decimal(value) -> Decimal | None:
        if value in (None, ""):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _as_int(value) -> int | None:
        text = clean(value)
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else None

    @staticmethod
    def _aware(value):
        if not value:
            return None
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_default_timezone())
        return value
