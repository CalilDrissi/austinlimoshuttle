"""
Root URL configuration.

The dashboard lives under /dashboard/ (Phase 5) and the API under /api/
(Phase 6). Django's own admin stays at /admin/ for model CRUD that does not
warrant a bespoke screen.
"""

from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Austin Limo Shuttle"
admin.site.site_title = "Austin Limo Shuttle"
admin.site.index_title = "Administration"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("api/", include("api.urls")),
]
