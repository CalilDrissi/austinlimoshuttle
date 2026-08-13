"""Enquiries admin. The inbox proper lives in the dashboard (Phase 5)."""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import ContactMessage


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ["created_at", "name", "email", "nature", "subject", "state"]
    list_filter = ["nature", "is_read", "created_at"]
    search_fields = ["name", "email", "phone", "subject", "message", "company_name"]
    date_hierarchy = "created_at"
    readonly_fields = [
        "name", "email", "phone", "nature", "subject", "message",
        "company_name", "source_ip", "created_at", "legacy_table", "legacy_row_id",
    ]
    actions = ["mark_read", "mark_unread"]

    fieldsets = (
        ("Enquiry", {
            "fields": ("created_at", "nature", "name", "email", "phone",
                       "company_name", "subject", "message", "source_ip"),
        }),
        ("Handling", {"fields": ("is_read", "replied_at", "replied_by", "reply_body")}),
        ("Legacy", {
            "fields": ("legacy_table", "legacy_row_id"), "classes": ("collapse",),
        }),
    )

    @admin.display(description="State")
    def state(self, obj):
        if obj.is_answered:
            return format_html('<span style="color:#1e6b41">Replied</span>')
        if obj.is_read:
            return format_html('<span style="color:#8a6320">Read</span>')
        return format_html('<strong>Unread</strong>')

    @admin.action(description="Mark selected as read")
    def mark_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f"{updated} marked as read.")

    @admin.action(description="Mark selected as unread")
    def mark_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f"{updated} marked as unread.")

    def save_model(self, request, obj, form, change):
        """Record who replied, and when, the first time a reply is written."""
        if obj.reply_body and not obj.replied_at:
            obj.replied_at = timezone.now()
            obj.replied_by = request.user
            obj.is_read = True
        super().save_model(request, obj, form, change)
