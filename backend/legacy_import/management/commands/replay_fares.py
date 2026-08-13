"""
Replay every historical booking through the new pricing engine.

This is the highest-value check in the project. Nine years of real bookings
carry their distance, vehicle, pickup time and the fare actually charged; if the
new engine reproduces those numbers, the rewrite prices identically to the
system it replaces. Where it does not, the difference is one of:

  * a rate-card change    -- rates were edited over nine years, so old bookings
                             were priced with rates we no longer have
  * a legacy bug          -- the old system charged something its own rules do
                             not justify
  * an engine bug         -- ours is wrong, and must be fixed

Only the third is a defect. The first is expected and unavoidable: the legacy
schema stores only the current rate card, not its history.

    manage.py replay_fares --report
    manage.py replay_fares --tolerance 0.02 --show 40
"""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from django.core.management.base import BaseCommand

from bookings.models import Booking
from fleet.models import Vehicle
from pricing.engine import QuoteError, money, quote
from pricing.models import BlackoutDate, PricingSettings, TimeSurcharge

AGREEMENT_TARGET_PCT = 99


class Command(BaseCommand):
    help = "Replay historical bookings through the pricing engine and diff the totals."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tolerance", type=Decimal, default=Decimal("0.01"),
            help="Absolute difference tolerated, in dollars (default 0.01).",
        )
        parser.add_argument(
            "--show", type=int, default=25,
            help="How many mismatches to list (default 25).",
        )
        parser.add_argument(
            "--report", action="store_true",
            help="Include the breakdown by vehicle and by cause.",
        )
        parser.add_argument(
            "--write", action="store_true",
            help="Persist recomputed price lines onto matching bookings.",
        )

    def handle(self, *args, **options):
        tolerance: Decimal = options["tolerance"]
        settings = PricingSettings.load()
        surcharges = list(TimeSurcharge.objects.filter(is_active=True))
        blackouts = {b.date: b for b in BlackoutDate.objects.filter(is_active=True)}
        bands_by_vehicle = {
            v.pk: list(v.bands.all())
            for v in Vehicle.objects.prefetch_related("bands")
        }

        exact = 0
        within = 0
        mismatches: list[tuple[Booking, Decimal, Decimal]] = []
        unpriceable: list[tuple[Booking, str]] = []
        zero_priced = 0

        bookings = (
            Booking.objects.select_related("vehicle")
            .filter(legacy_order_id__isnull=False)
            .order_by("legacy_order_id")
        )

        for booking in bookings.iterator(chunk_size=500):
            recorded = booking.total or Decimal("0.00")

            # Legacy rows with no price were never completed; nothing to compare.
            if recorded <= 0:
                zero_priced += 1
                continue

            try:
                result = quote(
                    booking.vehicle,
                    pickup_at=booking.pickup_at,
                    distance_miles=booking.distance_miles,
                    hours=booking.hours,
                    meet_and_greet=booking.meet_and_greet,
                    settings=settings,
                    surcharges=surcharges,
                    blackouts=blackouts,
                    bands=bands_by_vehicle.get(booking.vehicle_id, []),
                )
            except QuoteError as exc:
                unpriceable.append((booking, str(exc)))
                continue

            computed = money(result.total)
            difference = computed - recorded

            if difference == 0:
                exact += 1
            elif abs(difference) <= tolerance:
                within += 1
            else:
                mismatches.append((booking, recorded, computed))

            if options["write"] and abs(difference) <= tolerance:
                booking.price_lines.all().delete()
                for line in result.as_price_lines(booking):
                    line.save()

        self._render(
            exact, within, mismatches, unpriceable, zero_priced,
            tolerance, options["show"], options["report"],
        )

    # -- output ------------------------------------------------------------

    def _render(self, exact, within, mismatches, unpriceable, zero_priced,
                tolerance, show, full_report):
        compared = exact + within + len(mismatches)
        total_rows = compared + len(unpriceable) + zero_priced

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Fare replay"))
        self.stdout.write(f"  bookings examined     {total_rows}")
        self.stdout.write(f"  compared              {compared}")
        self.stdout.write(f"  skipped (no price)    {zero_priced}")
        self.stdout.write(f"  skipped (unpriceable) {len(unpriceable)}")
        self.stdout.write("")

        if compared:
            agree = exact + within
            pct = agree / compared * 100
            style = self.style.SUCCESS if pct >= AGREEMENT_TARGET_PCT else self.style.WARNING
            self.stdout.write(style(
                f"  exact match           {exact} ({exact / compared * 100:.1f}%)"
            ))
            self.stdout.write(
                f"  within ±{tolerance}           {within}"
            )
            self.stdout.write(style(
                f"  agreement             {agree}/{compared} ({pct:.1f}%)"
            ))
            self.stdout.write(
                self.style.ERROR(f"  mismatched            {len(mismatches)}")
                if mismatches else "  mismatched            0"
            )

        if mismatches and show:
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING(f"First {show} mismatches"))
            self.stdout.write(
                f"  {'legacy':>7}  {'recorded':>10}  {'computed':>10}  "
                f"{'diff':>10}  {'ratio':>6}  vehicle / journey"
            )
            for booking, recorded, computed in mismatches[:show]:
                diff = computed - recorded
                ratio = (computed / recorded) if recorded else Decimal("0")
                journey = (
                    f"{booking.hours:g}h"
                    if booking.hours
                    else f"{booking.distance_miles or 0:.1f}mi"
                )
                self.stdout.write(
                    f"  {booking.legacy_order_id:>7}  {recorded:>10.2f}  "
                    f"{computed:>10.2f}  {diff:>+10.2f}  {ratio:>6.2f}  "
                    f"{booking.vehicle_name_snapshot[:22]:22} {journey}"
                )

        if unpriceable and show:
            self.stdout.write("")
            self.stdout.write(self.style.MIGRATE_HEADING("Unpriceable"))
            reasons = Counter(reason for _, reason in unpriceable)
            for reason, count in reasons.most_common(10):
                self.stdout.write(f"  {count:>5}  {reason}")

        if full_report and mismatches:
            self._breakdown(mismatches)

        self.stdout.write("")

    def _breakdown(self, mismatches):
        """Group mismatches so systematic causes stand out from one-offs."""
        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Mismatches by vehicle"))
        by_vehicle = Counter(b.vehicle_name_snapshot for b, _, _ in mismatches)
        for name, count in by_vehicle.most_common():
            self.stdout.write(f"  {count:>5}  {name}")

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Mismatches by year of pickup"))
        by_year = Counter(b.pickup_at.year for b, _, _ in mismatches)
        for year in sorted(by_year):
            self.stdout.write(f"  {by_year[year]:>5}  {year}")

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Direction"))
        higher = sum(1 for _, rec, comp in mismatches if comp > rec)
        lower = len(mismatches) - higher
        self.stdout.write(f"  {higher:>5}  engine computes MORE than was charged")
        self.stdout.write(f"  {lower:>5}  engine computes LESS than was charged")

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Ratio clustering (computed / recorded)"))
        buckets = Counter()
        for _, rec, comp in mismatches:
            if not rec:
                continue
            ratio = comp / rec
            buckets[f"{ratio.quantize(Decimal('0.1'))}x"] += 1
        for bucket, count in buckets.most_common(12):
            self.stdout.write(f"  {count:>5}  {bucket}")
