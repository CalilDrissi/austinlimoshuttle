"""Pricing admin."""

from django.contrib import admin
from django.utils.html import format_html

from .models import BlackoutDate, PricingSettings, TimeSurcharge


@admin.register(TimeSurcharge)
class TimeSurchargeAdmin(admin.ModelAdmin):
    list_display = ["name", "window", "percentage", "is_active"]
    list_filter = ["is_active"]
    readonly_fields = ["legacy_rate_id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("name", "is_active")}),
        ("Window", {
            "fields": ("start_time", "end_time"),
            "description": (
                "Applies to pickups after the start time or before the end time "
                "when the window crosses midnight. Both bounds are exclusive, "
                "matching the pricing behaviour inherited from the previous system."
            ),
        }),
        ("Uplift", {"fields": ("percentage",)}),
        ("Legacy", {"fields": ("legacy_rate_id",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Window")
    def window(self, obj):
        arrow = " → " if obj.crosses_midnight else " – "
        suffix = " (crosses midnight)" if obj.crosses_midnight else ""
        return format_html(
            "{}{}{}{}", obj.start_time.strftime("%H:%M"), arrow,
            obj.end_time.strftime("%H:%M"), suffix,
        )


@admin.register(BlackoutDate)
class BlackoutDateAdmin(admin.ModelAdmin):
    list_display = ["date", "name", "percentage", "is_active"]
    list_filter = ["is_active", "date"]
    search_fields = ["name", "description"]
    date_hierarchy = "date"
    readonly_fields = ["legacy_busy_date_id", "created_at", "updated_at"]


@admin.register(PricingSettings)
class PricingSettingsAdmin(admin.ModelAdmin):
    """Singleton: no add, no delete."""

    list_display = ["__str__", "tax_rate", "currency", "cancellation_window_hours"]
    readonly_fields = ["updated_at"]

    def has_add_permission(self, request):
        return not PricingSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
