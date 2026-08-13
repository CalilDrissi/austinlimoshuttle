"""
Import CMS pages, banners, testimonials, gallery images and enquiries.

The mojibake repair matters most here: 29 of the 36 legacy pages contain
double-encoded UTF-8, and it is their meta descriptions that search engines
currently see with visible `â€™` corruption.

Slugs are preserved byte-identically, including the two malformed ones
(`wwwaustinlimoshuttlecom`, `httpswwwaustinlimoshuttlecom` -- URLs with their
punctuation stripped). Rankings depend on URLs not changing.

Eight legacy rows point at PHP templates that no longer exist (login.php,
lead_driver.php, confirm_driver_details.php, cancel_transaction.php,
contributor.php, edit_dashboard.php, login-or-register.php,
add_driver_details.php). Those routes are already broken on the live site and
are not imported.
"""

from datetime import datetime

from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from content.models import Banner, GalleryImage, Page, SiteSettings, Testimonial
from enquiries.models import ContactMessage
from legacy_import.base import ImportReport, LegacyImportCommand
from legacy_import.legacy_db import fetch_all
from legacy_import.text import clean, clean_email, clean_phone

# Legacy `template` -> new page type. Anything else falls back to STANDARD.
TEMPLATE_TO_PAGE_TYPE = {
    "home.php": Page.PageType.HOME,
    "services.php": Page.PageType.SERVICE,
    "content_page.php": Page.PageType.STANDARD,
    "fleet.php": Page.PageType.STANDARD,
    "contact.php": Page.PageType.STANDARD,
}

LEGAL_SLUGS = {"privacy-policy", "terms-conditions"}

# Templates referenced by the CMS that do not exist as files.
MISSING_TEMPLATES = {
    "login.php", "lead_driver.php", "confirm_driver_details.php",
    "cancel_transaction.php", "contributor.php", "edit_dashboard.php",
    "login-or-register.php", "add_driver_details.php",
}

# Funnel and account pages: routing is the frontend's job now, so they are not
# content pages.
FUNNEL_MENU_FLAGS = {"D", "C"}

MENU_FLAG_MAP = {
    "Y": Page.MenuPlacement.MAIN,
    "N": Page.MenuPlacement.NONE,
}


