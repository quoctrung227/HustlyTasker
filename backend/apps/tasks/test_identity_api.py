"""Request-scoped hints never replace live tenant/workflow authorization."""

import json
from datetime import date
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase, APIRequestFactory

from apps.audit.models import AuditLog
from apps.workspace.access import (
    resolve_profile_access_context,
    resolve_workspace_access_context,
)
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .models import Task, TaskAssignment
from .serializers import TaskReadSerializer


User = get_user_model()


class TaskIdentityApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for name in (
            "owner", "admin", "manager", "editor", "second-editor", "viewer",
            "member-only", "staff-outsider", "staff-editor", "other-owner",
        ):
            cls.users[name] = User.objects.create_user(
                email=f"identity-{name}@example.test",
                username=f"identity-{name}",
                password=None,
                is_staff=name.startswith("staff-"),
            )
        cls.users["editor"].first_name = "Lan"
        cls.users["editor"].last_name = "Trần"
        cls.users["editor"].save(update_fields=("first_name", "last_name"))
        cls.profile = create_profile_with_owner(
            owner=cls.users["owner"], name="Identity primary Profile",
        )
        cls.memberships = {
            "owner": ProfileMembership.objects.get(profile=cls.profile, user=cls.users["owner"]),
        }
        for name in ("admin", "manager", "editor", "second-editor", "viewer", "member-only", "staff-editor"):
            cls.memberships[name] = ProfileMembership.objects.create(
                profile=cls.profile,
                user=cls.users[name],
                role=ProfileMembership.Role.ADMIN if name == "admin" else ProfileMembership.Role.MEMBER,
            )
        cls.workspace = Workspace.objects.create(
            profile=cls.profile, owner=cls.users["owner"], name="Identity Workspace",
            period=date(2026, 10, 1),
        )
        cls.workspace_memberships = {}
        for name in ("owner", "admin", "manager", "editor", "second-editor", "viewer", "staff-editor"):
            cls.workspace_memberships[name] = WorkspaceMember.objects.create(
                workspace=cls.workspace, user=cls.users[name],
                role=(WorkspaceMember.Role.ADMIN if name == "manager" else
                      WorkspaceMember.Role.VIEWER if name == "viewer" else WorkspaceMember.Role.MEMBER),
            )
        cls.sibling_workspace = Workspace.objects.create(
            profile=cls.profile, owner=cls.users["owner"], name="Unassigned sibling",
            period=date(2026, 11, 1),
        )
        cls.task = Task.objects.create(
            workspace=cls.workspace, created_by=cls.users["owner"],
            title="Assigned identity Task", status=Task.Status.ASSIGNED,
        )
        cls.assignment = TaskAssignment.objects.create(task=cls.task, user=cls.users["editor"])
        cls.child = Task.objects.create(
            workspace=cls.workspace, parent=cls.task, created_by=cls.users["owner"],
            title="Assigned child identity Task", status=Task.Status.ASSIGNED,
        )
        TaskAssignment.objects.create(task=cls.child, user=cls.users["editor"])
        cls.sibling_task = Task.objects.create(
            workspace=cls.sibling_workspace, created_by=cls.users["owner"], title="Sibling secret Task",
        )
        cls.other_profile = create_profile_with_owner(
            owner=cls.users["other-owner"], name="Other identity Profile",
        )
        cls.other_membership = ProfileMembership.objects.create(
            profile=cls.other_profile, user=cls.users["editor"], role=ProfileMembership.Role.MEMBER,
        )
        cls.other_workspace = Workspace.objects.create(
            profile=cls.other_profile, owner=cls.users["other-owner"],
            name="Other identity Workspace", period=date(2026, 10, 1),
        )
        WorkspaceMember.objects.create(
            workspace=cls.other_workspace, user=cls.users["editor"], role=WorkspaceMember.Role.MEMBER,
        )
        cls.other_task = Task.objects.create(
            workspace=cls.other_workspace, created_by=cls.users["other-owner"],
            title="Other Profile Task", status=Task.Status.ASSIGNED,
        )
        TaskAssignment.objects.create(task=cls.other_task, user=cls.users["editor"])

    def setUp(self):
        self.client = APIClient()

    def login(self, name="editor"):
        self.client.force_login(self.users[name])

    def task_url(self, name="task-detail", task=None, workspace=None, profile=None):
        kwargs = {"profile_id": (profile or self.profile).id, "workspace_id": (workspace or self.workspace).id}
        if name != "task-list":
            kwargs["task_id"] = (task or self.task).id
        return reverse(f"tasks:{name}", kwargs=kwargs)

    def roster_url(self, workspace=None, profile=None):
        return reverse("workspace:workspace-member-list", kwargs={
            "profile_id": (profile or self.profile).id,
            "workspace_id": (workspace or self.workspace).id,
        })

    def roster(self):
        response = self.client.get(self.roster_url())
        self.assertEqual(response.status_code, 200)
        return {str(item["profile_membership_id"]): item for item in response.data["results"]}

    def assert_start_denied(self, expected_status):
        before = AuditLog.objects.count()
        response = self.client.post(self.task_url("task-start"), {}, format="json")
        self.assertEqual(response.status_code, expected_status)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.ASSIGNED)
        self.assertEqual(AuditLog.objects.count(), before)
        return response

    def test_same_user_maps_to_the_current_profile_membership_in_each_profile(self):
        self.login()
        for profile, workspace, task, membership in (
            (self.profile, self.workspace, self.task, self.memberships["editor"]),
            (self.other_profile, self.other_workspace, self.other_task, self.other_membership),
        ):
            with self.subTest(profile=profile.id):
                response = self.client.get(self.task_url(task=task, workspace=workspace, profile=profile))
                self.assertEqual(response.status_code, 200)
                self.assertIs(response.data["can_start"], True)
                self.assertEqual(str(response.data["active_assignment"]["profile_membership_id"]), str(membership.id))
                self.assertNotEqual(str(membership.id), str(self.users["editor"].id))

    def test_request_specific_hint_is_consistent_on_list_detail_and_direct_children(self):
        self.login()
        listing = self.client.get(self.task_url("task-list"))
        detail = self.client.get(self.task_url())
        children = self.client.get(self.task_url("task-subtask-list"))
        self.assertEqual([listing.status_code, detail.status_code, children.status_code], [200, 200, 200])
        self.assertTrue(all(row["can_start"] is True for row in listing.data["results"]))
        self.assertIs(detail.data["can_start"], True)
        self.assertEqual([str(row["id"]) for row in children.data["results"]], [str(self.child.id)])
        self.assertIs(children.data["results"][0]["can_start"], True)

    def test_owner_admin_manager_viewer_and_non_assignee_have_no_start_hint(self):
        for name in ("owner", "admin", "manager", "viewer", "second-editor"):
            with self.subTest(actor=name):
                self.login(name)
                response = self.client.get(self.task_url())
                self.assertEqual(response.status_code, 200)
                self.assertIs(response.data["can_start"], False)
                self.assert_start_denied(403)

    def test_staff_flag_grants_no_tenant_access(self):
        self.login("staff-outsider")
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)
        self.assertEqual(self.client.get(self.roster_url()).status_code, 404)
        self.assert_start_denied(404)

    def test_historical_assignment_does_not_make_a_manager_or_viewer_an_executor(self):
        # Imported/legacy attribution is not an alternate role grant. The
        # supported assignment service intentionally cannot create these rows.
        for name in ("owner", "admin", "manager", "viewer"):
            with self.subTest(actor=name):
                TaskAssignment.objects.filter(task=self.task).update(is_active=False)
                TaskAssignment.objects.create(task=self.task, user=self.users[name])
                self.login(name)
                self.assertIs(self.client.get(self.task_url()).data["can_start"], False)
                self.assert_start_denied(403)

    def test_staff_editor_still_requires_their_own_assignment(self):
        self.login("staff-editor")
        self.assertIs(self.client.get(self.task_url()).data["can_start"], False)
        self.assert_start_denied(403)
        TaskAssignment.objects.filter(task=self.task).update(is_active=False)
        TaskAssignment.objects.create(task=self.task, user=self.users["staff-editor"])
        self.assertIs(self.client.get(self.task_url()).data["can_start"], True)
        response = self.client.post(self.task_url("task-start"), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Task.Status.WORKING)
        self.assertIs(response.data["can_start"], False)

    def test_missing_or_mismatched_serializer_context_fails_closed(self):
        profile_context = resolve_profile_access_context(self.users["editor"], self.profile.id)
        workspace_context = resolve_workspace_access_context(profile_context, self.workspace.id)
        request = APIRequestFactory().get("/")
        request.user = self.users["second-editor"]
        for context in ({}, {"workspace_access_context": workspace_context}, {"request": request, "workspace_access_context": workspace_context}):
            with self.subTest(keys=tuple(context)):
                self.assertIs(TaskReadSerializer(self.task, context=context).data["can_start"], False)

    def test_unknown_client_identity_or_hint_fields_cannot_authorize_start(self):
        self.login("second-editor")
        response = self.client.post(self.task_url("task-start"), {
            "can_start": True,
            "user_id": str(self.users["editor"].id),
            "profile_membership_id": str(self.memberships["editor"].id),
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.ASSIGNED)

    def test_assignment_inactive_or_removed_makes_the_hint_false(self):
        self.login()
        self.assertIs(self.client.get(self.task_url()).data["can_start"], True)
        self.assignment.is_active = False
        self.assignment.save(update_fields=("is_active",))
        self.assertIs(self.client.get(self.task_url()).data["can_start"], False)
        self.assert_start_denied(403)

    def test_all_non_assigned_task_states_have_false_hint_and_conflict_on_start(self):
        self.login()
        for state in Task.Status.values:
            if state == Task.Status.ASSIGNED:
                continue
            with self.subTest(state=state):
                Task.objects.filter(pk=self.task.id).update(status=state)
                response = self.client.get(self.task_url())
                self.assertEqual(response.status_code, 200)
                self.assertIs(response.data["can_start"], False)
                denied = self.client.post(self.task_url("task-start"), {}, format="json")
                self.assertEqual(denied.status_code, 409)
                self.task.refresh_from_db()
                self.assertEqual(self.task.status, state)

    def test_start_success_has_a_current_false_hint_and_repeat_conflicts(self):
        self.login()
        self.assertIs(self.client.get(self.task_url()).data["can_start"], True)
        response = self.client.post(self.task_url("task-start"), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], Task.Status.WORKING)
        self.assertIs(response.data["can_start"], False)
        self.assertEqual(self.client.post(self.task_url("task-start"), {}, format="json").status_code, 409)

    def test_revoked_profile_membership_invalidates_a_previously_true_hint(self):
        self.login()
        self.assertIs(self.client.get(self.task_url()).data["can_start"], True)
        ProfileMembership.objects.filter(pk=self.memberships["editor"].id).update(is_active=False)
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)
        self.assert_start_denied(404)

    def test_revoked_workspace_membership_invalidates_a_previously_true_hint(self):
        self.login()
        self.assertIs(self.client.get(self.task_url()).data["can_start"], True)
        WorkspaceMember.objects.filter(pk=self.workspace_memberships["editor"].id).update(is_active=False)
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)
        self.assert_start_denied(404)

    def test_inactive_user_cannot_reuse_a_true_hint_or_session(self):
        self.login()
        self.assertIs(self.client.get(self.task_url()).data["can_start"], True)
        User.objects.filter(pk=self.users["editor"].id).update(is_active=False)
        self.assertEqual(self.client.get(self.task_url()).status_code, 403)
        self.assert_start_denied(403)

    def test_role_change_and_reassignment_invalidate_previously_true_hints(self):
        self.login()
        self.assertIs(self.client.get(self.task_url()).data["can_start"], True)
        WorkspaceMember.objects.filter(pk=self.workspace_memberships["editor"].id).update(role=WorkspaceMember.Role.VIEWER)
        self.assertIs(self.client.get(self.task_url()).data["can_start"], False)
        self.assert_start_denied(403)
        WorkspaceMember.objects.filter(pk=self.workspace_memberships["editor"].id).update(role=WorkspaceMember.Role.MEMBER)
        self.assignment.is_active = False
        self.assignment.save(update_fields=("is_active",))
        TaskAssignment.objects.create(task=self.task, user=self.users["second-editor"])
        self.assertIs(self.client.get(self.task_url()).data["can_start"], False)
        self.assert_start_denied(403)

    def test_archived_workspace_denies_start_after_a_true_hint(self):
        self.login()
        self.assertIs(self.client.get(self.task_url()).data["can_start"], True)
        Workspace.objects.filter(pk=self.workspace.id).update(status=Workspace.Status.ARCHIVED)
        self.assertIs(self.client.get(self.task_url()).data["can_start"], False)
        self.assert_start_denied(403)

    def test_archived_profile_denies_start_after_a_true_hint(self):
        self.login()
        self.assertIs(self.client.get(self.task_url()).data["can_start"], True)
        Profile.objects.filter(pk=self.profile.id).update(status=Profile.Status.ARCHIVED)
        self.assertIs(self.client.get(self.task_url()).data["can_start"], False)
        self.assert_start_denied(403)

    def test_hint_and_start_cannot_cross_profile_or_workspace_nesting(self):
        self.login()
        for profile, workspace, task in (
            (self.profile, self.workspace, self.other_task),
            (self.other_profile, self.workspace, self.task),
            (self.profile, self.workspace, self.sibling_task),
            (self.profile, self.sibling_workspace, self.task),
        ):
            with self.subTest(task=task.id, workspace=workspace.id, profile=profile.id):
                detail = self.client.get(self.task_url(task=task, workspace=workspace, profile=profile))
                mutation = self.client.post(self.task_url("task-start", task=task, workspace=workspace, profile=profile), {}, format="json")
                self.assertEqual([detail.status_code, mutation.status_code], [404, 404])
                self.assertNotIn("can_start", detail.data)
                self.assertNotIn(str(self.memberships["editor"].id), json.dumps(detail.data))

    def test_management_mutation_responses_have_false_hints_for_the_request_actor(self):
        self.login("owner")
        created = self.client.post(self.task_url("task-list"), {"title": "Fresh identity Task"}, format="json")
        self.assertEqual(created.status_code, 201)
        self.assertIs(created.data["can_start"], False)
        edited = self.client.patch(self.task_url(), {"description": "Updated by manager"}, format="json")
        self.assertEqual(edited.status_code, 200)
        self.assertIs(edited.data["can_start"], False)
        assigned = self.client.post(self.task_url("task-assign"), {"target_profile_membership_id": str(self.memberships["second-editor"].id)}, format="json")
        self.assertEqual(assigned.status_code, 200)
        self.assertIs(assigned.data["can_start"], False)

    def test_start_requires_csrf_even_when_a_read_hint_is_true(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.login()
        self.assertIs(self.client.get(self.task_url()).data["can_start"], True)
        self.assert_start_denied(403)

    def test_anonymous_cannot_read_task_identity_or_assignment_roster(self):
        self.assertEqual(self.client.get(self.task_url()).status_code, 403)
        self.assertEqual(self.client.get(self.roster_url()).status_code, 403)
        self.assert_start_denied(403)

    def test_roster_manager_role_ceiling_and_scoped_eligibility(self):
        for manager in ("owner", "admin", "manager"):
            with self.subTest(manager=manager):
                self.login(manager)
                rows = self.roster()
                for name in ("editor", "second-editor", "staff-editor"):
                    self.assertIs(rows[str(self.memberships[name].id)]["is_assignable"], True)
                for name in ("owner", "admin", "manager", "viewer"):
                    self.assertIs(rows[str(self.memberships[name].id)]["is_assignable"], False)
                self.assertNotIn(str(self.other_membership.id), rows)
                self.assertNotIn(str(self.memberships["member-only"].id), rows)

    def test_editor_viewer_member_only_and_staff_cannot_read_roster(self):
        for name, expected in (("editor", 403), ("viewer", 403), ("member-only", 404), ("staff-outsider", 404), ("staff-editor", 403)):
            with self.subTest(actor=name):
                self.login(name)
                self.assertEqual(self.client.get(self.roster_url()).status_code, expected)

    def test_roster_display_labels_omit_unnecessary_identity_fields(self):
        self.login("owner")
        response = self.client.get(self.roster_url())
        rows = {str(row["profile_membership_id"]): row for row in response.data["results"]}
        self.assertEqual(rows[str(self.memberships["editor"].id)]["display_label"], "Lan Trần")
        self.assertEqual(rows[str(self.memberships["second-editor"].id)]["display_label"], f"Thành viên {str(self.memberships['second-editor'].id)[:8]}")
        expected_fields = {"id", "profile_membership_id", "display_label", "is_assignable", "role", "is_active", "joined_at", "updated_at"}
        for row in rows.values():
            self.assertEqual(set(row), expected_fields)
            self.assertIs(type(row["is_assignable"]), bool)
        payload = json.dumps(response.data, ensure_ascii=False, default=str)
        for user in self.users.values():
            self.assertNotIn(user.email, payload)
            self.assertNotIn(user.username, payload)
            self.assertNotIn(str(user.id), payload)
        self.assertNotIn("password", payload)

    def test_roster_excludes_inactive_user_profile_and_workspace_memberships(self):
        self.login("owner")
        User.objects.filter(pk=self.users["editor"].id).update(is_active=False)
        ProfileMembership.objects.filter(pk=self.memberships["second-editor"].id).update(is_active=False)
        WorkspaceMember.objects.filter(pk=self.workspace_memberships["staff-editor"].id).update(is_active=False)
        rows = self.roster()
        for name in ("editor", "second-editor", "staff-editor"):
            self.assertNotIn(str(self.memberships[name].id), rows)

    def test_roster_archived_context_is_readable_to_managers_but_never_assignable(self):
        self.login("owner")
        Workspace.objects.filter(pk=self.workspace.id).update(status=Workspace.Status.ARCHIVED)
        self.assertTrue(self.roster())
        self.assertTrue(all(row["is_assignable"] is False for row in self.roster().values()))
        Workspace.objects.filter(pk=self.workspace.id).update(status=Workspace.Status.ACTIVE)
        Profile.objects.filter(pk=self.profile.id).update(status=Profile.Status.ARCHIVED)
        self.assertTrue(all(row["is_assignable"] is False for row in self.roster().values()))

    def test_roster_is_read_only_and_does_not_create_assignments_or_audits(self):
        self.login("owner")
        before = (TaskAssignment.objects.count(), Task.objects.count(), AuditLog.objects.count())
        response = self.client.get(self.roster_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual((TaskAssignment.objects.count(), Task.objects.count(), AuditLog.objects.count()), before)

    def test_roster_wrong_profile_workspace_pair_and_foreign_tenant_are_hidden(self):
        self.login("owner")
        for profile, workspace in ((self.profile, self.other_workspace), (self.other_profile, self.workspace), (self.other_profile, self.other_workspace)):
            with self.subTest(profile=profile.id, workspace=workspace.id):
                response = self.client.get(self.roster_url(workspace=workspace, profile=profile))
                self.assertEqual(response.status_code, 404)
                self.assertNotIn("display_label", response.data)

    def test_roster_eligibility_is_only_a_hint_and_assignment_revalidates(self):
        self.login("owner")
        target = self.memberships["second-editor"]
        self.assertIs(self.roster()[str(target.id)]["is_assignable"], True)
        WorkspaceMember.objects.filter(pk=self.workspace_memberships["second-editor"].id).update(role=WorkspaceMember.Role.VIEWER)
        before = AuditLog.objects.count()
        response = self.client.post(self.task_url("task-assign"), {"target_profile_membership_id": str(target.id)}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(AuditLog.objects.count(), before)
        self.assertTrue(TaskAssignment.objects.filter(pk=self.assignment.id, is_active=True).exists())

    def test_roster_preserves_pagination(self):
        self.login("owner")
        url = f"{self.roster_url()}?page_size=2"
        first = self.client.get(url)
        second = self.client.get(f"{url}&page=2")
        self.assertEqual([first.status_code, second.status_code], [200, 200])
        self.assertEqual(first.data["count"], 7)
        self.assertEqual(len(first.data["results"]), 2)
        self.assertEqual(len(second.data["results"]), 2)
        self.assertTrue({str(row["id"]) for row in first.data["results"]}.isdisjoint({str(row["id"]) for row in second.data["results"]}))

    def test_task_list_hint_does_not_add_per_task_database_queries(self):
        self.login()
        with CaptureQueriesContext(connection) as initial:
            response = self.client.get(self.task_url("task-list"))
        self.assertEqual(response.status_code, 200)
        for number in range(7):
            extra = Task.objects.create(workspace=self.workspace, created_by=self.users["owner"], title=f"Extra hint {number}", status=Task.Status.ASSIGNED)
            TaskAssignment.objects.create(task=extra, user=self.users["editor"])
        with CaptureQueriesContext(connection) as expanded:
            response = self.client.get(self.task_url("task-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 9)
        self.assertTrue(all(row["can_start"] is True for row in response.data["results"]))
        self.assertLessEqual(len(expanded), len(initial) + 2)

    def test_roster_labels_and_eligibility_do_not_add_per_row_queries(self):
        self.login("owner")
        with CaptureQueriesContext(connection) as initial:
            response = self.client.get(self.roster_url())
        self.assertEqual(response.status_code, 200)
        for number in range(7):
            user = User.objects.create_user(email=f"identity-extra-{number}@example.test", username=f"identity-extra-{number}", password=None)
            ProfileMembership.objects.create(profile=self.profile, user=user, role=ProfileMembership.Role.MEMBER)
            WorkspaceMember.objects.create(workspace=self.workspace, user=user, role=WorkspaceMember.Role.MEMBER)
        with CaptureQueriesContext(connection) as expanded:
            response = self.client.get(self.roster_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 14)
        self.assertLessEqual(len(expanded), len(initial) + 2)

    def test_unknown_membership_is_not_resolved_as_a_global_user_identity(self):
        self.login("owner")
        for target in (self.users["editor"].id, self.other_membership.id, uuid4()):
            with self.subTest(target=target):
                response = self.client.post(self.task_url("task-assign"), {"target_profile_membership_id": str(target)}, format="json")
                self.assertEqual(response.status_code, 400)
        self.assertTrue(TaskAssignment.objects.filter(pk=self.assignment.id, is_active=True).exists())
