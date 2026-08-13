"""
Shared base for legacy import commands.

Every importer is idempotent: it keys on a `legacy_*_id` field, so re-running
updates rather than duplicating. That matters because the import will be
rehearsed many times before the real cutover.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from .legacy_db import LegacyDataError, assert_sanitised

MAX_EXCEPTIONS_SHOWN = 20


@dataclass
class ImportReport:
    """Outcome of a single import run."""

    label: str
    created: int = 0
    updated: int = 0
    skipped: int = 0
    exceptions: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.created + self.updated + self.skipped

    def skip(self, reason: str) -> None:
        self.skipped += 1
        self.exceptions.append(reason)

    def render(self) -> str:
        lines = [
            f"{self.label}: {self.created} created, {self.updated} updated, "
            f"{self.skipped} skipped ({self.total} legacy rows seen)"
        ]
        if self.exceptions:
            lines.append(f"  {len(self.exceptions)} exception(s):")
            for item in self.exceptions[:MAX_EXCEPTIONS_SHOWN]:
                lines.append(f"    - {item}")
            if len(self.exceptions) > MAX_EXCEPTIONS_SHOWN:
                lines.append(f"    ... and {len(self.exceptions) - MAX_EXCEPTIONS_SHOWN} more")
        return "\n".join(lines)


class LegacyImportCommand(BaseCommand):
    """
    Base class for importers.

    Subclasses implement `run_import(report)` and set `label`.
    """

    label = "import"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Roll back at the end. Reports exactly what would change.",
        )
        parser.add_argument(
            "--limit", type=int, default=None,
            help="Process only the first N legacy rows (for quick checks).",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.limit = options["limit"]

        try:
            # Refuse to touch a replica that still holds cardholder data.
            assert_sanitised()
        except LegacyDataError as exc:
            raise CommandError(str(exc)) from exc

        report = ImportReport(label=self.label)

        try:
            with transaction.atomic():
                self.run_import(report)
                if self.dry_run:
                    self.stdout.write(self.style.WARNING("dry run — rolling back"))
                    transaction.set_rollback(True)
        except LegacyDataError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS(report.render()))

    def run_import(self, report: ImportReport) -> None:  # pragma: no cover
        raise NotImplementedError

    # -- helpers -----------------------------------------------------------

    def apply_limit(self, rows: list) -> list:
        return rows[: self.limit] if self.limit else rows
