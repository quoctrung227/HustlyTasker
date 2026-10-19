from uuid import uuid4
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog

from .access import (
    resolve_profile_access_context,
    resolve_workspace_access_context,
    workspace_members_visible_to_managers,
)
from .models import ProfileMembership, Workspace, WorkspaceMember
from .permissions import CanManageWorkspaceMembers
from .services import create_profile_with_owner


User = get_user_model()


class WorkspaceWriteApiTests(APITestCase):
    workspace_fields = {
        "id",
        "profile_id",
        "name",
        "description",
        "created_at",
        "updated_at",
    }
    workspace_member_fields = {
        "id",
        "profile_membership_id",
        "role",
        "joined_at",
        "updated_at",
    }

    @classmethod
    def setUpTestData(cls):
        cls.owner = cls._create_user("owner")
        cls.profile_admin = cls._create_user("profile-admin")
        cls.workspace_admin = cls._create_user("workspace-admin")
        cls.editor = cls._create_user("editor")
        cls.viewer = cls._create_user("viewer")
        cls.target = cls._create_user("target")
        cls.second_target = cls._create_user("second-target")
        cls.existing_member = cls._create_user("existing-member")
        cls.inactive_member = cls._create_user("inactive-membership")
        cls.inactive_user = cls._create_user(
            "inactive-user",
            is_active=False,
        )
        cls.other_owner = cls._create_user("other-owner")
        cls.other_target = cls._create_user("other-target")
        cls.outsider = cls._create_user("outsider")

        cls.profile = create_profile_with_owner(
            name="Primary Profile",
            owner=cls.owner,
        )
        cls.owner_profile_membership = ProfileMembership.objects.get(
            profile=cls.profile,
            user=cls.owner,
        )
        cls.profile_admin_membership = cls._create_profile_membership(
            cls.profile_admin,
            role=ProfileMembership.Role.ADMIN,
        )
        cls.workspace_admin_profile_membership = (
            cls._create_profile_membership(cls.workspace_admin)
        )
        cls.editor_profile_membership = cls._create_profile_membership(
            cls.editor
        )
        cls.viewer_profile_membership = cls._create_profile_membership(
            cls.viewer
        )
        cls.target_profile_membership = cls._create_profile_membership(
            cls.target
        )
        cls.second_target_profile_membership = (
            cls._create_profile_membership(cls.second_target)
        )
        cls.existing_profile_membership = cls._create_profile_membership(
            cls.existing_member
        )
        cls.inactive_profile_membership = cls._create_profile_membership(
            cls.inactive_member,
            is_active=False,
        )
        cls.inactive_user_profile_membership = (
            cls._create_profile_membership(cls.inactive_user)
        )

        cls.workspace = Workspace.objects.create(
            profile=cls.profile,
            owner=cls.owner,
            name="Primary Workspace",
            description="Original description",
        )
        cls.sibling_workspace = Workspace.objects.create(
            profile=cls.profile,
            owner=cls.owner,
            name="Sibling Workspace",
            description="Sibling description",
        )
        cls.workspace_admin_assignment = WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.workspace_admin,
            role=WorkspaceMember.Role.ADMIN,
        )
        cls.editor_assignment = WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.editor,
            role=WorkspaceMember.Role.MEMBER,
        )
        cls.viewer_assignment = WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.viewer,
            role=WorkspaceMember.Role.VIEWER,
        )
        cls.existing_assignment = WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.existing_member,
            role=WorkspaceMember.Role.VIEWER,
        )
        cls.sibling_assignment = WorkspaceMember.objects.create(
            workspace=cls.sibling_workspace,
            user=cls.target,
            role=WorkspaceMember.Role.VIEWER,
        )

        cls.other_profile = create_profile_with_owner(
            name="Other Profile",
            owner=cls.other_owner,
        )
        cls.other_target_profile_membership = ProfileMembership.objects.create(
            profile=cls.other_profile,
            user=cls.other_target,
            role=ProfileMembership.Role.MEMBER,
        )
        cls.other_workspace = Workspace.objects.create(
            profile=cls.other_profile,
            owner=cls.other_owner,
            name="Other Workspace",
            description="Other tenant data",
        )
        cls.other_assignment = WorkspaceMember.objects.create(
            workspace=cls.other_workspace,
            user=cls.other_target,
            role=WorkspaceMember.Role.VIEWER,
        )

    @classmethod
    def _create_user(cls, suffix, **extra_fields):
        return User.objects.create_user(
            email=f"write-api-{suffix}@example.test",
            username=f"write-api-{suffix}",
            password=None,
            **extra_fields,
        )

    @classmethod
    def _create_profile_membership(
        cls,
        user,
        *,
        role=ProfileMembership.Role.MEMBER,
        is_active=True,
    ):
        return ProfileMembership.objects.create(
            profile=cls.profile,
            user=user,
            role=role,
            is_active=is_active,
        )

    def setUp(self):
        self.client = APIClient()

    def workspace_list_url(self, profile_id=None):
        return reverse(
            "workspace:workspace-list",
            kwargs={"profile_id": profile_id or self.profile.id},
        )

    def workspace_detail_url(self, workspace_id=None, profile_id=None):
        return reverse(
            "workspace:workspace-detail",
            kwargs={
                "profile_id": profile_id or self.profile.id,
                "workspace_id": workspace_id or self.workspace.id,
            },
        )

    def workspace_member_list_url(
        self,
        *,
        profile_id=None,
        workspace_id=None,
    ):
        return reverse(
            "workspace:workspace-member-list",
            kwargs={
                "profile_id": profile_id or self.profile.id,
                "workspace_id": workspace_id or self.workspace.id,
            },
        )

    def workspace_member_detail_url(
        self,
        membership_id=None,
        *,
        profile_id=None,
        workspace_id=None,
    ):
        return reverse(
            "workspace:workspace-member-detail",
            kwargs={
                "profile_id": profile_id or self.profile.id,
                "workspace_id": workspace_id or self.workspace.id,
                "membership_id": (
                    membership_id or self.existing_assignment.id
                ),
            },
        )

    def assert_workspace_response(self, response, *, status_code):
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(set(response.data), self.workspace_fields)
        self.assertNotIn("owner", response.data)
        self.assertNotIn("owner_id", response.data)

    def assert_workspace_member_response(self, response, *, status_code):
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(set(response.data), self.workspace_member_fields)
        self.assertNotIn("user", response.data)
        self.assertNotIn("user_id", response.data)
        self.assertNotIn("email", response.data)

    def test_profile_owner_and_admin_can_create_workspace(self):
        cases = (
            (self.owner, "Owner-created Workspace"),
            (self.profile_admin, "Admin-created Workspace"),
        )

        for actor, name in cases:
            with self.subTest(actor=actor.username):
                client = APIClient()
                client.force_login(actor)
                response = client.post(
                    self.workspace_list_url(),
                    {"name": name, "description": "Created through API"},
                    format="json",
                )

                self.assert_workspace_response(
                    response,
                    status_code=status.HTTP_201_CREATED,
                )
                workspace = Workspace.objects.get(id=response.data["id"])
                self.assertEqual(workspace.profile, self.profile)
                self.assertEqual(workspace.owner, actor)
                self.assertEqual(workspace.name, name)

    def test_profile_member_cannot_create_workspace(self):
        self.client.force_login(self.workspace_admin)
        before_count = Workspace.objects.count()

        response = self.client.post(
            self.workspace_list_url(),
            {"name": "Forbidden Workspace"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Workspace.objects.count(), before_count)

    def test_workspace_create_rejects_server_owned_and_unknown_fields(self):
        self.client.force_login(self.owner)
        before_count = Workspace.objects.count()

        response = self.client.post(
            self.workspace_list_url(),
            {
                "name": "Mass-assignment attempt",
                "profile_id": str(self.other_profile.id),
                "owner_id": str(self.outsider.id),
                "unexpected": "value",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSetEqual(
            set(response.data),
            {"profile_id", "owner_id", "unexpected"},
        )
        self.assertEqual(Workspace.objects.count(), before_count)

    def test_workspace_create_requires_a_non_blank_name(self):
        self.client.force_login(self.owner)
        before_count = Workspace.objects.count()

        for payload in ({}, {"name": "   "}):
            with self.subTest(payload=payload):
                response = self.client.post(
                    self.workspace_list_url(),
                    payload,
                    format="json",
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertEqual(set(response.data), {"name"})

        self.assertEqual(Workspace.objects.count(), before_count)

    def test_workspace_patch_allows_profile_managers_and_workspace_admin(self):
        cases = (
            (self.owner, "Owner update"),
            (self.profile_admin, "Profile Admin update"),
            (self.workspace_admin, "Workspace Admin update"),
        )

        for actor, description in cases:
            with self.subTest(actor=actor.username):
                client = APIClient()
                client.force_login(actor)
                response = client.patch(
                    self.workspace_detail_url(),
                    {"description": description},
                    format="json",
                )

                self.assert_workspace_response(
                    response,
                    status_code=status.HTTP_200_OK,
                )
                self.workspace.refresh_from_db()
                self.assertEqual(self.workspace.description, description)

    def test_workspace_editor_and_viewer_cannot_patch_metadata(self):
        for actor in (self.editor, self.viewer):
            with self.subTest(actor=actor.username):
                client = APIClient()
                client.force_login(actor)
                response = client.patch(
                    self.workspace_detail_url(),
                    {"name": "Forbidden update"},
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                )

        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.name, "Primary Workspace")

    def test_workspace_patch_rejects_reparent_owner_and_unknown_fields(self):
        self.client.force_login(self.owner)

        response = self.client.patch(
            self.workspace_detail_url(),
            {
                "profile_id": str(self.other_profile.id),
                "owner": str(self.outsider.id),
                "not_a_field": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSetEqual(
            set(response.data),
            {"profile_id", "owner", "not_a_field"},
        )
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.profile, self.profile)
        self.assertEqual(self.workspace.owner, self.owner)

    def test_workspace_member_list_is_scoped_and_minimal(self):
        expected_assignments = {
            str(self.workspace_admin_assignment.id): (
                self.workspace_admin_profile_membership.id
            ),
            str(self.editor_assignment.id): self.editor_profile_membership.id,
            str(self.viewer_assignment.id): self.viewer_profile_membership.id,
            str(self.existing_assignment.id): self.existing_profile_membership.id,
        }
        for actor in (
            self.owner,
            self.profile_admin,
            self.workspace_admin,
        ):
            with self.subTest(actor=actor.username):
                client = APIClient()
                client.force_login(actor)
                response = client.get(
                    self.workspace_member_list_url(),
                    {"page_size": 100},
                )

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    set(response.data),
                    {"count", "next", "previous", "results"},
                )
                self.assertEqual(
                    response.data["count"],
                    len(expected_assignments),
                )
                self.assertSetEqual(
                    {item["id"] for item in response.data["results"]},
                    set(expected_assignments),
                )
                for item in response.data["results"]:
                    self.assertEqual(set(item), self.workspace_member_fields)
                    self.assertEqual(
                        item["profile_membership_id"],
                        str(expected_assignments[item["id"]]),
                    )
                    self.assertNotIn("user", item)
                    self.assertNotIn("user_id", item)
                    self.assertNotIn("email", item)

                serialized = str(response.data)
                self.assertNotIn(self.other_target.email, serialized)
                self.assertNotIn(
                    str(self.other_assignment.id),
                    serialized,
                )

    def test_editor_and_viewer_cannot_manage_workspace_roster(self):
        for actor in (self.editor, self.viewer):
            with self.subTest(actor=actor.username):
                client = APIClient()
                client.force_login(actor)
                responses = (
                    client.get(self.workspace_member_list_url()),
                    client.post(
                        self.workspace_member_list_url(),
                        {
                            "target_profile_membership_id": str(
                                self.target_profile_membership.id
                            ),
                            "role": WorkspaceMember.Role.MEMBER,
                        },
                        format="json",
                    ),
                    client.patch(
                        self.workspace_member_detail_url(),
                        {"role": WorkspaceMember.Role.MEMBER},
                        format="json",
                    ),
                )
                for response in responses:
                    self.assertEqual(
                        response.status_code,
                        status.HTTP_403_FORBIDDEN,
                    )

        self.assertFalse(
            WorkspaceMember.objects.filter(
                workspace=self.workspace,
                user=self.target,
            ).exists()
        )

    def test_roster_fails_closed_when_manager_role_changes_after_permission(self):
        self.client.force_login(self.workspace_admin)
        original_permission = CanManageWorkspaceMembers.has_permission

        def demote_after_permission(permission, request, view):
            allowed = original_permission(permission, request, view)
            if allowed:
                WorkspaceMember.objects.filter(
                    id=self.workspace_admin_assignment.id
                ).update(role=WorkspaceMember.Role.MEMBER)
            return allowed

        with patch.object(
            CanManageWorkspaceMembers,
            "has_permission",
            demote_after_permission,
        ):
            response = self.client.get(self.workspace_member_list_url())

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {"detail": "Not found."})

    def test_roster_lazy_queryset_rechecks_actor_scope_at_evaluation(self):
        profile_context = resolve_profile_access_context(
            self.workspace_admin,
            self.profile.id,
        )
        workspace_context = resolve_workspace_access_context(
            profile_context,
            self.workspace.id,
        )
        queryset = workspace_members_visible_to_managers(workspace_context)

        WorkspaceMember.objects.filter(
            id=self.workspace_admin_assignment.id
        ).update(role=WorkspaceMember.Role.MEMBER)

        self.assertEqual(list(queryset), [])

    def test_roster_excludes_legacy_workspace_owner_assignments(self):
        legacy_user = self._create_user("legacy-workspace-owner")
        ProfileMembership.objects.create(
            profile=self.profile,
            user=legacy_user,
            role=ProfileMembership.Role.MEMBER,
        )
        legacy_assignment = WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=legacy_user,
            role=WorkspaceMember.Role.OWNER,
        )
        self.client.force_login(self.owner)

        response = self.client.get(
            self.workspace_member_list_url(),
            {"page_size": 100},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn(
            str(legacy_assignment.id),
            {item["id"] for item in response.data["results"]},
        )

    def test_profile_owner_can_add_active_same_profile_member(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            self.workspace_member_list_url(),
            {
                "target_profile_membership_id": str(
                    self.target_profile_membership.id
                ),
                "role": WorkspaceMember.Role.ADMIN,
            },
            format="json",
        )

        self.assert_workspace_member_response(
            response,
            status_code=status.HTTP_201_CREATED,
        )
        self.assertEqual(
            response.data["profile_membership_id"],
            str(self.target_profile_membership.id),
        )
        membership = WorkspaceMember.objects.get(id=response.data["id"])
        self.assertEqual(membership.workspace, self.workspace)
        self.assertEqual(membership.user, self.target)
        self.assertEqual(membership.role, WorkspaceMember.Role.ADMIN)

    def test_workspace_admin_role_ceiling_on_direct_add(self):
        self.client.force_login(self.workspace_admin)

        allowed_response = self.client.post(
            self.workspace_member_list_url(),
            {
                "target_profile_membership_id": str(
                    self.target_profile_membership.id
                ),
                "role": WorkspaceMember.Role.MEMBER,
            },
            format="json",
        )
        denied_response = self.client.post(
            self.workspace_member_list_url(),
            {
                "target_profile_membership_id": str(
                    self.second_target_profile_membership.id
                ),
                "role": WorkspaceMember.Role.ADMIN,
            },
            format="json",
        )

        self.assert_workspace_member_response(
            allowed_response,
            status_code=status.HTTP_201_CREATED,
        )
        self.assertEqual(
            denied_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertFalse(
            WorkspaceMember.objects.filter(
                workspace=self.workspace,
                user=self.second_target,
            ).exists()
        )

    def test_direct_add_duplicate_returns_conflict_without_second_write(self):
        self.client.force_login(self.owner)
        before_audits = AuditLog.objects.filter(
            action="workspace.membership.created",
            entity_id=self.existing_assignment.id,
        ).count()

        response = self.client.post(
            self.workspace_member_list_url(),
            {
                "target_profile_membership_id": str(
                    self.existing_profile_membership.id
                ),
                "role": WorkspaceMember.Role.MEMBER,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            WorkspaceMember.objects.filter(
                workspace=self.workspace,
                user=self.existing_member,
            ).count(),
            1,
        )
        self.assertEqual(
            AuditLog.objects.filter(
                action="workspace.membership.created",
                entity_id=self.existing_assignment.id,
            ).count(),
            before_audits,
        )

    def test_invalid_body_membership_references_share_generic_400(self):
        self.client.force_login(self.owner)
        before_count = WorkspaceMember.objects.count()
        invalid_references = (
            uuid4(),
            self.inactive_profile_membership.id,
            self.inactive_user_profile_membership.id,
            self.other_target_profile_membership.id,
        )
        response_bodies = []

        for target_id in invalid_references:
            with self.subTest(target_id=target_id):
                response = self.client.post(
                    self.workspace_member_list_url(),
                    {
                        "target_profile_membership_id": str(target_id),
                        "role": WorkspaceMember.Role.MEMBER,
                    },
                    format="json",
                )

                self.assertEqual(
                    response.status_code,
                    status.HTTP_400_BAD_REQUEST,
                )
                self.assertEqual(
                    set(response.data),
                    {"target_profile_membership_id"},
                )
                response_bodies.append(response.data)

        self.assertTrue(
            all(body == response_bodies[0] for body in response_bodies[1:])
        )
        self.assertEqual(WorkspaceMember.objects.count(), before_count)

    def test_member_create_rejects_user_and_server_owned_fields(self):
        self.client.force_login(self.owner)

        response = self.client.post(
            self.workspace_member_list_url(),
            {
                "target_profile_membership_id": str(
                    self.target_profile_membership.id
                ),
                "role": WorkspaceMember.Role.MEMBER,
                "user_id": str(self.outsider.id),
                "workspace_id": str(self.other_workspace.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSetEqual(set(response.data), {"user_id", "workspace_id"})
        self.assertFalse(
            WorkspaceMember.objects.filter(
                workspace=self.workspace,
                user=self.target,
            ).exists()
        )

    def test_legacy_workspace_owner_role_is_not_accepted_by_the_api(self):
        self.client.force_login(self.owner)

        create_response = self.client.post(
            self.workspace_member_list_url(),
            {
                "target_profile_membership_id": str(
                    self.target_profile_membership.id
                ),
                "role": WorkspaceMember.Role.OWNER,
            },
            format="json",
        )
        update_response = self.client.patch(
            self.workspace_member_detail_url(),
            {"role": WorkspaceMember.Role.OWNER},
            format="json",
        )

        for response in (create_response, update_response):
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(set(response.data), {"role"})
        self.assertFalse(
            WorkspaceMember.objects.filter(
                workspace=self.workspace,
                user=self.target,
            ).exists()
        )
        self.existing_assignment.refresh_from_db()
        self.assertEqual(
            self.existing_assignment.role,
            WorkspaceMember.Role.VIEWER,
        )

    def test_profile_manager_can_update_workspace_member_role(self):
        for actor, role in (
            (self.owner, WorkspaceMember.Role.ADMIN),
            (self.profile_admin, WorkspaceMember.Role.MEMBER),
        ):
            with self.subTest(actor=actor.username, role=role):
                client = APIClient()
                client.force_login(actor)
                response = client.patch(
                    self.workspace_member_detail_url(),
                    {"role": role},
                    format="json",
                )

                self.assert_workspace_member_response(
                    response,
                    status_code=status.HTTP_200_OK,
                )
                self.existing_assignment.refresh_from_db()
                self.assertEqual(self.existing_assignment.role, role)

    def test_workspace_admin_role_ceiling_on_member_update(self):
        self.client.force_login(self.workspace_admin)

        allowed_response = self.client.patch(
            self.workspace_member_detail_url(),
            {"role": WorkspaceMember.Role.MEMBER},
            format="json",
        )
        denied_response = self.client.patch(
            self.workspace_member_detail_url(),
            {"role": WorkspaceMember.Role.ADMIN},
            format="json",
        )

        self.assert_workspace_member_response(
            allowed_response,
            status_code=status.HTTP_200_OK,
        )
        self.assertEqual(
            denied_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.existing_assignment.refresh_from_db()
        self.assertEqual(
            self.existing_assignment.role,
            WorkspaceMember.Role.MEMBER,
        )

    def test_member_patch_accepts_only_role(self):
        self.client.force_login(self.owner)

        response = self.client.patch(
            self.workspace_member_detail_url(),
            {
                "role": WorkspaceMember.Role.MEMBER,
                "target_profile_membership_id": str(
                    self.target_profile_membership.id
                ),
                "user_id": str(self.target.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertSetEqual(
            set(response.data),
            {"target_profile_membership_id", "user_id"},
        )
        self.existing_assignment.refresh_from_db()
        self.assertEqual(
            self.existing_assignment.role,
            WorkspaceMember.Role.VIEWER,
        )

    def test_nested_workspace_and_membership_idor_return_generic_404(self):
        self.client.force_login(self.owner)
        wrong_workspace = self.client.get(
            self.workspace_member_list_url(
                workspace_id=self.other_workspace.id,
            )
        )
        sibling_member = self.client.patch(
            self.workspace_member_detail_url(
                self.sibling_assignment.id,
            ),
            {"role": WorkspaceMember.Role.MEMBER},
            format="json",
        )
        unknown_member = self.client.patch(
            self.workspace_member_detail_url(uuid4()),
            {"role": WorkspaceMember.Role.MEMBER},
            format="json",
        )

        for response in (wrong_workspace, sibling_member, unknown_member):
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response.data, {"detail": "Not found."})

    def test_anonymous_access_is_denied_for_write_and_roster_endpoints(self):
        requests = (
            (
                "post",
                self.workspace_list_url(),
                {"name": "Anonymous Workspace"},
            ),
            (
                "patch",
                self.workspace_detail_url(),
                {"name": "Anonymous update"},
            ),
            ("get", self.workspace_member_list_url(), None),
            (
                "post",
                self.workspace_member_list_url(),
                {
                    "target_profile_membership_id": str(
                        self.target_profile_membership.id
                    ),
                    "role": WorkspaceMember.Role.MEMBER,
                },
            ),
            (
                "patch",
                self.workspace_member_detail_url(),
                {"role": WorkspaceMember.Role.MEMBER},
            ),
        )

        for method, url, payload in requests:
            with self.subTest(method=method, url=url):
                request = getattr(self.client, method)
                if payload is None:
                    response = request(url)
                else:
                    response = request(url, payload, format="json")
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_session_write_endpoints_enforce_csrf(self):
        requests = (
            (
                "post",
                self.workspace_list_url(),
                {"name": "CSRF Workspace"},
            ),
            (
                "patch",
                self.workspace_detail_url(),
                {"description": "CSRF update"},
            ),
            (
                "post",
                self.workspace_member_list_url(),
                {
                    "target_profile_membership_id": str(
                        self.target_profile_membership.id
                    ),
                    "role": WorkspaceMember.Role.MEMBER,
                },
            ),
            (
                "patch",
                self.workspace_member_detail_url(),
                {"role": WorkspaceMember.Role.MEMBER},
            ),
        )

        for method, url, payload in requests:
            with self.subTest(method=method, url=url):
                client = APIClient(enforce_csrf_checks=True)
                client.force_login(self.owner)
                response = getattr(client, method)(url, payload, format="json")
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_valid_csrf_token_allows_workspace_create(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.owner)
        csrf_response = client.get(reverse("accounts:csrf"))

        response = client.post(
            self.workspace_list_url(),
            {"name": "CSRF-authorized Workspace"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
        )

        self.assertEqual(csrf_response.status_code, status.HTTP_200_OK)
        self.assert_workspace_response(
            response,
            status_code=status.HTTP_201_CREATED,
        )

    def test_archive_and_membership_delete_remain_disabled(self):
        self.client.force_login(self.owner)
        workspace_count = Workspace.objects.count()
        member_count = WorkspaceMember.objects.count()

        workspace_response = self.client.delete(self.workspace_detail_url())
        membership_response = self.client.delete(
            self.workspace_member_detail_url()
        )

        self.assertEqual(
            workspace_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            membership_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(Workspace.objects.count(), workspace_count)
        self.assertEqual(WorkspaceMember.objects.count(), member_count)
