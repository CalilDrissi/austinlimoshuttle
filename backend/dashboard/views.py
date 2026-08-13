"""
Staff dashboard.

Django templates, served by Django. These are the screens that go beyond model
CRUD -- the work a dispatcher actually does during a shift. Everything else
stays in Django's generated admin.
"""

from __future__ import annotations

import csv
import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from bookings.models import Booking, BookingStatusChange, Driver
from enquiries.models import ContactMessage
from notifications import mailer
from notifications.models import EmailLog, EmailSettings
from payments import gateway
from payments.models import Payment, PaymentSettings

from .forms import EmailSettingsForm, PaymentSettingsForm
from .permissions import is_manager, role_names

logger = logging.getLogger(__name__)

BOOKINGS_PER_PAGE = 50


def staff_required(view):
    """Dashboard access requires a staff account, not merely a login."""
    return login_required(
        permission_required("bookings.view_booking", raise_exception=True)(view),
        login_url="/admin/login/",
    )


@staff_required
def home(request):
    """Overview: what needs attention today."""
    now = timezone.now()
    today_end = now.replace(hour=23, minute=59, second=59)
    week_ago = now - timedelta(days=7)

    upcoming = Booking.objects.for_dispatch().upcoming()

    context = {
        "today_count": upcoming.filter(pickup_at__lte=today_end).count(),
        "week_count": upcoming.filter(pickup_at__lte=now + timedelta(days=7)).count(),
        "unassigned": upcoming.filter(driver__isnull=True).count(),
        "pending": Booking.objects.filter(status=Booking.Status.PENDING).count(),
        "unread_enquiries": ContactMessage.objects.filter(is_read=False).count(),
        "recent_revenue": Booking.objects.filter(
            created_at__gte=week_ago,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.COMPLETED],
        ).aggregate(total=Sum("total"))["total"],
        "next_pickups": upcoming.order_by("pickup_at")[:8],
        "roles": role_names(request.user),
        "is_manager": is_manager(request.user),
    }
    return render(request, "dashboard/home.html", context)


@staff_required
def dispatch(request):
    """
    The dispatch board: today and tomorrow, in pickup order.

    This is the screen staff live in, so it answers one question at a glance --
    what is happening next, and does it have a driver.
    """
    now = timezone.now()
    horizon = now + timedelta(days=2)

    bookings = (
        Booking.objects.for_dispatch()
        .filter(pickup_at__gte=now - timedelta(hours=4), pickup_at__lte=horizon)
        .exclude(status=Booking.Status.CANCELLED)
        .order_by("pickup_at")
    )

    context = {
        "bookings": bookings,
        "drivers": Driver.objects.filter(is_active=True),
        "statuses": Booking.Status.choices,
        "now": now,
        "roles": role_names(request.user),
    }
    return render(request, "dashboard/dispatch.html", context)


@staff_required
def booking_list(request):
    """Searchable, filterable booking list."""
    bookings = Booking.objects.for_dispatch().order_by("-pickup_at")

    query = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    date_from = request.GET.get("from", "").strip()
    date_to = request.GET.get("to", "").strip()

    if query:
        bookings = bookings.filter(
            Q(reference__icontains=query)
            | Q(pickup_address__icontains=query)
            | Q(dropoff_address__icontains=query)
            | Q(pickup_sign__icontains=query)
            | Q(flight_number__icontains=query)
            | Q(customer__email__icontains=query)
            | Q(customer__first_name__icontains=query)
            | Q(customer__last_name__icontains=query)
        )
    if status:
        bookings = bookings.filter(status=status)
    if date_from:
        bookings = bookings.filter(pickup_at__date__gte=date_from)
    if date_to:
        bookings = bookings.filter(pickup_at__date__lte=date_to)

    if request.GET.get("export") == "csv":
        return _export_csv(bookings)

    total = bookings.count()
    context = {
        "bookings": bookings[:BOOKINGS_PER_PAGE],
        "total": total,
        "showing": min(total, BOOKINGS_PER_PAGE),
        "statuses": Booking.Status.choices,
        "filters": {"q": query, "status": status, "from": date_from, "to": date_to},
        "roles": role_names(request.user),
    }
    return render(request, "dashboard/booking_list.html", context)


@staff_required
def booking_detail(request, reference):
    booking = get_object_or_404(
        Booking.objects.select_related("vehicle", "driver", "customer")
        .prefetch_related("price_lines", "payments", "status_changes__changed_by"),
        reference=reference,
    )
    context = {
        "booking": booking,
        "drivers": Driver.objects.filter(is_active=True),
        "statuses": Booking.Status.choices,
        "roles": role_names(request.user),
        "is_manager": is_manager(request.user),
    }
    return render(request, "dashboard/booking_detail.html", context)


