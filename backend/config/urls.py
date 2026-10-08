"""
Root URL configuration.

The dashboard lives under /dashboard/ (Phase 5) and the API under /api/
(Phase 6). Django's own admin stays at /admin/ for model CRUD that does not
warrant a bespoke screen.
"""

from django.contrib import admin
from django.urls import include, path

from dashboard.views import admin_login_redirect

admin.site.site_header = "Austin Limo Shuttle"
admin.site.site_title = "Austin Limo Shuttle"
admin.site.index_title = "Administration"

urlpatterns = [
    # Ahead of admin.site.urls so it wins: the admin's own login screen is
    # never reached, and staff see one sign-in page rather than two.
    path("admin/login/", admin_login_redirect),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("driver/", include("driver.urls")),
    path("api/", include("api.urls")),
    path("api/", include(("api.docs_urls", "api-docs"), namespace="api-docs")),
]
