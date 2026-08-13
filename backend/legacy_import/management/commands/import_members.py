"""
Import customer accounts.

Deliberately does NOT read `limousin_member.password`. Legacy stored passwords
in plaintext; importing them in any form would carry the vulnerability forward.
Every imported account lands with an unusable password and must reset before
signing in.

Legacy facts established during the audit:
  * `email` is the login identity (execute_function.php:470 compares with
    BINARY, so the old login was case-sensitive).
  * All 1,251 addresses are distinct even when lowercased, so normalising is
    safe and fixes the "Jo@x.com != jo@x.com" trap.
  * `user_email` is empty in every row. Not read.
  * `plan_*` columns are subscription fields from the CMS template this was
    built from; no subscription product exists. Not read.
"""

from django.contrib.auth import get_user_model
from django.utils import timezone

from accounts.models import BillingAddress
from legacy_import.base import ImportReport, LegacyImportCommand
from legacy_import.legacy_db import fetch_all
from legacy_import.text import clean, clean_email, clean_phone

User = get_user_model()

ISO_COUNTRY_CODE_LENGTH = 2

TITLE_MAP = {
    "mr": "mr", "mr.": "mr", "mister": "mr",
    "mrs": "mrs", "mrs.": "mrs",
    "ms": "ms", "ms.": "ms",
    "miss": "miss",
    "dr": "dr", "dr.": "dr", "doctor": "dr",
}


class Command(LegacyImportCommand):
    help = "Import customers from limousin_member. Passwords are never read."
    label = "Members"

    def run_import(self, report: ImportReport) -> None:
        # Column list is explicit so that `password` cannot be pulled in by a
        # future SELECT *.
        rows = self.apply_limit(fetch_all("""
            SELECT id, pfix, fname, lname, email, phone,
                   bill_address, bill_street_name, bill_city, bill_zip, bill_country,
                   terms, status, date
            FROM limousin_member
            ORDER BY id
        """))

        seen_emails: set[str] = set()

        for row in rows:
            email = clean_email(row.get("email"))
            if not email or "@" not in email:
                report.skip(f"member id={row['id']}: unusable email {row.get('email')!r}")
                continue

            if email in seen_emails:
                report.skip(f"member id={row['id']}: duplicate email {email}")
                continue
            seen_emails.add(email)

            # Guard against colliding with an account already imported under a
            # different legacy id.
            clash = User.objects.filter(email=email).exclude(
                legacy_member_id=row["id"]
            ).first()
            if clash:
                report.skip(
                    f"member id={row['id']}: email {email} already belongs to "
                    f"legacy id {clash.legacy_member_id}"
                )
                continue

            user, created = User.objects.update_or_create(
                legacy_member_id=row["id"],
                defaults={
                    "email": email,
                    "title": self._map_title(row.get("pfix")),
                    "first_name": clean(row.get("fname"), max_length=150),
                    "last_name": clean(row.get("lname"), max_length=150),
                    "phone": clean_phone(row.get("phone")),
                    "is_active": row.get("status") != "N",
                    "is_staff": False,
                    "marketing_opt_in": False,
                    "date_joined": self._joined(row.get("date")),
                },
            )

            if created:
                # No password argument at all: the account cannot authenticate
                # until the customer completes a reset.
                user.set_unusable_password()
                user.save(update_fields=["password"])
                report.created += 1
            else:
                report.updated += 1

            self._sync_address(user, row)

    # -- helpers -----------------------------------------------------------

    def _sync_address(self, user, row: dict) -> None:
        line1 = clean(row.get("bill_address"), max_length=255)
        line2 = clean(row.get("bill_street_name"), max_length=255)
        city = clean(row.get("bill_city"), max_length=120)
        postal = clean(row.get("bill_zip"), max_length=20)
        country = clean(row.get("bill_country"), max_length=64)

        if not any([line1, line2, city, postal]):
            return

        BillingAddress.objects.update_or_create(
            user=user,
            is_default=True,
            defaults={
                "line1": line1,
                "line2": line2,
                "city": city,
                "postal_code": postal,
                "country": self._country_code(country),
            },
        )

    @staticmethod
    def _map_title(value) -> str:
        return TITLE_MAP.get(clean(value).lower().strip(), "")

    @staticmethod
    def _country_code(value: str) -> str:
        text = (value or "").strip()
        if len(text) == ISO_COUNTRY_CODE_LENGTH and text.isalpha():
            return text.upper()
        if text.lower() in {"usa", "united states", "united states of america", "us"}:
            return "US"
        return "US"

    @staticmethod
    def _joined(value):
        if not value:
            return timezone.now()
        if timezone.is_naive(value):
            return timezone.make_aware(value, timezone.get_default_timezone())
        return value
