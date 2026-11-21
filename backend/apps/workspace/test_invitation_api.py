import hashlib
import json
from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .invitation_delivery import InvitationDeliveryUnavailable
from .invitation_throttles import InvitationRecipientThrottle
from .models import (
    ProfileInvitation,
    ProfileMembership,
    Workspace,
    WorkspaceMember,
)
from .services import create_profile_with_owner


User = get_user_model()


class ProfileInvitationApiTests(APITestCase):
    invitation_fields = {
        "id",
        "profile_id",
        "recipient_email",
        "acceptance_kind", "recipient_display_label", "recipient_username", "recipient_masked_email",
        "requested_role",
        "status",
        "delivery_status",
        "expires_at",
        "delivery_attempted_at",
        "delivered_at",
        "accepted_at",
        "declined_at",
        "revoked_at",
        "expired_at",
        "created_at",
        "updated_at",
    }

    def setUp(self):
        cache.clear()
        self.owner = self.create_user("owner")
        self.admin = self.create_user("admin")
        self.member = self.create_user("member")
        self.recipient = self.create_user("recipient")
        self.wrong_recipient = self.create_user("wrong-recipient")
        self.outsider = self.create_user("outsider")
        self.other_owner = self.create_user("other-owner")

        self.profile = create_profile_with_owner(
            name="Invitation API Profile",
            owner=self.owner,
        )
        self.owner_membership = ProfileMembership.objects.get(
            profile=self.profile,
            user=self.owner,
        )
        self.admin_membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=self.admin,
            role=ProfileMembership.Role.ADMIN,
        )
        self.member_membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=self.member,
            role=ProfileMembership.Role.MEMBER,
        )
        self.workspace = Workspace.objects.create(
            profile=self.profile,
            owner=self.owner,
            name="Invitation API Workspace",
            period=date(2026, 12, 1),
        )
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.member,
            role=WorkspaceMember.Role.ADMIN,
        )

        self.other_profile = create_profile_with_owner(
            name="Other Invitation API Profile",
            owner=self.other_owner,
        )
        self.other_owner_membership = ProfileMembership.objects.get(
            profile=self.other_profile,
            user=self.other_owner,
        )
        self.client = APIClient()

    def create_user(self, suffix, *, email=None):
        return User.objects.create_user(
            email=email or f"inv-api-{suffix}@example.test",
            username=f"inv-api-{suffix}",
            password="test-password-only",
        )

    def list_url(self, profile_id=None):
        return reverse(
            "workspace:profile-invitation-list",
            kwargs={"profile_id": profile_id or self.profile.id},
        )

    def detail_url(self, invitation_id, profile_id=None):
        return reverse(
            "workspace:profile-invitation-detail",
            kwargs={
                "profile_id": profile_id or self.profile.id,
                "invitation_id": invitation_id,
            },
        )

    def revoke_url(self, invitation_id, profile_id=None):
        return reverse(
            "workspace:profile-invitation-revoke",
            kwargs={
                "profile_id": profile_id or self.profile.id,
                "invitation_id": invitation_id,
            },
        )

    def resend_url(self, invitation_id, profile_id=None):
        return reverse(
            "workspace:profile-invitation-resend",
            kwargs={
                "profile_id": profile_id or self.profile.id,
                "invitation_id": invitation_id,
            },
        )

    def accept_url(self):
        return reverse("workspace:profile-invitation-accept")

    def decline_url(self):
        return reverse("workspace:profile-invitation-decline")

    def seed_invitation(
        self,
        *,
        recipient=None,
        profile=None,
        inviter_membership=None,
        requested_role=ProfileInvitation.Role.MEMBER,
        raw_token=None,
        delivery_status=ProfileInvitation.DeliveryStatus.SENT,
    ):
        recipient = recipient or self.recipient
        profile = profile or self.profile
        inviter_membership = inviter_membership or self.owner_membership
        raw_token = raw_token or f"api-test-token-{uuid4()}-{uuid4()}"
        now = timezone.now()
        sent = delivery_status == ProfileInvitation.DeliveryStatus.SENT
        invitation = ProfileInvitation.objects.create(
            profile=profile,
            recipient_email_normalized=recipient.email.strip().casefold(),
            recipient_user=recipient,
            requested_role=requested_role,
            invited_by_membership=inviter_membership,
            token_digest=hashlib.sha256(
                raw_token.encode("utf-8")
            ).hexdigest(),
            expires_at=now + timedelta(days=7),
            delivery_status=delivery_status,
            delivery_attempted_at=now if sent else None,
            delivered_at=now if sent else None,
        )
        return invitation, raw_token

    def assert_no_store(self, response):
        cache_control = response.headers.get("Cache-Control", "")
        self.assertIn("no-store", cache_control)
        self.assertIn("private", cache_control)

    def test_all_endpoints_require_authenticated_session(self):
        invitation, _ = self.seed_invitation()
        endpoints = (
            ("get", self.list_url(), None),
            ("post", self.list_url(), {"recipient_email": "x@example.test"}),
            ("get", self.detail_url(invitation.id), None),
            ("post", self.revoke_url(invitation.id), {}),
            ("post", self.resend_url(invitation.id), {}),
            ("post", self.accept_url(), {"token": "invalid"}),
            ("post", self.decline_url(), {"token": "invalid"}),
        )

        for method, url, payload in endpoints:
            with self.subTest(method=method, url=url):
                response = getattr(self.client, method)(
                    url,
                    payload,
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_create_defaults_member_and_response_is_sanitized(self):
        self.client.force_login(self.owner)
        with patch(
            "apps.workspace.invitation_services.secrets.token_urlsafe",
        ) as token:
            response = self.client.post(
                self.list_url(),
                {"recipient_user_id": str(self.recipient.pk)},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(set(response.data), self.invitation_fields)
        self.assertIsNone(response.data["recipient_email"])
        self.assertEqual(response.data["acceptance_kind"], "ACCOUNT")
        self.assertEqual(response.data["requested_role"], "MEMBER")
        self.assertNotIn("token", response.data)
        self.assertNotIn("token_digest", response.data)
        token.assert_not_called()
        self.assert_no_store(response)

    def test_owner_list_and_detail_are_paginated_and_never_expose_secret(self):
        first_recipient = self.create_user("list-first")
        second_recipient = self.create_user("list-second")
        first, first_token = self.seed_invitation(
            recipient=first_recipient,
            requested_role=ProfileInvitation.Role.ADMIN,
        )
        second, second_token = self.seed_invitation(recipient=second_recipient)
        self.client.force_login(self.owner)

        list_response = self.client.get(self.list_url())
        detail_response = self.client.get(self.detail_url(first.id))

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(list_response.data),
            {"count", "next", "previous", "results"},
        )
        self.assertEqual(list_response.data["count"], 2)
        for item in list_response.data["results"]:
            self.assertEqual(set(item), self.invitation_fields)
            self.assertNotIn("token", item)
            self.assertNotIn("token_digest", item)
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(detail_response.data), self.invitation_fields)
        serialized = json.dumps(
            {"list": list_response.data, "detail": detail_response.data}
        )
        self.assertNotIn(first_token, serialized)
        self.assertNotIn(second_token, serialized)

    def test_admin_role_ceiling_applies_to_create_list_detail_and_actions(self):
        member_target = self.create_user("admin-member-target")
        admin_target = self.create_user("admin-admin-target")
        member_invitation, _ = self.seed_invitation(recipient=member_target)
        admin_invitation, _ = self.seed_invitation(
            recipient=admin_target,
            requested_role=ProfileInvitation.Role.ADMIN,
        )
        self.client.force_login(self.admin)

        list_response = self.client.get(self.list_url())
        visible_ids = {
            item["id"] for item in list_response.data["results"]
        }
        self.assertSetEqual(visible_ids, {str(member_invitation.id)})
        self.assertEqual(
            self.client.get(self.detail_url(member_invitation.id)).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(self.detail_url(admin_invitation.id)).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post(
                self.revoke_url(admin_invitation.id),
                {},
                format="json",
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

        with patch(
            "apps.workspace.invitation_services.schedule_invitation_delivery"
        ):
            allowed = self.client.post(
                self.list_url(),
                {"recipient_user_id": str(self.recipient.pk)},
                format="json",
            )
            denied = self.client.post(
                self.list_url(),
                {
                    "recipient_user_id": str(self.wrong_recipient.pk),
                    "requested_role": "ADMIN",
                },
                format="json",
            )
        self.assertEqual(allowed.status_code, status.HTTP_201_CREATED)
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_profile_member_and_workspace_admin_lack_invitation_capability(self):
        self.client.force_login(self.member)

        list_response = self.client.get(self.list_url())
        create_response = self.client.post(
            self.list_url(),
            {"recipient_email": self.recipient.email},
            format="json",
        )

        self.assertEqual(list_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(create_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_wrong_parent_cross_tenant_and_unknown_ids_are_indistinguishable(self):
        other_target = self.create_user("other-profile-target")
        other_invitation, _ = self.seed_invitation(
            recipient=other_target,
            profile=self.other_profile,
            inviter_membership=self.other_owner_membership,
        )
        self.client.force_login(self.owner)

        wrong_parent = self.client.get(self.detail_url(other_invitation.id))
        inaccessible_parent = self.client.get(
            self.detail_url(other_invitation.id, self.other_profile.id)
        )
        unknown = self.client.get(self.detail_url(uuid4()))
        malformed = self.client.get(
            f"/api/v1/profiles/{self.profile.id}/invitations/not-a-uuid/"
        )

        for response in (
            wrong_parent,
            inaccessible_parent,
            unknown,
            malformed,
        ):
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(response.data, {"detail": "Not found."})

    def test_management_actions_keep_existing_legacy_expiry_and_forbid_rotation(self):
        invitation, old_token = self.seed_invitation()
        self.client.force_login(self.owner)

        unknown_field = self.client.post(
            self.revoke_url(invitation.id),
            {"status": "REVOKED"},
            format="json",
        )
        self.assertEqual(unknown_field.status_code, status.HTTP_400_BAD_REQUEST)

        original_expiry = invitation.expires_at
        with patch(
            "apps.workspace.invitation_services.schedule_invitation_delivery",
        ) as sender:
            response = self.client.post(
                self.resend_url(invitation.id),
                {},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProfileInvitation.Status.PENDING)
        self.assertEqual(invitation.expires_at, original_expiry)
        self.assertFalse(ProfileInvitation.objects.filter(replaces=invitation).exists())
        sender.assert_not_called()
        self.client.force_login(self.recipient)
        self.assertEqual(self.client.post(self.accept_url(), {"token": old_token}, format="json").status_code, 200)

    def test_accept_and_decline_require_matching_authenticated_recipient(self):
        invitation, raw_token = self.seed_invitation()
        self.client.force_login(self.wrong_recipient)

        wrong_response = self.client.post(
            self.accept_url(),
            {"token": raw_token},
            format="json",
        )
        invalid_response = self.client.post(
            self.accept_url(),
            {"token": "invalid-token"},
            format="json",
        )
        self.assertEqual(wrong_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(invalid_response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(wrong_response.data, invalid_response.data)
        self.assertNotIn(raw_token, json.dumps(wrong_response.data))

        self.client.force_login(self.recipient)
        accept_response = self.client.post(
            self.accept_url(),
            {"token": raw_token},
            format="json",
        )
        replay_response = self.client.post(
            self.accept_url(),
            {"token": raw_token},
            format="json",
        )
        self.assertEqual(accept_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(accept_response.data),
            {"status", "profile_id", "membership_id", "role"},
        )
        self.assertNotIn(raw_token, json.dumps(accept_response.data))
        self.assertEqual(replay_response.status_code, status.HTTP_409_CONFLICT)

        decline_target = self.create_user("decline-target")
        declined, decline_token = self.seed_invitation(recipient=decline_target)
        self.client.force_login(decline_target)
        decline_response = self.client.post(
            self.decline_url(),
            {"token": decline_token},
            format="json",
        )
        self.assertEqual(decline_response.status_code, status.HTTP_200_OK)
        self.assertEqual(decline_response.data, {"status": "DECLINED"})
        declined.refresh_from_db()
        self.assertEqual(declined.status, ProfileInvitation.Status.DECLINED)

    def test_malformed_create_body_is_400_not_500(self):
        self.client.force_login(self.owner)

        response = self.client.post(self.list_url(), [], format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_malformed_unicode_recipient_is_400_not_500(self):
        self.client.force_login(self.owner)
        malformed = "\ud800" * 32

        response = self.client.post(
            self.list_url(),
            json.dumps({"recipient_email": malformed}).encode("ascii"),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_session_unsafe_invitation_endpoints_enforce_csrf(self):
        invitation, raw_token = self.seed_invitation()
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.owner)
        manager_requests = (
            (self.list_url(), {"recipient_email": "csrf@example.test"}),
            (self.revoke_url(invitation.id), {}),
            (self.resend_url(invitation.id), {}),
        )
        for url, payload in manager_requests:
            with self.subTest(url=url):
                response = client.post(url, payload, format="json")
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        client.force_login(self.recipient)
        for url in (self.accept_url(), self.decline_url()):
            with self.subTest(url=url):
                response = client.post(
                    url,
                    {"token": raw_token},
                    format="json",
                )
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_csrf_allows_invitation_create(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.owner)
        csrf_response = client.get(reverse("accounts:csrf"))
        with patch(
            "apps.workspace.invitation_services.schedule_invitation_delivery"
        ):
            response = client.post(
                self.list_url(),
                {"recipient_user_id": str(self.recipient.pk)},
                format="json",
                HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
            )

        self.assertEqual(csrf_response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_accept_and_decline_share_invalid_token_throttle(self):
        self.client.force_login(self.recipient)

        responses = []
        for index in range(6):
            url = self.accept_url() if index % 2 == 0 else self.decline_url()
            responses.append(
                self.client.post(
                    url,
                    {"token": f"invalid-shared-token-{index}"},
                    format="json",
                )
            )

        for response in responses[:5]:
            self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(
            responses[5].status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    def test_create_uses_durable_account_quota_across_inviters_and_email_changes(self):
        for _ in range(5):
            old, _ = self.seed_invitation()
            ProfileInvitation.objects.filter(pk=old.pk).update(status="REVOKED", revoked_at=timezone.now(), revoked_by=self.owner)
        self.recipient.email = "changed-recipient@example.test"
        self.recipient.save()
        self.client.force_login(self.owner)
        first = self.client.post(self.list_url(), {"recipient_user_id": str(self.recipient.pk)}, format="json")
        self.client.force_login(self.other_owner)
        second = self.client.post(self.list_url(self.other_profile.id), {"recipient_user_id": str(self.recipient.pk)}, format="json")
        self.assertEqual(first.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_mail_failure_keeps_created_web_invitation_without_503_or_secret(self):
        self.client.force_login(self.owner)
        with patch("apps.common.email_delivery.EmailMessage.send", side_effect=RuntimeError("synthetic-private-mail-diagnostic")), self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.list_url(), {"recipient_user_id": str(self.recipient.pk)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ProfileInvitation.objects.get().delivery_status, "FAILED")
        self.assertNotIn("synthetic-private-mail-diagnostic", json.dumps(response.data))
        self.assertIsNone(response.data["recipient_email"])

    def test_unknown_fields_and_owner_role_are_rejected_before_service(self):
        self.client.force_login(self.owner)
        unknown = self.client.post(
            self.list_url(),
            {
                "recipient_user_id": str(self.recipient.pk),
                "token": "client-controlled-secret",
            },
            format="json",
        )
        owner_role = self.client.post(
            self.list_url(),
            {
                "recipient_user_id": str(self.recipient.pk),
                "requested_role": "OWNER",
            },
            format="json",
        )

        self.assertEqual(unknown.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(owner_role.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(ProfileInvitation.objects.count(), 0)
