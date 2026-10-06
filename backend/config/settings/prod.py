"""
Production settings, written against InMotion shared hosting.

Kept runnable locally so `manage.py check --deploy --settings=config.settings.prod`
is part of the test suite from Phase 0 rather than a surprise at deploy time.
"""

from .base import *
from .base import env

DEBUG = False

# No default: a missing SECRET_KEY must fail loudly at boot, not silently fall
# back to a shared value.
SECRET_KEY = env("DJANGO_SECRET_KEY")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS")

# WhiteNoise serves the collected static files from inside the container, so the
# reverse proxy doesn't need a static-file mapping. Must sit directly after
# SecurityMiddleware.
MIDDLEWARE = list(MIDDLEWARE)  # noqa: F405 -- from base via star import
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")

# --------------------------------------------------------------------------
# HTTPS / transport
# --------------------------------------------------------------------------
# Passenger terminates TLS upstream, so trust its forwarded proto header.

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # readable by JS so the SPA can send the header
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"

# --------------------------------------------------------------------------
# Static & media
# --------------------------------------------------------------------------
# collectstatic writes into the web root; media stays outside it and is served
# through Django. Publicly-servable archives in the web root are precisely how
# the legacy admin source and Stripe key leaked.

STATIC_ROOT = env("DJANGO_STATIC_ROOT", default="/home/austi118/public_html/static")
MEDIA_ROOT = env("DJANGO_MEDIA_ROOT", default="/home/austi118/media")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # Hashed names + gzip/brotli, served by WhiteNoise.
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# --------------------------------------------------------------------------
# Email -- the existing cPanel mailbox
# --------------------------------------------------------------------------

# Passenger may run several worker processes; a per-process cache would issue
# duplicate billable lookups. Create the table with `manage.py createcachetable`.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    }
}

# Reads SMTP host/credentials from EmailSettings so an administrator can
# change mail hosts in the dashboard without a deployment.
EMAIL_BACKEND = "notifications.backend.ConfigurableEmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="mail.austinlimoshuttle.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")

# Browsable API is a needless attack surface in production.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}

LOGGING["root"]["level"] = env("DJANGO_LOG_LEVEL", default="WARNING")