class Command(LegacyImportCommand):
    help = "Import CMS pages, media and enquiries, repairing double-encoded text."
    label = "Content"

    def run_import(self, report: ImportReport) -> None:
        self._import_pages(report)
        self._import_banners(report)
        self._import_testimonials(report)
        self._import_gallery(report)
        self._import_settings(report)
        self._import_enquiries(report)

    # -- pages -------------------------------------------------------------

    def _import_pages(self, report: ImportReport) -> None:
        rows = self.apply_limit(fetch_all("""
            SELECT id, name, `desc`, template, page_title, meta_title,
                   meta_keyword, meta_description, url_title, order_id,
                   for_menu, status
            FROM limousin_cms
            ORDER BY id
        """))

        for row in rows:
            template = (clean(row.get("template")) or "").strip()

            if template in MISSING_TEMPLATES:
                report.skip(
                    f"cms id={row['id']}: template {template} does not exist "
                    f"(route already broken on the live site)"
                )
                continue

            if (row.get("for_menu") or "").strip() in FUNNEL_MENU_FLAGS:
                report.skip(
                    f"cms id={row['id']}: funnel/account page ({template}) — "
                    f"routing now belongs to the frontend"
                )
                continue

            slug = clean(row.get("url_title"), max_length=200)
            if not slug:
                report.skip(f"cms id={row['id']}: no slug")
                continue

            page_type = TEMPLATE_TO_PAGE_TYPE.get(template, Page.PageType.STANDARD)
            if slug in LEGAL_SLUGS:
                page_type = Page.PageType.LEGAL

            clash = Page.objects.filter(slug=slug).exclude(legacy_cms_id=row["id"]).first()
            if clash:
                report.skip(f"cms id={row['id']}: slug {slug!r} already used")
                continue

            _, created = Page.objects.update_or_create(
                legacy_cms_id=row["id"],
                defaults={
                    "slug": slug,
                    "title": clean(row.get("name"), max_length=255) or slug,
                    "page_type": page_type,
                    # repaired by clean()
                    "body": clean(row.get("desc")),
                    "meta_title": clean(row.get("meta_title"), max_length=255),
                    "meta_description": clean(row.get("meta_description")),
                    "meta_keywords": clean(row.get("meta_keyword")),
                    "menu_placement": MENU_FLAG_MAP.get(
                        (row.get("for_menu") or "").strip(), Page.MenuPlacement.NONE,
                    ),
                    "display_order": self._as_int(row.get("order_id")),
                    "is_published": row.get("status") == "Y",
                },
            )
            report.created += int(created)
            report.updated += int(not created)

    # -- media --------------------------------------------------------------

    def _import_banners(self, report: ImportReport) -> None:
        for row in fetch_all("SELECT * FROM limousin_banner ORDER BY id"):
            _, created = Banner.objects.update_or_create(
                legacy_banner_id=row["id"],
                defaults={
                    "title": clean(row.get("banner_title"), max_length=200),
                    "description": clean(row.get("description")),
                    "display_order": self._as_int(row.get("order_no")),
                    "is_active": row.get("status") == "Y",
                },
            )
            report.created += int(created)
            report.updated += int(not created)

    def _import_testimonials(self, report: ImportReport) -> None:
        for row in fetch_all("SELECT * FROM limousin_castomer ORDER BY id"):
            _, created = Testimonial.objects.update_or_create(
                legacy_testimonial_id=row["id"],
                defaults={
                    "customer_name": clean(row.get("customer_name"), max_length=200)
                                     or "Anonymous",
                    "quote": clean(row.get("description")),
                    "rating": self._rating(row.get("rating")),
                    "is_published": row.get("status") == "Y",
                },
            )
            report.created += int(created)
            report.updated += int(not created)

    def _import_gallery(self, report: ImportReport) -> None:
        for row in fetch_all("SELECT * FROM limousin_gallery ORDER BY id"):
            _, created = GalleryImage.objects.update_or_create(
                legacy_gallery_id=row["id"],
                defaults={
                    "title": clean(row.get("name"), max_length=200),
                    "description": clean(row.get("description")),
                    "category": (
                        GalleryImage.Category.PARTNER
                        if row.get("partrers") == "P"  # legacy misspelling
                        else GalleryImage.Category.GALLERY
                    ),
                    "display_order": self._as_int(row.get("order_no")),
                    "is_active": row.get("status") == "Y",
                },
            )
            report.created += int(created)
            report.updated += int(not created)

    def _import_settings(self, report: ImportReport) -> None:
        settings_obj = SiteSettings.load()
        rows = fetch_all("SELECT * FROM limousin_social_media ORDER BY id LIMIT 1")
        if rows:
            row = rows[0]
            settings_obj.facebook = clean(row.get("facebook"))[:200]
            settings_obj.twitter = clean(row.get("twitter"))[:200]
            settings_obj.linkedin = clean(row.get("linkedin"))[:200]

        admin_rows = fetch_all("SELECT email FROM limousin_admin ORDER BY id LIMIT 1")
        if admin_rows:
            email = clean_email(admin_rows[0].get("email"))
            settings_obj.contact_email = email
            settings_obj.ops_notification_email = email

        settings_obj.save()
        report.updated += 1

    # -- enquiries ----------------------------------------------------------

    def _import_enquiries(self, report: ImportReport) -> None:
        sources = [
            ("limousin_contact_us", ContactMessage.Nature.GENERAL),
            ("limousin_service_inquiry", ContactMessage.Nature.SERVICE),
        ]

        for table, nature in sources:
            for row in fetch_all(f"SELECT * FROM `{table}` ORDER BY id"):  # noqa: S608
                email = clean_email(row.get("email"))
                if not email or "@" not in email:
                    report.skip(f"{table} id={row['id']}: unusable email")
                    continue

                _, created = ContactMessage.objects.update_or_create(
                    legacy_table=table, legacy_row_id=row["id"],
                    defaults={
                        "name": clean(row.get("name"), max_length=255) or "Unknown",
                        "email": email,
                        "phone": clean_phone(row.get("phone")),
                        "nature": nature,
                        "subject": clean(row.get("subject"), max_length=255),
                        "message": clean(row.get("message")),
                        "source_ip": self._ip(row.get("clint_ip")),
                        "created_at": self._aware(row.get("post_date")),
                    },
                )
                report.created += int(created)
                report.updated += int(not created)

        # Corporate applications become enquiries with a discriminator.
        for row in fetch_all("SELECT * FROM limousin_corporate_account ORDER BY id"):
            email = clean_email(row.get("email"))
            if not email or "@" not in email:
                report.skip(f"corporate id={row['id']}: unusable email")
                continue

            message_parts = [clean(row.get("message"))]
            if address := clean(row.get("address")):
                message_parts.append(f"Address: {address}")
            if alt := clean_phone(row.get("alt_phone")):
                message_parts.append(f"Alt phone: {alt}")

            _, created = ContactMessage.objects.update_or_create(
                legacy_table="limousin_corporate_account", legacy_row_id=row["id"],
                defaults={
                    "name": clean(row.get("name"), max_length=255) or "Unknown",
                    "email": email,
                    "phone": clean_phone(row.get("phone")),
                    "nature": ContactMessage.Nature.CORPORATE,
                    "subject": "Corporate account application",
                    "message": "\n".join(p for p in message_parts if p),
                    "company_name": clean(row.get("company_name"), max_length=255),
                    "created_at": self._aware(row.get("post_date")),
                },
            )
            report.created += int(created)
            report.updated += int(not created)

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _as_int(value) -> int:
        text = clean(value)
        digits = "".join(ch for ch in text if ch.isdigit())
        return int(digits) if digits else 0

    @staticmethod
    def _rating(value):
        text = clean(value)
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            return None
        rating = int(digits[0])
        return rating if 1 <= rating <= 5 else None  # noqa: PLR2004

    @staticmethod
    def _ip(value):
        text = clean(value)
        if not text:
            return None
        candidate = text.split(",")[0].strip()
        # Only store something that is plausibly an address.
        if all(part.isdigit() for part in candidate.split(".")) and \
                candidate.count(".") == 3:  # noqa: PLR2004
            return candidate
        return None

    @staticmethod
    def _aware(value):
        """
        Coerce a legacy timestamp to an aware datetime.

        `limousin_contact_us.post_date` is a real TIMESTAMP, but
        `limousin_corporate_account.post_date` is a varchar, so this receives
        both datetimes and free-text strings.
        """
        if not value:
            return timezone.now()

        if isinstance(value, str):
            # MySQL zero-dates ("0000-00-00") parse to year 0, which datetime
            # rejects. Legacy allowed them, so treat any unusable value as
            # "unknown" rather than failing the whole import.
            try:
                parsed = parse_datetime(value)
                if parsed is None and (parsed_date := parse_date(value)):
                    parsed = datetime.combine(parsed_date, datetime.min.time())
            except ValueError:
                parsed = None

            if parsed is None:
                return timezone.now()
            value = parsed

        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_default_timezone())
        return value
