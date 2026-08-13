"""
PayPal credential verification.

Scope note: this module verifies credentials. It does **not** create orders,
capture payments or handle webhooks — the PayPal checkout flow is not wired up.
Stripe is the working gateway. See docs/qa/phase-14.md.

The reason a verification helper exists at all: PayPal client ids and secrets
carry no prefix identifying them as sandbox or live, unlike Stripe's
`sk_live_` / `sk_test_`. So a mode/credential mismatch cannot be caught by
inspecting the strings — the only way to know is to authenticate against the
chosen environment and see whether it accepts them.
"""

from __future__ import annotations

import logging

import requests
from django.utils import timezone

from .models import PayPalSettings

logger = logging.getLogger(__name__)

OAUTH_ENDPOINT = "/v1/oauth2/token"
REQUEST_TIMEOUT_SECONDS = 12


class PayPalConfigurationError(Exception):
    """PayPal is not configured, or the credentials were rejected."""


def fetch_access_token(config: PayPalSettings | None = None) -> str:
    """
    Exchange the client credentials for an OAuth token.

    Raises `PayPalConfigurationError` with a message safe to show an
    administrator (never a customer).
    """
    config = config or PayPalSettings.load()

    client_id = config.client_id
    client_secret = config.client_secret
    if not client_id or not client_secret:
        raise PayPalConfigurationError(
            "A client ID and secret are required before PayPal can be used."
        )

    try:
        response = requests.post(
            f"{config.api_base}{OAUTH_ENDPOINT}",
            auth=(client_id, client_secret),
            data={"grant_type": "client_credentials"},
            headers={"Accept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.Timeout as exc:
        raise PayPalConfigurationError("PayPal did not respond. Try again.") from exc
    except requests.RequestException as exc:
        logger.warning("PayPal token request failed: %s", exc)
        raise PayPalConfigurationError("Could not reach PayPal.") from exc

    if response.status_code == 401:  # noqa: PLR2004
        # The most common real cause is live credentials against the sandbox
        # endpoint, or the reverse -- worth saying so rather than just "invalid".
        raise PayPalConfigurationError(
            f"PayPal rejected these credentials for the {config.get_mode_display()} "
            f"environment. Check the client ID and secret belong to a "
            f"{config.get_mode_display().lower()} app."
        )

    if not response.ok:
        detail = ""
        try:
            body = response.json()
            detail = body.get("error_description") or body.get("message") or ""
        except ValueError:
            detail = ""
        raise PayPalConfigurationError(
            f"PayPal returned HTTP {response.status_code}."
            + (f" {detail}" if detail else "")
        )

    try:
        token = response.json()["access_token"]
    except (ValueError, KeyError) as exc:
        raise PayPalConfigurationError("PayPal returned an unreadable reply.") from exc

    return token


def verify_credentials(config: PayPalSettings | None = None) -> tuple[bool, str]:
    """
    Check the stored credentials and record the outcome.

    Returns (ok, message). Never raises — this is called from a settings page
    and a failure is information, not an error condition.
    """
    config = config or PayPalSettings.load()

    try:
        fetch_access_token(config)
    except PayPalConfigurationError as exc:
        message = str(exc)
        ok = False
    else:
        message = f"Authenticated successfully against {config.get_mode_display()}."
        ok = True

    config.last_test_at = timezone.now()
    config.last_test_ok = ok
    config.last_test_error = "" if ok else message
    config.save(update_fields=["last_test_at", "last_test_ok", "last_test_error"])

    return ok, message
