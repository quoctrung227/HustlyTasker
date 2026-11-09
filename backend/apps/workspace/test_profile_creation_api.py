"""Profile onboarding contracts on the shared isolated PostgreSQL harness."""

from concurrent.futures import ThreadPoolExecutor
import json
from threading import Barrier
from unittest.mock import patch
from uuid import UUID, uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog

from .models import Profile, ProfileMembership, Workspace, WorkspaceMember
from .permissions import HasActiveTenantIdentity


User = get_user_model()


class ProfileCreationApiTests(APITestCase):
    profile_fields = {"id", "name", "status", "created_at", "updated_at"}

    @classmethod
    def setUpTestData(cls):
        cls.creator = User.objects.create_user(
            username="profile-onboarding-creator",
            email="profile-onboarding-creator@example.test",
            password=None,
        )
        cls.outsider = User.objects.create_user(
            username="profile-onboarding-outsider",
            email="profile-onboarding-outsider@example.test",
            password=None,
        )

    def setUp(self):
        self.url = reverse("workspace:profile-list")
        self.client.force_login(self.creator)

    def assert_no_profile_data(self):
        self.assertEqual(Profile.objects.count(), 0)
        self.assertEqual(ProfileMembership.objects.count(), 0)
        self.assertEqual(Workspace.objects.count(), 0)
        self.assertEqual(WorkspaceMember.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), 0)

    def create(self, payload=None):
        return self.client.post(
            self.url, {"name": "My first organization"} if payload is None else payload,
            format="json",
        )

    def test_active_user_with_no_profiles_creates_profile_and_owner_membership(self):
        self.assertEqual(self.client.get(self.url).data["count"], 0)
        response = self.create({"name": "  Nhóm sáng tạo  "})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(set(response.data), self.profile_fields)
        self.assertEqual(response.data["name"], "Nhóm sáng tạo")
        self.assertEqual(response.data["status"], Profile.Status.ACTIVE)
        self.assertIn("no-store", response["Cache-Control"])
        profile = Profile.objects.get(pk=response.data["id"])
        membership = ProfileMembership.objects.get(profile=profile)
        self.assertEqual(membership.user_id, self.creator.pk)
        self.assertEqual(membership.role, ProfileMembership.Role.OWNER)
        self.assertTrue(membership.is_active)
        self.assertEqual(ProfileMembership.objects.count(), 1)
        audit = AuditLog.objects.get(action="profile.membership.created")
        self.assertEqual(audit.user_id, self.creator.pk)
        self.assertEqual(audit.entity_id, membership.id)
        self.assertNotIn("email", audit.metadata)
        # Legacy unverified users remain eligible; onboarding grants no unrelated scope.
        self.assertIsNone(self.creator.email_verified_at)
        self.assertFalse(ProfileMembership.objects.filter(user=self.outsider).exists())
        self.assertFalse(Workspace.objects.exists())

    def test_created_profile_is_visible_in_existing_list_and_detail_contracts(self):
        created = self.create().data
        listing = self.client.get(self.url)
        detail = self.client.get(reverse("workspace:profile-detail", kwargs={"profile_id": created["id"]}))

        self.assertEqual(listing.status_code, status.HTTP_200_OK)
        self.assertEqual(listing.data["count"], 1)
        self.assertEqual(listing.data["results"], [created])
        self.assertEqual(detail.status_code, status.HTTP_200_OK)
        self.assertEqual(detail.data, created)

    def test_created_owner_can_use_existing_workspace_creation_without_membership_bypass(self):
        profile_id = self.create().data["id"]
        url = reverse("workspace:workspace-list", kwargs={"profile_id": profile_id})
        response = self.client.post(url, {"name": "First month", "period": "2026-11-01"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["profile_id"], profile_id)
        workspace = Workspace.objects.get(pk=response.data["id"])
        self.assertEqual(workspace.profile_id, UUID(profile_id))
        self.assertEqual(workspace.owner_id, self.creator.pk)
        self.assertEqual(self.client.get(url).data["count"], 1)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_404_NOT_FOUND)
        denied = self.client.post(url, {"name": "Injected", "period": "2026-12-01"}, format="json")
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Workspace.objects.count(), 1)

    def test_unrelated_user_cannot_read_created_profile_or_inherit_ownership(self):
        profile_id = self.create().data["id"]
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.url).data["count"], 0)
        denied = self.client.get(reverse("workspace:profile-detail", kwargs={"profile_id": profile_id}))
        unknown = self.client.get(reverse("workspace:profile-detail", kwargs={"profile_id": uuid4()}))
        self.assertEqual(denied.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(denied.data, unknown.data)
        self.assertFalse(ProfileMembership.objects.filter(user=self.outsider).exists())

    def test_existing_user_can_create_another_profile_without_changing_previous_membership(self):
        first_id = self.create({"name": "First"}).data["id"]
        first_membership = ProfileMembership.objects.get(profile_id=first_id)
        second = self.create({"name": "Second"})

        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(second.data["id"], first_id)
        first_membership.refresh_from_db()
        self.assertTrue(first_membership.is_active)
        self.assertEqual(first_membership.role, ProfileMembership.Role.OWNER)
        self.assertEqual(first_membership.user_id, self.creator.pk)
        self.assertEqual(self.client.get(self.url).data["count"], 2)

    def test_repeated_names_are_distinct_profiles_under_existing_nonunique_domain_rules(self):
        first = self.create()
        second = self.create()

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(first.data["id"], second.data["id"])
        for profile in Profile.objects.all():
            self.assertEqual(profile.memberships.count(), 1)
            self.assertTrue(profile.memberships.get(user=self.creator, role="OWNER").is_active)
        self.assertEqual(AuditLog.objects.filter(action="profile.membership.created").count(), 2)

    def test_required_blank_and_oversized_names_are_rejected_without_side_effects(self):
        for payload in ({}, {"name": ""}, {"name": " \t\n "}, {"name": "x" * 256}):
            with self.subTest(payload=payload):
                response = self.create(payload)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("name", response.data)
                self.assert_no_profile_data()

    def test_name_at_existing_maximum_length_is_accepted(self):
        response = self.create({"name": "x" * 255})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["name"]), 255)

    def test_name_must_be_text_not_numeric_boolean_null_list_or_object(self):
        for value in (123, 1.2, True, None, [], {}):
            with self.subTest(value=value):
                response = self.create({"name": value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("name", response.data)
                self.assert_no_profile_data()

    def test_invalid_unicode_and_nul_are_rejected_before_database_write(self):
        for value in ("bad\x00name", "bad\ud800name"):
            with self.subTest(value=repr(value)):
                response = self.client.generic(
                    "POST", self.url,
                    data=json.dumps({"name": value}, ensure_ascii=True),
                    content_type="application/json",
                )
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn("name", response.data)
                self.assert_no_profile_data()

    def test_client_cannot_inject_identity_role_status_tenant_or_membership(self):
        forbidden = {
            "owner": str(self.outsider.pk), "owner_id": str(self.outsider.pk),
            "user_id": str(self.outsider.pk), "profile_id": str(uuid4()),
            "id": str(uuid4()), "status": "ARCHIVED", "is_active": False,
            "role": "OWNER", "memberships": [{"user": str(self.outsider.pk), "role": "OWNER"}],
            "created_at": "2026-01-01T00:00:00Z", "description": "Unsupported field",
        }
        for name, value in forbidden.items():
            with self.subTest(field=name):
                response = self.create({"name": "Injected", name: value})
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(name, response.data)
                self.assert_no_profile_data()

    def test_anonymous_creation_is_denied(self):
        self.client.logout()
        self.assertEqual(self.create().status_code, status.HTTP_403_FORBIDDEN)
        self.assert_no_profile_data()

    def test_inactive_authenticated_identity_is_denied(self):
        User.objects.filter(pk=self.creator.pk).update(is_active=False)
        self.client.force_authenticate(self.creator)
        self.assertEqual(self.create().status_code, status.HTTP_403_FORBIDDEN)
        self.assert_no_profile_data()

    def test_expired_session_cannot_create_profile(self):
        self.client.cookies.clear()
        self.assertEqual(self.create().status_code, status.HTTP_403_FORBIDDEN)
        self.assert_no_profile_data()

    def test_session_creation_requires_csrf_and_valid_bootstrap_allows_it(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.creator)
        denied = client.post(self.url, {"name": "No CSRF"}, format="json")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)
        self.assert_no_profile_data()
        token = client.get(reverse("accounts:csrf")).data["csrf_token"]
        invalid = client.post(self.url, {"name": "Invalid CSRF"}, format="json", HTTP_X_CSRFTOKEN="invalid")
        self.assertEqual(invalid.status_code, status.HTTP_403_FORBIDDEN)
        self.assert_no_profile_data()
        response = client.post(self.url, {"name": "With CSRF"}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProfileMembership.objects.get().user_id, self.creator.pk)

    def test_membership_failure_rolls_back_profile_and_audit(self):
        with patch.object(ProfileMembership, "save", side_effect=ValidationError({"name": "Creation failed."})):
            response = self.create()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assert_no_profile_data()

    def test_audit_failure_rolls_back_profile_and_owner_membership(self):
        with patch("apps.workspace.services._write_membership_audit", side_effect=ValidationError({"name": "Creation failed."})):
            response = self.create()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assert_no_profile_data()

    def test_creator_deactivation_after_permission_check_cannot_leave_active_owner(self):
        original = HasActiveTenantIdentity.has_permission

        def deactivate_after_permission(permission, request, view):
            allowed = original(permission, request, view)
            if allowed:
                User.objects.filter(pk=self.creator.pk).update(is_active=False)
            return allowed

        with patch.object(HasActiveTenantIdentity, "has_permission", deactivate_after_permission):
            response = self.create()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assert_no_profile_data()


class ProfileCreationConcurrencyTests(TransactionTestCase):
    def test_parallel_submissions_create_separate_consistent_profiles_without_new_dedup_rules(self):
        creator = User.objects.create_user(
            username="profile-onboarding-concurrent",
            email="profile-onboarding-concurrent@example.test",
            password=None,
        )
        barrier = Barrier(2)
        url = reverse("workspace:profile-list")

        def create():
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(creator)
                barrier.wait(timeout=10)
                response = client.post(url, {"name": "Concurrent organization"}, format="json")
                return response.status_code, response.data["id"]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: create(), range(2)))
        self.assertEqual([result[0] for result in results], [status.HTTP_201_CREATED] * 2)
        self.assertEqual(len({result[1] for result in results}), 2)
        self.assertEqual(Profile.objects.count(), 2)
        self.assertEqual(ProfileMembership.objects.count(), 2)
        self.assertEqual(AuditLog.objects.filter(action="profile.membership.created").count(), 2)
        for profile in Profile.objects.all():
            membership = profile.memberships.get()
            self.assertEqual(membership.user_id, creator.pk)
            self.assertEqual(membership.role, ProfileMembership.Role.OWNER)
            self.assertTrue(membership.is_active)
        self.assertEqual(Workspace.objects.count(), 0)
