"""Fleet admin. The rate card is the commercial control panel."""

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from .models import DistanceBand, Vehicle


class DistanceBandInlineFormSet(forms.BaseInlineFormSet):
    """
    Validates the rate card as a whole.

    Individual bands cannot detect gaps or overlaps -- only the full set can.
    A gap means miles charged at zero; an overlap means the first matching band
    silently wins. Both are pricing bugs that would be invisible until a
    customer complained.
    """

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        bands = []
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            bands.append(
                (form.cleaned_data["from_miles"], form.cleaned_data.get("to_miles"), form)
            )

        if not bands:
            return

        bands.sort(key=lambda b: b[0])

        if bands[0][0] != 0:
            raise ValidationError(
                f"The first band must start at 0 miles, not {bands[0][0]:g}. "
                "Otherwise short journeys are charged nothing."
            )

        unbounded = [b for b in bands if b[1] is None]
        if len(unbounded) != 1:
            raise ValidationError(
                "Exactly one band must be unbounded (empty upper bound) so that "
                "long journeys are always priced."
            )
        if bands[-1][1] is not None:
            raise ValidationError("The unbounded band must be the last one.")

        for (_, end, _), (next_start, _, _) in zip(bands, bands[1:], strict=False):
            if end is None:
                raise ValidationError("Only the final band may be unbounded.")
            if end != next_start:
                problem = "overlap" if end > next_start else "gap"
                raise ValidationError(
                    f"Bands must be contiguous: found a {problem} between "
                    f"{end:g} and {next_start:g} miles."
                )


class DistanceBandInline(admin.TabularInline):
    model = DistanceBand
    formset = DistanceBandInlineFormSet
    extra = 0
    fields = ["from_miles", "to_miles", "rate_per_mile"]
    verbose_name_plural = "Distance bands (cumulative — each applies only to miles within it)"


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        "name", "is_active", "passenger_capacity", "luggage_capacity",
        "hourly_rate", "minimum_fare", "meet_greet_fee", "band_summary",
    ]
    list_filter = ["is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [DistanceBandInline]
    readonly_fields = ["legacy_car_id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("name", "slug", "is_active", "display_order")}),
        ("Capacity", {"fields": ("passenger_capacity", "luggage_capacity")}),
        ("Rates", {
            "fields": ("hourly_rate", "meet_greet_fee", "minimum_fare"),
            "description": "Per-mile rates are set as distance bands below.",
        }),
        ("Presentation", {"fields": ("description", "features", "photo")}),
        ("Legacy", {"fields": ("legacy_car_id",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Rate card")
    def band_summary(self, obj):
        bands = list(obj.bands.all())
        if not bands:
            return format_html('<span style="color:#b3261e">no bands — cannot quote</span>')
        return format_html(
            "<br>".join(f"{b.label}: ${b.rate_per_mile}" for b in bands)
        )
