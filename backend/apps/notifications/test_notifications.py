from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.reviews.models import Deliverable, Review
from apps.tasks.comment_services import create_comment
from apps.tasks.models import Task, TaskAssignment, TaskComment
from apps.tasks.services import (
    approve_deliverable, assign_task, request_deliverable_changes,
    start_task, submit_deliverable,
)
from apps.workspace.access import TenantAccessNotFound
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .access import notifications_visible_to
from .content import EVENT_CONTENT
from .models import Notification
from .services import emit_task_notifications, mark_notification_read


class NotificationFixture:
    @classmethod
    def make_fixture(cls):
        for name in ("owner", "admin", "manager", "editor", "second", "viewer", "other", "staff"):
            setattr(cls, name, get_user_model().objects.create_user(
                username=f"notification-{name}", email=f"notification-{name}@example.test",
                password=None, is_staff=name == "staff",
            ))
        cls.profile = create_profile_with_owner(name="Notification profile", owner=cls.owner)
        cls.workspace = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner, name="October", period=date(2026, 10, 1),
        )
        cls.sibling = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner, name="November", period=date(2026, 11, 1),
        )
        cls.memberships = {}
        for name, profile_role, workspace_role in (
            ("admin", "ADMIN", None), ("manager", "MEMBER", "ADMIN"),
            ("editor", "MEMBER", "MEMBER"), ("second", "MEMBER", "MEMBER"),
            ("viewer", "MEMBER", "VIEWER"),
        ):
            cls.memberships[name] = ProfileMembership.objects.create(
                profile=cls.profile, user=getattr(cls, name), role=profile_role,
            )
            if workspace_role:
                WorkspaceMember.objects.create(workspace=cls.workspace, user=getattr(cls, name), role=workspace_role)
        cls.other_profile = create_profile_with_owner(name="Other profile", owner=cls.other)
        cls.other_workspace = Workspace.objects.create(
            profile=cls.other_profile, owner=cls.other, name="Other October", period=date(2026, 10, 1),
        )
        cls.task = Task.objects.create(
            workspace=cls.workspace, created_by=cls.owner, title="Private task title",
        )

    @classmethod
    def setUpTestData(cls):
        cls.make_fixture()

    def scope(self):
        return {"profile_id": self.profile.id, "workspace_id": self.workspace.id, "task_id": self.task.id}

    def assign(self, member="editor"):
        return assign_task(actor=self.owner, target_profile_membership_id=self.memberships[member].id, **self.scope())

    def submitted(self):
        self.assign()
        start_task(actor=self.editor, **self.scope())
        return submit_deliverable(actor=self.editor, file_url="https://example.test/private-deliverable", **self.scope())

    def assigned_notification(self):
        self.assign()
        return Notification.objects.get(user=self.editor, event_type="TASK_ASSIGNED")

    def feed_url(self):
        return reverse("notifications:notification-list")

    def count_url(self):
        return reverse("notifications:notification-unread-count")

    def read_url(self, notification):
        return reverse("notifications:notification-read", kwargs={
            "notification_id": notification.pk if isinstance(notification, Notification) else notification,
        })


