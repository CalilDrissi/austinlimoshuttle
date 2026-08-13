"""
Public API consumed by the Next.js frontend.

Two rules run through everything here:

  1. The server computes prices. No endpoint accepts a money value.
  2. A customer sees their own bookings and nobody else's. Legacy exposed
     `direct-payment.php?orderID=` with no authentication at all, which is how
     the orders table became readable by anyone.
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle

from accounts.forms import MigrationPasswordResetForm
from bookings.models import Booking, BookingStatusChange
from content.models import Page
from enquiries.models import ContactMessage
from fleet.models import Vehicle
from notifications import mailer
from pricing.distance import DistanceLookupError
from pricing.distance import lookup as measure_journey
from pricing.engine import quote_all
from pricing.models import BlackoutDate, TimeSurcharge

from . import quotes
from .serializers import (
    BookingCreateSerializer,
    BookingSerializer,
    EnquirySerializer,
    PageSerializer,
    QuoteRequestSerializer,
    VehicleSerializer,
)

User = get_user_model()


def money(value) -> str:
    """
    Render a monetary amount as a fixed-precision string.

    JSON has no decimal type, so a Decimal rendered by the default encoder
    becomes a float -- 145.10 arrives as 145.1, and anything a client computes
    from it inherits binary rounding error. Money crosses this boundary as a
    string, always.
    """
    return f"{Decimal(value):.2f}"


class QuoteThrottle(ScopedRateThrottle):
    scope = "quote"


class EnquiryThrottle(ScopedRateThrottle):
    scope = "enquiry"


# -- content ---------------------------------------------------------------


@api_view(["GET"])
@permission_classes([AllowAny])
def page_detail(request, slug):
    page = Page.objects.filter(slug=slug, is_published=True).first()
    if page is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(PageSerializer(page).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def page_list(request):
    pages = Page.objects.filter(is_published=True)
    return Response(PageSerializer(pages, many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def vehicle_list(request):
    vehicles = Vehicle.objects.filter(is_active=True).prefetch_related("bands")
    return Response(VehicleSerializer(vehicles, many=True).data)


@api_view(["GET"])
@permission_classes([AllowAny])
def availability(request):
    """Blackout dates and surcharge windows, for the date picker."""
    return Response({
        "blackout_dates": [
            {"date": b.date, "name": b.name, "percentage": money(b.percentage)}
            for b in BlackoutDate.objects.filter(is_active=True)
        ],
        "time_surcharges": [
            {
                "name": s.name,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "percentage": money(s.percentage),
                "crosses_midnight": s.crosses_midnight,
            }
            for s in TimeSurcharge.objects.filter(is_active=True)
        ],
    })


# -- quoting ---------------------------------------------------------------


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([QuoteThrottle])
def create_quote(request):
    """
    Price every bookable vehicle for a journey.

    Each result carries a signed token. Booking requires presenting one back;
    the fare is recomputed at that point, so a stale or edited token cannot buy
    a journey at yesterday's price.
    """
    serializer = QuoteRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    # The distance is measured here, from the addresses. It is never accepted
    # from the client, and there is no fallback if the lookup fails -- a
    # fallback would simply be the vulnerability behind a retry.
    journey = None
    distance_miles = None
    if data.get("hours") is None:
        try:
            journey = measure_journey(data["pickup_address"], data["dropoff_address"])
        except DistanceLookupError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        distance_miles = journey.distance_miles

    results = quote_all(
        data["pickup_at"],
        distance_miles=distance_miles,
        hours=data.get("hours"),
        meet_and_greet=data["meet_and_greet"],
    )

    if not results:
        return Response(
            {"detail": "No vehicle can be priced for that journey."},
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    payload = []
    for result in results:
        token = quotes.issue(quotes.QuoteRequest(
            vehicle_id=result.vehicle_id,
            pickup_at=data["pickup_at"],
            distance_miles=distance_miles,
            hours=data.get("hours"),
            meet_and_greet=data["meet_and_greet"],
            pickup_address=data["pickup_address"],
            dropoff_address=data.get("dropoff_address", ""),
        ))
        payload.append({
            "vehicle_id": result.vehicle_id,
            "vehicle_name": result.vehicle_name,
            "subtotal": money(result.subtotal),
            "surcharge_total": money(result.surcharge_total),
            "tax": money(result.tax),
            "total": money(result.total),
            "currency": result.currency,
            "lines": [
                {"kind": line.kind, "label": line.label, "amount": money(line.amount)}
                for line in result.lines
            ],
            "quote_token": token,
        })

    return Response({
        "journey": {
            "distance_miles": str(journey.distance_miles),
            "duration_minutes": journey.duration_minutes,
            "pickup_address": journey.resolved_origin,
            "dropoff_address": journey.resolved_destination,
        } if journey else None,
        "quotes": payload,
    })


# -- bookings --------------------------------------------------------------


@api_view(["POST"])
@permission_classes([AllowAny])
def create_booking(request):
    """Create a pending booking from a signed quote."""
    serializer = BookingCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data

    try:
        quote_request, recomputed = quotes.redeem(data["quote_token"])
    except quotes.QuoteTokenError as exc:
        raise ValidationError({"quote_token": str(exc)}) from exc

    customer = request.user if request.user.is_authenticated else None
    if customer is None and not data.get("guest_email"):
        raise ValidationError(
            {"guest_email": "Sign in or provide an email address for the booking."}
        )

    vehicle = Vehicle.objects.get(pk=quote_request.vehicle_id)

    with transaction.atomic():
        booking = Booking.objects.create(
            customer=customer,
            vehicle=vehicle,
            trip_type=(
                Booking.TripType.HOURLY
                if quote_request.hours is not None
                else Booking.TripType.TRANSFER
            ),
            status=Booking.Status.PENDING,
            pickup_address=quote_request.pickup_address,
            dropoff_address=quote_request.dropoff_address,
            pickup_at=quote_request.pickup_at,
            distance_miles=quote_request.distance_miles,
            hours=quote_request.hours,
            meet_and_greet=quote_request.meet_and_greet,
            passenger_count=data["passenger_count"],
            luggage_count=data["luggage_count"],
            flight_number=data.get("flight_number", ""),
            pickup_sign=data.get("pickup_sign") or data.get("guest_name", ""),
            notes=data.get("notes", ""),
            guest_email=data.get("guest_email", "") if customer is None else "",
            # Every figure below comes from the server-side recomputation.
            subtotal=recomputed.subtotal,
            surcharge_total=recomputed.surcharge_total,
            tax=recomputed.tax,
            total=recomputed.total,
            currency=recomputed.currency,
        )
        for line in recomputed.as_price_lines(booking):
            line.save()

        BookingStatusChange.objects.create(
            booking=booking, from_status="", to_status=booking.status,
            note="Created via website",
        )

    return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_bookings(request):
    bookings = (
        Booking.objects.filter(customer=request.user)
        .prefetch_related("price_lines")
        .order_by("-pickup_at")
    )
    return Response(BookingSerializer(bookings, many=True).data)


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
def my_booking_detail(request, reference):
    """
    A customer's own booking.

    Scoped to `customer=request.user`, so an unknown reference and someone
    else's reference are indistinguishable -- both 404. That prevents using the
    endpoint to confirm whether a reference exists.
    """
    booking = (
        Booking.objects.filter(reference=reference, customer=request.user)
        .prefetch_related("price_lines")
        .first()
    )
    if booking is None:
        return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == "PATCH":
        action = request.data.get("action")
        if action != "cancel":
            raise ValidationError({"action": "Only 'cancel' is supported."})
        if not booking.is_cancellable:
            raise ValidationError(
                {"detail": "This booking can no longer be cancelled online."}
            )

        BookingStatusChange.objects.create(
            booking=booking, from_status=booking.status,
            to_status=Booking.Status.CANCELLED,
            changed_by=request.user, note="Cancelled by customer",
        )
        booking.status = Booking.Status.CANCELLED
        booking.cancelled_at = timezone.now()
        booking.save()
        mailer.send_booking_cancelled(booking)

    return Response(BookingSerializer(booking).data)


# -- auth -------------------------------------------------------------------


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def auth_login(request):
    email = (request.data.get("email") or "").strip().lower()
    password = request.data.get("password") or ""

    user = authenticate(request, username=email, password=password)
    if user is None:
        # One message for both causes: revealing which is wrong lets an attacker
        # enumerate registered addresses.
        return Response(
            {"detail": "Email or password is incorrect."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    login(request, user)
    return Response({
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def auth_logout(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def auth_register(request):
    email = (request.data.get("email") or "").strip().lower()
    password = request.data.get("password") or ""

    if not email or "@" not in email:
        raise ValidationError({"email": "A valid email address is required."})

    try:
        validate_password(password)
    except DjangoValidationError as exc:
        raise ValidationError({"password": list(exc.messages)}) from exc

    if User.objects.filter(email=email).exists():
        # Deliberately not "that email is taken" -- same enumeration concern.
        return Response(
            {"detail": "If that address can be registered, you'll receive an email."},
            status=status.HTTP_202_ACCEPTED,
        )

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=(request.data.get("first_name") or "").strip()[:150],
        last_name=(request.data.get("last_name") or "").strip()[:150],
        phone=(request.data.get("phone") or "").strip()[:32],
    )
    login(request, user)
    return Response({"email": user.email}, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([AnonRateThrottle])
def auth_password_reset(request):
    """
    Trigger a password reset email.

    Delegates to Django's own `PasswordResetForm`, which generates the signed
    one-time token and sends the mail. The reset itself is completed on the
    Django-served pages under /accounts/.

    Always answers 202, whether or not the address is registered: a different
    response for a known address turns this endpoint into a way to enumerate
    customers. Every imported legacy account needs this flow, so the endpoint
    must be safe to hammer.
    """
    form = MigrationPasswordResetForm(data={"email": (request.data.get("email") or "").strip()})
    if form.is_valid():
        form.save(
            request=request,
            use_https=request.is_secure(),
            from_email=settings.DEFAULT_FROM_EMAIL,
            email_template_name="accounts/email/password_reset.txt",
            html_email_template_name="accounts/email/password_reset.html",
            subject_template_name="accounts/email/password_reset_subject.txt",
        )

    return Response(
        {"detail": "If that address has an account, a reset link is on its way."},
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def auth_me(request):
    user = request.user
    return Response({
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
    })


# -- enquiries --------------------------------------------------------------


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([EnquiryThrottle])
def create_enquiry(request):
    serializer = EnquirySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    ContactMessage.objects.create(
        **serializer.validated_data,
        source_ip=_client_ip(request),
        created_at=timezone.now(),
    )
    return Response({"detail": "Thank you — we'll be in touch."},
                    status=status.HTTP_201_CREATED)


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")
