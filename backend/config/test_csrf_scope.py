"""
Path-scoped CSRF cookie (config.session.ScopedCsrfMiddleware).

The session cookie is scoped per path so the storefront (/api/) and the staff
dashboard/driver portal can't clobber each other's login. The CSRF cookie must
be scoped the same way: Django's ``login()`` rotates the CSRF token, so with one
site-wide ``csrftoken`` cookie a customer signing in on the storefront would
invalidate the token already baked into an open dashboard or driver form -- the
next staff/driver POST then fails with "CSRF token from POST incorrect".
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from config.session import (
    STOREFRONT_CSRF_COOKIE_NAME,
    csrf_cookie_name_for,
)


class _Req:
    def __init__(self, path):
        self.path = path


def test_cookie_name_is_scoped_by_path():
    assert csrf_cookie_name_for(_Req("/api/auth/csrf/")) == STOREFRONT_CSRF_COOKIE_NAME
    assert csrf_cookie_name_for(_Req("/driver/login/")) == "csrftoken"
    assert csrf_cookie_name_for(_Req("/dashboard/")) == "csrftoken"


@pytest.mark.django_db
def test_api_csrf_endpoint_sets_only_the_storefront_cookie():
    resp = Client().get(reverse("api:csrf"))
    assert STOREFRONT_CSRF_COOKIE_NAME in resp.cookies
    assert "csrftoken" not in resp.cookies


@pytest.mark.django_db
def test_driver_login_page_sets_the_default_cookie():
    resp = Client().get(reverse("driver:login"))
    assert "csrftoken" in resp.cookies
    assert STOREFRONT_CSRF_COOKIE_NAME not in resp.cookies


@pytest.mark.django_db
def test_storefront_login_does_not_clobber_the_staff_csrf_token():
    """The regression: a login under /api/ rotates the storefront token but must
    leave the staff/driver ``csrftoken`` cookie untouched."""
    User = get_user_model()
    User.objects.create_user(email="rider@example.com", password="RiderPass!2026")
    client = Client(enforce_csrf_checks=True)

    # A dashboard/driver page issues the default csrftoken cookie.
    client.get(reverse("driver:login"))
    staff_token = client.cookies["csrftoken"].value

    # Prime + log in on the storefront, which rotates the CSRF token on login().
    client.get(reverse("api:csrf"))
    store_token = client.cookies[STOREFRONT_CSRF_COOKIE_NAME].value
    resp = client.post(
        reverse("api:login"),
        data={"email": "rider@example.com", "password": "RiderPass!2026"},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=store_token,
    )
    assert resp.status_code == 200

    # The storefront token rotated; the staff token did not.
    assert client.cookies[STOREFRONT_CSRF_COOKIE_NAME].value != store_token
    assert client.cookies["csrftoken"].value == staff_token
