"""Context available to every dashboard template."""

from .permissions import is_manager, role_names


def staff_context(request):
    """
    Role information for the navigation.

    Set here rather than in each view so a new screen cannot accidentally hide
    (or reveal) the Settings link by forgetting to pass it.
    """
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    return {"roles": role_names(user), "is_manager": is_manager(user)}
