"""
Email backend that reads its SMTP settings from the database.

Django's SMTP backend takes host, port and credentials from settings at import
time. Ours reads `EmailSettings` on each connection, so an administrator can
change mail hosts in the dashboard and the next message uses them -- no
deployment, no restart.

Falls back to the values in Django settings when nothing is configured, so a
development machine keeps working with the console backend.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as SMTPBackend

logger = logging.getLogger(__name__)


class ConfigurableEmailBackend(SMTPBackend):
    """SMTP backend configured from `EmailSettings`."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._apply_database_settings()

    def _apply_database_settings(self) -> None:
        # Imported here: the backend is constructed during app startup in some
        # code paths, before the model registry is ready.
        from .models import EmailSettings

        try:
            config = EmailSettings.load()
        except Exception:
            logger.warning("Email settings unavailable; using values from settings.py")
            return

        if not config.is_enabled or not config.host:
            return

        self.host = config.host
        self.port = config.port
        self.username = config.username or ""
        self.password = config.password or ""
        self.use_tls = config.use_tls
        self.use_ssl = config.use_ssl
        self.timeout = config.timeout_seconds or settings.EMAIL_TIMEOUT

        # Django rejects both at once, and so does every mail server.
        if self.use_ssl and self.use_tls:
            self.use_tls = False
