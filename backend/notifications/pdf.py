"""
Booking confirmation PDF.

Rendered from the same HTML the confirmation email uses, via xhtml2pdf (pure
Python -- WeasyPrint needs cairo and pango, which cannot be installed on the
target shared host).

Generating the PDF from the email's own template means the attachment and the
message cannot drift apart. The legacy system built its PDFs with a different
library and a different layout, so the two disagreed.
"""

from __future__ import annotations

import logging
from io import BytesIO

from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def render_booking_pdf(booking) -> bytes | None:
    """
    Produce a confirmation PDF, or None if it cannot be rendered.

    A failed attachment must never stop the email: a customer would rather have
    the confirmation without the PDF than not at all.
    """
    try:
        from xhtml2pdf import pisa
    except ImportError:
        logger.warning("xhtml2pdf is not installed; sending without an attachment")
        return None

    html = render_to_string(
        "notifications/pdf/booking_confirmation.html", {"booking": booking},
    )

    buffer = BytesIO()
    try:
        result = pisa.CreatePDF(src=html, dest=buffer, encoding="utf-8")
    except Exception:
        logger.exception("PDF rendering failed for booking %s", booking.reference)
        return None

    if result.err:
        logger.error("PDF rendering reported %s error(s) for %s",
                     result.err, booking.reference)
        return None

    return buffer.getvalue()
