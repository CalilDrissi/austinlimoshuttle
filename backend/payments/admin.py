"""
Payments admin.

Read-mostly by design: payment state is owned by the provider, not by staff
editing rows. Refunds are the one action, and they record who issued them.
"""

from django.contrib import admin

from .models import Payment, Refund


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0
    fields = ["amount", "reason", "created_by", "created_at", "stripe_refund_id"]
    readonly_fields = ["created_at"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "booking", "provider", "status", "amount", "currency",
        "masked_card", "created_at",
    ]
    list_filter = ["provider", "status", "currency", "created_at"]
    search_fields = [
        "booking__reference", "payment_intent_id", "charge_id", "card_last4",
    ]
    date_hierarchy = "created_at"
    autocomplete_fields = ["booking"]
    inlines = [RefundInline]
    readonly_fields = [
        "provider", "payment_intent_id", "charge_id", "amount", "currency",
        "card_brand", "card_last4", "receipt_url", "error_message",
        "legacy_orderdetail_id", "created_at", "updated_at",
    ]

    def has_add_permission(self, request):
        """Payments are created by the checkout flow, never typed in by hand."""
        return False

    @admin.display(description="Card")
    def masked_card(self, obj):
        return obj.masked_card or "—"


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ["payment", "amount", "reason", "created_by", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["payment__booking__reference", "stripe_refund_id"]
    readonly_fields = ["created_at"]

    def save_model(self, request, obj, form, change):
        """Attribute the refund to the signed-in staff member."""
        if not change and obj.created_by is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
