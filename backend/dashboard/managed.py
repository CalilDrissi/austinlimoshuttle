"""
What staff can manage from the dashboard.

One entry per model that previously required Django's admin. The order here is
the order they appear in the sidebar.
"""

from __future__ import annotations

from bookings.models import Driver
from content.models import Banner, GalleryImage, Page, Testimonial
from fleet.models import Vehicle
from pricing.models import BlackoutDate, TimeSurcharge

from . import forms
from .crud import Column, Managed, register

QUOTE_PREVIEW_CHARS = 70

User = Driver._meta.apps.get_model("accounts", "User")


def _truncate(text: str | None) -> str:
    text = text or ""
    return text[:QUOTE_PREVIEW_CHARS] + ("…" if len(text) > QUOTE_PREVIEW_CHARS else "")


def _money(attr, prefix="$"):
    def render(instance):
        value = getattr(instance, attr)
        return f"{prefix}{value:,.2f}" if value is not None else "—"
    return render


# -- operations -------------------------------------------------------------

register(Managed(
    slug="drivers",
    model=Driver,
    form_class=forms.DriverForm,
    label="Driver",
    label_plural="Drivers",
    permission="bookings.change_driver",
    icon="bi-person-badge",
    lede="Chauffeurs available for assignment on the dispatch board.",
    search_fields=["full_name", "phone", "email"],
    ordering=["full_name"],
    columns=[
        Column("Name", "full_name", sub="email"),
        Column("Phone", "phone"),
        Column("Active", "is_active", boolean=True),
    ],
))

# -- fleet and pricing ------------------------------------------------------

register(Managed(
    slug="vehicles",
    model=Vehicle,
    form_class=forms.VehicleForm,
    label="Vehicle",
    label_plural="Vehicles & rates",
    permission="fleet.change_vehicle",
    icon="bi-car-front",
    lede="Vehicle classes and their per-mile rate cards.",
    form_note=(
        "The rate card is cumulative: a 70-mile journey is charged the first "
        "band for its opening miles, the next band for the miles after that, "
        "and so on. Bands must be continuous and start at zero — a gap prices "
        "those miles at nothing, and an overlap charges them twice."
    ),
    search_fields=["name", "slug"],
    ordering=["display_order", "name"],
    prefetch_related=["bands"],
    inline_formset=forms.DistanceBandFormSet,
    inline_label="Rate card",
    inline_note="From/to are miles. Leave the final band's upper bound empty.",
    columns=[
        Column("Vehicle", "name", sub="slug"),
        Column("Seats", "passenger_capacity"),
        Column("Luggage", "luggage_capacity"),
        Column("Hourly", _money("hourly_rate"), align_end=True),
        Column("Minimum fare", _money("minimum_fare"), align_end=True),
        Column("Bands", lambda v: v.bands.count()),
        Column("Active", "is_active", boolean=True),
    ],
))

register(Managed(
    slug="surcharges",
    model=TimeSurcharge,
    form_class=forms.TimeSurchargeForm,
    label="Time surcharge",
    label_plural="Time surcharges",
    permission="pricing.change_timesurcharge",
    icon="bi-clock-history",
    lede="Windows that cost more — late night, early morning.",
    search_fields=["name"],
    ordering=["start_time"],
    columns=[
        Column("Name", "name"),
        Column("From", lambda s: s.start_time.strftime("%H:%M")),
        Column("To", lambda s: s.end_time.strftime("%H:%M")),
        Column("Uplift", lambda s: f"+{s.percentage:g}%", align_end=True),
        Column("Active", "is_active", boolean=True),
    ],
))

register(Managed(
    slug="blackout-dates",
    model=BlackoutDate,
    form_class=forms.BlackoutDateForm,
    label="Event date",
    label_plural="Event dates",
    permission="pricing.change_blackoutdate",
    icon="bi-calendar-event",
    lede="Dates that carry an uplift — SXSW, ACL, New Year's Eve.",
    search_fields=["name", "description"],
    ordering=["date"],
    columns=[
        Column("Date", lambda b: b.date.strftime("%d %b %Y")),
        Column("Name", "name", sub="description"),
        Column("Uplift", lambda b: f"+{b.percentage:g}%", align_end=True),
        Column("Active", "is_active", boolean=True),
    ],
))

# -- website content --------------------------------------------------------

