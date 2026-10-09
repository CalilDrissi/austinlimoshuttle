"""
City-to-city booking: the public /api/city-routes/ options and the
`city_to_city=true` quote path (flat route price, no distance lookup).
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.urls import reverse
from django.utils import timezone

from fleet.models import Vehicle
from pricing.models import CityRoute, CityRoutePrice, PricingSettings


@pytest.fixture
def routes(db):
    PricingSettings.load()
    bc = Vehicle.objects.create(name="Business Class", slug="bc", is_active=True)
    suv = Vehicle.objects.create(name="Business SUV", slug="suv", is_active=True)
    austin_houston = CityRoute.objects.create(origin="Austin", destination="Houston")
    CityRoutePrice.objects.create(route=austin_houston, vehicle=bc, price=Decimal("395.00"))
    CityRoutePrice.objects.create(route=austin_houston, vehicle=suv, price=Decimal("495.00"))
    # A second route with NO prices -- its cities appear, but no pair is bookable.
    CityRoute.objects.create(origin="Austin", destination="Dallas")
    return {"bc": bc, "suv": suv, "austin_houston": austin_houston}


@pytest.fixture
def future():
    return (timezone.now() + timedelta(days=3)).replace(microsecond=0)


def test_city_routes_lists_cities_and_pairs(client, routes):
    resp = client.get(reverse("api:city_routes"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["cities"] == ["Austin", "Dallas", "Houston"]  # sorted, deduped
    pairs = {(r["origin"], r["destination"]) for r in data["routes"]}
    assert ("Austin", "Houston") in pairs


def test_city_quote_uses_flat_price_without_a_distance_lookup(client, routes, future):
    resp = client.post(
        reverse("api:quotes"),
        {"pickup_address": "Austin", "dropoff_address": "Houston",
         "pickup_at": future.isoformat(), "city_to_city": True},
        content_type="application/json",
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["journey"] is None  # no Google call for a fixed route
    totals = {q["vehicle_name"]: q["total"] for q in body["quotes"]}
    assert totals == {"Business Class": "395.00", "Business SUV": "495.00"}


def test_city_quote_is_bidirectional(client, routes, future):
    resp = client.post(
        reverse("api:quotes"),
        {"pickup_address": "Houston", "dropoff_address": "Austin",
         "pickup_at": future.isoformat(), "city_to_city": True},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.json()["quotes"], "reverse direction should price the same route"


def test_city_quote_rejects_an_unpriced_pair(client, routes, future):
    resp = client.post(
        reverse("api:quotes"),
        {"pickup_address": "Austin", "dropoff_address": "Dallas",
         "pickup_at": future.isoformat(), "city_to_city": True},
        content_type="application/json",
    )
    assert resp.status_code == 422
    assert "fixed price" in resp.json()["detail"].lower()


def test_city_quote_rejects_hours(client, routes, future):
    resp = client.post(
        reverse("api:quotes"),
        {"pickup_address": "Austin", "dropoff_address": "Houston",
         "pickup_at": future.isoformat(), "city_to_city": True, "hours": "3"},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_city_booking_creates_with_the_flat_total(client, routes, future):
    token = client.post(
        reverse("api:quotes"),
        {"pickup_address": "Austin", "dropoff_address": "Houston",
         "pickup_at": future.isoformat(), "city_to_city": True},
        content_type="application/json",
    ).json()["quotes"][0]["quote_token"]
    resp = client.post(
        reverse("api:create_booking"),
        {"quote_token": token, "guest_email": "c@example.com",
         "guest_phone": "+15125550000", "passenger_count": 2},
        content_type="application/json",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["total"] == "395.00"
    assert body["pickup_address"] == "Austin"
    assert body["dropoff_address"] == "Houston"
