"""
Dashboard access control and workflow.

The permission matrix is the point: the legacy system had one shared admin
login, so every staff member could do everything and no action was attributable.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from bookings.models import Booking, BookingStatusChange, Driver
from dashboard.permissions import DISPATCHER, EDITOR, MANAGER, sync_roles
from enquiries.models import ContactMessage
from fleet.models import Vehicle

User = get_user_model()

DASHBOARD_URLS = ["dashboard:home", "dashboard:dispatch",
                  "dashboard:bookings", "dashboard:enquiries"]


@pytest.fixture
def roles(db):
    sync_roles()


@pytest.fixture
def vehicle(db):
    return Vehicle.objects.create(name="Business Class", slug="bc", hourly_rate=85)


@pytest.fixture
def booking(db, vehicle):
    return Booking.objects.create(
        vehicle=vehicle, pickup_address="ABIA", dropoff_address="Downtown",
        pickup_at=timezone.now() + timedelta(hours=6),
        total=Decimal("95.00"), status=Booking.Status.CONFIRMED,
    )


def staff_in(role, roles):
    user = User.objects.create_user(
        email=f"{role.lower()}@example.com", password="DashLocal!2026", is_staff=True,
    )
    user.groups.add(__import__("django.contrib.auth.models",
                               fromlist=["Group"]).Group.objects.get(name=role))
    return user


@pytest.mark.django_db
class TestAccessControl:
    @pytest.mark.parametrize("url_name", DASHBOARD_URLS)
    def test_anonymous_is_redirected(self, client, url_name):
        response = client.get(reverse(url_name))
        assert response.status_code == 302
        assert "/admin/login/" in response["Location"]

    @pytest.mark.parametrize("url_name", DASHBOARD_URLS)
    def test_customer_account_is_forbidden(self, client, roles, url_name):
        User.objects.create_user(email="cust@example.com", password="DashLocal!2026")
        client.login(username="cust@example.com", password="DashLocal!2026")
        assert client.get(reverse(url_name)).status_code in (302, 403)

    @pytest.mark.parametrize("url_name", DASHBOARD_URLS)
    def test_dispatcher_can_reach_every_screen(self, client, roles, url_name):
        staff_in(DISPATCHER, roles)
        client.login(username="dispatcher@example.com", password="DashLocal!2026")
        assert client.get(reverse(url_name)).status_code == 200

    def test_editor_cannot_reach_bookings(self, client, roles):
        """Content editors have no business seeing customer journeys."""
        staff_in(EDITOR, roles)
        client.login(username="editor@example.com", password="DashLocal!2026")
        assert client.get(reverse("dashboard:bookings")).status_code == 403


@pytest.mark.django_db
class TestDispatchBoard:
    def test_shows_upcoming_bookings(self, client, roles, booking):
        staff_in(DISPATCHER, roles)
        client.login(username="dispatcher@example.com", password="DashLocal!2026")
        response = client.get(reverse("dashboard:dispatch"))
        assert booking.reference in response.content.decode()

    def test_hides_bookings_beyond_the_horizon(self, client, roles, vehicle):
        far = Booking.objects.create(
            vehicle=vehicle, pickup_address="later",
            pickup_at=timezone.now() + timedelta(days=10), total=Decimal("50"),
        )
        staff_in(DISPATCHER, roles)
        client.login(username="dispatcher@example.com", password="DashLocal!2026")
        response = client.get(reverse("dashboard:dispatch"))
        assert far.reference not in response.content.decode()


@pytest.mark.django_db
class TestBookingUpdate:
    def _login(self, client, roles):
        staff_in(DISPATCHER, roles)
        client.login(username="dispatcher@example.com", password="DashLocal!2026")

    def test_status_change_is_audited_with_the_acting_user(self, client, roles, booking):
        self._login(client, roles)
        client.post(
            reverse("dashboard:booking_update", args=[booking.reference]),
            {"status": Booking.Status.COMPLETED, "driver": "", "note": "Dropped off"},
        )
        booking.refresh_from_db()
        assert booking.status == Booking.Status.COMPLETED

        change = BookingStatusChange.objects.get(booking=booking)
        assert change.from_status == Booking.Status.CONFIRMED
        assert change.to_status == Booking.Status.COMPLETED
        assert change.changed_by.email == "dispatcher@example.com"
        assert change.note == "Dropped off"

    def test_assigning_a_driver(self, client, roles, booking):
        self._login(client, roles)
        driver = Driver.objects.create(full_name="Alex Ruiz")
        client.post(
            reverse("dashboard:booking_update", args=[booking.reference]),
            {"status": booking.status, "driver": str(driver.pk)},
        )
        booking.refresh_from_db()
        assert booking.driver == driver

    def test_cancelling_stamps_the_time_and_reason(self, client, roles, booking):
        self._login(client, roles)
        client.post(
            reverse("dashboard:booking_update", args=[booking.reference]),
            {"status": Booking.Status.CANCELLED, "driver": "", "note": "Customer called"},
        )
        booking.refresh_from_db()
        assert booking.cancelled_at is not None
        assert booking.cancellation_reason == "Customer called"

    def test_unknown_status_is_rejected(self, client, roles, booking):
        self._login(client, roles)
        client.post(
            reverse("dashboard:booking_update", args=[booking.reference]),
            {"status": "teleported", "driver": ""},
        )
        booking.refresh_from_db()
        assert booking.status == Booking.Status.CONFIRMED
        assert not BookingStatusChange.objects.exists()

    def test_no_change_writes_no_audit_row(self, client, roles, booking):
        self._login(client, roles)
        client.post(
            reverse("dashboard:booking_update", args=[booking.reference]),
            {"status": booking.status, "driver": ""},
        )
        assert not BookingStatusChange.objects.exists()

    def test_get_is_not_allowed(self, client, roles, booking):
        self._login(client, roles)
        response = client.get(
            reverse("dashboard:booking_update", args=[booking.reference])
        )
        assert response.status_code == 405


@pytest.mark.django_db
class TestBookingList:
    def test_search_by_reference(self, client, roles, booking, vehicle):
        other = Booking.objects.create(
            vehicle=vehicle, pickup_address="x",
            pickup_at=timezone.now() + timedelta(days=1), total=Decimal("10"),
        )
        staff_in(DISPATCHER, roles)
        client.login(username="dispatcher@example.com", password="DashLocal!2026")
        body = client.get(
            reverse("dashboard:bookings"), {"q": booking.reference}
        ).content.decode()
        assert booking.reference in body
        assert other.reference not in body

    def test_csv_export(self, client, roles, booking):
        staff_in(DISPATCHER, roles)
        client.login(username="dispatcher@example.com", password="DashLocal!2026")
        response = client.get(reverse("dashboard:bookings"), {"export": "csv"})
        assert response["Content-Type"] == "text/csv"
        body = response.content.decode()
        assert "Reference" in body
        assert booking.reference in body

    def test_csv_export_contains_no_card_columns(self, client, roles, booking):
        staff_in(DISPATCHER, roles)
        client.login(username="dispatcher@example.com", password="DashLocal!2026")
        header = client.get(
            reverse("dashboard:bookings"), {"export": "csv"}
        ).content.decode().splitlines()[0].lower()
        for forbidden in ("card", "cvv", "expiry", "security"):
            assert forbidden not in header


@pytest.mark.django_db
class TestEnquiryInbox:
    def _login(self, client, roles):
        staff_in(MANAGER, roles)
        client.login(username="manager@example.com", password="DashLocal!2026")

    def test_opening_an_enquiry_marks_it_read(self, client, roles):
        enquiry = ContactMessage.objects.create(
            name="Jo", email="jo@example.com", message="hi", created_at=timezone.now(),
        )
        self._login(client, roles)
        client.get(reverse("dashboard:enquiry_detail", args=[enquiry.pk]))
        enquiry.refresh_from_db()
        assert enquiry.is_read

    def test_replying_records_who_and_when(self, client, roles):
        enquiry = ContactMessage.objects.create(
            name="Jo", email="jo@example.com", message="hi", created_at=timezone.now(),
        )
        self._login(client, roles)
        client.post(
            reverse("dashboard:enquiry_detail", args=[enquiry.pk]),
            {"reply": "Yes, we cover ABIA."},
        )
        enquiry.refresh_from_db()
        assert enquiry.is_answered
        assert enquiry.replied_by.email == "manager@example.com"
        assert enquiry.reply_body == "Yes, we cover ABIA."


@pytest.mark.django_db
class TestRoleSync:
    def test_is_idempotent(self, roles):
        from django.contrib.auth.models import Group

        first = {g.name: g.permissions.count() for g in Group.objects.all()}
        sync_roles()
        second = {g.name: g.permissions.count() for g in Group.objects.all()}
        assert first == second

    def test_creates_the_three_roles(self, roles):
        from django.contrib.auth.models import Group

        assert set(Group.objects.values_list("name", flat=True)) == {
            DISPATCHER, MANAGER, EDITOR,
        }

    def test_dispatcher_cannot_change_rates(self, roles):
        user = staff_in(DISPATCHER, roles)
        assert not user.has_perm("fleet.change_vehicle")
        assert user.has_perm("bookings.change_booking")

    def test_manager_can_change_rates(self, roles):
        user = staff_in(MANAGER, roles)
        assert user.has_perm("fleet.change_vehicle")
        assert user.has_perm("payments.add_refund")
