"""Content admin."""

from django.contrib import admin
from django.utils.html import format_html

from .models import Banner, GalleryImage, Page, SiteSettings, Testimonial


@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ["title", "url", "page_type", "menu_placement", "is_published"]
    list_filter = ["page_type", "menu_placement", "is_published"]
    search_fields = ["title", "slug", "body", "meta_title", "meta_description"]
    readonly_fields = ["legacy_cms_id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("title", "slug", "page_type", "is_published")}),
        ("Content", {"fields": ("body", "hero_image")}),
        ("SEO", {
            "fields": ("meta_title", "meta_description", "meta_keywords"),
            "description": (
                "These are what search engines show. Changing the slug breaks "
                "existing rankings and inbound links — treat it as permanent."
            ),
        }),
        ("Navigation", {"fields": ("parent", "menu_placement", "display_order")}),
        ("Legacy", {"fields": ("legacy_cms_id",), "classes": ("collapse",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="URL")
    def url(self, obj):
        return format_html("<code>{}</code>", obj.url_path)


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ["__str__", "placement", "display_order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["title"]
    autocomplete_fields = ["page"]

    @admin.display(description="Placement")
    def placement(self, obj):
        return obj.page.title if obj.page else "Homepage"


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ["customer_name", "rating", "is_published", "display_order"]
    list_filter = ["is_published", "rating"]
    search_fields = ["customer_name", "quote"]


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ["__str__", "category", "display_order", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["title"]


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Singleton."""

    readonly_fields = ["updated_at"]
    fieldsets = (
        ("Contact", {"fields": ("contact_email", "contact_phone", "ops_notification_email")}),
        ("Social", {"fields": ("facebook", "instagram", "twitter", "linkedin")}),
        (None, {"fields": ("updated_at",)}),
    )

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
