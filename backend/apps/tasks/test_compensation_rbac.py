"""Field-level Task compensation projection; isolated PostgreSQL only."""

import json
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.workspace.access import (
    ProfileAccessContext, WorkspaceAccessContext,
    resolve_profile_access_context, resolve_workspace_access_context,
)
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .access import can_view_task_compensation
from .models import Task, TaskAssignment
from .serializers import TaskReadSerializer
from .views import _task_read_queryset


User = get_user_model()
AMOUNT = "9007199254740993"


class TaskCompensationRbacTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        for label in ("owner", "admin", "manager", "assignee", "member", "viewer", "outsider", "foreign", "staff"):
            setattr(cls, label, User.objects.create_user(
                username=f"compensation-{label}", email=f"compensation-{label}@example.test", password=None,
            ))
        cls.profile = create_profile_with_owner(name="Compensation tenant", owner=cls.owner)
        cls.workspace = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner, name="Compensation month", period=date(2026, 11, 1),
        )
        cls.sibling = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner, name="Other month", period=date(2026, 12, 1),
        )
        cls.memberships = {"owner": ProfileMembership.objects.get(profile=cls.profile, user=cls.owner)}
        for label, profile_role, workspace_role in (
            ("admin", "ADMIN", None), ("manager", "MEMBER", "ADMIN"),
            ("assignee", "MEMBER", "MEMBER"), ("member", "MEMBER", "MEMBER"),
            ("viewer", "MEMBER", "VIEWER"), ("staff", "MEMBER", "VIEWER"),
        ):
            actor = getattr(cls, label)
            cls.memberships[label] = ProfileMembership.objects.create(profile=cls.profile, user=actor, role=profile_role)
            if workspace_role:
                WorkspaceMember.objects.create(workspace=cls.workspace, user=actor, role=workspace_role)
        cls.foreign_profile = create_profile_with_owner(name="Other tenant", owner=cls.foreign)
        cls.foreign_workspace = Workspace.objects.create(
            profile=cls.foreign_profile, owner=cls.foreign, name="Other tenant month", period=date(2026, 11, 1),
        )
        cls.task = Task.objects.create(
            workspace=cls.workspace, created_by=cls.owner, title="Confidential expected pay", status=Task.Status.ASSIGNED,
            estimated_compensation_vnd=AMOUNT, script_url="https://example.test/script",
        )
        cls.child = Task.objects.create(
            workspace=cls.workspace, created_by=cls.owner, parent=cls.task, title="Independent child pay",
            estimated_compensation_vnd="123456",
        )
        cls.sibling_task = Task.objects.create(workspace=cls.sibling, created_by=cls.owner, title="Sibling pay", estimated_compensation_vnd=AMOUNT)
        cls.foreign_task = Task.objects.create(workspace=cls.foreign_workspace, created_by=cls.foreign, title="Foreign pay", estimated_compensation_vnd=AMOUNT)
        cls.assignment = TaskAssignment.objects.create(task=cls.task, user=cls.assignee)

    def url(self, task=None, *, route=None, workspace=None, profile=None):
        kwargs = {"profile_id": (profile or self.profile).pk, "workspace_id": (workspace or self.workspace).pk}
        if task is not None:
            kwargs["task_id"] = getattr(task, "pk", task)
        return reverse(f"tasks:{route or ('task-detail' if task is not None else 'task-list')}", kwargs=kwargs)

    def login(self, actor):
        self.client.force_login(actor)

    def context(self, actor):
        return resolve_workspace_access_context(resolve_profile_access_context(actor, self.profile.pk), self.workspace.pk)

    def serialized(self, actor, task=None, *, context=None):
        return TaskReadSerializer(task or self.task, context={
            "request": SimpleNamespace(user=actor), "workspace_access_context": context or self.context(actor),
        }).data

    def assert_redacted(self, response, status=200):
        self.assertEqual(response.status_code, status)
        self.assertIsNone(response.data["estimated_compensation_vnd"])
        self.assertNotIn(AMOUNT, json.dumps(response.data, default=str))

    def test_profile_owner_and_admin_need_no_explicit_workspace_membership(self):
        for actor in (self.owner, self.admin):
            with self.subTest(actor=actor.username):
                self.login(actor)
                response = self.client.get(self.url(self.task))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["estimated_compensation_vnd"], AMOUNT)
                self.assertTrue(can_view_task_compensation(actor, self.task))

    def test_delegated_workspace_admin_reads_compensation_in_managed_workspace_only(self):
        self.login(self.manager)
        self.assertEqual(self.client.get(self.url(self.task)).data["estimated_compensation_vnd"], AMOUNT)
        self.assertEqual(self.client.get(self.url(self.sibling_task, workspace=self.sibling)).status_code, 404)
        self.assertFalse(can_view_task_compensation(self.manager, self.sibling_task))

    def test_current_assignee_reads_exact_whole_task_amount_without_edit_grant(self):
        self.login(self.assignee)
        response = self.client.get(self.url(self.task))
        self.assertEqual(response.data["estimated_compensation_vnd"], AMOUNT)
        self.assertTrue(can_view_task_compensation(self.assignee, self.task))
        denied = self.client.patch(self.url(self.task), {"estimated_compensation_vnd": "1"}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.estimated_compensation_vnd, Decimal(AMOUNT))

    def test_unassigned_member_and_viewer_keep_task_and_urls_but_get_null_pay(self):
        for actor in (self.member, self.viewer):
            with self.subTest(actor=actor.username):
                self.login(actor)
                response = self.client.get(self.url(self.task))
                self.assert_redacted(response)
                self.assertEqual(response.data["script_url"], "https://example.test/script")
                self.assertEqual(response.data["title"], self.task.title)
                self.assertFalse(can_view_task_compensation(actor, self.task))

    def test_list_filter_and_detail_apply_the_same_field_policy(self):
        for actor, visible in ((self.owner, True), (self.admin, True), (self.manager, True), (self.assignee, True), (self.member, False), (self.viewer, False)):
            with self.subTest(actor=actor.username):
                self.login(actor)
                detail = self.client.get(self.url(self.task))
                listed = self.client.get(self.url(), {"status": "ASSIGNED", "ordering": "priority", "include_compensation": "true"})
                self.assertEqual(listed.status_code, 200)
                row = next(row for row in listed.data["results"] if str(row["id"]) == str(self.task.pk))
                self.assertEqual(row["estimated_compensation_vnd"], AMOUNT if visible else None)
                self.assertEqual(row["estimated_compensation_vnd"], detail.data["estimated_compensation_vnd"])

    def test_assignment_is_specific_to_each_task_not_parent_or_sibling(self):
        self.login(self.assignee)
        self.assert_redacted(self.client.get(self.url(self.child)))
        children = self.client.get(self.url(self.task, route="task-subtask-list"))
        self.assertEqual(children.status_code, 200)
        self.assertIsNone(children.data["results"][0]["estimated_compensation_vnd"])
        self.login(self.manager)
        self.assertEqual(self.client.get(self.url(self.task, route="task-subtask-list")).data["results"][0]["estimated_compensation_vnd"], "123456")

    def test_historical_assignment_does_not_grant_visibility_or_multiply_pay(self):
        TaskAssignment.objects.filter(pk=self.assignment.pk).update(is_active=False)
        TaskAssignment.objects.create(task=self.task, user=self.member)
        for actor, visible in ((self.assignee, False), (self.member, True), (self.owner, True)):
            self.login(actor)
            self.assertEqual(self.client.get(self.url(self.task)).data["estimated_compensation_vnd"], AMOUNT if visible else None)
        self.assertEqual(TaskAssignment.objects.filter(task=self.task).count(), 2)
        self.task.refresh_from_db()
        self.assertEqual(self.task.estimated_compensation_vnd, Decimal(AMOUNT))

    def test_existing_single_active_assignee_constraint_is_preserved(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TaskAssignment.objects.create(task=self.task, user=self.member)
        self.assertEqual(TaskAssignment.objects.filter(task=self.task, is_active=True).count(), 1)

    def test_viewer_downgrade_makes_retained_assignment_ineffective(self):
        context = self.context(self.assignee)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.assignee).update(role="VIEWER")
        self.assertFalse(can_view_task_compensation(self.assignee, self.task, context=context))
        self.login(self.assignee)
        self.assert_redacted(self.client.get(self.url(self.task)))
        self.assertTrue(TaskAssignment.objects.get(pk=self.assignment.pk).is_active)

    def test_revoked_workspace_membership_denies_even_active_assignment(self):
        context = self.context(self.assignee)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.assignee).update(is_active=False)
        self.assertFalse(can_view_task_compensation(self.assignee, self.task, context=context))
        self.login(self.assignee)
        response = self.client.get(self.url(self.task))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn(AMOUNT, json.dumps(response.data, default=str))

    def test_revoked_profile_membership_denies_even_retained_workspace_and_assignment(self):
        context = self.context(self.assignee)
        ProfileMembership.objects.filter(pk=self.memberships["assignee"].pk).update(is_active=False)
        self.assertFalse(can_view_task_compensation(self.assignee, self.task, context=context))
        self.login(self.assignee)
        self.assertEqual(self.client.get(self.url(self.task)).status_code, 404)

    def test_profile_admin_downgrade_cannot_use_a_stale_manager_context(self):
        context = self.context(self.admin)
        ProfileMembership.objects.filter(pk=self.memberships["admin"].pk).update(role="MEMBER")
        WorkspaceMember.objects.create(workspace=self.workspace, user=self.admin, role="MEMBER")
        self.assertIsNone(self.serialized(self.admin, context=context)["estimated_compensation_vnd"])
        self.login(self.admin)
        self.assert_redacted(self.client.get(self.url(self.task)))

    def test_workspace_manager_downgrade_revokes_field_visibility_before_response(self):
        context = self.context(self.manager)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.manager).update(role="MEMBER")
        self.assertIsNone(self.serialized(self.manager, context=context)["estimated_compensation_vnd"])
        self.login(self.manager)
        self.assert_redacted(self.client.get(self.url(self.task)))
        self.assertEqual(self.client.patch(self.url(self.task), {"title": "stale form", "estimated_compensation_vnd": None}, format="json").status_code, 403)

    def test_inactive_account_is_denied_even_when_python_user_object_is_stale(self):
        context = self.context(self.assignee)
        User.objects.filter(pk=self.assignee.pk).update(is_active=False)
        self.assertTrue(self.assignee.is_active)
        self.assertIsNone(self.serialized(self.assignee, context=context)["estimated_compensation_vnd"])

    def test_staff_and_superuser_flags_are_not_tenant_authority(self):
        User.objects.filter(pk=self.staff.pk).update(is_staff=True, is_superuser=True)
        self.staff.refresh_from_db()
        self.login(self.staff)
        self.assert_redacted(self.client.get(self.url(self.task)))

    def test_inspection_only_admin_does_not_auto_disclose_confidential_model_field(self):
        User.objects.filter(pk=self.staff.pk).update(is_staff=True, is_superuser=True)
        self.staff.refresh_from_db()
        self.login(self.staff)
        response = self.client.get(reverse("admin:tasks_task_change", args=(self.task.pk,)))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, AMOUNT)
        self.assertNotContains(response, "estimated_compensation_vnd")
        self.assertNotContains(response, "Estimated compensation vnd")
        self.assertContains(response, self.task.title)

    def test_other_profile_manager_and_known_ids_do_not_grant_access(self):
        for actor in (self.outsider, self.foreign):
            self.login(actor)
            for url in (self.url(), self.url(self.task), self.url(self.child), self.url(self.foreign_task)):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn(AMOUNT, json.dumps(response.data, default=str))
            self.assertFalse(can_view_task_compensation(actor, self.task))

    def test_multi_profile_membership_does_not_spread_assignment_or_management(self):
        ProfileMembership.objects.create(profile=self.foreign_profile, user=self.assignee, role="ADMIN")
        self.login(self.assignee)
        self.assertEqual(self.client.get(self.url(self.task)).data["estimated_compensation_vnd"], AMOUNT)
        TaskAssignment.objects.filter(pk=self.assignment.pk).update(is_active=False)
        self.assert_redacted(self.client.get(self.url(self.task)))

    def test_missing_mismatched_or_anonymous_serializer_context_is_fail_closed(self):
        for context in ({}, {"request": SimpleNamespace(user=self.owner)},
                        {"workspace_access_context": self.context(self.owner)},
                        {"request": SimpleNamespace(user=self.owner), "workspace_access_context": self.context(self.member)},
                        {"request": SimpleNamespace(user=AnonymousUser()), "workspace_access_context": self.context(self.owner)}):
            with self.subTest(context_fields=tuple(context)):
                self.assertIsNone(TaskReadSerializer(self.task, context=context).data["estimated_compensation_vnd"])

    def test_mixed_scope_serializer_rows_do_not_disclose_out_of_scope_pay(self):
        rows = TaskReadSerializer([self.task, self.sibling_task, self.foreign_task], many=True, context={
            "request": SimpleNamespace(user=self.owner), "workspace_access_context": self.context(self.owner),
        }).data
        self.assertEqual([row["estimated_compensation_vnd"] for row in rows], [AMOUNT, None, None])

    def test_forged_unverified_context_with_real_identifiers_cannot_grant_pay(self):
        context = WorkspaceAccessContext(profile_context=ProfileAccessContext(
            user_id=self.owner.pk, profile_id=self.profile.pk,
            membership_id=self.memberships["owner"].pk, profile_role="OWNER",
        ), workspace_id=self.workspace.pk, workspace_role=None)
        self.assertFalse(can_view_task_compensation(self.owner, self.task, context=context))
        self.assertIsNone(self.serialized(self.owner, context=context)["estimated_compensation_vnd"])

    def test_prefetched_assignment_cache_cannot_survive_live_revocation(self):
        context = self.context(self.assignee)
        loaded = list(_task_read_queryset(context).filter(pk=self.task.pk))[0]
        self.assertEqual(loaded._active_assignments[0].user_id, self.assignee.pk)
        TaskAssignment.objects.filter(pk=self.assignment.pk).update(is_active=False)
        self.assertIsNone(self.serialized(self.assignee, loaded, context=context)["estimated_compensation_vnd"])

    def test_readable_archived_context_keeps_pay_visibility_and_disallows_writes(self):
        Workspace.objects.filter(pk=self.workspace.pk).update(status=Workspace.Status.ARCHIVED)
        Profile.objects.filter(pk=self.profile.pk).update(status=Profile.Status.ARCHIVED)
        for actor in (self.owner, self.admin, self.manager, self.assignee):
            self.login(actor)
            self.assertEqual(self.client.get(self.url(self.task)).data["estimated_compensation_vnd"], AMOUNT)
            self.assertEqual(self.client.patch(self.url(self.task), {"estimated_compensation_vnd": "1"}, format="json").status_code, 403)
        self.login(self.viewer)
        self.assert_redacted(self.client.get(self.url(self.task)))

    def test_create_update_and_assignment_responses_use_same_authorized_dto(self):
        for actor in (self.owner, self.admin, self.manager):
            self.login(actor)
            created = self.client.post(self.url(), {"title": "Manager created pay", "estimated_compensation_vnd": AMOUNT}, format="json")
            self.assertEqual(created.status_code, 201)
            self.assertEqual(created.data["estimated_compensation_vnd"], AMOUNT)
            changed = self.client.patch(self.url(created.data["id"]), {"title": "Other metadata only"}, format="json")
            self.assertEqual(changed.status_code, 200)
            self.assertEqual(changed.data["estimated_compensation_vnd"], AMOUNT)
            assigned = self.client.post(self.url(created.data["id"], route="task-assign"), {"target_profile_membership_id": str(self.memberships["assignee"].pk)}, format="json")
            self.assertEqual(assigned.status_code, 200)
            self.assertEqual(assigned.data["estimated_compensation_vnd"], AMOUNT)

    def test_start_response_returns_pay_only_to_the_current_assignee(self):
        self.login(self.assignee)
        response = self.client.post(self.url(self.task, route="task-start"), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["estimated_compensation_vnd"], AMOUNT)
        self.assertEqual(response.data["status"], "WORKING")

    def test_member_viewer_and_assignee_cannot_inject_pay_writes_or_tenant_fields(self):
        for actor in (self.member, self.viewer, self.assignee):
            self.login(actor)
            for payload in ({"estimated_compensation_vnd": None}, {"estimated_compensation_vnd": "1"},
                            {"estimated_compensation_vnd": "1", "workspace_id": str(self.foreign_workspace.pk)}):
                response = self.client.patch(self.url(self.task), payload, format="json")
                self.assertEqual(response.status_code, 403)
                self.assertNotIn(AMOUNT, json.dumps(response.data, default=str))
            self.assertIn(self.client.put(self.url(self.task), {"estimated_compensation_vnd": "1"}, format="json").status_code, (403, 405))
            self.assertEqual(self.client.post(self.url(), {"title": "Forged pay", "estimated_compensation_vnd": "1"}, format="json").status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.estimated_compensation_vnd, Decimal(AMOUNT))

    def test_null_zero_and_maximum_amount_do_not_confuse_redaction_or_precision(self):
        for amount in (None, "0", "999999999999999999"):
            Task.objects.filter(pk=self.task.pk).update(estimated_compensation_vnd=amount)
            for actor, allowed in ((self.owner, True), (self.assignee, True), (self.viewer, False)):
                self.login(actor)
                response = self.client.get(self.url(self.task))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["estimated_compensation_vnd"], amount if allowed else None)

    def test_unsafe_request_without_csrf_and_anonymous_reads_remain_denied(self):
        client = APIClient(enforce_csrf_checks=True)
        response = client.get(self.url(self.task))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(AMOUNT, json.dumps(response.data, default=str))
        client.force_login(self.owner)
        denied = client.patch(self.url(self.task), {"estimated_compensation_vnd": "1"}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.estimated_compensation_vnd, Decimal(AMOUNT))

    def test_pay_is_not_copied_into_audit_payloads(self):
        self.login(self.owner)
        self.assertEqual(self.client.patch(self.url(self.task), {"estimated_compensation_vnd": "123456789012345678"}, format="json").status_code, 200)
        payloads = json.dumps(list(AuditLog.objects.values_list("metadata", flat=True)), default=str)
        self.assertNotIn(AMOUNT, payloads)
        self.assertNotIn("123456789012345678", payloads)

    def test_list_serialization_queries_do_not_grow_with_task_count(self):
        self.login(self.assignee)
        with CaptureQueriesContext(connection) as first:
            small = self.client.get(self.url(), {"page_size": 50})
        self.assertEqual(small.status_code, 200)
        for index in range(12):
            task = Task.objects.create(workspace=self.workspace, created_by=self.owner, title=f"Pay page {index}", estimated_compensation_vnd=AMOUNT)
            if index % 2:
                TaskAssignment.objects.create(task=task, user=self.assignee)
        with CaptureQueriesContext(connection) as second:
            large = self.client.get(self.url(), {"page_size": 50})
        self.assertEqual(large.status_code, 200)
        self.assertEqual(len(large.data["results"]), 14)
        self.assertEqual(len(second), len(first))
        rows = {str(row["id"]): row["estimated_compensation_vnd"] for row in large.data["results"]}
        self.assertEqual(rows[str(self.task.pk)], AMOUNT)
        self.assertIsNone(rows[str(self.child.pk)])

    def test_related_comment_deliverable_and_notification_responses_never_contain_pay(self):
        self.login(self.assignee)
        comment = self.client.post(self.url(self.task, route="task-comment-list"), {"content": "Safe unrelated comment"}, format="json")
        self.assertEqual(comment.status_code, 201)
        self.assertEqual(self.client.post(self.url(self.task, route="task-start"), {}, format="json").status_code, 200)
        submitted = self.client.post(self.url(self.task, route="task-deliverable-list"), {"file_url": "https://example.test/finished"}, format="json")
        self.assertEqual(submitted.status_code, 201)
        self.login(self.owner)
        approve_url = reverse("tasks:task-deliverable-approve", kwargs={
            "profile_id": self.profile.pk, "workspace_id": self.workspace.pk,
            "task_id": self.task.pk, "deliverable_id": submitted.data["id"],
        })
        approved = self.client.post(approve_url, {"comment": "Safe review feedback"}, format="json")
        self.assertEqual(approved.status_code, 200)
        self.assertIsNotNone(approved.data["review"])
        self.login(self.viewer)
        for url in (self.url(self.task, route="task-comment-list"), self.url(self.task, route="task-deliverable-list"), "/api/v1/notifications/"):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            rendered = json.dumps(response.data, default=str)
            self.assertNotIn("estimated_compensation_vnd", rendered)
            self.assertNotIn(AMOUNT, rendered)
        reviewed = self.client.get(self.url(self.task, route="task-deliverable-list"))
        self.assertEqual(len(reviewed.data["results"]), 1)
        self.assertIsNotNone(reviewed.data["results"][0]["review"])

    def test_former_assignee_notification_keeps_safe_target_without_confidential_pay(self):
        self.login(self.owner)
        created = self.client.post(self.url(), {"title": "Assignment notification pay", "estimated_compensation_vnd": AMOUNT}, format="json")
        self.assertEqual(created.status_code, 201)
        task_id = created.data["id"]
        for target in ("assignee", "member"):
            assigned = self.client.post(self.url(task_id, route="task-assign"), {
                "target_profile_membership_id": str(self.memberships[target].pk),
            }, format="json")
            self.assertEqual(assigned.status_code, 200)
        self.login(self.assignee)
        self.assert_redacted(self.client.get(self.url(task_id)))
        notifications = self.client.get("/api/v1/notifications/")
        self.assertEqual(notifications.status_code, 200)
        self.assertTrue(any(str(row["task_id"]) == str(task_id) for row in notifications.data["results"]))
        rendered = json.dumps(notifications.data, default=str)
        self.assertNotIn("estimated_compensation_vnd", rendered)
        self.assertNotIn(AMOUNT, rendered)
