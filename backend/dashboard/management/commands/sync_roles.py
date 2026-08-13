"""Create or refresh the staff role groups."""

from django.core.management.base import BaseCommand

from dashboard.permissions import sync_roles


class Command(BaseCommand):
    help = "Create the Dispatcher, Manager and Editor groups and set permissions."

    def handle(self, *args, **options):
        counts = sync_roles()
        for role, count in counts.items():
            self.stdout.write(self.style.SUCCESS(f"{role}: {count} permissions"))
