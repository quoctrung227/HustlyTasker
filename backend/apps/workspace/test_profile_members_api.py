"""Profile governance reads; all fixtures belong to the isolated test database."""

import json
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from .access import (
    TenantAccessNotFound,
    profile_invitation_capabilities,
    profile_members_visible_to_managers,
    resolve_profile_access_context,
)
from .models import Profile, ProfileMembership
from .serializers import ProfileMemberReadSerializer
from .services import create_profile_with_owner


User = get_user_model()


class ProfileMemberReadApiTests(APITestCase):
    fields = {"id", "profile_id", "display_label", "role", "is_active", "joined_at"}

    @classmethod
    def setUpTestData(cls):
        cls.owner = cls.make_user("owner", first_name="Chủ", last_name="Tổ chức")
        cls.admin = cls.make_user("admin", first_name="Quản trị")
        cls.member = cls.make_user("member")
        cls.outsider = cls.make_user("outsider")
        cls.profile = create_profile_with_owner(name="Synthetic member roster", owner=cls.owner)
        cls.owner_membership = ProfileMembership.objects.get(profile=cls.profile, user=cls.owner)
        cls.admin_membership = ProfileMembership.objects.create(
            profile=cls.profile, user=cls.admin, role=ProfileMembership.Role.ADMIN,
        )
        cls.member_membership = ProfileMembership.objects.create(
            profile=cls.profile, user=cls.member, role=ProfileMembership.Role.MEMBER,
        )
        cls.history = ProfileMembership.objects.create(
            profile=cls.profile, user=cls.member,
            role=ProfileMembership.Role.MEMBER, is_active=False,
        )
        cls.foreign = create_profile_with_owner(name="Foreign synthetic roster", owner=cls.outsider)

    @classmethod
    def make_user(cls, suffix, **fields):
        return User.objects.create_user(
            email=f"members-{suffix}@example.test",
            username=f"members-{suffix}@example.test",
            password="synthetic-test-input-only", **fields,
        )

    def url(self, profile_id=None):
        return reverse("workspace:profile-member-list", kwargs={
            "profile_id": self.profile.id if profile_id is None else profile_id,
        })

    def test_owner_reads_sanitized_same_profile_roster_and_existing_role_ceiling(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data), {"count", "next", "previous", "results", "capabilities"})
        self.assertEqual(response.data["count"], 4)
        self.assertEqual(response.data["capabilities"], {
            "can_invite": True, "can_manage_invitations": True,
            "allowed_invitation_roles": ["MEMBER", "ADMIN"],
        })
        for row in response.data["results"]:
            self.assertEqual(set(row), self.fields)
            self.assertEqual(row["profile_id"], str(self.profile.id))
            self.assertNotIn("@", row["display_label"])
        owner = next(row for row in response.data["results"] if row["id"] == str(self.owner_membership.id))
        self.assertEqual(owner["display_label"], "Chủ Tổ chức")
        member = next(row for row in response.data["results"] if row["id"] == str(self.member_membership.id))
        self.assertEqual(member["display_label"], f"Thành viên {str(self.member_membership.id)[:8]}")
        serialized = json.dumps(response.data)
        for user in (self.owner, self.admin, self.member, self.outsider):
            self.assertNotIn(user.email, serialized)
            self.assertNotIn(str(user.id), serialized)

    def test_admin_can_read_roster_but_invite_only_member(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["capabilities"], {
            "can_invite": True, "can_manage_invitations": True,
            "allowed_invitation_roles": ["MEMBER"],
        })
        self.assertEqual(response.data["count"], 4)

    def test_inactive_membership_history_is_read_only_and_not_reactivated(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url())
        history = next(row for row in response.data["results"] if row["id"] == str(self.history.id))
        self.assertFalse(history["is_active"])
        self.history.refresh_from_db()
        self.assertFalse(self.history.is_active)
        self.assertEqual(ProfileMembership.objects.filter(profile=self.profile, is_active=True).count(), 3)

    def test_regular_member_has_no_organization_roster_or_invite_authority(self):
        self.client.force_login(self.member)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("results", response.data)

    def test_cross_profile_unknown_and_malformed_ids_are_generic_not_found(self):
        self.client.force_login(self.owner)
        for profile_id in (str(self.foreign.id), str(uuid4()), "not-a-profile"):
            with self.subTest(profile_id=profile_id):
                response = self.client.get(self.url(profile_id))
                self.assertEqual(response.status_code, 404)
                self.assertNotIn("results", response.data)

    def test_staff_or_superuser_flags_do_not_grant_tenant_authority(self):
        self.outsider.is_staff = True
        self.outsider.is_superuser = True
        self.outsider.save(update_fields=("is_staff", "is_superuser"))
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.member.is_staff = True
        self.member.save(update_fields=("is_staff",))
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_inactive_actor_and_revoked_membership_fail_closed(self):
        self.client.force_login(self.admin)
        ProfileMembership.objects.filter(pk=self.admin_membership.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.client.force_login(self.owner)
        User.objects.filter(pk=self.owner.pk).update(is_active=False)
        self.assertEqual(self.client.get(self.url()).status_code, 403)

    def test_archived_profile_is_readable_without_mutation_capabilities(self):
        Profile.objects.filter(pk=self.profile.pk).update(status=Profile.Status.ARCHIVED)
        self.client.force_login(self.owner)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["capabilities"], {
            "can_invite": False, "can_manage_invitations": False,
            "allowed_invitation_roles": [],
        })
        self.assertEqual(response.data["count"], 4)

    def test_read_only_methods_authentication_csrf_and_cache_headers(self):
        self.assertEqual(self.client.get(self.url()).status_code, 403)
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.owner)
        response = client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertIn("private", response.headers["Cache-Control"])
        self.assertEqual(client.post(self.url(), {}, format="json").status_code, 403)
        token = client.get(reverse("accounts:csrf")).data["csrf_token"]
        self.assertEqual(client.post(self.url(), {}, format="json", HTTP_X_CSRFTOKEN=token).status_code, 405)
        self.assertEqual(client.head(self.url()).status_code, 200)
        self.assertEqual(client.options(self.url()).status_code, 200)

    def test_pagination_is_stable_bounded_and_preserves_capabilities(self):
        self.client.force_login(self.owner)
        first = self.client.get(self.url(), {"page_size": 2})
        second = self.client.get(self.url(), {"page_size": 2, "page": 2})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        ids = [row["id"] for row in first.data["results"] + second.data["results"]]
        expected = [str(value) for value in ProfileMembership.objects.filter(
            profile=self.profile,
        ).order_by("joined_at", "id").values_list("id", flat=True)]
        self.assertEqual(ids, expected)
        self.assertEqual(first.data["capabilities"], second.data["capabilities"])
        self.assertEqual(self.client.get(self.url(), {"page": 999}).status_code, 404)

    def test_roster_serialization_uses_one_joined_query_without_pii_or_n_plus_one(self):
        context = resolve_profile_access_context(self.owner, self.profile.id)
        queryset = profile_members_visible_to_managers(context).order_by("joined_at", "id")
        with self.assertNumQueries(1):
            memberships = list(queryset)
        with self.assertNumQueries(0):
            data = ProfileMemberReadSerializer(memberships, many=True).data
        self.assertEqual(len(data), 4)

    def test_lazy_queryset_rechecks_actor_revocation_before_evaluation(self):
        context = resolve_profile_access_context(self.owner, self.profile.id)
        queryset = profile_members_visible_to_managers(context)
        ProfileMembership.objects.filter(pk=self.owner_membership.pk).update(is_active=False)
        self.assertEqual(list(queryset), [])
        with self.assertRaises(TenantAccessNotFound):
            profile_invitation_capabilities(context)

    def test_stale_owner_context_cannot_keep_authority_after_role_downgrade(self):
        context = resolve_profile_access_context(self.owner, self.profile.id)
        queryset = profile_members_visible_to_managers(context)
        ProfileMembership.objects.filter(pk=self.owner_membership.pk).update(role=ProfileMembership.Role.MEMBER)
        self.assertEqual(list(queryset), [])
        with self.assertRaises(TenantAccessNotFound):
            profile_members_visible_to_managers(context)
        with self.assertRaises(TenantAccessNotFound):
            profile_invitation_capabilities(context)
