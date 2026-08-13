"""Admin registration for accounts."""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm, AdminUserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import BillingAddress, CorporateAccount, User


class BillingAddressInline(admin.TabularInline):
    model = BillingAddress
    extra = 0


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Email-based user admin.

    Django's stock UserAdmin assumes a `username` field; every fieldset below is
    reworked for email identity.
    """

    # AdminUserCreationForm (not UserCreationForm) supplies the `usable_password`
    # choice, which lets staff create an account with no usable password -- the
    # same state imported legacy accounts land in.
    add_form = AdminUserCreationForm
    change_password_form = AdminPasswordChangeForm

    ordering = ["-date_joined"]
    list_display = ["email", "get_full_name", "phone", "is_active", "is_staff", "date_joined"]
    list_filter = ["is_active", "is_staff", "is_superuser", "marketing_opt_in", "date_joined"]
    search_fields = ["email", "first_name", "last_name", "phone", "legacy_member_id"]
    readonly_fields = ["last_login", "date_joined", "legacy_member_id"]
    inlines = [BillingAddressInline]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("title", "first_name", "last_name", "phone")}),
        (_("Permissions"), {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        (_("Preferences"), {"fields": ("marketing_opt_in",)}),
        (_("Legacy"), {
            "fields": ("legacy_member_id",),
            "classes": ("collapse",),
            "description": "Traceability to the pre-migration system.",
        }),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "usable_password", "password1", "password2"),
        }),
    )

    def get_inlines(self, request, obj=None):
        """
        Hide inlines on the add page.

        A billing address cannot be attached to a user that does not exist yet,
        and rendering the formset there means every add-user POST must carry its
        management form or silently fail validation with no visible error.
        """
        if obj is None:
            return []
        return super().get_inlines(request, obj)

    @admin.display(description="Name", ordering="last_name")
    def get_full_name(self, obj):
        return obj.get_full_name() or "—"


@admin.register(CorporateAccount)
class CorporateAccountAdmin(admin.ModelAdmin):
    list_display = ["company_name", "contact_name", "email", "phone", "status", "created_at"]
    list_filter = ["status", "created_at"]
    search_fields = ["company_name", "contact_name", "email", "phone"]
    readonly_fields = ["created_at"]
    autocomplete_fields = ["user"]
