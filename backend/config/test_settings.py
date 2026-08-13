"""
Phase 0 environment guarantees.

These assert the things that are expensive to discover late: that production
settings import at all, that the database really is the version the host runs,
and that no security regression slips into the prod configuration.
"""

import importlib

import pytest
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import connection


def test_dev_settings_import():
    assert importlib.import_module("config.settings.dev")


def test_prod_settings_import(monkeypatch):
    """
    Production settings must import cleanly.

    They intentionally have no default SECRET_KEY -- a missing key should fail
    loudly at boot rather than silently fall back to a shared value -- so the
    required environment is supplied here.
    """
    monkeypatch.setenv("DJANGO_SECRET_KEY", "test-key-for-import-check")
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.com")

    module = importlib.import_module("config.settings.prod")
    importlib.reload(module)

    assert module.DEBUG is False
    assert module.SESSION_COOKIE_SECURE is True
    assert module.CSRF_COOKIE_SECURE is True
    assert module.SECURE_SSL_REDIRECT is True
    assert module.SECURE_HSTS_SECONDS >= 31536000
    assert module.X_FRAME_OPTIONS == "DENY"


def test_prod_requires_secret_key(monkeypatch):
    """An absent SECRET_KEY must raise, not fall back to a default."""
    monkeypatch.delenv("DJANGO_SECRET_KEY", raising=False)
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "example.com")

    module = importlib.import_module("config.settings.prod")
    with pytest.raises(ImproperlyConfigured):
        importlib.reload(module)


def test_custom_user_model_is_configured():
    """
    Retrofitting a custom user model after the first migration means rebuilding
    the database, so this is locked down from Phase 0.
    """
    assert settings.AUTH_USER_MODEL == "accounts.User"


def test_timezone_is_austin():
    assert settings.TIME_ZONE == "America/Chicago"
    assert settings.USE_TZ is True


@pytest.mark.django_db
def test_database_is_mariadb_matching_production():
    """
    Local development must match the InMotion server (10.11.18-MariaDB).
    A version drift here means bugs that only appear in production.
    """
    with connection.cursor() as cur:
        cur.execute("SELECT VERSION()")
        version = cur.fetchone()[0]

    assert "MariaDB" in version, f"expected MariaDB, got {version!r}"
    assert version.startswith("10.11"), (
        f"expected MariaDB 10.11 to match production, got {version!r}"
    )


@pytest.mark.django_db
def test_database_charset_is_utf8mb4():
    """
    The legacy database was latin1 holding UTF-8, which is how 29 of 36 CMS
    pages ended up double-encoded. The new database must be utf8mb4 end to end.
    """
    with connection.cursor() as cur:
        cur.execute("SELECT @@character_set_database, @@collation_database")
        charset, collation = cur.fetchone()

    assert charset == "utf8mb4", f"database charset is {charset!r}"
    assert collation.startswith("utf8mb4"), f"database collation is {collation!r}"


@pytest.mark.django_db
def test_emoji_survives_a_round_trip():
    """Proves utf8mb4 rather than utf8mb3 -- a 4-byte character must survive."""
    from accounts.models import User

    user = User.objects.create_user(email="emoji@example.com", first_name="Zoë 🚗")
    user.refresh_from_db()
    assert user.first_name == "Zoë 🚗"


def test_passenger_entry_point_exists():
    """InMotion's Python app hosting imports `application` from this file."""
    from pathlib import Path

    path = Path(settings.BASE_DIR) / "passenger_wsgi.py"
    assert path.exists(), "passenger_wsgi.py is required by cPanel Python hosting"
    assert "application" in path.read_text()
