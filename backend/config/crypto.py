"""
Encryption for secrets held in the database.

Stripe's secret key authorises charges and refunds against the real account, so
it must not sit in the database in plaintext where a dump, a backup, or an
over-permissive admin screen would expose it. That is a milder version of the
failure that put the legacy site's key in a web-root PHP file.

The encryption key is derived from `DJANGO_SECRET_KEY`, which lives in the
environment and never in the database. Someone with only a database copy cannot
decrypt; they need the running environment too.

Consequence worth knowing: **rotating DJANGO_SECRET_KEY makes stored secrets
unreadable.** They must be re-entered afterwards. `decrypt()` returns None
rather than raising so a bad key degrades to "not configured" instead of a
500 on every page.
"""

from __future__ import annotations

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

logger = logging.getLogger(__name__)

_KEY_INFO = b"austinlimo.payments.secretbox.v1"


def _fernet() -> Fernet:
    """Derive a stable Fernet key from DJANGO_SECRET_KEY."""
    digest = hashlib.sha256(_KEY_INFO + settings.SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(value: str | None) -> str:
    """Encrypt a secret for storage. Empty input stays empty."""
    if not value:
        return ""
    return _fernet().encrypt(value.encode()).decode()


def decrypt(token: str | None) -> str | None:
    """
    Decrypt a stored secret.

    Returns None if the value is unreadable -- typically because
    DJANGO_SECRET_KEY changed since it was written.
    """
    if not token:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except (InvalidToken, ValueError, TypeError):
        logger.error(
            "Stored payment secret could not be decrypted. This usually means "
            "DJANGO_SECRET_KEY changed; the credentials must be re-entered."
        )
        return None


def mask(value: str | None, *, keep: int = 4) -> str:
    """
    Render a secret for display without disclosing it.

    `sk_live_51H...abcd` becomes `sk_live_••••abcd`, which is enough to confirm
    which key is configured and whether it is a live or test key.
    """
    if not value:
        return ""
    prefix = ""
    for known in ("sk_live_", "sk_test_", "pk_live_", "pk_test_", "whsec_"):
        if value.startswith(known):
            prefix = known
            break
    tail = value[-keep:] if len(value) > keep else ""
    return f"{prefix}••••{tail}"
