"""Tenant-scoped discussion, moderation and transaction regression tests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4
import json

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.db.models.deletion import ProtectedError
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.workspace.access import TenantAccessNotFound, resolve_profile_access_context, resolve_workspace_access_context
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .comment_services import comments_visible_to, create_comment, delete_comment, update_comment
from .models import Task, TaskAssignment, TaskComment
from .services import TaskWorkflowConflict


User = get_user_model()


def discussion_fixture(namespace):
    result = {}
    for name in ("owner", "admin", "manager", "editor", "peer", "viewer", "staff", "foreign_owner"):
        result[name] = User.objects.create_user(
            username=f"{namespace}-{name}", email=f"{namespace}-{name}@example.test",
            password=None, is_staff=name == "staff",
        )
    profile = result["profile"] = create_profile_with_owner(name="Discussion Profile", owner=result["owner"])
    workspace = result["workspace"] = Workspace.objects.create(
        profile=profile, owner=result["owner"], name="Discussion October", period=date(2026, 10, 1),
    )
    result["sibling"] = Workspace.objects.create(
        profile=profile, owner=result["owner"], name="Discussion November", period=date(2026, 11, 1),
    )
    for name, role in (("admin", "ADMIN"), ("manager", "MEMBER"), ("editor", "MEMBER"), ("peer", "MEMBER"), ("viewer", "MEMBER")):
        result[f"{name}_membership"] = ProfileMembership.objects.create(profile=profile, user=result[name], role=role)
    for name, role in (("manager", "ADMIN"), ("editor", "MEMBER"), ("peer", "MEMBER"), ("viewer", "VIEWER")):
        WorkspaceMember.objects.create(workspace=workspace, user=result[name], role=role)
    result["foreign_profile"] = create_profile_with_owner(name="Foreign Discussion", owner=result["foreign_owner"])
    result["foreign_workspace"] = Workspace.objects.create(
        profile=result["foreign_profile"], owner=result["foreign_owner"], name="Foreign October", period=date(2026, 10, 1),
    )
    task = result["task"] = Task.objects.create(workspace=workspace, created_by=result["owner"], title="Discussion root")
    result["child"] = Task.objects.create(workspace=workspace, created_by=result["owner"], title="Discussion child", parent=task)
    result["sibling_task"] = Task.objects.create(workspace=result["sibling"], created_by=result["owner"], title="Other month")
    result["foreign_task"] = Task.objects.create(workspace=result["foreign_workspace"], created_by=result["foreign_owner"], title="Other tenant")
    TaskAssignment.objects.create(task=task, user=result["editor"], is_active=True)
    result["comment"] = TaskComment.objects.create(task=task, user=result["editor"], content="Original feedback")
    result["sibling_comment"] = TaskComment.objects.create(task=result["sibling_task"], user=result["owner"], content="Other month feedback")
    result["foreign_comment"] = TaskComment.objects.create(task=result["foreign_task"], user=result["foreign_owner"], content="Private other tenant")
    return result


class TaskCommentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        for name, value in discussion_fixture("comment-tests").items():
            setattr(cls, name, value)

    def setUp(self):
        self.client.force_login(self.editor)

    def url(self, comment=None, task=None, **overrides):
        kwargs = {"profile_id": self.profile.id, "workspace_id": self.workspace.id,
                  "task_id": (task or self.task).id, **overrides}
        name = "task-comment-list"
        if comment is not None:
            name = "task-comment-detail"
            kwargs["comment_id"] = comment.id if isinstance(comment, TaskComment) else comment
        return reverse(f"tasks:{name}", kwargs=kwargs)

    def scope(self, **extra):
        return {"actor": self.editor, "profile_id": self.profile.id,
                "workspace_id": self.workspace.id, "task_id": self.task.id, **extra}

    def post(self, payload=None, **url_kwargs):
        return self.client.post(self.url(**url_kwargs), payload if payload is not None else {"content": "New feedback"}, format="json")

    def test_create_normalizes_text_binds_author_and_leaves_task_state_unchanged(self):
        before = (self.task.status, self.task.priority, self.task.deadline, self.task.parent_id)
        response = self.post({"content": "  Cần chỉnh sửa phần mở đầu.  "})
        self.assertEqual(response.status_code, 201)
        created = TaskComment.objects.get(pk=response.data["id"])
        self.assertEqual(created.content, "Cần chỉnh sửa phần mở đầu.")
        self.assertEqual((created.user_id, created.task_id), (self.editor.id, self.task.id))
        self.assertEqual(response.data["author_profile_membership_id"], str(self.editor_membership.id))
        self.task.refresh_from_db()
        self.assertEqual((self.task.status, self.task.priority, self.task.deadline, self.task.parent_id), before)

    def test_subtask_uses_same_comment_api_without_leaking_parent_comments(self):
        response = self.post(task=self.child)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(response.data["task_id"]), str(self.child.id))
        listing = self.client.get(self.url(task=self.child))
        self.assertEqual(listing.data["count"], 1)
        self.assertNotIn(str(self.comment.id), [str(row["id"]) for row in listing.data["results"]])

    def test_read_contract_exposes_current_membership_not_user_pii(self):
        response = self.client.get(self.url(self.comment))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"id", "task_id", "author_profile_membership_id", "content", "is_deleted", "edited_at", "deleted_at", "created_at", "updated_at"})
        for value in (self.editor.email, self.editor.username, str(self.editor.id)):
            self.assertNotIn(value, response.content.decode())
        self.assertIn("no-store", response["Cache-Control"])

    def test_list_is_paginated_and_stably_ordered(self):
        for number in range(5):
            TaskComment.objects.create(task=self.task, user=self.editor, content=f"Feedback {number}")
        response = self.client.get(self.url(), {"page_size": 2})
        expected = list(TaskComment.objects.filter(task=self.task).order_by("created_at", "id").values_list("id", flat=True)[:2])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 6)
        self.assertEqual([str(row["id"]) for row in response.data["results"]], [str(pk) for pk in expected])
        self.assertIsNotNone(response.data["next"])

    def test_list_author_projection_has_bounded_queries(self):
        with CaptureQueriesContext(connection) as small:
            first = self.client.get(self.url())
        self.assertEqual(first.status_code, 200)
        for number in range(12):
            TaskComment.objects.create(task=self.task, user=self.editor, content=f"More {number}")
        with CaptureQueriesContext(connection) as large:
            response = self.client.get(self.url())
        self.assertEqual(response.data["count"], 13)
        self.assertLessEqual(len(large), len(small) + 1)
        self.assertTrue(all(row["author_profile_membership_id"] for row in response.data["results"]))

    def test_existing_managers_and_editors_can_create(self):
        for actor in (self.owner, self.admin, self.manager, self.editor, self.peer):
            with self.subTest(actor=actor.pk):
                self.client.force_login(actor)
                self.assertEqual(self.post().status_code, 201)

    def test_viewer_reads_but_cannot_mutate_even_own_comment(self):
        own = TaskComment.objects.create(task=self.task, user=self.viewer, content="Historical viewer comment")
        self.client.force_login(self.viewer)
        self.assertEqual(self.client.get(self.url(own)).status_code, 200)
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(self.client.patch(self.url(own), {"content": "Changed"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.url(own)).status_code, 403)

    def test_author_edits_own_comment_and_audits_without_copying_body(self):
        response = self.client.patch(self.url(self.comment), {"content": "Edited feedback"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "Edited feedback")
        self.assertIsNotNone(self.comment.edited_at)
        audit = AuditLog.objects.get(action="task.comment.updated", entity_id=self.comment.id)
        self.assertEqual(audit.metadata["task_id"], str(self.task.id))
        self.assertNotIn("Edited feedback", json.dumps(audit.metadata))

    def test_manager_can_moderate_but_cannot_rewrite_another_authors_text(self):
        self.client.force_login(self.manager)
        self.assertEqual(self.client.patch(self.url(self.comment), {"content": "Manager rewrite"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.url(self.comment)).status_code, 204)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "Original feedback")
        self.assertIsNotNone(self.comment.deleted_at)

    def test_another_editor_cannot_edit_or_delete_comment(self):
        self.client.force_login(self.peer)
        self.assertEqual(self.client.patch(self.url(self.comment), {"content": "Peer rewrite"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.url(self.comment)).status_code, 403)

    def test_author_soft_delete_retains_internal_body_and_returns_tombstones(self):
        self.assertEqual(self.client.delete(self.url(self.comment)).status_code, 204)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "Original feedback")
        self.assertIsNotNone(self.comment.deleted_at)
        detail = self.client.get(self.url(self.comment))
        self.assertIsNone(detail.data["content"])
        self.assertTrue(detail.data["is_deleted"])
        listing = self.client.get(self.url())
        self.assertIsNone(listing.data["results"][0]["content"])
        self.assertNotIn("Original feedback", detail.content.decode())

    def test_repeated_delete_is_idempotent_and_does_not_repeat_audit(self):
        self.assertEqual(self.client.delete(self.url(self.comment)).status_code, 204)
        self.comment.refresh_from_db()
        deleted_at = self.comment.deleted_at
        self.assertEqual(self.client.delete(self.url(self.comment)).status_code, 204)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.deleted_at, deleted_at)
        self.assertEqual(AuditLog.objects.filter(action="task.comment.deleted", entity_id=self.comment.pk).count(), 1)

    def test_deleted_comment_cannot_be_edited_or_resurrected(self):
        self.client.delete(self.url(self.comment))
        response = self.client.patch(self.url(self.comment), {"content": "Resurrection"}, format="json")
        self.assertEqual(response.status_code, 409)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "Original feedback")
        self.assertIsNotNone(self.comment.deleted_at)

    def test_invalid_input_and_unicode_are_400_without_writes(self):
        before = TaskComment.objects.count()
        for value in (None, 4, True, [], {}, "", "   ", "x" * 4001, "bad\x00text", "bad\ud800text", "bad\udffftext"):
            with self.subTest(value_type=type(value).__name__):
                response = self.client.generic("POST", self.url(),
                    data=json.dumps({"content": value}, ensure_ascii=True), content_type="application/json")
                self.assertEqual(response.status_code, 400)
                response = self.client.generic("PATCH", self.url(self.comment),
                    data=json.dumps({"content": value}, ensure_ascii=True), content_type="application/json")
                self.assertEqual(response.status_code, 400)
        self.assertEqual(TaskComment.objects.count(), before)

    def test_unicode_character_limit_is_validated_in_characters(self):
        self.assertEqual(self.post({"content": "đ" * 4000}).status_code, 201)
        self.assertEqual(self.post({"content": "đ" * 4001}).status_code, 400)

    def test_malformed_unicode_field_names_return_400_without_rendering_errors(self):
        before = TaskComment.objects.count()
        for field in ("\ud800", "\udfff", "nul\x00key"):
            payload = json.dumps({"content": "Valid text", field: "Unexpected"}, ensure_ascii=True)
            for method, url in (("POST", self.url()), ("PATCH", self.url(self.comment))):
                response = self.client.generic(method, url, data=payload, content_type="application/json")
                self.assertEqual(response.status_code, 400)
        self.assertEqual(TaskComment.objects.count(), before)

    def test_strict_inputs_forbid_author_task_and_lifecycle_mass_assignment(self):
        for extra in ({"user": str(self.owner.id)}, {"author_id": str(self.owner.id)},
                      {"task_id": str(self.sibling_task.id)}, {"deleted_at": None}, {"edited_at": None}):
            with self.subTest(field=next(iter(extra))):
                self.assertEqual(self.post({"content": "Attempt", **extra}).status_code, 400)
                self.assertEqual(self.client.patch(self.url(self.comment), {"content": "Attempt", **extra}, format="json").status_code, 400)
        self.assertEqual(self.client.patch(self.url(self.comment), {}, format="json").status_code, 400)
        self.assertEqual(self.client.delete(self.url(self.comment), {"content": "unexpected"}, format="json").status_code, 400)

    def test_nested_task_and_comment_ids_fail_closed_across_workspaces_and_profiles(self):
        self.client.force_login(self.owner)
        for comment_id in (self.sibling_comment.id, self.foreign_comment.id, uuid4(), "bad-uuid"):
            for method, payload in (("get", None), ("patch", {"content": "Invalid parent"}), ("delete", {})):
                response = getattr(self.client, method)(self.url(comment_id), payload, format="json")
                self.assertEqual(response.status_code, 404)
        for task in (self.sibling_task, self.foreign_task):
            self.assertEqual(self.client.get(self.url(task=task)).status_code, 404)
            self.assertEqual(self.post(task=task).status_code, 404)

    def test_foreign_actor_and_staff_without_membership_have_no_tenant_access(self):
        for actor in (self.foreign_owner, self.staff):
            self.client.force_login(actor)
            self.assertEqual(self.client.get(self.url()).status_code, 404)
            self.assertEqual(self.client.get(self.url(self.comment)).status_code, 404)
            self.assertEqual(self.post().status_code, 404)

    def test_staff_with_real_editor_membership_uses_normal_capability(self):
        ProfileMembership.objects.create(profile=self.profile, user=self.staff, role="MEMBER")
        WorkspaceMember.objects.create(workspace=self.workspace, user=self.staff, role="MEMBER")
        self.client.force_login(self.staff)
        self.assertEqual(self.post().status_code, 201)

    def test_archived_workspace_and_profile_allow_history_but_no_mutation(self):
        for model, pk in ((Workspace, self.workspace.pk), (Profile, self.profile.pk)):
            model.objects.filter(pk=pk).update(status="ARCHIVED")
            self.assertEqual(self.client.get(self.url(self.comment)).status_code, 200)
            self.assertEqual(self.post().status_code, 403)
            self.assertEqual(self.client.patch(self.url(self.comment), {"content": "Changed"}, format="json").status_code, 403)
            self.assertEqual(self.client.delete(self.url(self.comment)).status_code, 403)
            model.objects.filter(pk=pk).update(status="ACTIVE")

    def test_revoked_profile_membership_removes_author_read_and_write(self):
        ProfileMembership.objects.filter(pk=self.editor_membership.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.url(self.comment)).status_code, 404)
        self.assertEqual(self.post().status_code, 404)
        self.assertEqual(self.client.patch(self.url(self.comment), {"content": "Changed"}, format="json").status_code, 404)
        self.assertEqual(self.client.delete(self.url(self.comment)).status_code, 404)

    def test_revoked_workspace_membership_removes_author_access(self):
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(is_active=False)
        self.assertEqual(self.client.get(self.url(self.comment)).status_code, 404)
        self.assertEqual(self.client.delete(self.url(self.comment)).status_code, 404)

    def test_downgraded_author_is_read_only_and_historical_attribution_can_be_null(self):
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(role="VIEWER")
        self.assertEqual(self.client.get(self.url(self.comment)).status_code, 200)
        self.assertEqual(self.client.patch(self.url(self.comment), {"content": "Changed"}, format="json").status_code, 403)
        ProfileMembership.objects.filter(pk=self.editor_membership.pk).update(is_active=False)
        self.client.force_login(self.owner)
        response = self.client.get(self.url(self.comment))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["author_profile_membership_id"])

    def test_lazy_comment_queryset_rechecks_revoked_membership(self):
        profile = resolve_profile_access_context(self.editor, self.profile.id)
        context = resolve_workspace_access_context(profile, self.workspace.id)
        queryset = comments_visible_to(context, self.task.id)
        ProfileMembership.objects.filter(pk=self.editor_membership.pk).update(is_active=False)
        self.assertFalse(queryset.exists())

    def test_csrf_is_required_for_session_authenticated_mutations(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.editor)
        self.assertEqual(client.post(self.url(), {"content": "Missing CSRF"}, format="json").status_code, 403)
        self.assertEqual(client.patch(self.url(self.comment), {"content": "Missing CSRF"}, format="json").status_code, 403)
        self.assertEqual(client.delete(self.url(self.comment)).status_code, 403)
        token = client.get(reverse("accounts:csrf")).data["csrf_token"]
        self.assertEqual(client.post(self.url(), {"content": "Valid CSRF"}, format="json", HTTP_X_CSRFTOKEN=token).status_code, 201)
        self.assertEqual(client.patch(self.url(self.comment), {"content": "Valid edit"}, format="json", HTTP_X_CSRFTOKEN=token).status_code, 200)
        self.assertEqual(client.delete(self.url(self.comment), HTTP_X_CSRFTOKEN=token).status_code, 204)

    def test_anonymous_and_inactive_user_cannot_access_discussion(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        self.assertEqual(self.post().status_code, 403)
        self.client.force_login(self.editor)
        User.objects.filter(pk=self.editor.id).update(is_active=False)
        self.assertIn(self.client.get(self.url()).status_code, (403, 404))
        self.assertIn(self.post().status_code, (403, 404))

    def test_unsupported_methods_and_bad_nested_uuid_are_rejected(self):
        self.assertEqual(self.client.put(self.url(self.comment), {"content": "No PUT"}, format="json").status_code, 405)
        self.assertEqual(self.client.delete(self.url()).status_code, 405)
        self.assertEqual(self.client.get(self.url("malformed-comment-id")).status_code, 404)

    def test_direct_service_rejects_invalid_unicode_and_nontext(self):
        before = TaskComment.objects.count()
        for value in (None, 1, " ", "x\x00y", "x\ud800y", "x" * 4001):
            with self.assertRaises(ValidationError):
                create_comment(**self.scope(), content=value)
            with self.assertRaises(ValidationError):
                update_comment(**self.scope(), comment_id=self.comment.id, content=value)
        self.assertEqual(TaskComment.objects.count(), before)

    def test_direct_service_invalid_comment_scope_is_not_found(self):
        for comment_id in (self.sibling_comment.id, self.foreign_comment.id, uuid4(), "invalid"):
            with self.assertRaises(TenantAccessNotFound):
                update_comment(**self.scope(), comment_id=comment_id, content="Attempt")

    def test_audit_failure_rolls_back_create_edit_and_delete(self):
        before = TaskComment.objects.count()
        with patch("apps.tasks.comment_services.AuditLog.objects.create", side_effect=RuntimeError("Audit unavailable")):
            with self.assertRaises(RuntimeError):
                create_comment(**self.scope(), content="Rolled back")
            with self.assertRaises(RuntimeError):
                update_comment(**self.scope(), comment_id=self.comment.id, content="Rolled back edit")
            with self.assertRaises(RuntimeError):
                delete_comment(**self.scope(), comment_id=self.comment.id)
        self.comment.refresh_from_db()
        self.assertEqual(TaskComment.objects.count(), before)
        self.assertEqual(self.comment.content, "Original feedback")
        self.assertIsNone(self.comment.edited_at)
        self.assertIsNone(self.comment.deleted_at)

    def test_notification_failure_rolls_back_comment_audit_and_inserted_notification(self):
        from apps.notifications.services import emit_task_notifications
        before = (TaskComment.objects.count(), AuditLog.objects.count(), Notification.objects.count())
        def emit_then_fail(**kwargs):
            emit_task_notifications(**kwargs)
            raise RuntimeError("Notification transaction unavailable")
        with patch("apps.notifications.services.emit_task_notifications", side_effect=emit_then_fail):
            with self.assertRaises(RuntimeError):
                create_comment(**self.scope(), content="Must roll back everything")
        self.assertEqual((TaskComment.objects.count(), AuditLog.objects.count(), Notification.objects.count()), before)

    def test_create_audit_has_identifiers_but_no_comment_body_or_identity(self):
        created = create_comment(**self.scope(), content="Only the discussion API exposes this content")
        audit = AuditLog.objects.get(action="task.comment.created", entity_id=created.id)
        self.assertEqual(audit.metadata["comment_id"], str(created.id))
        encoded = json.dumps(audit.metadata)
        self.assertNotIn(created.content, encoded)
        self.assertNotIn(self.editor.email, encoded)

    def test_legacy_oversized_comment_can_be_moderated_without_trimming(self):
        TaskComment.objects.filter(pk=self.comment.pk).update(content="L" * 5000)
        self.client.force_login(self.manager)
        self.assertEqual(self.client.delete(self.url(self.comment)).status_code, 204)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "L" * 5000)
        self.assertIsNotNone(self.comment.deleted_at)

    def test_existing_oversized_comment_can_be_replaced_by_valid_author_edit(self):
        TaskComment.objects.filter(pk=self.comment.pk).update(content="L" * 5000)
        response = self.client.patch(self.url(self.comment), {"content": "New valid feedback"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.content, "New valid feedback")

    def test_comment_history_protects_task_from_hard_delete(self):
        leaf = Task.objects.create(workspace=self.workspace, created_by=self.owner, title="Protected leaf")
        comment = TaskComment.objects.create(task=leaf, user=self.editor, content="Retained history")
        with self.assertRaises(ProtectedError):
            leaf.delete()
        self.assertTrue(TaskComment.objects.filter(pk=comment.pk).exists())


class ConcurrentTaskCommentTests(TransactionTestCase):
    def setUp(self):
        for name, value in discussion_fixture("comment-race").items():
            setattr(self, name, value)

    def race(self, operations):
        barrier = Barrier(2)
        def invoke(operation):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout='10s'")
                actor = User.objects.get(pk=self.editor.pk)
                barrier.wait(timeout=10)
                kwargs = {"actor": actor, "profile_id": self.profile.id, "workspace_id": self.workspace.id,
                          "task_id": self.task.id, "comment_id": self.comment.id}
                if operation == "edit":
                    update_comment(**kwargs, content="Concurrent edit")
                else:
                    delete_comment(**kwargs)
                return None
            except Exception as error:
                return error
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(invoke, operations))

    def test_concurrent_edit_and_delete_cannot_resurrect_deleted_body(self):
        errors = self.race(("edit", "delete"))
        self.assertTrue(all(error is None or isinstance(error, TaskWorkflowConflict) for error in errors))
        self.comment.refresh_from_db()
        self.assertIsNotNone(self.comment.deleted_at)
        self.assertIn(self.comment.content, ("Original feedback", "Concurrent edit"))
        self.assertEqual(AuditLog.objects.filter(entity_id=self.comment.pk, action="task.comment.deleted").count(), 1)

    def test_concurrent_repeated_deletion_creates_one_audit_event(self):
        self.assertEqual(self.race(("delete", "delete")), [None, None])
        self.assertEqual(AuditLog.objects.filter(entity_id=self.comment.pk, action="task.comment.deleted").count(), 1)
