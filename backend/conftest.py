"""
Shared pytest fixtures.

The storefront API (``/api/``) authenticates under its own session cookie
(``mm_store_sessionid``) via ``config.session.ScopedSessionMiddleware`` -- see
that module for why the dashboard and the storefront keep separate logins.

Django's test ``Client.login()`` only sets the default ``sessionid`` cookie, so
an authenticated client is *not* recognised on ``/api/`` paths. The real
storefront logs in through ``POST /api/auth/login/``, which sets the scoped
cookie; mirroring the cookie here reproduces that without every test having to
round-trip the login endpoint.
"""

import pytest
from django.conf import settings
from django.test import Client as DjangoClient

from config.session import STOREFRONT_COOKIE_NAME


class ScopedClient(DjangoClient):
    """A test client whose login also authenticates the scoped ``/api/`` cookie."""

    def login(self, **credentials):
        ok = super().login(**credentials)
        if ok and settings.SESSION_COOKIE_NAME in self.cookies:
            self.cookies[STOREFRONT_COOKIE_NAME] = self.cookies[settings.SESSION_COOKIE_NAME].value
        return ok


@pytest.fixture
def client():
    return ScopedClient()
