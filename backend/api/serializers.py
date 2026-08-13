"""API serializers."""

from __future__ import annotations

from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from bookings.models import Booking
from content.models import Page
from enquiries.models import ContactMessage
from fleet.models import Vehicle

MAX_PASSENGERS = 20
MAX_HOURS = Decimal("24")
MAX_DISTANCE_MILES = Decimal("1000")


class PageSerializer(serializers.ModelSerializer):
    url = serializers.CharField(source="url_path", read_only=True)

    class Meta:
        model = Page
        fields = [
            "slug", "url", "title", "page_type", "body",
            "meta_title", "meta_description", "meta_keywords",
        ]


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            "id", "name", "slug", "description", "features",
            "passenger_capacity", "luggage_capacity", "minimum_fare",
        ]


class QuoteRequestSerializer(serializers.Serializer):
    """
    A request for fares.

    Deliberately accepts NO distance and NO price. A transfer is described by
    its two addresses and the server measures it (pricing/distance.py); an
    hourly hire is described by its duration. A client-supplied distance is a
    client-supplied fare with extra steps.
    """

    pickup_address = serializers.CharField(max_length=255)
    dropoff_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    pickup_at = serializers.DateTimeField()
    hours = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True,
        min_value=Decimal("0.5"), max_value=MAX_HOURS,
        help_text="Hourly hire only. Omit for a point-to-point transfer.",
    )
    meet_and_greet = serializers.BooleanField(default=False)

    def validate_pickup_at(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Pickup time must be in the future.")
        return value

    def validate(self, attrs):
        hours = attrs.get("hours")
        dropoff = (attrs.get("dropoff_address") or "").strip()

        if hours is None and not dropoff:
            raise serializers.ValidationError(
                "Provide a destination address for a transfer, or hours for hourly hire."
            )
        if hours is not None and dropoff:
            raise serializers.ValidationError(
                "A journey is either a transfer (two addresses) or hourly hire "
                "(a duration), not both."
            )
        attrs["dropoff_address"] = dropoff
        return attrs


class PriceLineSerializer(serializers.Serializer):
    kind = serializers.CharField()
    label = serializers.CharField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class BookingCreateSerializer(serializers.Serializer):
    """
    Create a booking from a signed quote token.

    Deliberately has no `total`, `subtotal` or any other money field: the server
    recomputes the fare from the token. A client-supplied amount is not merely
    ignored here, it is impossible to express.
    """

    quote_token = serializers.CharField()
    passenger_count = serializers.IntegerField(min_value=1, max_value=MAX_PASSENGERS, default=1)
    luggage_count = serializers.IntegerField(min_value=0, max_value=MAX_PASSENGERS, default=0)
    flight_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    pickup_sign = serializers.CharField(max_length=120, required=False, allow_blank=True)
    notes = serializers.CharField(required=False, allow_blank=True)

    # Guest checkout
    guest_email = serializers.EmailField(required=False, allow_blank=True)
    guest_name = serializers.CharField(max_length=150, required=False, allow_blank=True)


class BookingSerializer(serializers.ModelSerializer):
    vehicle_name = serializers.CharField(source="vehicle_name_snapshot", read_only=True)
    price_lines = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "reference", "status", "status_display", "trip_type",
            "pickup_address", "dropoff_address", "pickup_at",
            "distance_miles", "duration_minutes", "hours",
            "passenger_count", "luggage_count", "flight_number", "pickup_sign",
            "meet_and_greet", "notes", "vehicle_name",
            "subtotal", "surcharge_total", "tax", "total", "currency",
            "price_lines", "created_at",
        ]
        read_only_fields = fields

    def get_price_lines(self, obj):
        return [
            {"kind": line.kind, "label": line.label, "amount": f"{line.amount:.2f}"}
            for line in obj.price_lines.all()
        ]


class EnquirySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "nature", "subject", "message", "company_name"]

    def validate_message(self, value):
        if len(value.strip()) < 10:  # noqa: PLR2004
            raise serializers.ValidationError("Please provide a little more detail.")
        return value
