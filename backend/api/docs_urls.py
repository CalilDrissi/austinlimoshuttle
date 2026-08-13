"""
API documentation routes.

Served from our own domain via drf-spectacular-sidecar: the Content-Security-
Policy forbids external scripts, so the default CDN-hosted Swagger UI would
render a blank page.

Open in development, staff-only in production. The schema lists every endpoint,
its throttles and its error shapes -- useful reconnaissance, and of no value to
a customer.
"""

from django.conf import settings
from django.urls import path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.permissions import BasePermission


class DocsAccess(BasePermission):
    """
    Open when DEBUG, staff-only otherwise.

    Checked per request rather than resolved at import: a module-level
    `[AllowAny] if settings.DEBUG else [IsAdminUser]` freezes whichever value
    DEBUG had at startup, which is invisible until the wrong one ships.
    """

    message = "API documentation is available to staff accounts only."

    def has_permission(self, request, view):
        if settings.DEBUG:
            return True
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and user.is_staff)


urlpatterns = [
    path("schema/", SpectacularAPIView.as_view(
        permission_classes=[DocsAccess]), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(
        url_name="api-docs:schema", permission_classes=[DocsAccess]), name="swagger"),
    path("redoc/", SpectacularRedocView.as_view(
        url_name="api-docs:schema", permission_classes=[DocsAccess]), name="redoc"),
]
