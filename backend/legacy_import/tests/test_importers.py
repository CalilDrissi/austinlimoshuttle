"""
Importer behaviour against the sanitised legacy replica.

Marked `legacy` because they need the replica loaded (./ops/load-legacy.sh).
Run with `-m "not legacy"` to skip.

The properties that matter are idempotency -- the import will be rehearsed many
times before cutover -- and the absolute guarantee that no password or card
value crosses over.
"""

from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from fleet.models import DistanceBand, Vehicle
from legacy_import.legacy_db import LegacyDataError, assert_sanitised, table_exists
from pricing.models import BlackoutDate, TimeSurcharge

User = get_user_model()
pytestmark = pytest.mark.legacy


@pytest.fixture(scope="module", autouse=True)
def require_replica():
    try:
        if not table_exists("limousin_member"):
            pytest.skip("legacy replica not loaded — run ./ops/load-legacy.sh")
    except LegacyDataError as exc:
        pytest.skip(str(exc))


def run(command, **kwargs):
    out = StringIO()
    call_command(command, stdout=out, **kwargs)
    return out.getvalue()


@pytest.mark.django_db
class TestSanitisationGuard:
    def test_replica_is_sanitised(self):
        """Fails loudly if anyone loads a production dump locally."""
        assert_sanitised()


@pytest.mark.django_db
class TestFleetImport:
    def test_imports_vehicles_and_expands_bands(self):
        run("import_fleet")

        assert Vehicle.objects.count() == 7
        assert Vehicle.objects.filter(is_active=True).count() == 4

        business = Vehicle.objects.get(name="Business Class")
        bands = list(business.bands.all())
        assert len(bands) == 4

        # The real legacy rate card, expanded from four fixed columns.
        assert bands[0].from_miles == 0 and bands[0].rate_per_mile == Decimal("15.00")
        assert bands[1].from_miles == 6 and bands[1].rate_per_mile == Decimal("2.90")
        assert bands[2].from_miles == 50 and bands[2].rate_per_mile == Decimal("2.20")
        assert bands[3].from_miles == 100 and bands[3].to_miles is None
        assert bands[3].rate_per_mile == Decimal("1.50")

    def test_bands_are_contiguous_and_lossless(self):
        run("import_fleet")
        for vehicle in Vehicle.objects.filter(bands__isnull=False).distinct():
            bands = list(vehicle.bands.all())
            assert bands[0].from_miles == 0
            assert bands[-1].to_miles is None
            for lower, upper in zip(bands, bands[1:], strict=False):
                assert lower.to_miles == upper.from_miles

    def test_import_is_idempotent(self):
        run("import_fleet")
        first_vehicles = Vehicle.objects.count()
        first_bands = DistanceBand.objects.count()

        run("import_fleet")
        assert Vehicle.objects.count() == first_vehicles
        assert DistanceBand.objects.count() == first_bands

    def test_reports_a_vehicle_that_cannot_be_quoted(self):
        output = run("import_fleet")
        assert "cannot quote" in output


@pytest.mark.django_db
class TestPricingImport:
    def test_late_night_window_comes_from_the_php_not_the_prose(self):
        """
        Legacy `title` described the window in English while the real hours were
        hardcoded. The PHP is authoritative: 21:00 -> 06:00.
        """
        run("import_pricing")

        rule = TimeSurcharge.objects.get()
        assert rule.start_time.hour == 21
        assert rule.end_time.hour == 6
        assert rule.crosses_midnight
        assert rule.percentage == Decimal("20.00")

    def test_imports_blackout_dates_with_their_uplifts(self):
        run("import_pricing")

        assert BlackoutDate.objects.count() == 11
        # Real data: SXSW at +40%, Formula 1 at +80%.
        assert BlackoutDate.objects.filter(percentage=Decimal("40.00")).exists()
        assert BlackoutDate.objects.filter(percentage=Decimal("80.00")).exists()

    def test_import_is_idempotent(self):
        run("import_pricing")
        before = (TimeSurcharge.objects.count(), BlackoutDate.objects.count())
        run("import_pricing")
        assert (TimeSurcharge.objects.count(), BlackoutDate.objects.count()) == before


@pytest.mark.django_db
class TestMemberImport:
    def test_imports_every_customer(self):
        run("import_members")
        assert User.objects.filter(legacy_member_id__isnull=False).count() == 1251

    def test_no_imported_account_can_authenticate(self):
        """
        The single most important assertion in the import. Legacy passwords were
        plaintext; every migrated account must require a reset.
        """
        run("import_members")
        imported = User.objects.filter(legacy_member_id__isnull=False)
        assert imported.exists()
        assert not any(u.has_usable_password() for u in imported)

    def test_emails_are_normalised_to_lowercase(self):
        run("import_members")
        assert not User.objects.filter(email__regex=r"[A-Z]").exists()

    def test_import_is_idempotent(self):
        run("import_members", limit=50)
        before = User.objects.count()
        run("import_members", limit=50)
        assert User.objects.count() == before

    def test_dry_run_changes_nothing(self):
        before = User.objects.count()
        run("import_members", dry_run=True, limit=25)
        assert User.objects.count() == before
