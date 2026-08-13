"""Context available to every dashboard template."""

from datetime import timedelta

from django.utils import timezone

from bookings.models import Booking
from enquiries.models import ContactMessage

from .permissions import is_manager, role_names


def staff_context(request):
    """
    Role information and navigation badges.

    Set here rather than in each view so a new screen cannot accidentally hide
    (or reveal) the Settings link, or lose its unread badge, by forgetting to
    pass them.

    Only runs for authenticated staff -- an anonymous request must not trigger
    two count queries on every page, including the login form.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}

    context = {"roles": role_names(user), "is_manager": is_manager(user)}

    if not user.is_staff:
        return context

    now = timezone.now()
    context["nav_dispatch_count"] = (
        Booking.objects.filter(
            pickup_at__gte=now - timedelta(hours=4),
            pickup_at__lte=now + timedelta(days=2),
        )
        .exclude(status=Booking.Status.CANCELLED)
        .count()
    )
    context["nav_unread_enquiries"] = ContactMessage.objects.filter(is_read=False).count()
    return context
