from uuid import uuid4
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog

from .models import Profile, ProfileMembership, Workspace, WorkspaceMember
from .permissions import HasProfileAccess, HasWorkspaceReadAccess
from .services import create_profile_with_owner


User = get_user_model()


class ProfileWorkspaceReadApiTests(APITestCase):
    profile_fields = {
        "id",
        "name",
        "created_at",
        "updated_at",
    }
    workspace_fields = {
        "id",
        "profile_id",
        "name",
        "description",
        "created_at",
        "updated_at",
    }

    @classmethod
    def setUpTestData(cls):
        cls.owner = cls._create_user("owner")
        cls.admin = cls._create_user("admin")
        cls.member = cls._create_user("member")
        cls.other_owner = cls._create_user("other-owner")
        cls.hidden_owner = cls._create_user("hidden-owner")
        cls.outsider = cls._create_user("outsider")

        cls.profile = create_profile_with_owner(
            name="Primary Profile",
            owner=cls.owner,
        )
        cls.admin_membership = ProfileMembership.objects.create(
            profile=cls.profile,
            user=cls.admin,
            role=ProfileMembership.Role.ADMIN,
        )
        cls.member_membership = ProfileMembership.objects.create(
            profile=cls.profile,
            user=cls.member,
            role=ProfileMembership.Role.MEMBER,
        )

        cls.other_profile = create_profile_with_owner(
            name="Other Visible Profile",
            owner=cls.other_owner,
        )
        cls.other_member_membership = ProfileMembership.objects.create(
            profile=cls.other_profile,
            user=cls.member,
            role=ProfileMembership.Role.MEMBER,
        )

        cls.hidden_profile = create_profile_with_owner(
            name="Hidden Profile",
            owner=cls.hidden_owner,
        )

        cls.admin_workspace = cls._create_workspace(
            "Admin Workspace",
            profile=cls.profile,
            owner=cls.owner,
        )
        cls.editor_workspace = cls._create_workspace(
            "Editor Workspace",
            profile=cls.profile,
            owner=cls.owner,
        )
        cls.viewer_workspace = cls._create_workspace(
            "Viewer Workspace",
            profile=cls.profile,
            owner=cls.owner,
        )
        cls.legacy_owner_workspace = cls._create_workspace(
            "Legacy Owner Workspace",
            profile=cls.profile,
            owner=cls.owner,
        )
        cls.unassigned_workspace = cls._create_workspace(
            "Unassigned Workspace",
            profile=cls.profile,
            owner=cls.owner,
        )

        cls.admin_workspace_membership = WorkspaceMember.objects.create(
            workspace=cls.admin_workspace,
            user=cls.member,
            role=WorkspaceMember.Role.ADMIN,
        )
        cls.editor_workspace_membership = WorkspaceMember.objects.create(
            workspace=cls.editor_workspace,
            user=cls.member,
            role=WorkspaceMember.Role.MEMBER,
        )
        cls.viewer_workspace_membership = WorkspaceMember.objects.create(
            workspace=cls.viewer_workspace,
            user=cls.member,
            role=WorkspaceMember.Role.VIEWER,
        )
        cls.legacy_owner_membership = WorkspaceMember.objects.create(
            workspace=cls.legacy_owner_workspace,
            user=cls.member,
            role=WorkspaceMember.Role.OWNER,
        )

        cls.other_workspace = cls._create_workspace(
            "Other Profile Workspace",
            profile=cls.other_profile,
            owner=cls.other_owner,
        )
        cls.other_workspace_membership = WorkspaceMember.objects.create(
            workspace=cls.other_workspace,
            user=cls.member,
            role=WorkspaceMember.Role.VIEWER,
        )
        cls.hidden_workspace = cls._create_workspace(
            "Hidden Workspace",
            profile=cls.hidden_profile,
            owner=cls.hidden_owner,
        )

        cls.unmapped_workspace = Workspace(
            name="Unmapped Legacy Workspace",
            owner=cls.owner,
        )
        Workspace.objects.bulk_create((cls.unmapped_workspace,))

    @classmethod
    def _create_user(cls, suffix, **extra_fields):
        return User.objects.create_user(
            email=f"api-{suffix}@example.test",
            username=f"api-{suffix}",
            password=None,
            **extra_fields,
        )

    @classmethod
    def _create_workspace(cls, name, *, profile, owner):
        return Workspace.objects.create(
            name=name,
            description=f"Description for {name}",
            profile=profile,
            owner=owner,
        )

    def setUp(self):
        self.client = APIClient()

    def profile_list_url(self):
        return reverse("workspace:profile-list")

    def profile_detail_url(self, profile_id):
        return reverse(
            "workspace:profile-detail",
            kwargs={"profile_id": profile_id},
        )

    def workspace_list_url(self, profile_id):
        return reverse(
            "workspace:workspace-list",
            kwargs={"profile_id": profile_id},
        )

    def workspace_detail_url(self, profile_id, workspace_id):
        return reverse(
            "workspace:workspace-detail",
            kwargs={
                "profile_id": profile_id,
                "workspace_id": workspace_id,
            },
        )

    def assert_page(self, response, *, count=None):
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.data),
            {"count", "next", "previous", "results"},
        )
        if count is not None:
            self.assertEqual(response.data["count"], count)

    def response_ids(self, response):
        return {item["id"] for item in response.data["results"]}

    def test_all_read_endpoints_require_session_authentication(self):
        urls = (
            self.profile_list_url(),
            self.profile_detail_url(self.profile.id),
            self.workspace_list_url(self.profile.id),
            self.workspace_detail_url(
                self.profile.id,
                self.viewer_workspace.id,
            ),
        )

        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_profile_list_is_paginated_and_scoped_for_one_or_many_profiles(self):
        cases = (
            (self.admin, {str(self.profile.id)}),
            (
                self.member,
                {str(self.profile.id), str(self.other_profile.id)},
            ),
            (self.outsider, set()),
        )

        for actor, expected_ids in cases:
            with self.subTest(actor=actor.username):
                client = APIClient()
                client.force_login(actor)
                response = client.get(self.profile_list_url())

                self.assert_page(response, count=len(expected_ids))
                self.assertSetEqual(self.response_ids(response), expected_ids)

    def test_profile_list_uses_stable_created_at_and_id_ordering(self):
        self.client.force_login(self.member)

        response = self.client.get(self.profile_list_url())

        self.assert_page(response, count=2)
        expected_ids = list(
            Profile.objects.filter(
                id__in=(self.profile.id, self.other_profile.id)
            )
            .order_by("created_at", "id")
            .values_list("id", flat=True)
        )
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [str(profile_id) for profile_id in expected_ids],
        )

    def test_profile_detail_has_minimal_read_only_contract(self):
        self.client.force_login(self.member)

        response = self.client.get(self.profile_detail_url(self.profile.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), self.profile_fields)
        self.assertEqual(response.data["id"], str(self.profile.id))
        self.assertEqual(response.data["name"], self.profile.name)
        self.assertIsInstance(response.data["created_at"], str)
        self.assertIsInstance(response.data["updated_at"], str)

    def test_profile_detail_does_not_disclose_cross_tenant_or_unknown_ids(self):
        self.client.force_login(self.admin)

        hidden_response = self.client.get(
            self.profile_detail_url(self.hidden_profile.id)
        )
        unknown_response = self.client.get(self.profile_detail_url(uuid4()))
        malformed_response = self.client.get(
            "/api/v1/profiles/not-a-uuid/"
        )

        for response in (
            hidden_response,
            unknown_response,
            malformed_response,
        ):
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response["Content-Type"], "application/json")
            self.assertEqual(response.data, hidden_response.data)

    def test_profile_membership_deactivation_revokes_profile_and_workspace_reads(self):
        self.client.force_login(self.member)
        ProfileMembership.objects.filter(id=self.member_membership.id).update(
            is_active=False
        )

        profile_list = self.client.get(self.profile_list_url())
        profile_detail = self.client.get(
            self.profile_detail_url(self.profile.id)
        )
        workspace_list = self.client.get(
            self.workspace_list_url(self.profile.id)
        )
        workspace_detail = self.client.get(
            self.workspace_detail_url(
                self.profile.id,
                self.viewer_workspace.id,
            )
        )

        self.assert_page(profile_list, count=1)
        self.assertSetEqual(
            self.response_ids(profile_list),
            {str(self.other_profile.id)},
        )
        for response in (profile_detail, workspace_list, workspace_detail):
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_stale_context_during_workspace_query_fails_with_generic_404(self):
        self.client.force_login(self.member)
        original_profile_permission = HasProfileAccess.has_permission

        def revoke_after_profile_permission(permission, request, view):
            allowed = original_profile_permission(permission, request, view)
            if allowed:
                ProfileMembership.objects.filter(
                    id=self.member_membership.id
                ).update(is_active=False)
            return allowed

        with patch.object(
            HasProfileAccess,
            "has_permission",
            revoke_after_profile_permission,
        ):
            list_response = self.client.get(
                self.workspace_list_url(self.profile.id)
            )

        ProfileMembership.objects.filter(
            id=self.member_membership.id
        ).update(is_active=True)
        original_workspace_permission = HasWorkspaceReadAccess.has_permission

        def revoke_after_workspace_permission(permission, request, view):
            allowed = original_workspace_permission(permission, request, view)
            if allowed:
                ProfileMembership.objects.filter(
                    id=self.member_membership.id
                ).update(is_active=False)
            return allowed

        with patch.object(
            HasWorkspaceReadAccess,
            "has_permission",
            revoke_after_workspace_permission,
        ):
            detail_response = self.client.get(
                self.workspace_detail_url(
                    self.profile.id,
                    self.viewer_workspace.id,
                )
            )

        for response in (list_response, detail_response):
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response["Content-Type"], "application/json")
            self.assertEqual(response.data, {"detail": "Not found."})

    def test_profile_owner_and_admin_inherit_all_mapped_workspace_reads(self):
        expected_ids = {
            str(self.admin_workspace.id),
            str(self.editor_workspace.id),
            str(self.viewer_workspace.id),
            str(self.legacy_owner_workspace.id),
            str(self.unassigned_workspace.id),
        }

        for actor in (self.owner, self.admin):
            with self.subTest(actor=actor.username):
                client = APIClient()
                client.force_login(actor)
                response = client.get(
                    self.workspace_list_url(self.profile.id),
                    {"page_size": 100},
                )

                self.assert_page(response, count=len(expected_ids))
                self.assertSetEqual(self.response_ids(response), expected_ids)
                detail_response = client.get(
                    self.workspace_detail_url(
                        self.profile.id,
                        self.unassigned_workspace.id,
                    )
                )
                self.assertEqual(
                    detail_response.status_code,
                    status.HTTP_200_OK,
                )

    def test_profile_member_sees_only_effective_workspace_roles(self):
        self.client.force_login(self.member)

        response = self.client.get(
            self.workspace_list_url(self.profile.id),
            {"page_size": 100},
        )

        expected_ids = {
            str(self.admin_workspace.id),
            str(self.editor_workspace.id),
            str(self.viewer_workspace.id),
        }
        self.assert_page(response, count=3)
        self.assertSetEqual(self.response_ids(response), expected_ids)

        for workspace in (
            self.admin_workspace,
            self.editor_workspace,
            self.viewer_workspace,
        ):
            with self.subTest(visible_workspace=workspace.name):
                detail_response = self.client.get(
                    self.workspace_detail_url(self.profile.id, workspace.id)
                )
                self.assertEqual(
                    detail_response.status_code,
                    status.HTTP_200_OK,
                )

        for workspace in (
            self.legacy_owner_workspace,
            self.unassigned_workspace,
        ):
            with self.subTest(hidden_workspace=workspace.name):
                detail_response = self.client.get(
                    self.workspace_detail_url(self.profile.id, workspace.id)
                )
                self.assertEqual(
                    detail_response.status_code,
                    status.HTTP_404_NOT_FOUND,
                )

    def test_workspace_viewer_receives_minimal_contract_without_owner_or_pii(self):
        self.client.force_login(self.member)

        response = self.client.get(
            self.workspace_detail_url(
                self.profile.id,
                self.viewer_workspace.id,
            )
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.data), self.workspace_fields)
        self.assertEqual(response.data["id"], str(self.viewer_workspace.id))
        self.assertEqual(response.data["profile_id"], str(self.profile.id))
        self.assertEqual(response.data["name"], self.viewer_workspace.name)
        self.assertEqual(
            response.data["description"],
            self.viewer_workspace.description,
        )
        self.assertNotIn("owner", response.data)
        self.assertNotIn("members", response.data)

    def test_workspace_membership_deletion_revokes_read_immediately(self):
        self.client.force_login(self.member)
        WorkspaceMember.objects.filter(
            id=self.viewer_workspace_membership.id
        ).delete()

        list_response = self.client.get(
            self.workspace_list_url(self.profile.id),
            {"page_size": 100},
        )
        detail_response = self.client.get(
            self.workspace_detail_url(
                self.profile.id,
                self.viewer_workspace.id,
            )
        )

        self.assert_page(list_response, count=2)
        self.assertNotIn(
            str(self.viewer_workspace.id),
            self.response_ids(list_response),
        )
        self.assertEqual(
            detail_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_inactive_user_cannot_use_an_established_session(self):
        self.client.force_login(self.member)
        User.objects.filter(id=self.member.id).update(is_active=False)

        urls = (
            self.profile_list_url(),
            self.profile_detail_url(self.profile.id),
            self.workspace_list_url(self.profile.id),
            self.workspace_detail_url(
                self.profile.id,
                self.viewer_workspace.id,
            ),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_nested_workspace_lookup_cannot_cross_profiles(self):
        self.client.force_login(self.member)

        correct_parent_response = self.client.get(
            self.workspace_detail_url(
                self.other_profile.id,
                self.other_workspace.id,
            )
        )
        wrong_parent_response = self.client.get(
            self.workspace_detail_url(
                self.profile.id,
                self.other_workspace.id,
            )
        )
        unknown_response = self.client.get(
            self.workspace_detail_url(self.profile.id, uuid4())
        )

        self.assertEqual(
            correct_parent_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            wrong_parent_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(wrong_parent_response.data, unknown_response.data)

    def test_sibling_workspace_idor_matches_unknown_and_malformed_errors(self):
        self.client.force_login(self.member)

        sibling_response = self.client.get(
            self.workspace_detail_url(
                self.profile.id,
                self.unassigned_workspace.id,
            )
        )
        unknown_response = self.client.get(
            self.workspace_detail_url(self.profile.id, uuid4())
        )
        malformed_response = self.client.get(
            f"/api/v1/profiles/{self.profile.id}/workspaces/not-a-uuid/"
        )

        for response in (
            sibling_response,
            unknown_response,
            malformed_response,
        ):
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response["Content-Type"], "application/json")
            self.assertEqual(response.data, sibling_response.data)

    def test_unmapped_workspace_is_never_listed_or_retrieved(self):
        self.client.force_login(self.owner)

        list_response = self.client.get(
            self.workspace_list_url(self.profile.id),
            {"page_size": 100},
        )
        detail_response = self.client.get(
            self.workspace_detail_url(
                self.profile.id,
                self.unmapped_workspace.id,
            )
        )

        self.assert_page(list_response, count=5)
        self.assertNotIn(
            str(self.unmapped_workspace.id),
            self.response_ids(list_response),
        )
        self.assertEqual(
            detail_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_transitional_workspace_owner_does_not_grant_profile_access(self):
        forged_owner_workspace = Workspace(
            name="Forged Transitional Owner",
            profile=self.profile,
            owner=self.outsider,
        )
        Workspace.objects.bulk_create((forged_owner_workspace,))
        self.client.force_login(self.outsider)

        profile_list = self.client.get(self.profile_list_url())
        profile_detail = self.client.get(
            self.profile_detail_url(self.profile.id)
        )
        workspace_detail = self.client.get(
            self.workspace_detail_url(
                self.profile.id,
                forged_owner_workspace.id,
            )
        )

        self.assert_page(profile_list, count=0)
        self.assertEqual(
            profile_detail.status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            workspace_detail.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_staff_and_superuser_flags_do_not_bypass_tenant_scope(self):
        operator = self._create_user(
            "platform-operator",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(operator)

        profile_list = self.client.get(self.profile_list_url())
        profile_detail = self.client.get(
            self.profile_detail_url(self.profile.id)
        )

        self.assert_page(profile_list, count=0)
        self.assertEqual(
            profile_detail.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_workspace_pagination_count_and_links_are_tenant_scoped(self):
        self.client.force_login(self.member)
        list_url = self.workspace_list_url(self.profile.id)

        first_page = self.client.get(
            list_url,
            {"page": 1, "page_size": 2},
        )
        second_page = self.client.get(
            list_url,
            {"page": 2, "page_size": 2},
        )

        self.assert_page(first_page, count=3)
        self.assert_page(second_page, count=3)
        self.assertEqual(len(first_page.data["results"]), 2)
        self.assertEqual(len(second_page.data["results"]), 1)
        self.assertIsNotNone(first_page.data["next"])
        self.assertIsNone(first_page.data["previous"])
        self.assertIsNone(second_page.data["next"])
        self.assertIsNotNone(second_page.data["previous"])

        paged_ids = self.response_ids(first_page) | self.response_ids(
            second_page
        )
        self.assertSetEqual(
            paged_ids,
            {
                str(self.admin_workspace.id),
                str(self.editor_workspace.id),
                str(self.viewer_workspace.id),
            },
        )

    def test_unsupported_unsafe_methods_do_not_write(self):
        self.client.force_login(self.owner)
        before_counts = {
            "profiles": Profile.objects.count(),
            "workspaces": Workspace.objects.count(),
            "workspace_members": WorkspaceMember.objects.count(),
            "audit_logs": AuditLog.objects.count(),
        }
        method_urls = (
            ("POST", self.profile_list_url()),
            ("PUT", self.profile_detail_url(self.profile.id)),
            ("PATCH", self.profile_detail_url(self.profile.id)),
            ("DELETE", self.profile_detail_url(self.profile.id)),
            (
                "PUT",
                self.workspace_detail_url(
                    self.profile.id,
                    self.unassigned_workspace.id,
                ),
            ),
            (
                "DELETE",
                self.workspace_detail_url(
                    self.profile.id,
                    self.unassigned_workspace.id,
                ),
            ),
        )

        for method, url in method_urls:
            with self.subTest(method=method, url=url):
                response = self.client.generic(
                    method,
                    url,
                    data="{}",
                    content_type="application/json",
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )

        self.assertEqual(Profile.objects.count(), before_counts["profiles"])
        self.assertEqual(
            Workspace.objects.count(),
            before_counts["workspaces"],
        )
        self.assertEqual(
            WorkspaceMember.objects.count(),
            before_counts["workspace_members"],
        )
        self.assertEqual(
            AuditLog.objects.count(),
            before_counts["audit_logs"],
        )

    def test_unsupported_unsafe_method_enforces_session_csrf_before_405(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.owner)

        denied_response = client.post(
            self.profile_list_url(),
            {},
            format="json",
        )
        csrf_response = client.get(reverse("accounts:csrf"))
        self.assertEqual(csrf_response.status_code, status.HTTP_200_OK)
        allowed_response = client.post(
            self.profile_list_url(),
            {},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
        )

        self.assertEqual(
            denied_response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            allowed_response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_endpoint_options_expose_only_implemented_methods(self):
        self.client.force_login(self.member)
        cases = (
            (
                self.profile_list_url(),
                {"GET", "HEAD", "OPTIONS"},
            ),
            (
                self.profile_detail_url(self.profile.id),
                {"GET", "HEAD", "OPTIONS"},
            ),
            (
                self.workspace_list_url(self.profile.id),
                {"GET", "POST", "HEAD", "OPTIONS"},
            ),
            (
                self.workspace_detail_url(
                    self.profile.id,
                    self.viewer_workspace.id,
                ),
                {"GET", "PATCH", "HEAD", "OPTIONS"},
            ),
        )

        for url, expected_methods in cases:
            with self.subTest(url=url):
                head_response = self.client.head(url)
                options_response = self.client.options(url)

                self.assertEqual(head_response.status_code, status.HTTP_200_OK)
                self.assertEqual(head_response.content, b"")
                self.assertEqual(
                    options_response.status_code,
                    status.HTTP_200_OK,
                )
                self.assertEqual(
                    set(
                        options_response["Allow"]
                        .replace(" ", "")
                        .split(",")
                    ),
                    expected_methods,
                )
