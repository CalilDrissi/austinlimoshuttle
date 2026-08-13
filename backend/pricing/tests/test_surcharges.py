"""
Surcharge window behaviour.

The inherited rule crosses midnight (21:00 -> 06:00) and both bounds are
exclusive, matching legacy/pickup_details.php:335:

    if ($time < strtotime('06:00:00') || $time > strtotime('21:00:00'))

Boundary handling is the whole point of these tests: shifting either end by one
second silently reprices every booking made near it.
"""

from datetime import time
from decimal import Decimal

import pytest

from pricing.models import BlackoutDate, PricingSettings, TimeSurcharge


@pytest.fixture
def late_night(db):
    return TimeSurcharge.objects.create(
        name="Late night", start_time=time(21, 0), end_time=time(6, 0),
        percentage=Decimal("20.00"),
    )


@pytest.fixture
def daytime_window(db):
    """A window that does not cross midnight, for contrast."""
    return TimeSurcharge.objects.create(
        name="Midday", start_time=time(11, 0), end_time=time(14, 0),
        percentage=Decimal("5.00"),
    )


@pytest.mark.django_db
class TestMidnightCrossingWindow:
    def test_detects_that_it_crosses_midnight(self, late_night):
        assert late_night.crosses_midnight

    @pytest.mark.parametrize("at", [time(22, 0), time(23, 59), time(0, 0),
                                    time(3, 30), time(5, 59)])
    def test_inside_the_window(self, late_night, at):
        assert late_night.applies_at(at)

    @pytest.mark.parametrize("at", [time(6, 0), time(9, 0), time(12, 0),
                                    time(18, 0), time(20, 59)])
    def test_outside_the_window(self, late_night, at):
        assert not late_night.applies_at(at)

    def test_start_boundary_is_exclusive(self, late_night):
        """Legacy used `> 21:00:00`, so 21:00:00 exactly is not surcharged."""
        assert not late_night.applies_at(time(21, 0, 0))
        assert late_night.applies_at(time(21, 0, 1))

    def test_end_boundary_is_exclusive(self, late_night):
        """Legacy used `< 06:00:00`, so 06:00:00 exactly is not surcharged."""
        assert not late_night.applies_at(time(6, 0, 0))
        assert late_night.applies_at(time(5, 59, 59))

    def test_inactive_rule_never_applies(self, late_night):
        late_night.is_active = False
        late_night.save()
        assert not late_night.applies_at(time(23, 0))


@pytest.mark.django_db
class TestSameDayWindow:
    def test_inside(self, daytime_window):
        assert daytime_window.applies_at(time(12, 30))

    def test_outside(self, daytime_window):
        assert not daytime_window.applies_at(time(9, 0))
        assert not daytime_window.applies_at(time(15, 0))

    def test_bounds_are_exclusive(self, daytime_window):
        assert not daytime_window.applies_at(time(11, 0))
        assert not daytime_window.applies_at(time(14, 0))


@pytest.mark.django_db
class TestValidation:
    def test_identical_start_and_end_is_rejected(self, db):
        from django.core.exceptions import ValidationError

        rule = TimeSurcharge(
            name="Broken", start_time=time(9, 0), end_time=time(9, 0), percentage=10,
        )
        with pytest.raises(ValidationError):
            rule.clean()


@pytest.mark.django_db
class TestBlackoutDate:
    def test_date_is_unique(self, db):
        from datetime import date

        from django.db import IntegrityError

        BlackoutDate.objects.create(name="SXSW", date=date(2026, 3, 13), percentage=40)
        with pytest.raises(IntegrityError):
            BlackoutDate.objects.create(name="Dup", date=date(2026, 3, 13), percentage=10)


@pytest.mark.django_db
class TestPricingSettingsSingleton:
    def test_load_creates_once(self):
        first = PricingSettings.load()
        second = PricingSettings.load()
        assert first.pk == second.pk == 1
        assert PricingSettings.objects.count() == 1

    def test_saving_a_second_instance_overwrites_the_first(self):
        PricingSettings.load()
        other = PricingSettings(tax_rate=Decimal("8.25"))
        other.save()
        assert PricingSettings.objects.count() == 1
        assert PricingSettings.load().tax_rate == Decimal("8.25")

    def test_cannot_be_deleted(self):
        from django.core.exceptions import ValidationError

        obj = PricingSettings.load()
        with pytest.raises(ValidationError):
            obj.delete()
