"""PostgreSQL-isolated Trash behavior; these tests never select development."""
import io
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, IntegrityError, close_old_connections, connection, transaction
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.reviews.models import Deliverable, Review
from apps.tasks.models import Task, TaskAssignment, TaskComment
from apps.workspace.models import Profile, ProfileInvitation, ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .services import RETENTION, TrashConflict, item_data, mutate, purge_blockers

User = get_user_model()


class TrashFixture:
    def fixture(self):
        for label in ("owner", "admin", "manager", "editor", "viewer", "outsider"):
            setattr(self, label, User.objects.create_user(username=f"trash-{label}", email=f"trash-{label}@example.test", password=None))
        self.profile = create_profile_with_owner(name="Trash organization", owner=self.owner)
        self.memberships = {}
        for label in ("admin", "manager", "editor", "viewer"):
            self.memberships[label] = ProfileMembership.objects.create(profile=self.profile, user=getattr(self, label), role="ADMIN" if label == "admin" else "MEMBER")
        self.workspace = Workspace.objects.create(profile=self.profile, owner=self.owner, name="Trash Workspace", period=date(2026, 11, 1))
        for label, role in (("manager", "ADMIN"), ("editor", "MEMBER"), ("viewer", "VIEWER")):
            WorkspaceMember.objects.create(workspace=self.workspace, user=getattr(self, label), role=role)
        self.other_profile = create_profile_with_owner(name="Other organization", owner=self.outsider)
        self.other_workspace = Workspace.objects.create(profile=self.other_profile, owner=self.outsider, name="Other Workspace", period=date(2026, 11, 1))
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def task(self, **overrides):
        return Task.objects.create(**{"workspace": self.workspace, "created_by": self.owner, "title": "Preserved task", **overrides})

    def action(self, obj, action, actor=None, **kwargs):
        return mutate(actor=actor or self.owner, object_type=obj.__class__.__name__.upper(), object_id=obj.pk, action=action, **kwargs)

    def age(self, obj, days=31):
        at = timezone.now() - timedelta(days=days)
        type(obj).objects.filter(pk=obj.pk).update(deleted_at=at, deleted_by=self.owner, purge_after=at+RETENTION)
        obj.refresh_from_db()
        return obj

    def notice(self, task):
        event = AuditLog.objects.create(user=self.owner, action="task.assigned", entity_name="Task", entity_id=task.pk, metadata={"profile_id": str(self.profile.pk)})
        return Notification.objects.create(user=self.editor, title="Task notice", message="Synthetic", event_type="TASK_ASSIGNED", profile=self.profile, workspace=self.workspace, task=task, event=event)

    def url(self, obj, action):
        return f"/api/v1/trash/{obj.__class__.__name__.lower()}/{obj.pk}/{action}/"


