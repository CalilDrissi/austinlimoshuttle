"""
Distance band arithmetic.

Bands are cumulative, which is the part that goes wrong silently: charging the
whole journey at the band the total distance lands in, rather than charging each
band only for the miles inside it, inflates long trips dramatically.
"""

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from fleet.models import DistanceBand, Vehicle


@pytest.fixture
def vehicle(db):
    v = Vehicle.objects.create(
        name="Business Class", slug="business-class",
        hourly_rate=Decimal("85.00"), minimum_fare=Decimal("95.00"),
    )
    # The real Business Class rate card.
    DistanceBand.objects.create(vehicle=v, from_miles=0, to_miles=6, rate_per_mile=Decimal("15.00"))
    DistanceBand.objects.create(vehicle=v, from_miles=6, to_miles=50, rate_per_mile=Decimal("2.90"))
    DistanceBand.objects.create(vehicle=v, from_miles=50, to_miles=100, rate_per_mile=Decimal("2.20"))
    DistanceBand.objects.create(vehicle=v, from_miles=100, to_miles=None, rate_per_mile=Decimal("1.50"))
    return v


@pytest.mark.django_db
class TestMilesWithin:
    def test_distance_inside_first_band(self, vehicle):
        first = vehicle.bands.first()
        assert first.miles_within(Decimal("4")) == Decimal("4")

    def test_distance_beyond_band_is_capped_at_band_width(self, vehicle):
        first = vehicle.bands.first()
        assert first.miles_within(Decimal("30")) == Decimal("6")

    def test_distance_below_band_start_contributes_nothing(self, vehicle):
        second = vehicle.bands.all()[1]
        assert second.miles_within(Decimal("4")) == Decimal("0")

    def test_partial_fill_of_middle_band(self, vehicle):
        second = vehicle.bands.all()[1]  # 6-50
        assert second.miles_within(Decimal("30")) == Decimal("24")

    def test_unbounded_band_takes_everything_above_its_start(self, vehicle):
        last = vehicle.bands.last()  # 100+
        assert last.miles_within(Decimal("250")) == Decimal("150")

    def test_exact_boundary_belongs_to_the_lower_band(self, vehicle):
        first, second = vehicle.bands.all()[0], vehicle.bands.all()[1]
        assert first.miles_within(Decimal("6")) == Decimal("6")
        assert second.miles_within(Decimal("6")) == Decimal("0")

    def test_bands_sum_to_the_total_distance(self, vehicle):
        """No miles may be lost or double-counted across the rate card."""
        for total in [Decimal("0.5"), Decimal("6"), Decimal("49.9"),
                      Decimal("100"), Decimal("137.4"), Decimal("500")]:
            covered = sum(b.miles_within(total) for b in vehicle.bands.all())
            assert covered == total, f"{total} miles -> {covered} covered"


@pytest.mark.django_db
class TestBandContains:
    def test_contains_is_lower_inclusive_upper_exclusive(self, vehicle):
        first = vehicle.bands.first()
        assert first.contains(Decimal("0"))
        assert first.contains(Decimal("5.99"))
        assert not first.contains(Decimal("6"))

    def test_unbounded_band_contains_any_large_value(self, vehicle):
        assert vehicle.bands.last().contains(Decimal("99999"))


@pytest.mark.django_db
class TestBandValidation:
    def test_upper_bound_must_exceed_lower(self, vehicle):
        band = DistanceBand(vehicle=vehicle, from_miles=50, to_miles=20, rate_per_mile=1)
        with pytest.raises(ValidationError):
            band.clean()

    def test_band_start_is_unique_per_vehicle(self, vehicle):
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            DistanceBand.objects.create(
                vehicle=vehicle, from_miles=0, to_miles=3, rate_per_mile=1,
            )


@pytest.mark.django_db
class TestVehicle:
    def test_rate_for_mile_picks_the_right_band(self, vehicle):
        assert vehicle.rate_for_mile(Decimal("3")) == Decimal("15.00")
        assert vehicle.rate_for_mile(Decimal("20")) == Decimal("2.90")
        assert vehicle.rate_for_mile(Decimal("75")) == Decimal("2.20")
        assert vehicle.rate_for_mile(Decimal("500")) == Decimal("1.50")

    def test_vehicle_without_bands_returns_zero_rate(self, db):
        bare = Vehicle.objects.create(name="Bare", slug="bare")
        assert bare.rate_for_mile(Decimal("10")) == Decimal("0.00")