@staff_required
@require_POST
def booking_update(request, reference):
    """
    Change status and/or driver.

    Every status transition writes an audit row naming the acting user -- the
    thing a single shared admin login made impossible.
    """
    booking = get_object_or_404(Booking, reference=reference)
    changed: list[str] = []
    status_changed = False
    driver_changed = False

    new_status = request.POST.get("status", "").strip()
    if new_status and new_status != booking.status:
        valid = {value for value, _ in Booking.Status.choices}
        if new_status not in valid:
            messages.error(request, f"Unknown status {new_status!r}.")
            return redirect("dashboard:booking_detail", reference=reference)

        BookingStatusChange.objects.create(
            booking=booking,
            from_status=booking.status,
            to_status=new_status,
            changed_by=request.user,
            note=request.POST.get("note", "").strip(),
        )
        previous = booking.get_status_display()
        booking.status = new_status
        if new_status == Booking.Status.CANCELLED and not booking.cancelled_at:
            booking.cancelled_at = timezone.now()
            booking.cancellation_reason = request.POST.get("note", "").strip()
        changed.append(f"status {previous} → {booking.get_status_display()}")
        status_changed = True

    driver_id = request.POST.get("driver", "").strip()
    if driver_id != str(booking.driver_id or ""):
        booking.driver = Driver.objects.filter(pk=driver_id).first() if driver_id else None
        changed.append(
            f"driver → {booking.driver.full_name}" if booking.driver else "driver cleared"
        )
        driver_changed = True

    if changed:
        booking.save()

        if driver_changed and booking.driver:
            mailer.send_driver_assigned(booking)
        if booking.status == Booking.Status.CANCELLED and status_changed:
            mailer.send_booking_cancelled(booking)

        messages.success(request, f"{booking.reference}: " + "; ".join(changed))
    else:
        messages.info(request, "Nothing changed.")

    return redirect(request.POST.get("next") or "dashboard:booking_detail",
                    reference=reference)


@staff_required
def enquiry_inbox(request):
    enquiries = ContactMessage.objects.all()

    state = request.GET.get("state", "unread")
    if state == "unread":
        enquiries = enquiries.filter(is_read=False)
    elif state == "unanswered":
        enquiries = enquiries.filter(replied_at__isnull=True)

    nature = request.GET.get("nature", "").strip()
    if nature:
        enquiries = enquiries.filter(nature=nature)

    context = {
        "enquiries": enquiries[:100],
        "counts": ContactMessage.objects.aggregate(
            all=Count("id"),
            unread=Count("id", filter=Q(is_read=False)),
            unanswered=Count("id", filter=Q(replied_at__isnull=True)),
        ),
        "natures": ContactMessage.Nature.choices,
        "state": state,
        "nature": nature,
        "roles": role_names(request.user),
    }
    return render(request, "dashboard/enquiries.html", context)


@staff_required
def enquiry_detail(request, pk):
    enquiry = get_object_or_404(ContactMessage, pk=pk)

    if request.method == "POST":
        reply = request.POST.get("reply", "").strip()
        if reply:
            enquiry.reply_body = reply
            enquiry.replied_at = timezone.now()
            enquiry.replied_by = request.user
            enquiry.is_read = True
            enquiry.save()
            messages.success(request, "Reply recorded.")
            return redirect("dashboard:enquiries")
        messages.error(request, "Write a reply first.")

    if not enquiry.is_read:
        enquiry.is_read = True
        enquiry.save(update_fields=["is_read"])

    return render(request, "dashboard/enquiry_detail.html",
                  {"enquiry": enquiry, "roles": role_names(request.user)})


def _export_csv(bookings) -> HttpResponse:
    response = HttpResponse(content_type="text/csv")
    stamp = timezone.now().strftime("%Y%m%d-%H%M")
    response["Content-Disposition"] = f'attachment; filename="bookings-{stamp}.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Reference", "Pickup (local)", "Status", "Customer", "Email", "Phone",
        "Vehicle", "Driver", "Pickup address", "Dropoff address",
        "Distance (mi)", "Hours", "Total", "Currency",
    ])
    for booking in bookings.iterator(chunk_size=500):
        writer.writerow([
            booking.reference,
            timezone.localtime(booking.pickup_at).strftime("%Y-%m-%d %H:%M"),
            booking.get_status_display(),
            booking.customer_name,
            booking.customer.email if booking.customer else "",
            booking.customer.phone if booking.customer else "",
            booking.vehicle_name_snapshot,
            booking.driver.full_name if booking.driver else "",
            booking.pickup_address,
            booking.dropoff_address,
            booking.distance_miles or "",
            booking.hours or "",
            booking.total,
            booking.currency,
        ])
    return response