class TrashApiServiceTests(TrashFixture, TestCase):
    def setUp(self):
        self.fixture()

    def test_task_delete_restore_preserves_all_states_and_720_hour_deadline(self):
        for state in Task.Status.values:
            with self.subTest(state=state):
                task = self.task(status=state)
                self.action(task, "delete")
                task.refresh_from_db()
                self.assertEqual(task.status, state)
                self.assertEqual(task.purge_after-task.deleted_at, RETENTION)
                self.assertEqual(task.deleted_by_id, self.owner.pk)
                self.action(task, "restore")
                task.refresh_from_db()
                self.assertEqual(task.status, state)
                self.assertIsNone(task.deleted_at)
                self.assertIsNone(task.deleted_by_id)
                self.assertIsNone(task.purge_after)

    def test_repeated_delete_never_extends_deadline_or_duplicates_audit(self):
        task = self.task()
        self.action(task, "delete")
        task.refresh_from_db()
        before = (task.deleted_at, task.purge_after, task.updated_at)
        self.action(task, "delete")
        task.refresh_from_db()
        self.assertEqual(before, (task.deleted_at, task.purge_after, task.updated_at))
        self.assertEqual(AuditLog.objects.filter(action="task.deleted", entity_id=task.pk).count(), 1)

    def test_independent_child_deletion_survives_parent_restore(self):
        parent = self.task()
        child = self.task(parent=parent)
        self.action(child, "delete")
        child.refresh_from_db()
        original = (child.deleted_at, child.purge_after)
        self.action(parent, "delete")
        self.assertTrue(item_data(child, self.owner)["parent_deleted"])
        with self.assertRaises(TrashConflict) as ctx:
            self.action(child, "restore")
        self.assertEqual(ctx.exception.code, "PARENT_DELETED")
        self.action(parent, "restore")
        child.refresh_from_db()
        self.assertEqual(original, (child.deleted_at, child.purge_after))

    def test_workspace_profile_deletion_is_effective_and_does_not_stamp_children(self):
        task = self.task()
        self.action(self.workspace, "delete")
        task.refresh_from_db()
        self.assertIsNone(task.deleted_at)
        self.assertTrue(item_data(task, self.owner)["parent_deleted"])
        self.action(self.workspace, "restore")
        self.action(self.profile, "delete")
        self.workspace.refresh_from_db()
        self.assertIsNone(self.workspace.deleted_at)
        self.assertTrue(item_data(self.workspace, self.owner)["parent_deleted"])
        self.action(self.profile, "restore")

    def test_restore_never_reactivates_revoked_membership_or_assignment(self):
        task = self.task()
        assignment = TaskAssignment.objects.create(task=task, user=self.editor, is_active=False)
        wm = WorkspaceMember.objects.get(workspace=self.workspace, user=self.editor)
        wm.is_active = False
        wm.save(update_fields=("is_active",))
        self.memberships["editor"].is_active = False
        self.memberships["editor"].save(update_fields=("is_active",))
        self.action(task, "delete")
        self.action(task, "restore")
        self.assertFalse(TaskAssignment.objects.get(pk=assignment.pk).is_active)
        self.assertFalse(WorkspaceMember.objects.get(pk=wm.pk).is_active)
        self.assertFalse(ProfileMembership.objects.get(pk=self.memberships["editor"].pk).is_active)

    def test_archived_profile_roundtrip_preserves_archive_and_blocks_child_restore(self):
        task = self.task()
        self.action(task, "delete")
        Profile.objects.filter(pk=self.profile.pk).update(status="ARCHIVED")
        with self.assertRaises(TrashConflict) as ctx:
            self.action(task, "restore")
        self.assertEqual(ctx.exception.code, "PARENT_ARCHIVED")
        self.action(self.profile, "delete")
        self.action(self.profile, "restore")
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.status, "ARCHIVED")

    def test_expired_restore_is_blocked_without_deadline_extension(self):
        task = self.age(self.task())
        before = task.purge_after
        with self.assertRaises(TrashConflict) as ctx:
            self.action(task, "restore")
        self.assertEqual(ctx.exception.code, "EXPIRED")
        task.refresh_from_db()
        self.assertEqual(task.purge_after, before)

    def test_owner_admin_workspace_manager_and_viewer_permissions(self):
        task = self.task()
        self.action(task, "delete", actor=self.manager)
        self.action(task, "restore", actor=self.manager)
        for actor in (self.editor, self.viewer, self.outsider):
            self.client.force_authenticate(actor)
            self.assertEqual(self.client.post(self.url(task, "delete"), {}, format="json").status_code, 404)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(self.url(self.profile, "delete"), {}, format="json").status_code, 404)
        self.assertEqual(self.client.post(self.url(self.workspace, "delete"), {}, format="json").status_code, 200)

    def test_pagination_filters_strict_validation_and_nonpii_deleter(self):
        for index in range(22):
            task = self.task(title=f"Deleted {index}")
            self.action(task, "delete")
        response = self.client.get("/api/v1/trash/?object_type=TASK")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 22)
        self.assertEqual(len(response.data["results"]), 20)
        item = response.data["results"][0]
        self.assertEqual(set(item["deleted_by"]), {"display_name"})
        self.assertNotIn("email", json.dumps(response.data, default=str))
        self.assertEqual(len(self.client.get("/api/v1/trash/?object_type=TASK&page=2").data["results"]), 2)
        self.assertEqual(self.client.get("/api/v1/trash/?search=not-found").data["count"], 0)
        self.assertEqual(self.client.get("/api/v1/trash/?page_size=100").status_code, 400)
        self.assertEqual(self.client.get("/api/v1/trash/?profile_id="+str(self.other_profile.pk)).status_code, 404)

    def test_invalid_unicode_nul_unknown_fields_and_identity_injection_rejected(self):
        task = self.task()
        for payload in ({"owner_id": str(self.outsider.pk)}, {"deleted_at": timezone.now().isoformat()}, {"role": "OWNER"}):
            self.assertEqual(self.client.post(self.url(task, "delete"), payload, format="json").status_code, 400)
        for value in ("\x00", "\ud800", "\n"):
            from urllib.parse import quote
            self.assertEqual(self.client.get("/api/v1/trash/?search="+quote(value, errors="surrogatepass")).status_code, 400)

    def test_session_auth_csrf_preserved(self):
        client = APIClient(enforce_csrf_checks=True)
        task = self.task()
        self.assertEqual(client.post(self.url(task, "delete"), {}, format="json").status_code, 403)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url(task, "delete"), {}, format="json").status_code, 403)
        client.get("/api/auth/csrf/")
        response = client.post(self.url(task, "delete"), {}, format="json", HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value)
        self.assertEqual(response.status_code, 200)

    def test_audit_failure_rolls_back_delete_and_restore(self):
        task = self.task()
        with patch("apps.trash.services._audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.action(task, "delete")
        task.refresh_from_db()
        self.assertIsNone(task.deleted_at)
        self.action(task, "delete")
        with patch("apps.trash.services._audit", side_effect=RuntimeError("synthetic audit failure")):
            with self.assertRaises(RuntimeError):
                self.action(task, "restore")
        task.refresh_from_db()
        self.assertIsNotNone(task.deleted_at)

    def test_purge_defaults_disabled_and_does_not_mutate(self):
        task = self.age(self.task())
        with override_settings(TRASH_PURGE_ENABLED=False):
            response = self.client.post(self.url(task, "purge"), {"confirm": True}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_purge_before_thirty_days_blocked_and_owner_only(self):
        task = self.task()
        self.action(task, "delete")
        self.assertEqual(self.client.post(self.url(task, "purge"), {"confirm": True}, format="json").status_code, 409)
        self.age(task)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(self.url(task, "purge"), {"confirm": True}, format="json").status_code, 403)

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_exact_name_and_literal_confirmation_required(self):
        self.age(self.workspace)
        for payload in ({"confirm": "true", "confirmation_name": self.workspace.name}, {"confirm": True, "confirmation_name": self.workspace.name+" "}, {"confirm": True}):
            self.assertEqual(self.client.post(self.url(self.workspace, "purge"), payload, format="json").status_code, 400)
        self.assertEqual(self.client.post(self.url(self.workspace, "purge"), {"confirm": True, "confirmation_name": self.workspace.name}, format="json").status_code, 204)

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_clean_subtree_purge_orders_protected_children_and_retains_audit_users(self):
        parent = self.task()
        child = self.task(parent=parent)
        TaskComment.objects.create(task=child, user=self.editor, content="Synthetic comment")
        TaskAssignment.objects.create(task=child, user=self.editor)
        Deliverable.objects.create(task=child, uploaded_by=self.editor, file_url="https://example.test/result", revision=1)
        notice = self.notice(child)
        audit_id = notice.event_id
        self.age(parent)
        self.action(parent, "purge", confirm=True)
        self.assertFalse(Task.objects.filter(pk__in=(parent.pk, child.pk)).exists())
        self.assertFalse(Notification.objects.filter(pk=notice.pk).exists())
        self.assertTrue(AuditLog.objects.filter(pk=audit_id).exists())
        self.assertTrue(AuditLog.objects.filter(action="task.purged", entity_id=parent.pk).exists())
        self.assertEqual(User.objects.count(), 6)

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_financial_history_hold_preserves_approved_and_unknown_snapshots(self):
        for recorded in (False, True):
            task = self.task(status="COMPLETED")
            delivered = Deliverable.objects.create(task=task, uploaded_by=self.editor, file_url="https://example.test/result", revision=1, status="APPROVED")
            review = Review.objects.create(deliverable=delivered, reviewer=self.owner, status="APPROVED", compensation_snapshot_recorded=recorded, compensation_snapshot_vnd="500000" if recorded else None)
            self.age(task)
            with self.assertRaises(TrashConflict) as ctx:
                self.action(task, "purge", confirm=True)
            self.assertIn("PROTECTED_HISTORY", {row["code"] for row in ctx.exception.blockers})
            self.assertTrue(Review.objects.filter(pk=review.pk).exists())

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_pending_and_changes_requested_reviews_are_retention_holds(self):
        for state in (Review.Status.PENDING, Review.Status.REQUEST_CHANGE):
            with self.subTest(state=state):
                task = self.age(self.task(status="WORKING"))
                delivered = Deliverable.objects.create(task=task, uploaded_by=self.editor,
                    file_url="https://example.test/result", revision=1)
                review = Review.objects.create(deliverable=delivered, reviewer=self.owner,
                    status=state, comment="Preserve synthetic feedback")
                with self.assertRaises(TrashConflict) as ctx:
                    self.action(task, "purge", confirm=True)
                self.assertIn("PROTECTED_HISTORY", {row["code"] for row in ctx.exception.blockers})
                self.assertTrue(Review.objects.filter(pk=review.pk).exists())
                self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_concurrent_restore_is_not_serialized_as_a_deleted_trash_row(self):
        task = self.task()
        self.action(task, "delete")
        from .services import resolve_entry

        def restore_before_hydration(kind, object_id):
            Task.objects.filter(pk=task.pk).update(deleted_at=None, deleted_by=None, purge_after=None)
            return resolve_entry(kind, object_id)

        with patch("apps.trash.views.resolve_entry", side_effect=restore_before_hydration):
            response = self.client.get("/api/v1/trash/?object_type=TASK")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])

    def test_concurrent_purge_does_not_fail_the_entire_trash_page(self):
        task = self.task()
        self.action(task, "delete")
        from apps.workspace.access import TenantAccessNotFound
        with patch("apps.trash.views.resolve_entry", side_effect=TenantAccessNotFound):
            response = self.client.get("/api/v1/trash/?object_type=TASK")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_profile_purge_never_deletes_multitenant_global_user(self):
        empty = create_profile_with_owner(name="Disposable organization", owner=self.owner)
        self.age(empty)
        self.action(empty, "purge", confirm=True, confirmation_name=empty.name)
        self.assertFalse(Profile.objects.filter(pk=empty.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.owner.pk, is_active=True).exists())
        self.assertTrue(ProfileMembership.objects.filter(profile=self.profile, user=self.owner, is_active=True).exists())
        self.assertTrue(Profile.objects.filter(pk=self.other_profile.pk).exists())

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_due_command_dry_run_execution_gate_and_retry(self):
        task = self.age(self.task())
        out = io.StringIO()
        call_command("purge_trash", stdout=out)
        self.assertTrue(json.loads(out.getvalue())["dry_run"])
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())
        with override_settings(TRASH_PURGE_ENABLED=False), self.assertRaises(CommandError):
            call_command("purge_trash", execute=True, stdout=io.StringIO())
        call_command("purge_trash", execute=True, stdout=io.StringIO())
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())
        out = io.StringIO()
        call_command("purge_trash", execute=True, stdout=out)
        self.assertEqual(json.loads(out.getvalue())["purged"], 0)

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_unknown_fk_blocks_without_querying_unapplied_ai_tables(self):
        task = self.age(self.task())
        # PostgreSQL temporary tables cannot reference permanent tables. This
        # exact owned fixture table lives only inside the isolated test database.
        self.assertRegex(connection.settings_dict["NAME"], r"^test_hustlytasker_[0-9a-f]{32}$")
        table = "trash_unknown_reference_" + uuid4().hex
        quoted = connection.ops.quote_name(table)
        with connection.cursor() as cursor:
            cursor.execute(f'CREATE TABLE public.{quoted} (id uuid PRIMARY KEY, task_id uuid REFERENCES tasks_task(id))')
            cursor.execute(f'INSERT INTO public.{quoted} (id,task_id) VALUES (%s,%s)', [self.owner.pk, task.pk])
        try:
            with self.assertRaises(TrashConflict) as ctx:
                self.action(task, "purge", confirm=True)
            self.assertEqual(ctx.exception.code, "UNKNOWN_REFERENCE")
            self.assertTrue(Task.objects.filter(pk=task.pk).exists())
        finally:
            with connection.cursor() as cursor:
                cursor.execute(f'DROP TABLE public.{quoted}')

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_purge_failure_rolls_back_child_removal_and_audit(self):
        task = self.age(self.task())
        notice = self.notice(task)
        original = QuerySet._raw_delete
        def fail_on_task(query, using):
            if query.model is Task:
                raise RuntimeError("synthetic physical failure")
            return original(query, using)
        with patch.object(QuerySet, "_raw_delete", fail_on_task):
            with self.assertRaises(RuntimeError):
                self.action(task, "purge", confirm=True)
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())
        self.assertTrue(Notification.objects.filter(pk=notice.pk).exists())
        self.assertFalse(AuditLog.objects.filter(action="task.purged", entity_id=task.pk).exists())

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_profile_invitation_twelve_month_hold_then_scoped_removal(self):
        now = timezone.now()
        invitation = ProfileInvitation.objects.create(
            profile=self.profile, recipient_email_normalized="synthetic-history@example.test",
            recipient_user=self.editor, requested_role="MEMBER", token_digest="a"*64,
            invited_by_membership=ProfileMembership.objects.get(profile=self.profile, user=self.owner),
            status="ACCEPTED", accepted_at=now, accepted_by=self.editor, delivery_status="SENT",
            delivery_attempted_at=now, delivered_at=now,
        )
        self.age(self.profile)
        with self.assertRaises(TrashConflict) as ctx:
            self.action(self.profile, "purge", confirm=True, confirmation_name=self.profile.name)
        self.assertIn("INVITATION_RETENTION", {row["code"] for row in ctx.exception.blockers})
        old = now.replace(year=now.year-2)
        ProfileInvitation.objects.filter(pk=invitation.pk).update(created_at=old, expires_at=old+timedelta(days=7), accepted_at=old, delivery_attempted_at=old, delivered_at=old)
        self.action(self.profile, "purge", confirm=True, confirmation_name=self.profile.name)
        self.assertFalse(Profile.objects.filter(pk=self.profile.pk).exists())
        self.assertTrue(Profile.objects.filter(pk=self.other_profile.pk).exists())
        self.assertTrue(User.objects.filter(pk=self.editor.pk).exists())

    def test_calendar_twelve_month_boundary_does_not_shorten_leap_year(self):
        from .services import _calendar_year
        at = datetime(2023, 3, 1, tzinfo=datetime_timezone.utc)
        self.assertEqual((_calendar_year(at)-at).days, 366)
        self.assertEqual(_calendar_year(datetime(2024, 2, 29, tzinfo=datetime_timezone.utc)), datetime(2025, 2, 28, tzinfo=datetime_timezone.utc))

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_child_with_later_explicit_deadline_is_never_purged_early(self):
        parent = self.age(self.task())
        child = self.age(self.task(parent=parent), days=10)
        with self.assertRaises(TrashConflict) as ctx:
            self.action(parent, "purge", confirm=True)
        self.assertIn("RETENTION_NOT_ELAPSED", {row["code"] for row in ctx.exception.blockers})
        self.assertTrue(Task.objects.filter(pk=child.pk).exists())

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_ai_proposal_reference_blocks_workspace_without_ai0002(self):
        from apps.ai.models import AiProposal
        now = timezone.now()
        proposal = AiProposal.objects.create(actor=self.owner, profile=self.profile, workspace=self.workspace,
            scenario_id="isolated-trash", expires_at=now+timedelta(minutes=30), payload_expires_at=now+timedelta(days=7))
        self.age(self.workspace)
        with self.assertRaises(TrashConflict) as ctx:
            self.action(self.workspace, "purge", confirm=True, confirmation_name=self.workspace.name)
        self.assertIn("AI_DEPENDENCY", {row["code"] for row in ctx.exception.blockers})
        self.assertTrue(AiProposal.objects.filter(pk=proposal.pk).exists())

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_cross_tenant_corrupt_notification_is_not_removed(self):
        task = self.age(self.task())
        notice = self.notice(task)
        Notification.objects.filter(pk=notice.pk).update(profile=self.other_profile)
        with self.assertRaises(TrashConflict) as ctx:
            self.action(task, "purge", confirm=True)
        self.assertEqual(ctx.exception.code, "UNKNOWN_REFERENCE")
        self.assertTrue(Notification.objects.filter(pk=notice.pk).exists())

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_fk_inspection_failure_returns_safe_conflict(self):
        task = self.age(self.task())
        with patch("apps.trash.services._inspect_foreign_reference", side_effect=DatabaseError("private database detail must not leak")):
            response = self.client.post(self.url(task, "purge"), {"confirm": True}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.data["code"], "UNKNOWN_REFERENCE")
        self.assertNotIn("private database detail", str(response.data))
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_command_limit_does_not_starve_eligible_rows_behind_retention_holds(self):
        held = self.age(self.task(status="COMPLETED"), days=32)
        eligible = self.age(self.task(), days=31)
        out = io.StringIO()
        call_command("purge_trash", execute=True, limit=1, stdout=out)
        report = json.loads(out.getvalue())
        self.assertEqual(report["purged"], 1)
        self.assertEqual(report["blocked"], 1)
        self.assertEqual(report["scanned"], 2)
        self.assertEqual(report["blocker_counts"], {"PROTECTED_HISTORY": 1})
        self.assertTrue(Task.objects.filter(pk=held.pk).exists())
        self.assertFalse(Task.objects.filter(pk=eligible.pk).exists())

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_command_logs_allowlisted_blockers_and_rechecks_held_rows(self):
        task = self.age(self.task())
        with patch("apps.trash.management.commands.purge_trash.purge_blockers",
                   side_effect=TrashConflict("private-detail", "Do not log private detail")):
            out = io.StringIO()
            with self.assertLogs("apps.trash.management.commands.purge_trash", level="INFO") as captured:
                call_command("purge_trash", execute=True, stdout=out)
        report = json.loads(out.getvalue())
        self.assertEqual(report["blocker_counts"], {"OTHER_BLOCKER": 1})
        self.assertEqual((report["blocked"], report["purged"], report["errors"]), (1, 0, 0))
        self.assertNotIn("private-detail", " ".join(captured.output))
        self.assertNotIn("Do not log", " ".join(captured.output))
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())
        retry = io.StringIO()
        call_command("purge_trash", execute=True, stdout=retry)
        self.assertEqual(json.loads(retry.getvalue())["purged"], 1)

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_command_treats_concurrently_removed_target_as_safe_noop(self):
        self.age(self.task())
        from apps.workspace.access import TenantAccessNotFound
        out = io.StringIO()
        with patch("apps.trash.management.commands.purge_trash.mutate", side_effect=TenantAccessNotFound):
            call_command("purge_trash", execute=True, stdout=out)
        report = json.loads(out.getvalue())
        self.assertEqual((report["already_absent"], report["purged"], report["blocked"], report["errors"]), (1, 0, 0, 0))

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_command_unexpected_failure_is_nonzero_without_false_success(self):
        task = self.age(self.task())
        out = io.StringIO()
        with patch("apps.trash.management.commands.purge_trash.mutate", side_effect=RuntimeError("private error")):
            with self.assertRaises(CommandError) as caught:
                call_command("purge_trash", execute=True, stdout=out)
        report = json.loads(out.getvalue())
        self.assertEqual((report["purged"], report["errors"]), (0, 1))
        self.assertNotIn("private error", str(caught.exception))
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_database_rejects_partial_or_non720_hour_metadata(self):
        task = self.task()
        for obj in (task, self.workspace, self.profile):
            at = timezone.now()
            for changes in ({"deleted_at": at}, {"deleted_at": at, "purge_after": at+timedelta(days=29)}):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    type(obj).objects.filter(pk=obj.pk).update(**changes)
            obj.refresh_from_db()
            self.assertIsNone(obj.deleted_at)

    def test_permission_revocation_between_preview_and_delete_is_revalidated(self):
        task = self.task()
        self.client.force_authenticate(self.manager)
        current = self.client.get(f"/api/v1/profiles/{self.profile.pk}/workspaces/{self.workspace.pk}/tasks/{task.pk}/")
        self.assertEqual(current.status_code, 200)
        self.assertTrue(current.data["can_delete"])
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.manager).update(is_active=False)
        self.assertEqual(self.client.post(self.url(task, "delete"), {}, format="json").status_code, 404)
        task.refresh_from_db()
        self.assertIsNone(task.deleted_at)


