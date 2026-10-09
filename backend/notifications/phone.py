"""Phone-number normalisation to E.164 for SMS delivery (US default)."""

import re


def to_e164(phone: str | None, default_country: str = "1") -> str | None:
    """
    Normalise a phone to E.164 (e.g. "(512) 555-0142" -> "+15125550142").

    Returns None if it can't be made into a plausible number. US is assumed when
    no country code is given, which is correct for this Austin operator.
    """
    if not phone:
        return None
    raw = phone.strip()
    if raw.startswith("+"):
        digits = re.sub(r"\D", "", raw)
        return f"+{digits}" if len(digits) >= 8 else None  # noqa: PLR2004

    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:  # noqa: PLR2004  -- bare US number
        return f"+{default_country}{digits}"
    if len(digits) == 11 and digits.startswith("1"):  # noqa: PLR2004
        return f"+{digits}"
    if 8 <= len(digits) <= 15:  # noqa: PLR2004  -- already includes a country code
        return f"+{digits}"
    return None
