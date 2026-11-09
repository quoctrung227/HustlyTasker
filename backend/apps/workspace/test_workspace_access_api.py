"""Workspace access UI hints reuse current domain authority, never grant it."""

import json
from datetime import date
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.reviews.models import Deliverable
from apps.tasks.models import Task, TaskAssignment

from .access import (
    TenantAccessNotFound,
    resolve_profile_access_context,
    resolve_workspace_access_context,
    workspace_member_candidates_visible_to_managers,
    workspace_member_management_capabilities,
    workspace_members_visible_to_managers,
)
from .models import Profile, ProfileMembership, Workspace, WorkspaceMember
from .permissions import CanManageWorkspaceMembers
from .serializers import (
    WorkspaceMemberCandidateReadSerializer,
    WorkspaceMemberReadSerializer,
)
from .services import create_profile_with_owner


User = get_user_model()


class WorkspaceAccessApiTests(APITestCase):
    candidate_fields = {
        "profile_membership_id", "display_label", "profile_role",
        "has_inherited_access",
    }
    member_fields = {
        "id", "profile_membership_id", "display_label", "is_assignable",
        "role", "is_active", "joined_at", "updated_at", "capabilities",
    }

    @classmethod
    def setUpTestData(cls):
        cls.users = {}
        for name in (
            "owner", "admin", "manager", "editor", "viewer", "target",
            "reactivated", "legacy", "inactive-membership", "inactive-user",
            "outsider",
        ):
            cls.users[name] = User.objects.create_user(
                email=f"workspace-access-{name}@example.test",
                username=f"workspace-access-{name}@example.test",
                first_name="Synthetic", last_name=name, password=None,
                is_active=name != "inactive-user",
            )
        cls.owner = cls.users["owner"]
        cls.profile = create_profile_with_owner(name="Synthetic access", owner=cls.owner)
        cls.memberships = {
            "owner": ProfileMembership.objects.get(profile=cls.profile, user=cls.owner),
        }
        for name, user in cls.users.items():
            if name not in ("owner", "outsider"):
                cls.memberships[name] = ProfileMembership.objects.create(
                    profile=cls.profile, user=user,
                    role=ProfileMembership.Role.ADMIN if name == "admin" else ProfileMembership.Role.MEMBER,
                    is_active=name != "inactive-membership",
                )
        cls.workspace = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner,
            name="Synthetic access month", period=date(2026, 11, 1),
        )
        cls.sibling = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner,
            name="Sibling access month", period=date(2026, 12, 1),
        )
        cls.assignments = {}
        for name, role in (
            ("manager", WorkspaceMember.Role.ADMIN),
            ("editor", WorkspaceMember.Role.MEMBER),
            ("viewer", WorkspaceMember.Role.VIEWER),
            ("reactivated", WorkspaceMember.Role.VIEWER),
            ("legacy", WorkspaceMember.Role.OWNER),
        ):
            cls.assignments[name] = WorkspaceMember.objects.create(
                workspace=cls.workspace, user=cls.users[name], role=role,
                is_active=name != "reactivated",
            )
        cls.foreign_profile = create_profile_with_owner(
            name="Foreign synthetic access", owner=cls.users["outsider"],
        )
        cls.foreign_workspace = Workspace.objects.create(
            profile=cls.foreign_profile, owner=cls.users["outsider"],
            name="Foreign synthetic month", period=date(2026, 11, 1),
        )

    def url(self, route="members", *, profile_id=None, workspace_id=None, membership_id=None):
        name = "workspace-member-candidate-list" if route == "candidates" else "workspace-member-list"
        kwargs = {
            "profile_id": self.profile.id if profile_id is None else profile_id,
            "workspace_id": self.workspace.id if workspace_id is None else workspace_id,
        }
        if membership_id is not None:
            name = "workspace-member-detail"
            kwargs["membership_id"] = membership_id
        return reverse(f"workspace:{name}", kwargs=kwargs)

    def login(self, name="owner"):
        self.client.force_login(self.users[name])

    def context(self, name="owner"):
        return resolve_workspace_access_context(
            resolve_profile_access_context(self.users[name], self.profile.id),
            self.workspace.id,
        )

    def rows(self, response):
        self.assertEqual(response.status_code, 200)
        return {row["profile_membership_id"]: row for row in response.data["results"]}

    def add(self, name="target", role="MEMBER"):
        return self.client.post(self.url(), {
            "target_profile_membership_id": str(self.memberships[name].id),
            "role": role,
        }, format="json")

    def test_owner_roster_preserves_old_fields_and_exposes_current_management_hints(self):
        self.login()
        response = self.client.get(self.url())
        rows = self.rows(response)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results", "capabilities"})
        self.assertEqual(response.data["capabilities"], {
            "can_add": True, "allowed_roles": ["ADMIN", "MEMBER", "VIEWER"],
            "profile_role": "OWNER", "workspace_role": None,
            "has_inherited_access": True,
        })
        self.assertEqual(len(rows), 3)
        for row in rows.values():
            self.assertEqual(set(row), self.member_fields)
            self.assertEqual(row["capabilities"], {
                "can_update": True, "can_revoke": True,
                "allowed_roles": ["ADMIN", "MEMBER", "VIEWER"],
                "has_inherited_access": False,
            })

    def test_profile_admin_has_inherited_management_without_workspace_row(self):
        self.login("admin")
        self.assertFalse(WorkspaceMember.objects.filter(user=self.users["admin"]).exists())
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["capabilities"]["profile_role"], "ADMIN")
        self.assertIsNone(response.data["capabilities"]["workspace_role"])
        self.assertTrue(response.data["capabilities"]["has_inherited_access"])
        self.assertEqual(response.data["capabilities"]["allowed_roles"], ["ADMIN", "MEMBER", "VIEWER"])

    def test_workspace_admin_gets_scoped_candidates_without_profile_governance(self):
        self.login("manager")
        profile_roster = reverse("workspace:profile-member-list", kwargs={"profile_id": self.profile.id})
        self.assertEqual(self.client.get(profile_roster).status_code, 403)
        self.assertEqual(self.client.get(self.url("candidates")).status_code, 200)
        response = self.client.get(self.url())
        rows = self.rows(response)
        self.assertEqual(response.data["capabilities"], {
            "can_add": True, "allowed_roles": ["MEMBER", "VIEWER"],
            "profile_role": "MEMBER", "workspace_role": "ADMIN",
            "has_inherited_access": False,
        })
        self.assertEqual(rows[str(self.memberships["manager"].id)]["capabilities"], {
            "can_update": False, "can_revoke": False,
            "allowed_roles": [], "has_inherited_access": False,
        })
        self.assertTrue(rows[str(self.memberships["editor"].id)]["capabilities"]["can_update"])
        self.assertEqual(rows[str(self.memberships["viewer"].id)]["capabilities"]["allowed_roles"], ["MEMBER", "VIEWER"])

    def test_candidate_projection_excludes_unrelated_inactive_and_already_active_assignments(self):
        self.login()
        rows = self.rows(self.client.get(self.url("candidates")))
        self.assertEqual(set(rows), {str(self.memberships[name].id) for name in ("owner", "admin", "target", "reactivated")})
        for row in rows.values():
            self.assertEqual(set(row), self.candidate_fields)
            self.assertNotIn("@", row["display_label"])
        self.assertTrue(rows[str(self.memberships["owner"].id)]["has_inherited_access"])
        self.assertEqual(rows[str(self.memberships["admin"].id)]["profile_role"], "ADMIN")
        self.assertFalse(rows[str(self.memberships["target"].id)]["has_inherited_access"])
        serialized = json.dumps(list(rows.values()))
        for user in self.users.values():
            self.assertNotIn(user.email, serialized)
            self.assertNotIn(str(user.id), serialized)

    def test_candidate_fallback_is_membership_label_never_email_username(self):
        User.objects.filter(pk=self.users["target"].pk).update(first_name="", last_name="")
        self.login()
        rows = self.rows(self.client.get(self.url("candidates")))
        self.assertEqual(rows[str(self.memberships["target"].id)]["display_label"], f"Thành viên {str(self.memberships['target'].id)[:8]}")

    def test_candidate_pagination_is_stable_bounded_and_workspace_scoped(self):
        self.login()
        first = self.client.get(self.url("candidates"), {"page_size": 2})
        second = self.client.get(self.url("candidates"), {"page_size": 2, "page": 2})
        self.assertEqual(first.data["count"], 4)
        actual = [row["profile_membership_id"] for row in first.data["results"] + second.data["results"]]
        expected = [str(value) for value in ProfileMembership.objects.filter(
            id__in=[self.memberships[name].id for name in ("owner", "admin", "target", "reactivated")],
        ).order_by("joined_at", "id").values_list("id", flat=True)]
        self.assertEqual(actual, expected)
        sibling = self.client.get(self.url("candidates", workspace_id=self.sibling.id))
        self.assertIn(str(self.memberships["editor"].id), self.rows(sibling))
        self.assertLessEqual(len(self.client.get(self.url("candidates"), {"page_size": 10000}).data["results"]), 100)
        self.assertEqual(self.client.get(self.url("candidates"), {"page": 999}).status_code, 404)

    def test_archived_profile_and_workspace_keep_roster_read_only_and_candidates_empty(self):
        self.login()
        for model, instance in ((Profile, self.profile), (Workspace, self.workspace)):
            with self.subTest(model=model.__name__):
                model.objects.filter(pk=instance.pk).update(status="ARCHIVED")
                roster = self.client.get(self.url())
                self.assertEqual(roster.status_code, 200)
                self.assertFalse(roster.data["capabilities"]["can_add"])
                self.assertEqual(roster.data["capabilities"]["allowed_roles"], [])
                for row in roster.data["results"]:
                    self.assertFalse(row["capabilities"]["can_update"])
                    self.assertFalse(row["capabilities"]["can_revoke"])
                    self.assertEqual(row["capabilities"]["allowed_roles"], [])
                self.assertEqual(self.client.get(self.url("candidates")).data["count"], 0)
                self.assertEqual(self.add().status_code, 403)
                model.objects.filter(pk=instance.pk).update(status="ACTIVE")

    def test_anonymous_editor_viewer_and_unassigned_member_cannot_read_management_data(self):
        for route in ("members", "candidates"):
            self.assertEqual(self.client.get(self.url(route)).status_code, 403)
        for name, expected in (("editor", 403), ("viewer", 403), ("target", 404), ("outsider", 404)):
            self.login(name)
            for route in ("members", "candidates"):
                with self.subTest(name=name, route=route):
                    response = self.client.get(self.url(route))
                    self.assertEqual(response.status_code, expected)
                    self.assertNotIn("results", response.data)

    def test_cross_parent_malformed_and_foreign_scope_ids_are_generic_not_found(self):
        self.login()
        for profile_id, workspace_id in (
            (self.profile.id, self.foreign_workspace.id),
            (self.foreign_profile.id, self.foreign_workspace.id),
            (uuid4(), self.workspace.id), (self.profile.id, "invalid"),
        ):
            for route in ("members", "candidates"):
                response = self.client.get(self.url(route, profile_id=profile_id, workspace_id=workspace_id))
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.data, {"detail": "Not found."})

    def test_staff_flags_inactive_user_and_revoked_profile_membership_do_not_bypass_scope(self):
        User.objects.filter(pk=self.users["outsider"].pk).update(is_staff=True, is_superuser=True)
        self.login("outsider")
        self.assertEqual(self.client.get(self.url("candidates")).status_code, 404)
        self.login("admin")
        ProfileMembership.objects.filter(pk=self.memberships["admin"].pk).update(is_active=False)
        self.assertEqual(self.client.get(self.url("candidates")).status_code, 404)
        self.login()
        User.objects.filter(pk=self.owner.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.url("candidates")).status_code, 403)

    def test_candidate_permission_drift_is_revalidated_after_permission_check(self):
        self.login("manager")
        original = CanManageWorkspaceMembers.has_permission

        def demote(permission, request, view):
            allowed = original(permission, request, view)
            if allowed:
                WorkspaceMember.objects.filter(pk=self.assignments["manager"].pk).update(role="VIEWER")
            return allowed

        with patch.object(CanManageWorkspaceMembers, "has_permission", demote):
            response = self.client.get(self.url("candidates"))
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("results", response.data)

    def test_lazy_candidates_recheck_workspace_actor_role_at_evaluation(self):
        context = self.context("manager")
        queryset = workspace_member_candidates_visible_to_managers(context)
        WorkspaceMember.objects.filter(pk=self.assignments["manager"].pk).update(role="MEMBER")
        self.assertEqual(list(queryset), [])
        with self.assertRaises(TenantAccessNotFound):
            workspace_member_management_capabilities(context)

    def test_lazy_candidates_recheck_profile_actor_and_target_account_at_evaluation(self):
        queryset = workspace_member_candidates_visible_to_managers(self.context())
        User.objects.filter(pk=self.users["target"].pk).update(is_active=False)
        self.assertNotIn(self.memberships["target"].id, [row.id for row in queryset])
        queryset = workspace_member_candidates_visible_to_managers(self.context())
        ProfileMembership.objects.filter(pk=self.memberships["owner"].pk).update(is_active=False)
        self.assertEqual(list(queryset), [])

    def test_final_roster_capability_check_rejects_revocation_during_serialization(self):
        self.login()
        original = WorkspaceMemberReadSerializer.get_capabilities

        def revoke(serializer, membership):
            result = original(serializer, membership)
            ProfileMembership.objects.filter(pk=self.memberships["owner"].pk).update(is_active=False)
            return result

        with patch.object(WorkspaceMemberReadSerializer, "get_capabilities", revoke):
            response = self.client.get(self.url())
        self.assertEqual(response.status_code, 404)
        self.assertNotIn("results", response.data)

    def test_candidates_are_read_only_session_protected_noncacheable(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.get(self.url("candidates"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertIn("private", response.headers["Cache-Control"])
        self.assertEqual(client.post(self.url("candidates"), {}, format="json").status_code, 403)
        token = client.get(reverse("accounts:csrf")).data["csrf_token"]
        self.assertEqual(client.post(self.url("candidates"), {}, format="json", HTTP_X_CSRFTOKEN=token).status_code, 405)
        self.assertEqual(client.head(self.url("candidates")).status_code, 200)
        self.assertEqual(client.options(self.url("candidates")).status_code, 200)

    def test_archive_during_candidate_serialization_removes_stale_selection_data(self):
        self.login()
        original = WorkspaceMemberCandidateReadSerializer.get_has_inherited_access

        def archive(serializer, membership):
            result = original(serializer, membership)
            Workspace.objects.filter(pk=self.workspace.pk).update(status="ARCHIVED")
            return result

        with patch.object(WorkspaceMemberCandidateReadSerializer, "get_has_inherited_access", archive):
            response = self.client.get(self.url("candidates"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"count": 0, "results": [], "next": None, "previous": None})

    def test_stale_read_capability_cannot_authorize_a_later_membership_mutation(self):
        self.login("manager")
        self.assertTrue(self.client.get(self.url()).data["capabilities"]["can_add"])
        WorkspaceMember.objects.filter(pk=self.assignments["manager"].pk).update(role="VIEWER")
        self.assertEqual(self.add().status_code, 403)
        self.assertFalse(WorkspaceMember.objects.filter(workspace=self.workspace, user=self.users["target"]).exists())

    def test_row_capabilities_match_existing_workspace_admin_role_ceiling(self):
        self.login("manager")
        editor = self.assignments["editor"]
        self.assertEqual(self.client.patch(self.url(membership_id=editor.id), {"role": "VIEWER"}, format="json").status_code, 200)
        self.assertEqual(self.add(role="ADMIN").status_code, 403)
        self.assertEqual(self.client.patch(self.url(membership_id=self.assignments["manager"].id), {"role": "MEMBER"}, format="json").status_code, 403)
        self.assertEqual(self.client.delete(self.url(membership_id=self.assignments["manager"].id)).status_code, 403)

    def test_candidate_reactivation_reuses_row_and_duplicate_grant_conflicts(self):
        self.login()
        old_id = self.assignments["reactivated"].id
        self.assertIn(str(self.memberships["reactivated"].id), self.rows(self.client.get(self.url("candidates"))))
        response = self.add("reactivated", "MEMBER")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["id"], str(old_id))
        self.assertFalse(response.data["capabilities"]["can_update"])
        self.assertNotIn(str(self.memberships["reactivated"].id), self.rows(self.client.get(self.url("candidates"))))
        self.assertEqual(self.add("reactivated", "VIEWER").status_code, 409)
        self.assertEqual(WorkspaceMember.objects.filter(workspace=self.workspace, user=self.users["reactivated"]).count(), 1)
        self.assertEqual(WorkspaceMember.objects.get(pk=old_id).role, "MEMBER")

    def test_inherited_target_flags_explain_that_explicit_revoke_does_not_remove_access(self):
        assignment = WorkspaceMember.objects.create(workspace=self.workspace, user=self.owner, role="MEMBER")
        self.login()
        row = self.rows(self.client.get(self.url()))[str(self.memberships["owner"].id)]
        self.assertTrue(row["capabilities"]["has_inherited_access"])
        self.assertTrue(row["capabilities"]["can_revoke"])
        self.assertFalse(row["is_assignable"])
        self.assertEqual(self.client.delete(self.url(membership_id=assignment.id)).status_code, 204)
        roster = self.client.get(self.url())
        self.assertTrue(roster.data["capabilities"]["can_add"])
        self.assertTrue(roster.data["capabilities"]["has_inherited_access"])

    def test_no_new_last_workspace_admin_rule_is_invented(self):
        self.login()
        self.assertEqual(WorkspaceMember.objects.filter(workspace=self.workspace, is_active=True, role="ADMIN").count(), 1)
        self.assertEqual(self.client.delete(self.url(membership_id=self.assignments["manager"].id)).status_code, 204)
        self.assertEqual(WorkspaceMember.objects.filter(workspace=self.workspace, is_active=True, role="ADMIN").count(), 0)
        self.assertTrue(self.client.get(self.url()).data["capabilities"]["has_inherited_access"])

    def test_read_capabilities_are_not_accepted_as_client_controlled_write_fields(self):
        self.login()
        response = self.client.post(self.url(), {
            "target_profile_membership_id": str(self.memberships["target"].id),
            "role": "MEMBER", "capabilities": {"can_add": True},
        }, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.data), {"capabilities"})
        self.assertFalse(WorkspaceMember.objects.filter(workspace=self.workspace, user=self.users["target"]).exists())

    def test_roster_and_candidates_serialize_without_n_plus_one_queries(self):
        context = self.context()
        capabilities = workspace_member_management_capabilities(context)
        roster = workspace_members_visible_to_managers(context).order_by("joined_at", "id")
        with self.assertNumQueries(1):
            members = list(roster)
        with self.assertNumQueries(0):
            data = WorkspaceMemberReadSerializer(members, many=True, context={"workspace_member_capabilities": capabilities}).data
            self.assertTrue(all(row["capabilities"]["can_update"] for row in data))
        queryset = workspace_member_candidates_visible_to_managers(context).order_by("joined_at", "id")
        with self.assertNumQueries(1):
            candidates = list(queryset)
        with self.assertNumQueries(0):
            self.assertEqual(len(WorkspaceMemberCandidateReadSerializer(candidates, many=True).data), 4)

    def test_grant_role_update_task_assignment_and_revoke_preserve_work_history(self):
        task = Task.objects.create(
            workspace=self.workspace, created_by=self.owner,
            title="Synthetic access execution",
        )
        task_kwargs = {"profile_id": self.profile.id, "workspace_id": self.workspace.id, "task_id": task.id}
        assign_url = reverse("tasks:task-assign", kwargs=task_kwargs)
        detail_url = reverse("tasks:task-detail", kwargs=task_kwargs)
        start_url = reverse("tasks:task-start", kwargs=task_kwargs)
        deliverables_url = reverse("tasks:task-deliverable-list", kwargs=task_kwargs)
        self.login()
        grant = self.add(role="VIEWER")
        self.assertEqual(grant.status_code, 201)
        assignment_url = self.url(membership_id=grant.data["id"])
        self.assertFalse(self.rows(self.client.get(self.url()))[str(self.memberships["target"].id)]["is_assignable"])
        payload = {"target_profile_membership_id": str(self.memberships["target"].id)}
        self.assertEqual(self.client.post(assign_url, payload, format="json").status_code, 400)
        self.assertEqual(self.client.patch(assignment_url, {"role": "MEMBER"}, format="json").status_code, 200)
        self.assertTrue(self.rows(self.client.get(self.url()))[str(self.memberships["target"].id)]["is_assignable"])
        self.assertEqual(self.client.post(assign_url, payload, format="json").status_code, 200)
        self.login("target")
        self.assertEqual(self.client.post(start_url, {}, format="json").status_code, 200)
        self.login()
        self.assertEqual(self.client.delete(assignment_url).status_code, 204)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.WORKING)
        self.assertTrue(TaskAssignment.objects.get(task=task, user=self.users["target"]).is_active)
        self.login("target")
        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.assertEqual(self.client.post(deliverables_url, {"file_url": "https://example.test/synthetic"}, format="json").status_code, 404)
        self.login()
        self.assertEqual(self.add(role="MEMBER").status_code, 200)
        self.login("target")
        self.assertEqual(self.client.post(deliverables_url, {"file_url": "https://example.test/synthetic"}, format="json").status_code, 201)
        self.assertEqual(Deliverable.objects.filter(task=task).count(), 1)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.REVIEW)
