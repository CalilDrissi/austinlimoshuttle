"""
Staff roles.

The legacy system had a single shared admin login, so no action could be
attributed to a person and everyone had every capability. Three groups replace
it:

  Dispatcher -- the daily job: see bookings, assign drivers, change status
  Manager    -- the above plus rates, surcharges, refunds and exports
  Editor     -- content only

Group membership is the source of truth; `is_staff` only controls whether an
account can reach the dashboard at all.
"""

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

DISPATCHER = "Dispatcher"
MANAGER = "Manager"
EDITOR = "Editor"

# app_label.model -> permission codenames granted
ROLE_PERMISSIONS: dict[str, dict[str, list[str]]] = {
    DISPATCHER: {
        "bookings.booking": ["view", "add", "change"],
        "bookings.driver": ["view", "add", "change"],
        "bookings.bookingstatuschange": ["view", "add"],
        "bookings.bookingpriceline": ["view"],
        "payments.payment": ["view"],
        "enquiries.contactmessage": ["view", "change"],
        "accounts.user": ["view"],
        "fleet.vehicle": ["view"],
    },
    MANAGER: {
        "bookings.booking": ["view", "add", "change"],
        "bookings.driver": ["view", "add", "change", "delete"],
        "bookings.bookingstatuschange": ["view", "add"],
        "bookings.bookingpriceline": ["view"],
        "payments.payment": ["view"],
        "payments.refund": ["view", "add"],
        # Stripe credentials. Manager only -- these authorise charges and
        # refunds against the real account.
        "payments.paymentsettings": ["view", "change"],
        "payments.paypalsettings": ["view", "change"],
        "notifications.emailsettings": ["view", "change"],
        "notifications.emaillog": ["view"],
        "notifications.smssettings": ["view", "change"],
        "notifications.smslog": ["view"],
        "enquiries.contactmessage": ["view", "change"],
        "accounts.user": ["view", "add", "change"],
        "accounts.billingaddress": ["view", "change"],
        "accounts.corporateaccount": ["view", "change"],
        "fleet.vehicle": ["view", "add", "change"],
        "fleet.distanceband": ["view", "add", "change", "delete"],
        "pricing.timesurcharge": ["view", "add", "change"],
        "pricing.blackoutdate": ["view", "add", "change", "delete"],
        "pricing.cityroute": ["view", "add", "change", "delete"],
        "pricing.cityrouteprice": ["view", "add", "change", "delete"],
        "pricing.pricingsettings": ["view", "change"],
        # The whole of website content. A Manager is the client's own account,
        # and the point of the dashboard is that they never need Django's admin
        # -- which means every model with a screen must be reachable by them.
        "content.page": ["view", "add", "change", "delete"],
        "content.banner": ["view", "add", "change", "delete"],
        "content.testimonial": ["view", "add", "change", "delete"],
        "content.galleryimage": ["view", "add", "change", "delete"],
        "content.sitesettings": ["view", "change"],
    },
    EDITOR: {
        "content.page": ["view", "add", "change"],
        "content.banner": ["view", "add", "change", "delete"],
        "content.testimonial": ["view", "add", "change", "delete"],
        "content.galleryimage": ["view", "add", "change", "delete"],
        "content.sitesettings": ["view", "change"],
        "fleet.vehicle": ["view"],
    },
}


def sync_roles() -> dict[str, int]:
    """
    Create the groups and set their permissions.

    Idempotent: safe to run on every deploy, and the way permissions are kept in
    code review rather than clicked into a UI nobody audits.
    """
    counts: dict[str, int] = {}

    for role, model_permissions in ROLE_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=role)
        wanted: list[Permission] = []

        for dotted, actions in model_permissions.items():
            app_label, model = dotted.split(".")
            try:
                content_type = ContentType.objects.get(app_label=app_label, model=model)
            except ContentType.DoesNotExist:
                continue
            for action in actions:
                codename = f"{action}_{model}"
                permission = Permission.objects.filter(
                    content_type=content_type, codename=codename,
                ).first()
                if permission:
                    wanted.append(permission)

        group.permissions.set(wanted)
        counts[role] = len(wanted)

    return counts


def role_names(user) -> list[str]:
    return sorted(user.groups.values_list("name", flat=True))


def is_manager(user) -> bool:
    return user.is_superuser or user.groups.filter(name=MANAGER).exists()


def is_dispatcher(user) -> bool:
    return (
        user.is_superuser
        or user.groups.filter(name__in=[DISPATCHER, MANAGER]).exists()
    )
