"""
Read-only access to the sanitised legacy replica.

Kept outside Django's DATABASES on purpose: the legacy schema is not managed by
migrations, has no models, and must never be written to. A plain PyMySQL
connection makes that explicit.

The replica is *sanitised* -- card numbers reduced to last-4, expiry dates
cleared, CVV destroyed, passwords replaced. `assert_sanitised()` re-checks that
at import time rather than trusting the filename.
"""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from typing import Any

import pymysql
from django.conf import settings


class LegacyDataError(Exception):
    """Raised when the legacy replica is missing, unreadable, or unsanitised."""


@contextlib.contextmanager
def legacy_connection() -> Iterator[pymysql.connections.Connection]:
    """Open a read-only connection to the legacy replica."""
    cfg = settings.LEGACY_DATABASE
    try:
        conn = pymysql.connect(
            host=cfg["HOST"],
            port=int(cfg["PORT"]),
            user=cfg["USER"],
            password=cfg["PASSWORD"],
            database=cfg["NAME"],
            charset="latin1",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )
    except pymysql.Error as exc:
        raise LegacyDataError(
            f"Cannot reach the legacy replica ({cfg['NAME']} on "
            f"{cfg['HOST']}:{cfg['PORT']}). Is the container up and loaded? "
            f"Try: ./ops/load-legacy.sh\n  {exc}"
        ) from exc

    # PyMySQL maps MySQL's "latin1" onto Python's cp1252 codec, following
    # MySQL's own convention. But cp1252 leaves 0x81, 0x8d, 0x8f, 0x90 and 0x9d
    # undefined, and those bytes occur in exactly the rows we need to repair --
    # so the default decoding raises UnicodeDecodeError and the import dies.
    #
    # latin-1 maps every byte 0x00-0xFF onto the code point of the same value,
    # losing nothing. repair_mojibake() re-encodes to latin-1 to recover the
    # original UTF-8 sequence, so this is the codec the repair logic expects.
    #
    # Overriding the codec (rather than passing use_unicode=False) keeps
    # PyMySQL's type converters working: with raw bytes, DECIMAL and DATE
    # columns fail to convert.
    conn.encoding = "latin-1"

    try:
        yield conn
    finally:
        conn.close()


def _decode_row(row: dict[str, Any]) -> dict[str, Any]:
    """Belt and braces: decode any column PyMySQL still hands back as bytes."""
    return {
        key: value.decode("latin-1") if isinstance(value, bytes | bytearray) else value
        for key, value in row.items()
    }


def fetch_all(sql: str, params: tuple | None = None) -> list[dict[str, Any]]:
    with legacy_connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params or ())
        return [_decode_row(row) for row in cur.fetchall()]


def table_exists(name: str) -> bool:
    rows = fetch_all(
        "SELECT COUNT(*) AS n FROM information_schema.tables "
        "WHERE table_schema = %s AND table_name = %s",
        (settings.LEGACY_DATABASE["NAME"], name),
    )
    return bool(rows and rows[0]["n"])


def assert_sanitised() -> None:
    """
    Refuse to run against a replica still holding cardholder data.

    The importers never read card columns, but an unsanitised replica on a
    developer's machine is itself the problem this project exists to remove.
    """
    checks = [
        ("limousin_order", "card_number REGEXP '^[0-9]{13,19}$'", "card numbers"),
        ("limousin_orderdetails", "card_number REGEXP '^[0-9]{13,19}$'", "card numbers"),
        ("limousin_orderdetails", "securitycode <> ''", "security codes (CVV)"),
    ]

    offences = []
    for table, predicate, label in checks:
        if not table_exists(table):
            continue
        rows = fetch_all(f"SELECT COUNT(*) AS n FROM `{table}` WHERE {predicate}")  # noqa: S608
        count = rows[0]["n"] if rows else 0
        if count:
            offences.append(f"{count} {label} in {table}")

    if offences:
        raise LegacyDataError(
            "The legacy replica still contains cardholder data: "
            + "; ".join(offences)
            + ". Load the sanitised dump instead (./ops/load-legacy.sh)."
        )
