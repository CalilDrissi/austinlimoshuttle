"""
Import surcharge rules.

The late-night window is the interesting case. Legacy stored a prose
description in `limousin_special_time_rate.title`:

    "For early pickup,  12 am to 6 am. For late pickup,  from 9 pm to 11.59 pm"

while the actual behaviour was hardcoded in PHP
(legacy/pickup_details.php:335):

    if ($time < strtotime('06:00:00') || $time > strtotime('21:00:00'))

Those agree: 21:00->06:00 as one window crossing midnight. The PHP is
authoritative, so the times below come from the code, not the sentence. The
original wording is preserved in the description for traceability.
"""

from datetime import time
from decimal import Decimal

from legacy_import.base import ImportReport, LegacyImportCommand
from legacy_import.legacy_db import fetch_all
from legacy_import.text import clean
from pricing.models import BlackoutDate, PricingSettings, TimeSurcharge

# Authoritative, from legacy/pickup_details.php:335. Both bounds exclusive.
LATE_NIGHT_START = time(21, 0, 0)
LATE_NIGHT_END = time(6, 0, 0)


class Command(LegacyImportCommand):
    help = "Import time surcharges, blackout dates and pricing settings."
    label = "Pricing"

    def run_import(self, report: ImportReport) -> None:
        self._import_time_surcharges(report)
        self._import_blackout_dates(report)
        self._import_settings(report)

    def _import_time_surcharges(self, report: ImportReport) -> None:
        for row in fetch_all("SELECT * FROM limousin_special_time_rate ORDER BY id"):
            percentage = self._as_decimal(row.get("increase_amount"))
            if percentage <= 0:
                report.skip(f"time surcharge id={row['id']}: zero percentage")
                continue

            _, created = TimeSurcharge.objects.update_or_create(
                legacy_rate_id=row["id"],
                defaults={
                    "name": "Late night and early morning pickup",
                    # Times come from the PHP condition, not from `title`.
                    "start_time": LATE_NIGHT_START,
                    "end_time": LATE_NIGHT_END,
                    "percentage": percentage,
                    "is_active": row.get("status") == "Y",
                },
            )
            report.created += int(created)
            report.updated += int(not created)

    def _import_blackout_dates(self, report: ImportReport) -> None:
        for row in fetch_all("SELECT * FROM limousin_busy_date ORDER BY busey_date"):
            date_value = row.get("busey_date")  # legacy misspelling
            if not date_value:
                report.skip(f"blackout id={row['id']}: no date")
                continue

            percentage = self._as_decimal(row.get("increase_amount"))
            name = clean(row.get("date_heading"), max_length=120) or f"Blackout {date_value}"

            # `date` is unique, and legacy holds one row per day of a multi-day
            # event (SXSW spans seven). Key on the date so re-runs converge.
            existing = BlackoutDate.objects.filter(date=date_value).first()
            if existing:
                existing.name = name
                existing.description = clean(row.get("date_description"), max_length=255)
                existing.percentage = percentage
                existing.is_active = row.get("status") == "Y"
                existing.legacy_busy_date_id = row["id"]
                existing.save()
                report.updated += 1
            else:
                BlackoutDate.objects.create(
                    date=date_value,
                    name=name,
                    description=clean(row.get("date_description"), max_length=255),
                    percentage=percentage,
                    is_active=row.get("status") == "Y",
                    legacy_busy_date_id=row["id"],
                )
                report.created += 1

    def _import_settings(self, report: ImportReport) -> None:
        """
        Tax rate lived on the admin user row in the legacy schema
        (`limousin_admin.vat`) -- business configuration attached to a person.
        """
        settings_obj = PricingSettings.load()

        rows = fetch_all("SELECT vat FROM limousin_admin ORDER BY id LIMIT 1")
        if rows and rows[0].get("vat") is not None:
            settings_obj.tax_rate = self._as_decimal(rows[0]["vat"])

        settings_obj.save()
        report.updated += 1

    @staticmethod
    def _as_decimal(value) -> Decimal:
        if value in (None, ""):
            return Decimal("0.00")
        try:
            return Decimal(str(value)).quantize(Decimal("0.01"))
        except (ArithmeticError, ValueError):
            return Decimal("0.00")
