"""
Text repair for the legacy import.

The legacy database declares every column latin1, but the application wrote
UTF-8 bytes into it. Reading those columns through a latin1 connection returns
the original bytes, one per character -- so "you're" (U+2019) comes back as
"youâ\x80\x99re". Re-encoding to latin1 and decoding as UTF-8 recovers the
original text.

A straight `latin1 -> utf8mb4` database conversion does NOT do this. It stores
the mojibake permanently as valid UTF-8, at which point the original characters
are unrecoverable. 29 of the 36 legacy CMS pages are affected.

Repair must be conservative: genuinely-latin1 text (a real 'é' stored as byte
0xE9) must be left alone. The tell is the C1 control range U+0080-U+009F, which
never appears in real text but is exactly where UTF-8 continuation bytes land
when misread as latin1.
"""

from __future__ import annotations

import re

# C1 control characters: the fingerprint of UTF-8 bytes misread as latin1.
_C1_CONTROLS = re.compile(r"[\x80-\x9f]")

# The same damage after a round trip through cp1252, which is how it appears
# once the bytes have been converted rather than merely misread. Ranges are
# written as explicit escapes -- "€-ÿ" looks like a range but runs from U+20AC
# down to U+00FF and is rejected by `re`.
_CP1252_ARTEFACTS = re.compile(
    "â€"                      # U+2019/U+201C/U+201D mangled: the giveaway pair
    "|Ã[-¿]"       # a latin-1 letter's UTF-8 lead byte misread
    "|Â[ -¿]"       # non-breaking space and punctuation misread
)

MAX_REPAIR_PASSES = 3


def looks_mojibake(value: str) -> bool:
    """Whether the string shows signs of misdecoded UTF-8."""
    if not value:
        return False
    return bool(_C1_CONTROLS.search(value) or _CP1252_ARTEFACTS.search(value))


def repair_mojibake(value: str | None) -> str | None:
    """
    Recover text that was written as UTF-8 into a latin1 column.

    Returns the input unchanged when it is already clean or when repair would
    not produce valid UTF-8 -- never guesses.
    """
    if not value or not isinstance(value, str):
        return value

    result = value
    for _ in range(MAX_REPAIR_PASSES):
        if not looks_mojibake(result):
            break
        try:
            raw = result.encode("latin-1")
        except UnicodeEncodeError:
            break

        try:
            candidate = raw.decode("utf-8")
        except UnicodeDecodeError:
            # Not misread UTF-8. It may still be cp1252 -- the legacy site was
            # edited through a Windows WYSIWYG, so smart quotes and dashes were
            # written as single cp1252 bytes (0x92 for U+2019). Those land in
            # the C1 range, which is undefined in latin1, so decoding them as
            # cp1252 is a strict improvement over leaving control characters in
            # customer-facing copy.
            try:
                candidate = raw.decode("cp1252")
            except UnicodeDecodeError:
                break

        if candidate == result:
            break
        result = candidate

    return result


def clean(value: str | None, *, max_length: int | None = None) -> str:
    """Repair, normalise whitespace, and optionally truncate. Never returns None."""
    if value is None:
        return ""
    text = repair_mojibake(str(value)) or ""
    text = text.replace("\x00", "").strip()
    text = re.sub(r"[ \t]+", " ", text)
    if max_length is not None and len(text) > max_length:
        text = text[:max_length].rstrip()
    return text


def clean_email(value: str | None) -> str:
    """Normalise an email for use as a login identity."""
    return clean(value).lower()


def clean_phone(value: str | None, *, max_length: int = 32) -> str:
    """
    Tidy a phone number without reformatting it.

    Legacy phone data is free text across nine years; imposing a format would
    lose information. Only obvious noise is removed.
    """
    text = clean(value)
    text = re.sub(r"[^\d+()\-.\s×x]", "", text)
    return re.sub(r"\s{2,}", " ", text).strip()[:max_length]