class NotificationTests(NotificationFixture, APITestCase):
    def setUp(self):
        self.client.force_login(self.editor)

    def test_actual_assignment_notifies_only_new_assignee_with_safe_content(self):
        notification = self.assigned_notification()
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual((notification.profile_id, notification.workspace_id, notification.task_id),
                         (self.profile.id, self.workspace.id, self.task.id))
        self.assertEqual((notification.title, notification.message), EVENT_CONTENT["TASK_ASSIGNED"])
        self.assertNotIn(self.task.title, notification.message)

    def test_actual_submission_notifies_only_current_review_managers(self):
        self.submitted()
        recipients = set(Notification.objects.filter(event_type="REVIEW_SUBMITTED").values_list("user_id", flat=True))
        self.assertEqual(recipients, {self.owner.id, self.admin.id, self.manager.id})

    def test_actual_approval_notifies_uploader_and_preserves_completion_workflow(self):
        deliverable = self.submitted()
        approve_deliverable(actor=self.owner, deliverable_id=deliverable.id, comment="Private feedback", **self.scope())
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "COMPLETED")
        self.assertEqual(set(Notification.objects.filter(event_type="REVIEW_APPROVED").values_list("user_id", flat=True)), {self.editor.id})
        self.assertTrue(all("Private feedback" not in row.message for row in Notification.objects.all()))

    def test_actual_request_changes_notifies_uploader_and_keeps_revision_workflow(self):
        deliverable = self.submitted()
        request_deliverable_changes(actor=self.owner, deliverable_id=deliverable.id, comment="Private requested changes", **self.scope())
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "WORKING")
        self.assertEqual(set(Notification.objects.filter(event_type="REVIEW_CHANGES_REQUESTED").values_list("user_id", flat=True)), {self.editor.id})

    def test_actual_comment_notifies_creator_and_assignee_without_actor_or_body(self):
        self.assign()
        comment = create_comment(actor=self.manager, content="Private comment body", **self.scope())
        rows = Notification.objects.filter(event_type="TASK_COMMENTED")
        self.assertEqual(set(rows.values_list("user_id", flat=True)), {self.owner.id, self.editor.id})
        self.assertTrue(all(comment.content not in row.message for row in rows))

    def test_comment_does_not_notify_actor_or_unrelated_profile_members(self):
        create_comment(actor=self.owner, content="Owner-only task", **self.scope())
        self.assertFalse(Notification.objects.exists())

    def test_existing_event_retry_is_deduplicated_and_does_not_reset_read_state(self):
        notification = self.assigned_notification()
        mark_notification_read(actor=self.editor, notification_id=notification.id)
        emit_task_notifications(event=notification.event, actor=self.owner, task=self.task, event_type="TASK_ASSIGNED")
        notification.refresh_from_db()
        self.assertEqual(Notification.objects.count(), 1)
        self.assertTrue(notification.is_read)

    def test_replaying_old_assignment_never_notifies_new_assignee(self):
        notification = self.assigned_notification()
        old_event = notification.event
        self.assign("second")
        count = Notification.objects.count()
        self.assertEqual(emit_task_notifications(event=old_event, actor=self.owner, task=self.task, event_type="TASK_ASSIGNED"), [])
        self.assertEqual(Notification.objects.count(), count)

    def test_no_notification_for_currently_revoked_recipients(self):
        ProfileMembership.objects.filter(pk=self.memberships["admin"].pk).update(is_active=False)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.manager).update(is_active=False)
        self.submitted()
        self.assertEqual(set(Notification.objects.filter(event_type="REVIEW_SUBMITTED").values_list("user_id", flat=True)), {self.owner.id})

    def test_review_outcome_skips_revoked_uploader(self):
        deliverable = self.submitted()
        self.memberships["editor"].is_active = False
        self.memberships["editor"].save(update_fields=("is_active",))
        approve_deliverable(actor=self.owner, deliverable_id=deliverable.id, **self.scope())
        self.assertFalse(Notification.objects.filter(event_type="REVIEW_APPROVED").exists())

    def test_assignment_notification_failure_rolls_back_task_assignment_and_audit(self):
        before = AuditLog.objects.count()
        with patch("apps.notifications.services.Notification.objects.get_or_create", side_effect=RuntimeError("notification unavailable")):
            with self.assertRaises(RuntimeError):
                self.assign()
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "PENDING")
        self.assertFalse(TaskAssignment.objects.exists())
        self.assertEqual(AuditLog.objects.count(), before)
        self.assertFalse(Notification.objects.exists())

    def test_submission_notification_failure_rolls_back_deliverable_status_and_audit(self):
        self.assign()
        start_task(actor=self.editor, **self.scope())
        before = (AuditLog.objects.count(), Notification.objects.count())
        with patch("apps.notifications.services.Notification.objects.get_or_create", side_effect=RuntimeError("notification unavailable")):
            with self.assertRaises(RuntimeError):
                submit_deliverable(actor=self.editor, file_url="https://example.test/rollback", **self.scope())
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "WORKING")
        self.assertFalse(Deliverable.objects.exists())
        self.assertEqual((AuditLog.objects.count(), Notification.objects.count()), before)

    def test_both_review_notification_failures_roll_back_review_and_decision(self):
        deliverable = self.submitted()
        for operation, extra in ((approve_deliverable, {}), (request_deliverable_changes, {"comment": "Needs changes"})):
            with self.subTest(operation=operation.__name__):
                before = (AuditLog.objects.count(), Notification.objects.count())
                with patch("apps.notifications.services.Notification.objects.get_or_create", side_effect=RuntimeError("notification unavailable")):
                    with self.assertRaises(RuntimeError):
                        operation(actor=self.owner, deliverable_id=deliverable.id, **self.scope(), **extra)
                self.task.refresh_from_db()
                deliverable.refresh_from_db()
                self.assertEqual((self.task.status, deliverable.status), ("REVIEW", "SUBMITTED"))
                self.assertFalse(Review.objects.exists())
                self.assertEqual((AuditLog.objects.count(), Notification.objects.count()), before)

    def test_comment_notification_failure_rolls_back_comment_and_audit(self):
        before = AuditLog.objects.count()
        with patch("apps.notifications.services.Notification.objects.get_or_create", side_effect=RuntimeError("notification unavailable")):
            with self.assertRaises(RuntimeError):
                create_comment(actor=self.editor, content="Rollback comment", **self.scope())
        self.assertFalse(TaskComment.objects.exists())
        self.assertEqual(AuditLog.objects.count(), before)
        self.assertFalse(Notification.objects.exists())

    def test_outer_business_rollback_leaves_no_notification(self):
        before = AuditLog.objects.count()
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.assign()
                raise RuntimeError("outer rollback")
        self.assertFalse(Notification.objects.exists())
        self.assertFalse(TaskAssignment.objects.exists())
        self.assertEqual(AuditLog.objects.count(), before)

    def test_mutable_event_object_does_not_override_persisted_audit_proof(self):
        notification = self.assigned_notification()
        other_task = Task.objects.create(workspace=self.workspace, created_by=self.owner, title="Different task")
        event = notification.event
        event.metadata["task_id"] = str(other_task.id)
        with self.assertRaises(ValidationError):
            emit_task_notifications(event=event, actor=self.owner, task=other_task, event_type="TASK_ASSIGNED")
        self.assertEqual(Notification.objects.count(), 1)

    def test_submission_requires_correct_persisted_deliverable_entity(self):
        deliverable = self.submitted()
        event = AuditLog.objects.get(action="task.deliverable.submitted")
        for updates in ({"entity_name": "Task"}, {"entity_id": uuid4()}):
            with self.subTest(updates=updates):
                original = {key: getattr(event, key) for key in updates}
                AuditLog.objects.filter(pk=event.pk).update(**updates)
                with self.assertRaises(ValidationError):
                    emit_task_notifications(event=event, actor=self.editor, task=self.task, event_type="REVIEW_SUBMITTED", deliverable=deliverable)
                AuditLog.objects.filter(pk=event.pk).update(**original)

    def test_review_event_cannot_reference_another_review_or_actor(self):
        deliverable = self.submitted()
        approve_deliverable(actor=self.owner, deliverable_id=deliverable.id, **self.scope())
        event = AuditLog.objects.get(action="task.deliverable.approved")
        AuditLog.objects.filter(pk=event.pk).update(entity_id=uuid4())
        with self.assertRaises(ValidationError):
            emit_task_notifications(event=event, actor=self.owner, task=self.task, event_type="REVIEW_APPROVED", deliverable=deliverable)

    def test_review_outcome_uses_persisted_uploader_not_mutable_instance(self):
        deliverable = self.submitted()
        approve_deliverable(actor=self.owner, deliverable_id=deliverable.id, **self.scope())
        event = AuditLog.objects.get(action="task.deliverable.approved")
        deliverable.uploaded_by_id = self.second.id
        emit_task_notifications(event=event, actor=self.owner, task=self.task,
                                event_type="REVIEW_APPROVED", deliverable=deliverable)
        self.assertEqual(set(Notification.objects.filter(event_type="REVIEW_APPROVED").values_list("user_id", flat=True)), {self.editor.id})

    def test_context_and_event_uniqueness_database_guards(self):
        notification = self.assigned_notification()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Notification.objects.create(user=self.editor, title="Partial", message="", profile=self.profile)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Notification.objects.create(user=self.editor, title="Duplicate", message="", event=notification.event,
                event_type="TASK_ASSIGNED", profile=self.profile, workspace=self.workspace, task=self.task)
        notification.workspace = self.sibling
        with self.assertRaises(ValidationError):
            notification.full_clean()

    def test_feed_and_count_hide_unmapped_legacy_and_mismatched_tenant_target(self):
        good = self.assigned_notification()
        Notification.objects.create(user=self.editor, title="Legacy private title", message="Legacy private body", is_read=False)
        # Even access to both tenants cannot make a mismatched stored context valid.
        ProfileMembership.objects.create(profile=self.other_profile, user=self.editor, role="MEMBER")
        WorkspaceMember.objects.create(workspace=self.other_workspace, user=self.editor, role="VIEWER")
        bad_event = AuditLog.objects.create(user=self.owner, action="task.assigned")
        Notification.objects.create(user=self.editor, title="Mismatched", message="Never show", event=bad_event,
            event_type="TASK_ASSIGNED", profile=self.other_profile, workspace=self.other_workspace, task=self.task)
        response = self.client.get(self.feed_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual([str(row["id"]) for row in response.data["results"]], [str(good.id)])
        self.assertEqual(self.client.get(self.count_url()).data, {"unread_count": 1})

    def test_own_feed_pagination_filter_safe_text_and_target(self):
        notification = self.assigned_notification()
        Notification.objects.filter(pk=notification.pk).update(title="Do not expose stored title", message="Do not expose stored body")
        response = self.client.get(self.feed_url(), {"page_size": 1, "is_read": "false"})
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        row = response.data["results"][0]
        self.assertEqual((row["title"], row["message"]), EVENT_CONTENT["TASK_ASSIGNED"])
        self.assertEqual(row["target_url"], reverse("tasks:task-detail", kwargs=self.scope()))
        self.assertFalse({"user", "user_id", "event", "event_id", "email"} & set(row))
        self.assertEqual(self.client.get(self.feed_url(), {"is_read": "invalid"}).status_code, 400)

    def test_only_recipient_can_read_notification_and_mark_read_is_idempotent(self):
        notification = self.assigned_notification()
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(self.read_url(notification), {}, format="json").status_code, 404)
        self.client.force_login(self.editor)
        first = self.client.post(self.read_url(notification), {}, format="json")
        second = self.client.post(self.read_url(notification), {}, format="json")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data, second.data)
        self.assertTrue(second.data["is_read"])
        self.assertEqual(self.client.get(self.count_url()).data, {"unread_count": 0})
        self.assertEqual(self.client.get(self.feed_url(), {"is_read": "true"}).data["count"], 1)

    def test_revoked_membership_hides_lazy_feed_count_and_mark_read(self):
        notification = self.assigned_notification()
        lazy = notifications_visible_to(self.editor)
        self.memberships["editor"].is_active = False
        self.memberships["editor"].save(update_fields=("is_active",))
        self.assertFalse(lazy.exists())
        self.assertEqual(self.client.get(self.feed_url()).data["count"], 0)
        self.assertEqual(self.client.get(self.count_url()).data, {"unread_count": 0})
        self.assertEqual(self.client.post(self.read_url(notification), {}, format="json").status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_workspace_revocation_and_legacy_owner_role_fail_closed(self):
        self.assigned_notification()
        membership = WorkspaceMember.objects.get(workspace=self.workspace, user=self.editor)
        for updates in ({"is_active": False}, {"is_active": True, "role": "OWNER"}):
            with self.subTest(updates=updates):
                WorkspaceMember.objects.filter(pk=membership.pk).update(**updates)
                self.assertFalse(notifications_visible_to(self.editor).exists())

    def test_inactive_user_and_staff_without_membership_have_no_feed_access(self):
        notification = self.assigned_notification()
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.feed_url()).data["count"], 0)
        self.assertEqual(self.client.post(self.read_url(notification), {}, format="json").status_code, 404)
        get_user_model().objects.filter(pk=self.editor.pk).update(is_active=False)
        self.assertFalse(notifications_visible_to(self.editor).exists())

    def test_archive_preserves_personal_read_but_cannot_emit_new_notifications(self):
        notification = self.assigned_notification()
        Profile.objects.filter(pk=self.profile.pk).update(status="ARCHIVED")
        Workspace.objects.filter(pk=self.workspace.pk).update(status="ARCHIVED")
        self.assertEqual(self.client.get(self.feed_url()).data["count"], 1)
        self.assertEqual(self.client.post(self.read_url(notification), {}, format="json").status_code, 200)
        self.assertEqual(emit_task_notifications(event=notification.event, actor=self.owner, task=self.task, event_type="TASK_ASSIGNED"), [])

    def test_read_requires_csrf_and_strict_empty_body(self):
        notification = self.assigned_notification()
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.editor)
        self.assertEqual(client.post(self.read_url(notification), {}, format="json").status_code, 403)
        token = client.get(reverse("accounts:csrf")).data["csrf_token"]
        self.assertEqual(client.post(self.read_url(notification), {"user_id": str(self.owner.id)}, format="json", HTTP_X_CSRFTOKEN=token).status_code, 400)
        self.assertEqual(client.post(self.read_url(notification), '{"\\ud800":true}', content_type="application/json", HTTP_X_CSRFTOKEN=token).status_code, 400)
        self.assertEqual(client.post(self.read_url(notification), {}, format="json", HTTP_X_CSRFTOKEN=token).status_code, 200)

    def test_unknown_invalid_ids_and_anonymous_are_denied(self):
        for notification_id in (uuid4(), "not-a-uuid"):
            self.assertEqual(self.client.post(self.read_url(notification_id), {}, format="json").status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.feed_url()).status_code, 403)
        self.assertEqual(self.client.get(self.count_url()).status_code, 403)

    def test_notification_list_query_count_is_bounded_as_feed_grows(self):
        notification = self.assigned_notification()
        with CaptureQueriesContext(connection) as small:
            first = self.client.get(self.feed_url())
        self.assertEqual(first.data["count"], 1)
        for number in range(12):
            event = AuditLog.objects.create(user=self.owner, action="task.assigned")
            Notification.objects.create(user=self.editor, event=event, task=self.task, profile=self.profile,
                workspace=self.workspace, event_type="TASK_ASSIGNED", title="Static", message="Static")
        with CaptureQueriesContext(connection) as large:
            response = self.client.get(self.feed_url())
        self.assertEqual(response.data["count"], 13)
        self.assertLessEqual(len(large), len(small) + 1)


class ConcurrentNotificationTests(NotificationFixture, TransactionTestCase):
    def setUp(self):
        self.make_fixture()

    def parallel(self, callback):
        barrier = Barrier(2)
        def run(number):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout='15000ms'")
                barrier.wait(timeout=10)
                return callback(number)
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(run, (0, 1)))

    def test_concurrent_same_event_retries_create_one_notification(self):
        notification = self.assigned_notification()
        Notification.objects.filter(pk=notification.pk).delete()
        def replay(_):
            emit_task_notifications(event=AuditLog.objects.get(pk=notification.event_id),
                actor=get_user_model().objects.get(pk=self.owner.id),
                task=Task.objects.get(pk=self.task.id), event_type="TASK_ASSIGNED")
            return True
        self.assertEqual(self.parallel(replay), [True, True])
        self.assertEqual(Notification.objects.filter(event_id=notification.event_id).count(), 1)

    def test_concurrent_mark_read_is_idempotent(self):
        notification = self.assigned_notification()
        def read(_):
            row = mark_notification_read(actor=get_user_model().objects.get(pk=self.editor.id), notification_id=notification.id)
            return row.is_read, row.updated_at
        results = self.parallel(read)
        self.assertEqual(results[0], results[1])
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
