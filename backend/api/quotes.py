"""
Signed fare quotes.

The browser never sends a price. It sends a token that this module issued, and
the server recomputes the fare from the token's contents before charging
anything. A price that arrives from the client is a price the customer can edit
-- the legacy funnel carried the fare in `$_SESSION` and re-derived it on the
payment page, which is the same class of trust with more steps.

The token is a `TimestampSigner` payload: tamper-evident (signed with
SECRET_KEY) and short-lived (expires after PricingSettings.quote_ttl_minutes).
It is not encrypted, and does not need to be -- it contains nothing secret, only
values the customer supplied.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.utils import timezone

from fleet.models import Vehicle
from pricing.engine import Quote, QuoteError, quote
from pricing.models import PricingSettings

SIGNER_SALT = "austinlimo.quote.v1"


class QuoteTokenError(ValueError):
    """The token is missing, malformed, tampered with, or expired."""


@dataclass(frozen=True)
class QuoteRequest:
    """The journey a quote was issued for."""

    vehicle_id: int
    pickup_at: datetime
    distance_miles: Decimal | None
    hours: Decimal | None
    meet_and_greet: bool
    pickup_address: str
    dropoff_address: str
    # Set when the journey matched a fixed city-to-city route. Signed into the
    # token so the flat price is re-applied at booking time, not spoofable.
    route_id: int | None = None


def issue(request: QuoteRequest) -> str:
    """Sign a quote request into an opaque token."""
    payload = {
        "v": request.vehicle_id,
        "at": request.pickup_at.isoformat(),
        "mi": str(request.distance_miles) if request.distance_miles is not None else None,
        "hr": str(request.hours) if request.hours is not None else None,
        "mg": request.meet_and_greet,
        "from": request.pickup_address,
        "to": request.dropoff_address,
        "rt": request.route_id,
    }
    return TimestampSigner(salt=SIGNER_SALT).sign(json.dumps(payload, separators=(",", ":")))


def redeem(token: str) -> tuple[QuoteRequest, Quote]:
    """
    Verify a token and recompute its fare.

    Returns both the journey and a freshly-computed quote. The caller must use
    the returned total -- never a total supplied by the client.
    """
    if not token:
        raise QuoteTokenError("A quote token is required.")

    ttl_minutes = PricingSettings.load().quote_ttl_minutes
    try:
        raw = TimestampSigner(salt=SIGNER_SALT).unsign(token, max_age=ttl_minutes * 60)
    except SignatureExpired as exc:
        raise QuoteTokenError(
            f"This quote expired after {ttl_minutes} minutes. Please request a new one."
        ) from exc
    except BadSignature as exc:
        raise QuoteTokenError("This quote is not valid.") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise QuoteTokenError("This quote is not valid.") from exc

    try:
        pickup_at = datetime.fromisoformat(payload["at"])
        quote_request = QuoteRequest(
            vehicle_id=int(payload["v"]),
            pickup_at=pickup_at,
            distance_miles=Decimal(payload["mi"]) if payload.get("mi") else None,
            hours=Decimal(payload["hr"]) if payload.get("hr") else None,
            meet_and_greet=bool(payload.get("mg")),
            pickup_address=payload.get("from", ""),
            dropoff_address=payload.get("to", ""),
            route_id=int(payload["rt"]) if payload.get("rt") else None,
        )
    except (KeyError, TypeError, ValueError, ArithmeticError) as exc:
        raise QuoteTokenError("This quote is not valid.") from exc

    vehicle = Vehicle.objects.filter(pk=quote_request.vehicle_id, is_active=True).first()
    if vehicle is None:
        raise QuoteTokenError("That vehicle is no longer available.")

    if quote_request.pickup_at < timezone.now():
        raise QuoteTokenError("That pickup time is in the past.")

    # Re-apply the fixed route price if the quote was issued for one and it is
    # still active. The id is signed, so this trusts only our own token.
    route = None
    if quote_request.route_id:
        from pricing.models import CityRoute
        route = CityRoute.objects.filter(pk=quote_request.route_id, is_active=True).first()

    try:
        recomputed = quote(
            vehicle,
            pickup_at=quote_request.pickup_at,
            distance_miles=quote_request.distance_miles,
            hours=quote_request.hours,
            meet_and_greet=quote_request.meet_and_greet,
            route=route,
        )
    except QuoteError as exc:
        raise QuoteTokenError(str(exc)) from exc

    return quote_request, recomputed
