from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "dashboard"

    def ready(self):
        """
        Populate the managed-records registry.

        Imported here rather than at module scope in crud.py: the entries name
        model classes, which cannot be imported until the app registry is
        ready. Without this the sidebar and every /manage/ URL would come up
        empty depending on import order, which is the kind of bug that only
        appears in production.
        """
        from . import managed  # noqa: F401, PLC0415