@staff_required
@permission_required("payments.change_paymentsettings", raise_exception=True)
def payment_settings(request):
    """
    Stripe credentials, editable by a Manager.

    Restricted beyond ordinary dashboard access: these keys authorise charges
    and refunds against the real account, so a Dispatcher must not reach them.
    """
    if not is_manager(request.user):
        raise PermissionDenied("Only managers can change payment settings.")

    instance = PaymentSettings.load()

    if request.method == "POST":
        form = PaymentSettingsForm(request.POST, instance=instance)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()

            changed = [
                form.fields[name].label or name.replace("_", " ")
                for name in form.changed_data
            ]
            logger.info(
                "Payment settings updated by %s (fields: %s)",
                request.user.email, ", ".join(form.changed_data) or "none",
            )
            messages.success(
                request,
                "Payment settings saved." + (f" Changed: {', '.join(changed)}." if changed else ""),
            )
            return redirect("dashboard:payment_settings")
        messages.error(request, "Please correct the errors below.")
    else:
        form = PaymentSettingsForm(instance=instance)

    context = {
        "form": form,
        "settings_obj": instance,
        "roles": role_names(request.user),
        "is_manager": True,
        "webhook_url": request.build_absolute_uri("/api/payments/webhook/"),
    }
    return render(request, "dashboard/payment_settings.html", context)


@staff_required
@require_POST
@permission_required("payments.add_refund", raise_exception=True)
def issue_refund(request, reference):
    """
    Refund a booking's payment, in full or in part.

    Manager only, and always attributed: the legacy single shared admin login
    made it impossible to say who refunded what.
    """
    booking = get_object_or_404(Booking, reference=reference)
    payment = booking.payments.filter(status=Payment.Status.SUCCEEDED).first()

    if payment is None:
        messages.error(request, "There is no successful payment to refund.")
        return redirect("dashboard:booking_detail", reference=reference)

    raw_amount = (request.POST.get("amount") or "").strip()
    reason = (request.POST.get("reason") or "").strip()

    try:
        amount = Decimal(raw_amount) if raw_amount else None
    except InvalidOperation:
        messages.error(request, f"{raw_amount!r} is not a valid amount.")
        return redirect("dashboard:booking_detail", reference=reference)

    try:
        refund = gateway.refund(
            payment, amount=amount, reason=reason, created_by=request.user,
        )
    except (gateway.PaymentConfigurationError, gateway.PaymentGatewayError) as exc:
        messages.error(request, str(exc))
        return redirect("dashboard:booking_detail", reference=reference)

    logger.info(
        "Refund %s of %s on %s issued by %s",
        refund.stripe_refund_id, refund.amount, booking.reference, request.user.email,
    )
    messages.success(
        request, f"Refunded {refund.amount} {payment.currency} on {booking.reference}.",
    )
    return redirect("dashboard:booking_detail", reference=reference)


@staff_required
@permission_required("notifications.change_emailsettings", raise_exception=True)
def email_settings(request):
    """SMTP credentials and a way to prove they work."""
    if not is_manager(request.user):
        raise PermissionDenied("Only managers can change email settings.")

    instance = EmailSettings.load()

    if request.method == "POST" and request.POST.get("action") == "test":
        recipient = (request.POST.get("test_email") or request.user.email).strip()
        ok, error = mailer.send_test_message(recipient)
        if ok:
            messages.success(request, f"Test message sent to {recipient}.")
        else:
            messages.error(request, f"Test message failed: {error}")
        return redirect("dashboard:email_settings")

    if request.method == "POST":
        form = EmailSettingsForm(request.POST, instance=instance)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            logger.info(
                "Email settings updated by %s (fields: %s)",
                request.user.email, ", ".join(form.changed_data) or "none",
            )
            messages.success(request, "Email settings saved.")
            return redirect("dashboard:email_settings")
        messages.error(request, "Please correct the errors below.")
    else:
        form = EmailSettingsForm(instance=instance)

    return render(request, "dashboard/email_settings.html", {
        "form": form,
        "settings_obj": instance,
        "recent": EmailLog.objects.all()[:15],
        "failures": EmailLog.objects.filter(succeeded=False).count(),
    })
