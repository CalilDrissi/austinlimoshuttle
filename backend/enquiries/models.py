"""
Enquiries.

Merges three near-identical legacy tables into one with a discriminator:
`limousin_contact_us` (923 rows), `limousin_service_inquiry` (8) and
`limousin_corporate_account` (3).

Adds read/replied state, which legacy had no concept of -- staff could not tell
an answered enquiry from an unanswered one.
"""

from django.conf import settings
from django.db import models


class ContactMessage(models.Model):
    """An enquiry submitted through a public form."""

    class Nature(models.TextChoices):
        GENERAL = "general", "General enquiry"
        SERVICE = "service", "Service enquiry"
        CORPORATE = "corporate", "Corporate account"

    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=32, blank=True)

    nature = models.CharField(
        max_length=30, choices=Nature.choices, default=Nature.GENERAL, db_index=True,
    )
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()

    company_name = models.CharField(
        max_length=255, blank=True, help_text="Corporate enquiries only.",
    )

    source_ip = models.GenericIPAddressField(
        null=True, blank=True,
        help_text="Legacy `clint_ip` (sic), stored as free text.",
    )

    is_read = models.BooleanField(default=False, db_index=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="enquiries_replied",
    )
    reply_body = models.TextField(blank=True)

    legacy_table = models.CharField(
        max_length=40, blank=True, help_text="Which legacy table this came from.",
    )
    legacy_row_id = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(db_index=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            # Deliberately NOT a conditional constraint. MariaDB has no partial
            # indexes, so Django silently drops `condition=...` on this backend
            # and the guard would not exist at all.
            #
            # A plain unique constraint gives the behaviour we want anyway:
            # MySQL/MariaDB treat NULLs as distinct in a unique index, so rows
            # created through the website (legacy_row_id IS NULL) are never
            # constrained, while imported rows cannot be duplicated.
            models.UniqueConstraint(
                fields=["legacy_table", "legacy_row_id"],
                name="unique_legacy_enquiry",
            ),
        ]
        indexes = [models.Index(fields=["is_read", "-created_at"])]

    def __str__(self):
        return f"{self.name} — {self.subject or self.get_nature_display()}"

    @property
    def is_answered(self) -> bool:
        return self.replied_at is not None