class TrashConcurrencyTests(TrashFixture, TransactionTestCase):
    def setUp(self):
        self.fixture()

    def race(self, calls):
        barrier = Barrier(len(calls))
        def worker(call):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                call()
                return "ok"
            except Exception as exc:
                from apps.workspace.access import TenantAccessNotFound
                if not isinstance(exc, (TrashConflict, TenantAccessNotFound)):
                    raise
                return "conflict"
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            return list(pool.map(worker, calls))

    def test_concurrent_delete_is_one_metadata_and_audit_transition(self):
        task = self.task()
        result = self.race([lambda: self.action(task, "delete"), lambda: self.action(task, "delete")])
        self.assertEqual(result, ["ok", "ok"])
        task.refresh_from_db()
        self.assertEqual(task.purge_after-task.deleted_at, RETENTION)
        self.assertEqual(AuditLog.objects.filter(entity_id=task.pk, action="task.deleted").count(), 1)

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_concurrent_purge_has_one_terminal_winner(self):
        task = self.age(self.task())
        result = self.race([lambda: self.action(task, "purge", confirm=True), lambda: self.action(task, "purge", confirm=True)])
        self.assertEqual(sorted(result), ["conflict", "ok"])
        self.assertEqual(AuditLog.objects.filter(entity_id=task.pk, action="task.purged").count(), 1)

    def test_concurrent_delete_restore_keeps_business_and_access_history(self):
        task = self.task(status="WORKING")
        assignment = TaskAssignment.objects.create(task=task, user=self.editor)
        self.action(task, "delete")
        self.race([lambda: self.action(task, "delete"), lambda: self.action(task, "restore")])
        task.refresh_from_db()
        assignment.refresh_from_db()
        self.assertEqual(task.status, "WORKING")
        self.assertTrue(assignment.is_active)
        self.assertEqual(AuditLog.objects.filter(entity_id=task.pk, action="task.restored").count(), 1)
        if task.deleted_at is None:
            self.assertIsNone(task.purge_after)
        else:
            self.assertEqual(task.purge_after-task.deleted_at, RETENTION)

    @override_settings(TRASH_PURGE_ENABLED=True)
    def test_expired_restore_racing_purge_cannot_revive_terminal_data(self):
        task = self.age(self.task())
        result = self.race([lambda: self.action(task, "restore"), lambda: self.action(task, "purge", confirm=True)])
        self.assertEqual(sorted(result), ["conflict", "ok"])
        self.assertFalse(Task.objects.filter(pk=task.pk).exists())
        self.assertEqual(AuditLog.objects.filter(entity_id=task.pk, action="task.purged").count(), 1)
