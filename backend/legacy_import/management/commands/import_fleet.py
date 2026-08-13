"""
Import vehicles and expand their rate cards into distance bands.

Legacy stored four per-mile rates as fixed columns, with the boundaries held in
PHP constants:

    ADJUST_DISTANCE                  = 6     product_price_mile
    ADJUST_DISTANCE_SIX_TO_FIFTY     = 50    product_price_mile_above
    ADJUST_DISTANCE_FIFTY_TO_HUNDRED = 100   product_price_fifty_hundred
    (beyond 100)                             product_price_above_hundred

Those become four DistanceBand rows per vehicle, so the tiers are editable
without a deployment.
"""

from decimal import Decimal

from django.utils.text import slugify

from fleet.models import DistanceBand, Vehicle
from legacy_import.base import ImportReport, LegacyImportCommand
from legacy_import.legacy_db import fetch_all
from legacy_import.text import clean

# (from_miles, to_miles, legacy column supplying the rate)
BAND_LAYOUT = [
    (Decimal("0"), Decimal("6"), "product_price_mile"),
    (Decimal("6"), Decimal("50"), "product_price_mile_above"),
    (Decimal("50"), Decimal("100"), "product_price_fifty_hundred"),
    (Decimal("100"), None, "product_price_above_hundred"),
]


class Command(LegacyImportCommand):
    help = "Import vehicles and rate cards from limousin_car_list."
    label = "Fleet"

    def run_import(self, report: ImportReport) -> None:
        rows = self.apply_limit(fetch_all("SELECT * FROM limousin_car_list ORDER BY id"))

        for row in rows:
            name = clean(row.get("car_name"), max_length=120)
            if not name:
                report.skip(f"car id={row['id']}: no name")
                continue

            defaults = {
                "name": name,
                "slug": self._unique_slug(name, row["id"]),
                "description": clean(row.get("description")),
                "features": clean(row.get("car_featured")) or clean(row.get("car_note")),
                "passenger_capacity": self._as_int(row.get("p_quantity")),
                "luggage_capacity": self._as_int(row.get("l_quantity")),
                "hourly_rate": self._as_decimal(row.get("product_price_hr")),
                "meet_greet_fee": self._as_decimal(row.get("product_price_mg")),
                "minimum_fare": self._as_decimal(row.get("product_price_min")),
                "display_order": self._as_int(row.get("order_id")),
                "is_active": row.get("status") == "Y",
            }

            vehicle, created = Vehicle.objects.update_or_create(
                legacy_car_id=row["id"], defaults=defaults,
            )
            report.created += int(created)
            report.updated += int(not created)

            self._sync_bands(vehicle, row, report)

    # -- bands -------------------------------------------------------------

    def _sync_bands(self, vehicle: Vehicle, row: dict, report: ImportReport) -> None:
        """Replace the vehicle's bands with those derived from the legacy row."""
        rates = {col: self._as_decimal(row.get(col)) for _, _, col in BAND_LAYOUT}

        # A vehicle priced entirely at zero per mile was never used for distance
        # work -- the legacy limousines are hourly-only. Creating zero-rate bands
        # would let it quote $0 for a transfer, so leave it with none.
        if not any(rates.values()):
            DistanceBand.objects.filter(vehicle=vehicle).delete()
            if vehicle.is_active and not vehicle.hourly_rate:
                report.skip(
                    f"{vehicle.name}: no per-mile and no hourly rate — cannot quote"
                )
            return

        DistanceBand.objects.filter(vehicle=vehicle).delete()
        DistanceBand.objects.bulk_create([
            DistanceBand(
                vehicle=vehicle,
                from_miles=start,
                to_miles=end,
                rate_per_mile=rates[col],
            )
            for start, end, col in BAND_LAYOUT
        ])

    # -- coercion ----------------------------------------------------------

    @staticmethod
    def _as_decimal(value) -> Decimal:
        if value in (None, ""):
            return Decimal("0.00")
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"))
        except (ArithmeticError, ValueError):
            return Decimal("0.00")

    @staticmethod
    def _as_int(value) -> int:
        text = clean(value)
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else 0

    @staticmethod
    def _unique_slug(name: str, legacy_id: int) -> str:
        base = slugify(name)[:130] or f"vehicle-{legacy_id}"
        slug = base
        n = 2
        while Vehicle.objects.filter(slug=slug).exclude(legacy_car_id=legacy_id).exists():
            slug = f"{base}-{n}"
            n += 1
        return slug
