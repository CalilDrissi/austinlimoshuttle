"""Local development settings. Never used on a server."""

from .base import *
from .base import env

DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

# Console backend so no mail escapes during development. Real SMTP is
# configured only in prod.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

INTERNAL_IPS = ["127.0.0.1"]

# Password hashing is deliberately NOT weakened here. Development accounts get
# the same PBKDF2 treatment as production; the fast hasher lives in
# settings/test.py where it cannot reach a real database.
