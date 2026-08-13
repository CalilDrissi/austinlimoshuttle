"""
Server-side distance lookup.

The fare depends on distance, so distance must not come from the browser. A
customer who can declare "1 mile" for a 40-mile airport run gets a legitimately
signed quote at the minimum fare, and every downstream check -- token signature,
server-side recomputation, booking creation -- passes happily on the wrong
input.

This module is the only place a journey distance is established. The API
serializers do not accept a distance for transfers; they accept addresses.

Failures are hard failures. There is deliberately no fallback to a
client-supplied value, because a fallback is just the vulnerability with extra
steps: anyone wanting the cheap quote need only make the lookup fail.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

ENDPOINT = "https://maps.googleapis.com/maps/api/distancematrix/json"
METRES_PER_MILE = Decimal("1609.344")
REQUEST_TIMEOUT_SECONDS = 8
CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # a week; road distances do not move


class DistanceLookupError(Exception):
    """The journey could not be measured. Never fall back to a client value."""


@dataclass(frozen=True)
class Journey:
    distance_miles: Decimal
    duration_minutes: int
    resolved_origin: str
    resolved_destination: str


def _cache_key(origin: str, destination: str) -> str:
    digest = hashlib.sha256(
        f"{origin.strip().lower()}|{destination.strip().lower()}".encode()
    ).hexdigest()[:32]
    return f"distance:v1:{digest}"


def lookup(origin: str, destination: str, *, use_cache: bool = True) -> Journey:
    """
    Measure a journey between two addresses.

    Results are cached for a week: the airport-to-downtown pair is requested
    constantly and each call costs money.
    """
    origin = (origin or "").strip()
    destination = (destination or "").strip()

    if not origin or not destination:
        raise DistanceLookupError("Both a pickup and a destination address are required.")

    key = _cache_key(origin, destination)
    if use_cache and (cached := cache.get(key)) is not None:
        return Journey(**cached)

    api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", "")
    if not api_key:
        raise DistanceLookupError(
            "Distance lookup is not configured (GOOGLE_MAPS_API_KEY is unset)."
        )

    try:
        response = requests.get(
            ENDPOINT,
            params={
                "origins": origin,
                "destinations": destination,
                "units": "imperial",
                "mode": "driving",
                "key": api_key,
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.Timeout as exc:
        raise DistanceLookupError(
            "The mapping service did not respond. Please try again."
        ) from exc
    except requests.RequestException as exc:
        logger.warning("Distance Matrix request failed: %s", exc)
        raise DistanceLookupError(
            "We could not measure that journey. Please try again."
        ) from exc
    except ValueError as exc:
        raise DistanceLookupError("The mapping service returned an unreadable reply.") from exc

    journey = _parse(payload, origin, destination)

    if use_cache:
        cache.set(key, journey.__dict__, CACHE_TTL_SECONDS)

    return journey


def _parse(payload: dict, origin: str, destination: str) -> Journey:
    status = payload.get("status")
    if status != "OK":
        # REQUEST_DENIED usually means the key is restricted to browser
        # referrers; OVER_QUERY_LIMIT means billing. Both are operator problems,
        # so log the detail and tell the customer something useful.
        logger.error(
            "Distance Matrix status=%s error=%s", status, payload.get("error_message"),
        )
        raise DistanceLookupError("We could not measure that journey right now.")

    try:
        element = payload["rows"][0]["elements"][0]
    except (KeyError, IndexError) as exc:
        raise DistanceLookupError("We could not measure that journey.") from exc

    element_status = element.get("status")
    if element_status == "ZERO_RESULTS":
        raise DistanceLookupError(
            "No driving route was found between those addresses."
        )
    if element_status == "NOT_FOUND":
        raise DistanceLookupError(
            "One of those addresses could not be found. Please check and try again."
        )
    if element_status != "OK":
        raise DistanceLookupError("We could not measure that journey.")

    metres = Decimal(str(element["distance"]["value"]))
    seconds = int(element["duration"]["value"])

    # Convert from metres rather than parsing the "11.3 mi" display string --
    # that text is rounded for humans and is locale-dependent.
    miles = (metres / METRES_PER_MILE).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    addresses = payload.get("destination_addresses") or [destination]
    origins = payload.get("origin_addresses") or [origin]

    return Journey(
        distance_miles=miles,
        duration_minutes=max(1, round(seconds / 60)),
        resolved_origin=origins[0] or origin,
        resolved_destination=addresses[0] or destination,
    )
