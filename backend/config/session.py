"""
Path-scoped session cookies.

The storefront (Next.js) authenticates against the API under ``/api/`` using
DRF's ``SessionAuthentication`` -- i.e. an ordinary Django session. The staff
dashboard and Django admin use a Django session too. On a single host (every
port is ``localhost`` in dev; cookies are not scoped by port) both surfaces
would share the one ``sessionid`` cookie -- so signing in as a customer on the
storefront overwrites the staff session, and the dashboard then sees a non-staff
account and answers 403.

Giving ``/api/`` its own cookie name keeps the two logins independent: a
customer session is written to ``mm_store_sessionid`` and is invisible to the
dashboard, which only ever reads ``sessionid`` (and vice versa). This mirrors
production, where the two live on different subdomains and never collide.

This is a faithful subclass of Django 5.2's ``SessionMiddleware`` -- the only
change is that the cookie name is chosen per request instead of read straight
from ``settings.SESSION_COOKIE_NAME``.
"""

import time

from django.conf import settings
from django.contrib.sessions.backends.base import UpdateError
from django.contrib.sessions.exceptions import SessionInterrupted
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date

# Requests under this path get the storefront's own session cookie; everything
# else (dashboard, admin, password-reset) keeps the default cookie.
STOREFRONT_PATH_PREFIX = "/api/"
STOREFRONT_COOKIE_NAME = "mm_store_sessionid"


def cookie_name_for(request) -> str:
    if request.path.startswith(STOREFRONT_PATH_PREFIX):
        return STOREFRONT_COOKIE_NAME
    return settings.SESSION_COOKIE_NAME


class ScopedSessionMiddleware(SessionMiddleware):
    """SessionMiddleware with a per-path cookie name (see module docstring)."""

    def process_request(self, request):
        cookie_name = cookie_name_for(request)
        session_key = request.COOKIES.get(cookie_name)
        request.session = self.SessionStore(session_key)

    def process_response(self, request, response):
        cookie_name = cookie_name_for(request)
        try:
            accessed = request.session.accessed
            modified = request.session.modified
            empty = request.session.is_empty()
        except AttributeError:
            return response
        # Delete the cookie only if the session is entirely empty.
        if cookie_name in request.COOKIES and empty:
            response.delete_cookie(
                cookie_name,
                path=settings.SESSION_COOKIE_PATH,
                domain=settings.SESSION_COOKIE_DOMAIN,
                samesite=settings.SESSION_COOKIE_SAMESITE,
            )
            need_vary_cookie = True
        else:
            need_vary_cookie = accessed
            if (modified or settings.SESSION_SAVE_EVERY_REQUEST) and not empty:
                if request.session.get_expire_at_browser_close():
                    max_age = None
                    expires = None
                else:
                    max_age = request.session.get_expiry_age()
                    expires_time = time.time() + max_age
                    expires = http_date(expires_time)
                # Skip session save for 5xx responses.
                if response.status_code < 500:
                    try:
                        request.session.save()
                    except UpdateError:
                        raise SessionInterrupted(
                            "The request's session was deleted before the "
                            "request completed. The user may have logged "
                            "out in a concurrent request, for example."
                        )
                    response.set_cookie(
                        cookie_name,
                        request.session.session_key,
                        max_age=max_age,
                        expires=expires,
                        domain=settings.SESSION_COOKIE_DOMAIN,
                        path=settings.SESSION_COOKIE_PATH,
                        secure=settings.SESSION_COOKIE_SECURE or None,
                        httponly=settings.SESSION_COOKIE_HTTPONLY or None,
                        samesite=settings.SESSION_COOKIE_SAMESITE,
                    )
                    need_vary_cookie = True
        if need_vary_cookie:
            patch_vary_headers(response, ("Cookie",))
        return response
