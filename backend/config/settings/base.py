"""
Settings shared by every environment.

Environment-specific modules (dev.py, prod.py) import * from here and override.
Nothing secret belongs in this file -- secrets come from the environment, read
via django-environ. The legacy application hardcoded its Stripe key and database
password into a file inside the web root; that is the failure mode this avoids.
"""

from pathlib import Path

import environ
import pymysql

# PyMySQL stands in for mysqlclient, which needs a C compiler and
# libmysqlclient headers that shared hosting does not provide.
pymysql.install_as_MySQLdb()

# backend/config/settings/base.py -> backend/
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BASE_DIR.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-override-in-env")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

# --------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
]

THIRD_PARTY_APPS = [
    "rest_framework",
]

LOCAL_APPS = [
    "accounts",
    "fleet",
    "pricing",
    "bookings",
    "payments",
    "content",
    "enquiries",
    "dashboard",
    "api",
    "legacy_import",
    "notifications",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "dashboard.context_processors.staff_context",
            ],
        },
    },
]

# --------------------------------------------------------------------------
# Database
# --------------------------------------------------------------------------
# MariaDB 10.11 -- matches the InMotion production server exactly
# (verified: 10.11.18-MariaDB). Do not bump without checking the host.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": env("DB_NAME", default="austinlimo"),
        "USER": env("DB_USER", default="austinlimo"),
        "PASSWORD": env("DB_PASSWORD", default="localdevonly"),
        "HOST": env("DB_HOST", default="127.0.0.1"),
        "PORT": env("DB_PORT", default="3307"),
        "OPTIONS": {
            "charset": "utf8mb4",
            # STRICT_TRANS_TABLES turns silent truncation into an error. The
            # legacy schema relied on MySQL quietly accepting oversized values.
            "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
        },
        "TEST": {
            "CHARSET": "utf8mb4",
            "COLLATION": "utf8mb4_unicode_ci",
        },
    }
}

# Read-only connection to the sanitised legacy replica, used only by the
# importers in legacy_import/. Never written to.
LEGACY_DATABASE = {
    "NAME": env("LEGACY_DB_NAME", default="austi118_austinlimo"),
    "USER": env("LEGACY_DB_USER", default="austinlimo"),
    "PASSWORD": env("LEGACY_DB_PASSWORD", default="localdevonly"),
    "HOST": env("LEGACY_DB_HOST", default="127.0.0.1"),
    "PORT": env.int("LEGACY_DB_PORT", default=3307),
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------
# Authentication
# --------------------------------------------------------------------------
# Set before the first migration. Retrofitting a custom user model later means
# rebuilding the database.

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "admin:login"
LOGIN_REDIRECT_URL = "/"

# --------------------------------------------------------------------------
# Internationalisation
# --------------------------------------------------------------------------
# The business operates in Austin, Texas. Bookings are stored in UTC and
# rendered in local time; the legacy system stored formatted local-time strings
# with no timezone at all.

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Chicago"
USE_I18N = True
USE_TZ = True

# --------------------------------------------------------------------------
# Static & media
# --------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = env("DJANGO_STATIC_ROOT", default=str(PROJECT_ROOT / "staticfiles"))
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").exists() else []

MEDIA_URL = "/media/"
# Deliberately outside any web-servable directory. On InMotion this must NOT
# live under public_html -- uploaded files are served through Django.
MEDIA_ROOT = env("DJANGO_MEDIA_ROOT", default=str(PROJECT_ROOT / "media"))

# --------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------

EMAIL_BACKEND = env("DJANGO_EMAIL_BACKEND",
                    default="django.core.mail.backends.console.EmailBackend")
DEFAULT_FROM_EMAIL = env("DJANGO_DEFAULT_FROM_EMAIL",
                         default="bookings@austinlimoshuttle.com")

# --------------------------------------------------------------------------
# REST framework
# --------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/hour",
        "user": "1000/day",
        "quote": "30/hour",
        "enquiry": "10/hour",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# --------------------------------------------------------------------------
# Business rules
# --------------------------------------------------------------------------
# Legacy hardcoded these mileage band boundaries as PHP constants
# (ADJUST_DISTANCE etc.), so changing a pricing tier required a code edit. They
# are seed values here: Phase 1 expands them into editable DistanceBand rows.

LEGACY_DISTANCE_BANDS = [0, 6, 50, 100]

# How long a fare quote stays valid before the customer must re-quote.
QUOTE_TTL_MINUTES = env.int("QUOTE_TTL_MINUTES", default=30)

# Google Distance Matrix. Read server-side only -- this key must never be
# rendered into a page. The legacy site embedded it in client-side JavaScript,
# which is why it should be replaced with a fresh, IP-restricted key before
# launch (see docs/qa/phase-9.md).
GOOGLE_MAPS_API_KEY = env("GOOGLE_MAPS_API_KEY", default="")

# Distance lookups are cached: the same airport-to-downtown pair is requested
# constantly and each call is billable. LocMem is per-process, which is fine for
# development; production uses the database so all Passenger workers share it.
CACHES = {
    "default": {
        "BACKEND": env(
            "DJANGO_CACHE_BACKEND",
            default="django.core.cache.backends.locmem.LocMemCache",
        ),
        "LOCATION": env("DJANGO_CACHE_LOCATION", default="austinlimo-cache"),
    }
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "{levelname} {asctime} {name} {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
}
