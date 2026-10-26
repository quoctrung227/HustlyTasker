from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .models import Task, TaskAssignment


class TaskPlanningApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        for name in ("owner", "manager", "editor", "viewer", "other", "staff"):
            setattr(cls, name, user_model.objects.create_user(
                username=f"planning-api-{name}", email=f"planning-api-{name}@example.test",
                password=None, is_staff=name == "staff",
            ))
        cls.profile = create_profile_with_owner(name="Planning API", owner=cls.owner)
        cls.workspace = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner, name="October", period=date(2026, 10, 1),
        )
        cls.sibling = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner, name="November", period=date(2026, 11, 1),
        )
        for user, role in ((cls.manager, "ADMIN"), (cls.editor, "MEMBER"), (cls.viewer, "VIEWER")):
            ProfileMembership.objects.create(profile=cls.profile, user=user, role="MEMBER")
            WorkspaceMember.objects.create(workspace=cls.workspace, user=user, role=role)
        cls.other_profile = create_profile_with_owner(name="Other planning tenant", owner=cls.other)
        cls.other_workspace = Workspace.objects.create(
            profile=cls.other_profile, owner=cls.other, name="Other October", period=date(2026, 10, 1),
        )
        cls.root = Task.objects.create(workspace=cls.workspace, created_by=cls.owner, title="Root")
        cls.child = Task.objects.create(
            workspace=cls.workspace, created_by=cls.owner, title="Child", parent=cls.root,
        )
        cls.grandchild = Task.objects.create(
            workspace=cls.workspace, created_by=cls.owner, title="Grandchild", parent=cls.child,
        )
        cls.sibling_task = Task.objects.create(workspace=cls.sibling, created_by=cls.owner, title="Sibling")
        cls.other_task = Task.objects.create(
            workspace=cls.other_workspace, created_by=cls.other, title="Other Task",
        )

    def setUp(self):
        self.client.force_login(self.owner)

    def url(self, name="task-list", task=None, **overrides):
        kwargs = {"profile_id": self.profile.id, "workspace_id": self.workspace.id, **overrides}
        if task is not None:
            kwargs["task_id"] = task.id if isinstance(task, Task) else task
        return reverse(f"tasks:{name}", kwargs=kwargs)

    def patch_task(self, task=None, payload=None):
        return self.client.patch(self.url("task-detail", task or self.child), payload or {}, format="json")

    def create(self, **payload):
        return self.client.post(self.url(), {"title": "New Task", **payload}, format="json")

    def test_create_subtask_reuses_task_api_and_preserves_old_fields(self):
        response = self.create(parent_id=str(self.root.id))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(response.data["parent_id"]), str(self.root.id))
        self.assertTrue({
            "id", "workspace_id", "title", "description", "status", "priority",
            "deadline", "active_assignment", "created_at", "updated_at",
        }.issubset(response.data))
        self.assertEqual(response.data["priority"], "MEDIUM")
        self.assertIsNone(response.data["deadline"])
        detail = self.client.get(self.url("task-detail", response.data["id"]))
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data, response.data)

    def test_default_list_is_flat_and_root_and_parent_filters_are_explicit(self):
        flat = self.client.get(self.url())
        self.assertEqual(flat.data["count"], 3)
        roots = self.client.get(self.url(), {"root_only": "true"})
        self.assertEqual([str(row["id"]) for row in roots.data["results"]], [str(self.root.id)])
        children = self.client.get(self.url(), {"parent_id": str(self.root.id)})
        self.assertEqual([str(row["id"]) for row in children.data["results"]], [str(self.child.id)])
        self.assertIsNone(roots.data["results"][0]["parent_id"])

    def test_subtask_route_returns_paginated_direct_children_only(self):
        Task.objects.create(workspace=self.workspace, created_by=self.owner, title="Second", parent=self.root)
        response = self.client.get(self.url("task-subtask-list", self.root), {"page_size": 1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results"})
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["next"])
        self.assertNotIn(str(self.grandchild.id), [str(row["id"]) for row in response.data["results"]])
        self.assertEqual(self.client.post(self.url("task-subtask-list", self.root), {}, format="json").status_code, 405)
        self.assertEqual(self.client.head(self.url("task-subtask-list", self.root)).status_code, 200)

    def test_manager_can_reparent_and_detach_without_changing_workflow(self):
        self.client.force_login(self.manager)
        detached = self.patch_task(payload={"parent_id": None, "priority": "HIGH"})
        self.assertEqual(detached.status_code, 200)
        self.assertIsNone(detached.data["parent_id"])
        attached = self.patch_task(payload={"parent_id": str(self.root.id)})
        self.assertEqual(attached.status_code, 200)
        self.assertEqual(attached.data["status"], "PENDING")
        self.assertEqual(attached.data["priority"], "HIGH")
        self.root.refresh_from_db()
        self.assertEqual(self.root.status, "PENDING")

    def test_self_parent_and_cycle_are_rejected_without_mutating_graph(self):
        for task, parent in ((self.root, self.root), (self.root, self.grandchild), (self.child, self.grandchild)):
            with self.subTest(task=task.id, parent=parent.id):
                before = AuditLog.objects.count()
                response = self.patch_task(task, {"parent_id": str(parent.id)})
                self.assertEqual(response.status_code, 400)
                self.assertEqual(AuditLog.objects.count(), before)
        self.root.refresh_from_db()
        self.child.refresh_from_db()
        self.assertIsNone(self.root.parent_id)
        self.assertEqual(self.child.parent_id, self.root.id)

    def test_maximum_depth_is_enforced_for_creation(self):
        deepest = self.create(parent_id=str(self.grandchild.id))
        self.assertEqual(deepest.status_code, 201)
        too_deep = self.create(parent_id=str(deepest.data["id"]))
        self.assertEqual(too_deep.status_code, 400)

    def test_cross_workspace_cross_profile_and_unknown_parent_are_nondisclosing(self):
        responses = []
        for task_id in (self.sibling_task.id, self.other_task.id, uuid4()):
            responses.extend((self.create(parent_id=str(task_id)), self.patch_task(payload={"parent_id": str(task_id)})))
            filtered = self.client.get(self.url(), {"parent_id": str(task_id)})
            responses.append(filtered)
        for response in responses:
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.data, {"detail": "Not found."})

    def test_nested_subtasks_route_checks_parent_and_tenant_scope(self):
        for url in (
            self.url("task-subtask-list", self.other_task),
            self.url("task-subtask-list", self.root, workspace_id=self.sibling.id),
            self.url("task-subtask-list", uuid4()),
            self.url("task-subtask-list", "not-a-uuid"),
        ):
            self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url("task-subtask-list", self.root)).status_code, 404)

    def test_editor_and_viewer_read_hierarchy_but_cannot_change_planning(self):
        TaskAssignment.objects.create(task=self.child, user=self.editor, is_active=True)
        for user in (self.editor, self.viewer):
            self.client.force_login(user)
            self.assertEqual(self.client.get(self.url("task-subtask-list", self.root)).status_code, 200)
            self.assertEqual(self.create(parent_id=str(self.root.id)).status_code, 403)
            self.assertEqual(self.patch_task(payload={"priority": "URGENT", "parent_id": None}).status_code, 403)

    def test_staff_without_membership_and_anonymous_receive_no_access(self):
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url("task-subtask-list", self.root)).status_code, 404)
        self.assertEqual(self.create(parent_id=str(self.root.id)).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url("task-subtask-list", self.root)).status_code, 403)

    def test_inactive_workspace_or_profile_membership_blocks_hierarchy(self):
        self.client.force_login(self.editor)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(is_active=False)
        self.assertEqual(self.client.get(self.url("task-subtask-list", self.root)).status_code, 404)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(is_active=True)
        ProfileMembership.objects.filter(profile=self.profile, user=self.editor).update(is_active=False)
        self.assertEqual(self.client.get(self.url("task-subtask-list", self.root)).status_code, 404)

    def test_archive_blocks_planning_mutations(self):
        Workspace.objects.filter(pk=self.workspace.pk).update(status=Workspace.Status.ARCHIVED)
        self.assertEqual(self.patch_task(payload={"parent_id": None}).status_code, 403)
        Workspace.objects.filter(pk=self.workspace.pk).update(status=Workspace.Status.ACTIVE)
        Profile.objects.filter(pk=self.profile.pk).update(status=Profile.Status.ARCHIVED)
        self.assertEqual(self.create(parent_id=str(self.root.id)).status_code, 403)

    def test_hierarchy_mutations_require_csrf_with_session_authentication(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url(), {"title": "Child", "parent_id": str(self.root.id)}, format="json").status_code, 403)
        self.assertEqual(client.patch(self.url("task-detail", self.child), {"parent_id": None}, format="json").status_code, 403)
        token = client.get(reverse("accounts:csrf")).data["csrf_token"]
        allowed = client.patch(self.url("task-detail", self.child), {"parent_id": None}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(allowed.status_code, 200)

    def test_deadline_timezone_null_and_parent_deadline_are_independent(self):
        response = self.patch_task(payload={"deadline": "2026-10-29T17:00:00+07:00"})
        self.assertEqual(response.status_code, 200)
        self.child.refresh_from_db()
        self.root.refresh_from_db()
        self.assertEqual(self.child.deadline, datetime(2026, 10, 29, 10, tzinfo=timezone.utc))
        self.assertIsNone(self.root.deadline)
        self.assertEqual(self.child.status, "PENDING")
        naive = self.patch_task(payload={"deadline": "2026-10-30T09:00:00"})
        self.assertEqual(naive.status_code, 200)
        cleared = self.patch_task(payload={"deadline": None})
        self.assertEqual(cleared.status_code, 200)
        self.assertIsNone(cleared.data["deadline"])

    def test_invalid_and_overflowing_deadlines_are_400(self):
        for deadline in ("not-a-date", "2026-02-30T10:00:00Z", "10000-01-01T00:00:00Z", "0001-01-01T00:00:00+23:59", "9999-12-31T23:59:59-23:59"):
            with self.subTest(deadline=deadline):
                self.assertEqual(self.patch_task(payload={"deadline": deadline}).status_code, 400)
                self.assertEqual(self.client.get(self.url(), {"deadline_before": deadline}).status_code, 400)

    def test_invalid_priority_and_mass_assignment_do_not_mutate_task(self):
        for payload in ({"priority": "CRITICAL"}, {"parent_id": "bad-uuid"}, {"status": "COMPLETED"}, {"workspace_id": str(self.other_workspace.id)}):
            with self.subTest(payload=payload):
                self.assertEqual(self.patch_task(payload=payload).status_code, 400)
        self.child.refresh_from_db()
        self.assertEqual(self.child.priority, "MEDIUM")
        self.assertEqual(self.child.status, "PENDING")

    def test_status_priority_deadline_filtering_and_semantic_priority_order(self):
        base = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
        Task.objects.filter(pk=self.root.pk).update(priority="HIGH", deadline=base)
        Task.objects.filter(pk=self.child.pk).update(priority="LOW", deadline=base + timedelta(hours=1))
        Task.objects.filter(pk=self.grandchild.pk).update(priority="URGENT", status="ASSIGNED")
        ordered = self.client.get(self.url(), {"ordering": "priority"})
        self.assertEqual([row["priority"] for row in ordered.data["results"]], ["LOW", "HIGH", "URGENT"])
        reversed_order = self.client.get(self.url(), {"ordering": "-priority"})
        self.assertEqual([row["priority"] for row in reversed_order.data["results"]], ["URGENT", "HIGH", "LOW"])
        filtered = self.client.get(self.url(), {"priority": "URGENT", "status": "ASSIGNED"})
        self.assertEqual(filtered.data["count"], 1)
        bounded = self.client.get(self.url(), {"deadline_before": base.isoformat(), "deadline_after": base.isoformat()})
        self.assertEqual([str(row["id"]) for row in bounded.data["results"]], [str(self.root.id)])

    def test_deadline_sort_keeps_nulls_last_in_both_directions(self):
        base = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
        Task.objects.filter(pk=self.root.pk).update(deadline=base)
        Task.objects.filter(pk=self.child.pk).update(deadline=base + timedelta(hours=1))
        for ordering, expected in (("deadline", [self.root.id, self.child.id, self.grandchild.id]), ("-deadline", [self.child.id, self.root.id, self.grandchild.id])):
            result = self.client.get(self.url(), {"ordering": ordering})
            self.assertEqual([str(row["id"]) for row in result.data["results"]], [str(pk) for pk in expected])

    def test_invalid_filter_values_are_safe_and_consistent(self):
        for query in ({"priority": "INVALID"}, {"status": "INVALID"}, {"ordering": "title"}, {"parent_id": "bad"}, {"root_only": "true", "parent_id": str(self.root.id)}, {"deadline_after": "2026-10-30T00:00:00Z", "deadline_before": "2026-10-01T00:00:00Z"}):
            with self.subTest(query=query):
                self.assertEqual(self.client.get(self.url(), query).status_code, 400)

    def test_existing_pagination_and_format_query_semantics_are_preserved(self):
        last_page = self.client.get(self.url(), {"page_size": "1", "page": "last", "format": "json"})
        self.assertEqual(last_page.status_code, 200)
        self.assertEqual(len(last_page.data["results"]), 1)
        self.assertIsNone(last_page.data["next"])
        for page_size in ("invalid", "0", "-1"):
            with self.subTest(page_size=page_size):
                response = self.client.get(self.url(), {"page_size": page_size})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["count"], 3)

    def test_hierarchy_assignment_serialization_does_not_add_queries_per_child(self):
        TaskAssignment.objects.create(task=self.child, user=self.editor, is_active=True)
        url = self.url("task-subtask-list", self.root)
        with CaptureQueriesContext(connection) as first:
            small = self.client.get(url)
        self.assertEqual(small.status_code, 200)
        for number in range(12):
            child = Task.objects.create(workspace=self.workspace, created_by=self.owner, title=f"Additional child {number}", parent=self.root)
            TaskAssignment.objects.create(task=child, user=self.editor, is_active=True)
        with CaptureQueriesContext(connection) as second:
            large = self.client.get(url)
        self.assertEqual(large.status_code, 200)
        self.assertEqual(large.data["count"], 13)
        self.assertLessEqual(len(second), len(first) + 1)
        self.assertTrue(all(row["active_assignment"]["profile_membership_id"] for row in large.data["results"]))

    def test_priority_change_is_audited_without_implicit_status_change(self):
        response = self.patch_task(payload={"priority": "HIGH"})
        self.assertEqual(response.status_code, 200)
        audit = AuditLog.objects.filter(action="task.updated", entity_id=self.child.id).latest("created_at")
        self.assertIn("priority", audit.metadata["changed_fields"])
        self.assertEqual(response.data["status"], "PENDING")
