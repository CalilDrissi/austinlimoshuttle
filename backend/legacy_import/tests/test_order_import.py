"""
Order import: date parsing, status mapping, and the guarantee that no card
value crosses the boundary.
"""

from datetime import datetime
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.db.models import Sum

from bookings.models import Booking
from legacy_import.legacy_db import fetch_all, table_exists
from legacy_import.management.commands.import_orders import Command as OrderImport
from payments.models import Payment

pytestmark = pytest.mark.legacy


@pytest.fixture(scope="module", autouse=True)
def require_replica():
    if not table_exists("limousin_order"):
        pytest.skip("legacy replica not loaded — run ./ops/load-legacy.sh")


@pytest.fixture
def imported(db):
    out = StringIO()
    call_command("import_fleet", stdout=out)
    call_command("import_members", stdout=out)
    call_command("import_orders", stdout=out)
    return out.getvalue()


class TestDateParsing:
    """The legacy format is `Fri, 21 Sep 2018, 2:30 PM`."""

    @pytest.mark.parametrize(
        ("raw", "expected"),
        [
            ("Fri, 21 Sep 2018, 2:30 PM", datetime(2018, 9, 21, 14, 30)),
            ("Mon, 11 Jan 2016, 5:00 AM", datetime(2016, 1, 11, 5, 0)),
            ("Sat, 03 Oct 2026, 10:15 PM", datetime(2026, 10, 3, 22, 15)),
            ("Thu, 13 Aug 2026, 11:00 PM", datetime(2026, 8, 13, 23, 0)),
        ],
    )
    def test_parses_the_legacy_format(self, raw, expected):
        result = OrderImport()._parse_pickup({"pickup_date": raw})
        assert result is not None
        assert (result.year, result.month, result.day) == (
            expected.year, expected.month, expected.day
        )
        assert (result.hour, result.minute) == (expected.hour, expected.minute)

    def test_result_is_timezone_aware(self):
        result = OrderImport()._parse_pickup({"pickup_date": "Fri, 21 Sep 2018, 2:30 PM"})
        assert result.tzinfo is not None

    @pytest.mark.parametrize("raw", ["", "not a date", "31 Feb 2020", None, "TBC"])
    def test_unparseable_values_return_none_rather_than_guessing(self, raw):
        assert OrderImport()._parse_pickup({"pickup_date": raw}) is None


class TestTripTypeDetection:
    """Transfers carry a distance; hourly hires carry bare hours and no distance."""

    def test_bare_number_with_no_distance_is_hourly(self):
        assert OrderImport()._hours("6", None) == Decimal("6.00")

    def test_duration_with_a_distance_is_not_hourly(self):
        assert OrderImport()._hours("40 mins", Decimal("28.5")) is None

    def test_text_duration_is_not_hours(self):
        assert OrderImport()._hours("40 mins", None) is None

    def test_minutes_are_extracted_from_text(self):
        assert OrderImport()._minutes("40 mins") == 40
        assert OrderImport()._minutes("2 hours") == 120
        assert OrderImport()._minutes("") is None


@pytest.mark.django_db
class TestOrderImport:
    def test_imports_every_booking(self, imported):
        assert Booking.objects.count() == 2217

    def test_revenue_reconciles_to_the_cent(self, imported):
        legacy = fetch_all("SELECT ROUND(SUM(price),2) AS total FROM limousin_order")
        legacy_total = Decimal(str(legacy[0]["total"]))
        new_total = Booking.objects.aggregate(s=Sum("total"))["s"]
        assert new_total == legacy_total

    def test_status_letters_map_correctly(self, imported):
        # Legacy: D=2056 completed, C=149 + DL=3 cancelled, P=9 pending
        assert Booking.objects.filter(status=Booking.Status.COMPLETED).count() == 2056
        assert Booking.objects.filter(status=Booking.Status.CANCELLED).count() == 152
        assert Booking.objects.filter(status=Booking.Status.PENDING).count() == 9

    def test_trip_types_split_on_distance(self, imported):
        assert Booking.objects.filter(trip_type=Booking.TripType.TRANSFER).count() == 2131
        assert Booking.objects.filter(trip_type=Booking.TripType.HOURLY).count() == 86

    def test_every_booking_has_a_vehicle(self, imported):
        assert not Booking.objects.filter(vehicle__isnull=True).exists()

    def test_references_are_unique(self, imported):
        refs = Booking.objects.values_list("reference", flat=True)
        assert len(set(refs)) == len(refs)

    def test_import_is_idempotent(self, imported):
        before = Booking.objects.count()
        call_command("import_orders", stdout=StringIO())
        assert Booking.objects.count() == before

    def test_orphaned_order_details_are_reported_not_invented(self, imported):
        """
        271 orderdetails rows reference bookings that no longer exist -- legacy
        deleted orders and left their payment rows behind. They must be skipped
        loudly, not turned into phantom bookings.
        """
        assert "no booking for order_id" in imported
        assert Payment.objects.count() == 2217


@pytest.mark.django_db
class TestNoCardholderDataCrossesOver:
    def test_no_payment_carries_card_details(self, imported):
        assert not Payment.objects.exclude(card_last4="").exists()
        assert not Payment.objects.exclude(card_brand="").exists()

    def test_importer_never_selects_card_columns(self):
        """The strongest guarantee: the SQL cannot return what it does not ask for."""
        import inspect

        source = inspect.getsource(OrderImport)
        for column in ("card_number", "securitycode", "expiration_date",
                       "expiration_dates", "name_on_card", "name_of_card"):
            assert column not in source, f"{column} appears in the importer"
