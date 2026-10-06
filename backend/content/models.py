"""
CMS content.

Replaces `limousin_cms`, which did three jobs at once: page content, SEO
metadata, and the URL routing table (its `template` column named a PHP file to
include). Routing now belongs to Next.js, so `page_type` selects a layout rather
than naming a file.

Slugs must survive the migration byte-identically -- organic search is how this
business is found, and two of the legacy slugs are malformed in ways that must
be preserved (`wwwaustinlimoshuttlecom` is a URL with its punctuation stripped).
"""

from django.db import models


class Page(models.Model):
    """A content page with its SEO metadata."""

    class PageType(models.TextChoices):
        HOME = "home", "Homepage"
        SERVICE = "service", "Service landing page"
        STANDARD = "standard", "Standard content page"
        LEGAL = "legal", "Legal / policy page"

    class MenuPlacement(models.TextChoices):
        MAIN = "main", "Main menu"
        FOOTER = "footer", "Footer"
        NONE = "none", "Not in any menu"

    slug = models.SlugField(
        max_length=200, unique=True, db_index=True,
        help_text="URL path. Changing this breaks search rankings — don't.",
    )
    title = models.CharField(max_length=255)
    page_type = models.CharField(
        max_length=20, choices=PageType.choices, default=PageType.STANDARD,
    )

    body = models.TextField(blank=True)

    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    meta_keywords = models.TextField(blank=True)

    hero_image = models.ImageField(upload_to="pages/", blank=True, null=True)

    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="children",
    )
    menu_placement = models.CharField(
        max_length=12, choices=MenuPlacement.choices, default=MenuPlacement.NONE,
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    is_published = models.BooleanField(default=True)

    legacy_cms_id = models.IntegerField(null=True, blank=True, unique=True, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["display_order", "title"]

    def __str__(self):
        return self.title

    @property
    def url_path(self) -> str:
        return "/" if self.page_type == self.PageType.HOME else f"/{self.slug}"


class Banner(models.Model):
    """A promotional banner. Null `page` means the homepage."""

    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="banners/", blank=True, null=True)
    link_url = models.URLField(blank=True)

    page = models.ForeignKey(
        Page, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="banners",
        help_text="Leave empty for the homepage. Replaces the legacy H/P flag.",
    )

    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    legacy_banner_id = models.IntegerField(null=True, blank=True, unique=True)

    class Meta:
        ordering = ["display_order", "id"]

    def __str__(self):
        return self.title or f"Banner #{self.pk}"


class Testimonial(models.Model):
    """
    A customer testimonial.

    Was `limousin_castomer` -- a misspelling, and unrelated to the customer
    accounts table despite the name.
    """

    # pytest collects any class matching Test* as a test case, and "Testimonial"
    # matches. This tells it not to.
    __test__ = False

    customer_name = models.CharField(max_length=200)
    quote = models.TextField()
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="1-5. Legacy stored this as free text.",
    )
    photo = models.ImageField(upload_to="testimonials/", blank=True, null=True)

    is_published = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    legacy_testimonial_id = models.IntegerField(null=True, blank=True, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "-created_at"]

    def __str__(self):
        return f"{self.customer_name}"


class GalleryImage(models.Model):
    """Gallery photos and partner logos, which legacy stored in one table."""

    class Category(models.TextChoices):
        GALLERY = "gallery", "Gallery"
        PARTNER = "partner", "Partner logo"

    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="gallery/", blank=True, null=True)
    category = models.CharField(
        max_length=12, choices=Category.choices, default=Category.GALLERY,
        help_text="Legacy used a misspelled `partrers` flag.",
    )
    display_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    legacy_gallery_id = models.IntegerField(null=True, blank=True, unique=True)

    class Meta:
        ordering = ["category", "display_order"]

    def __str__(self):
        return self.title or f"Image #{self.pk}"


class SiteSettings(models.Model):
    """
    Site-wide settings. Singleton.

    Absorbs `limousin_social_media` (a one-row table), `limousin_paging`
    (pagination config stored as data), and the notification addresses that
    legacy read off the admin user row.
    """

    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)

    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=32, blank=True)
    ops_notification_email = models.EmailField(
        blank=True, help_text="Where new-booking alerts are sent.",
    )

    google_maps_api_key = models.CharField(
        max_length=120, blank=True,
        help_text="Google Maps key for address autocomplete and distance pricing. "
                  "Leave blank to use the server's configured key.",
    )

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "site settings"
        verbose_name_plural = "site settings"

    def __str__(self):
        return "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