register(Managed(
    slug="pages",
    model=Page,
    form_class=forms.PageForm,
    label="Page",
    label_plural="Pages",
    permission="content.change_page",
    icon="bi-file-earmark-text",
    lede="Website pages and their search-engine metadata.",
    form_note=(
        "Changing a page's address breaks its search ranking and every link "
        "pointing at it. Treat an existing address as permanent."
    ),
    search_fields=["title", "slug", "body", "meta_description"],
    ordering=["display_order", "title"],
    columns=[
        Column("Title", "title", sub="url_path"),
        Column("Type", "get_page_type_display"),
        Column("Menu", "get_menu_placement_display"),
        Column("Published", "is_published", boolean=True),
    ],
))

register(Managed(
    slug="testimonials",
    model=Testimonial,
    form_class=forms.TestimonialForm,
    label="Testimonial",
    label_plural="Testimonials",
    permission="content.change_testimonial",
    icon="bi-chat-quote",
    lede="Customer quotes shown on the website.",
    search_fields=["customer_name", "quote"],
    ordering=["display_order", "-created_at"],
    columns=[
        Column("Customer", "customer_name"),
        Column("Quote", lambda t: _truncate(t.quote)),
        Column("Rating", lambda t: f"{t.rating}/5" if t.rating else "—"),
        Column("Published", "is_published", boolean=True),
    ],
))

register(Managed(
    slug="banners",
    model=Banner,
    form_class=forms.BannerForm,
    label="Banner",
    label_plural="Banners",
    permission="content.change_banner",
    icon="bi-image",
    lede="Promotional banners. Leaving the page empty puts one on the homepage.",
    search_fields=["title", "description"],
    ordering=["display_order", "id"],
    select_related=["page"],
    columns=[
        Column("Title", "__str__", sub=lambda b: b.page.title if b.page else "Homepage"),
        Column("Links to", "link_url"),
        Column("Active", "is_active", boolean=True),
    ],
))

register(Managed(
    slug="gallery",
    model=GalleryImage,
    form_class=forms.GalleryImageForm,
    label="Image",
    label_plural="Gallery & logos",
    permission="content.change_galleryimage",
    icon="bi-images",
    lede="Gallery photographs and partner logos.",
    search_fields=["title", "description"],
    ordering=["category", "display_order"],
    columns=[
        Column("Title", "__str__"),
        Column("Category", "get_category_display"),
        Column("Active", "is_active", boolean=True),
    ],
))

# -- people -----------------------------------------------------------------

register(Managed(
    slug="staff",
    model=User,
    form_class=forms.StaffUserForm,
    label="Staff account",
    label_plural="Staff accounts",
    permission="accounts.change_user",
    icon="bi-people",
    lede=(
        "One account per person. Every booking change is recorded against "
        "whoever made it, which only works if logins are not shared."
    ),
    search_fields=["email", "first_name", "last_name"],
    ordering=["email"],
    prefetch_related=["groups"],
    can_delete=False,  # deactivate instead; the audit trail points at these rows
    columns=[
        Column("Name", lambda u: u.get_full_name() or "—", sub="email"),
        Column("Role", lambda u: ", ".join(g.name for g in u.groups.all()) or "—"),
        Column("Superuser", "is_superuser", boolean=True),
        Column("Active", "is_active", boolean=True),
    ],
))

register(Managed(
    slug="customers",
    model=User,
    form_class=forms.CustomerForm,
    label="Customer",
    label_plural="Customers",
    permission="accounts.change_user",
    icon="bi-person-lines-fill",
    lede=(
        "Imported customers have no password until they use the reset link — "
        "passwords were deliberately not carried over from the old system."
    ),
    search_fields=["email", "first_name", "last_name", "phone"],
    ordering=["-date_joined"],
    can_delete=False,
    columns=[
        Column("Name", lambda u: u.get_full_name() or "—", sub="email"),
        Column("Phone", "phone"),
        Column("Bookings", lambda u: u.bookings.count(), align_end=True),
        Column("Joined", lambda u: u.date_joined.strftime("%d %b %Y")),
        Column("Active", "is_active", boolean=True),
    ],
))


def staff_queryset_filter(slug, queryset):
    """
    Staff and customers share one table, so each screen must exclude the other
    or the customer list shows dispatchers and the staff list shows 1,252
    customers.
    """
    if slug == "staff":
        return queryset.filter(is_staff=True)
    if slug == "customers":
        return queryset.filter(is_staff=False)
    return queryset
