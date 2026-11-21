import json
import logging
from heapq import merge

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.trash.services import MODELS, TrashConflict, mutate, purge_blockers
from apps.workspace.access import TenantAccessNotFound

logger = logging.getLogger(__name__)
BLOCKER_CODES = {
    "PURGE_DISABLED", "RETENTION_NOT_ELAPSED", "PROTECTED_HISTORY",
    "INVITATION_RETENTION", "AI_DEPENDENCY", "UNKNOWN_REFERENCE",
    "OWNER_REQUIRED", "PARENT_DELETED", "PARENT_ARCHIVED", "EXPIRED",
}


class Command(BaseCommand):
    help = "Preview due Trash entries. --execute also requires TRASH_PURGE_ENABLED; no scheduler is installed."

    def add_arguments(self, parser):
        parser.add_argument("--execute", action="store_true")
        parser.add_argument("--limit", type=int, default=100)

    def handle(self, *args, **options):
        execute = options["execute"]
        if not 1 <= options["limit"] <= 1000:
            raise CommandError("--limit must be between 1 and1000.")
        if execute and getattr(settings, "TRASH_PURGE_ENABLED", False) is not True:
            raise CommandError("TRASH_PURGE_ENABLED is false; purge execution is not authorized.")
        now = timezone.now()
        def due_entries(kind, model):
            rows = model.objects.filter(deleted_at__isnull=False, purge_after__lte=now).order_by("purge_after", "id").values("pk", "purge_after")
            for row in rows.iterator(chunk_size=100):
                yield row["purge_after"], kind, row["pk"]
        entries = merge(*(due_entries(kind, model) for kind, model in MODELS.items()))
        result = {"dry_run": not execute, "scanned": 0, "eligible": 0, "purged": 0,
                  "blocked": 0, "already_absent": 0, "errors": 0, "blocker_counts": {}}

        def blocked(rows):
            result["blocked"] += 1
            # Never log provider exceptions, names, feedback or other raw data.
            codes = {row.get("code") for row in rows}
            for code in {code if code in BLOCKER_CODES else "OTHER_BLOCKER" for code in codes}:
                result["blocker_counts"][code] = result["blocker_counts"].get(code, 0) + 1

        def emit_summary():
            serialized = json.dumps(result, sort_keys=True)
            logger.info("Trash purge summary %s", serialized)
            self.stdout.write(serialized)

        try:
            for _, kind, object_id in entries:
                if result["eligible"] >= options["limit"]:
                    break
                result["scanned"] += 1
                obj = MODELS[kind].objects.filter(pk=object_id).first()
                if obj is None:
                    result["already_absent"] += 1
                    continue
                try:
                    blockers = [row for row in purge_blockers(obj, evaluate_disabled=True) if row["code"] != "PURGE_DISABLED"]
                except TrashConflict as exc:
                    blocked(exc.blockers)
                    continue
                if blockers:
                    blocked(blockers)
                    continue
                result["eligible"] += 1
                if execute:
                    try:
                        mutate(actor=None, object_type=kind, object_id=object_id, action="purge", automatic=True)
                        result["purged"] += 1
                    except TrashConflict as exc:
                        blocked(exc.blockers)
                    except TenantAccessNotFound:
                        # Another approved worker already removed the target.
                        result["already_absent"] += 1
        except Exception:
            result["errors"] += 1
            emit_summary()
            raise CommandError("Trash purge stopped after an unexpected error; the failed item was not reported as purged.") from None
        emit_summary()
