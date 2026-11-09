"""Real commit/API delivery outcomes; all mail transport stays isolated/fake."""

import hashlib
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.db import connection
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITransactionTestCase

from apps.audit.models import AuditLog

from .models import ProfileInvitation, ProfileMembership
from .services import create_profile_with_owner


User = get_user_model()
LOCMEM_MAILER = {
    "default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"},
}
SMTP_MAILER = {
    "default": {"BACKEND": "django.core.mail.backends.smtp.EmailBackend"},
}
DELIVERY_DETAIL = {"detail": "Invitation delivery is currently unavailable."}


@override_settings(MAILERS=LOCMEM_MAILER, DEFAULT_FROM_EMAIL="robot@example.test")
class InvitationDeliveryApiTests(APITransactionTestCase):
    """Unlike APITestCase, POST exits a real transaction before returning HTTP."""

    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.owner = self.user("owner")
        self.admin = self.user("admin")
        self.member = self.user("member")
        self.other_owner = self.user("other-owner")
        self.profile = create_profile_with_owner(
            name="Delivery API isolated Profile", owner=self.owner,
        )
        self.other_profile = create_profile_with_owner(
            name="Delivery API other Profile", owner=self.other_owner,
        )
        ProfileMembership.objects.create(
            profile=self.profile, user=self.admin, role=ProfileMembership.Role.ADMIN,
        )
        ProfileMembership.objects.create(
            profile=self.profile, user=self.member, role=ProfileMembership.Role.MEMBER,
        )
        self.recipient = "delivery-recipient@example.test"
        self.client.force_login(self.owner)
        # No test can open SMTP, even if a sender mock is accidentally removed.
        guard = patch(
            "django.core.mail.backends.smtp.EmailBackend.open",
            side_effect=AssertionError("Live SMTP is forbidden in isolated tests."),
        )
        self.smtp_open = guard.start()
        self.addCleanup(guard.stop)
        self.addCleanup(self.smtp_open.assert_not_called)
        self.assertFalse(connection.in_atomic_block)

    @staticmethod
    def user(suffix):
        # Session force_login needs no usable password or external credentials.
        return User.objects.create_user(
            username=f"delivery-api-{suffix}",
            email=f"delivery-api-{suffix}@example.test",
        )

    def list_url(self, profile_id=None):
        return reverse("workspace:profile-invitation-list", kwargs={
            "profile_id": profile_id or self.profile.id,
        })

    def resend_url(self, invitation_id):
        return reverse("workspace:profile-invitation-resend", kwargs={
            "profile_id": self.profile.id, "invitation_id": invitation_id,
        })

    def create(self, *, recipient=None, role=ProfileInvitation.Role.MEMBER, client=None):
        return (client or self.client).post(self.list_url(), {
            "recipient_email": recipient or self.recipient,
            "requested_role": role,
        }, format="json")

    def assert_unavailable(self, response):
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertEqual(response.data, DELIVERY_DETAIL)
        self.assertIn("no-store", response.headers.get("Cache-Control", ""))

    def assert_failed(self, invitation):
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProfileInvitation.Status.PENDING)
        self.assertEqual(invitation.delivery_status, ProfileInvitation.DeliveryStatus.FAILED)
        self.assertIsNotNone(invitation.delivery_attempted_at)
        self.assertIsNone(invitation.delivered_at)

    def test_unsafe_development_backends_fail_before_token_row_audit_or_send(self):
        baseline_audit = AuditLog.objects.count()
        with patch("apps.workspace.invitation_services.secrets.token_urlsafe") as token, patch(
            "apps.common.email_delivery.EmailMessage.send",
        ) as sender:
            for backend in ("console", "dummy", "filebased"):
                with self.subTest(backend=backend), self.settings(MAILERS={
                    "default": {"BACKEND": f"django.core.mail.backends.{backend}.EmailBackend"},
                }):
                    self.assert_unavailable(self.create())
            token.assert_not_called()
            sender.assert_not_called()
        self.assertEqual(ProfileInvitation.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), baseline_audit)
        listed = self.client.get(self.list_url())
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(listed.data["results"], [])

    def test_locmem_success_is_committed_sent_and_never_returns_raw_credential(self):
        # Locmem proves adapter acceptance only, not genuine mailbox delivery.
        token = "L" * 43
        with patch("apps.workspace.invitation_services.secrets.token_urlsafe", return_value=token):
            response = self.create()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        invitation = ProfileInvitation.objects.get()
        self.assertEqual(invitation.delivery_status, ProfileInvitation.DeliveryStatus.SENT)
        self.assertIsNotNone(invitation.delivered_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.recipient])
        self.assertIn(token, mail.outbox[0].body)
        self.assertEqual(invitation.token_digest, hashlib.sha256(token.encode()).hexdigest())
        self.assertNotIn(token, json.dumps(response.data))
        self.assertNotIn("token_digest", response.data)
        self.assertNotIn("token", response.data)
        self.assertTrue(AuditLog.objects.filter(
            entity_id=invitation.id, action="profile.invitation.created",
        ).exists())

    @override_settings(MAILERS=SMTP_MAILER)
    def test_transport_error_returns_503_after_commit_and_failed_row_is_listed(self):
        token = "F" * 43
        provider_detail = "synthetic-private-provider-diagnostic"
        observed = []

        def fail_after_commit(*args, **kwargs):
            persisted = ProfileInvitation.objects.get()
            observed.append({
                "inside_atomic": connection.in_atomic_block,
                "delivery_status": persisted.delivery_status,
                "audit_committed": AuditLog.objects.filter(
                    entity_id=persisted.id, action="profile.invitation.created",
                ).exists(),
            })
            raise RuntimeError(provider_detail)

        with patch("apps.workspace.invitation_services.secrets.token_urlsafe", return_value=token), patch(
            "apps.common.email_delivery.EmailMessage.send", side_effect=fail_after_commit,
        ) as sender:
            response = self.create()
        self.assert_unavailable(response)
        sender.assert_called_once_with(fail_silently=False, using="default")
        # Assert outside the mailer's broad exception sanitizer so a failed
        # test assertion cannot be mistaken for an intended transport error.
        self.assertEqual(observed, [{
            "inside_atomic": False, "delivery_status": "QUEUED", "audit_committed": True,
        }])
        invitation = ProfileInvitation.objects.get()
        self.assert_failed(invitation)
        serialized = json.dumps(response.data)
        for private in (token, invitation.token_digest, provider_detail, self.recipient):
            self.assertNotIn(private, serialized)
        audit = json.dumps(list(AuditLog.objects.filter(
            entity_name="ProfileInvitation",
        ).values_list("metadata", flat=True)))
        self.assertNotIn(token, audit)
        self.assertNotIn(provider_detail, audit)
        listed = self.client.get(self.list_url())
        self.assertEqual(listed.status_code, status.HTTP_200_OK)
        self.assertEqual(listed.data["count"], 1)
        self.assertEqual(listed.data["results"][0]["id"], str(invitation.id))
        self.assertEqual(listed.data["results"][0]["status"], "PENDING")
        self.assertEqual(listed.data["results"][0]["delivery_status"], "FAILED")

    @override_settings(MAILERS=SMTP_MAILER)
    def test_transport_accepting_zero_messages_is_not_reported_as_sent(self):
        with patch("apps.common.email_delivery.EmailMessage.send", return_value=0) as sender:
            response = self.create()
        self.assert_unavailable(response)
        sender.assert_called_once_with(fail_silently=False, using="default")
        self.assert_failed(ProfileInvitation.objects.get())
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(MAILERS=SMTP_MAILER)
    def test_repeating_create_after_delivery_failure_conflicts_without_sending_twice(self):
        with patch("apps.common.email_delivery.EmailMessage.send", side_effect=RuntimeError("synthetic failure")) as sender:
            self.assert_unavailable(self.create())
            repeated = self.create()
        self.assertEqual(repeated.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(sender.call_count, 1)
        self.assertEqual(ProfileInvitation.objects.count(), 1)
        self.assert_failed(ProfileInvitation.objects.get())
        self.assertEqual(AuditLog.objects.filter(action="profile.invitation.created").count(), 1)

    @override_settings(MAILERS=SMTP_MAILER)
    def test_failed_delivery_resend_rotates_once_and_old_resend_cannot_replay(self):
        with patch("apps.common.email_delivery.EmailMessage.send", side_effect=[RuntimeError("synthetic failure"), 1]) as sender:
            self.assert_unavailable(self.create())
            failed = ProfileInvitation.objects.get()
            old_digest = failed.token_digest
            response = self.client.post(self.resend_url(failed.id), {}, format="json")
            replay = self.client.post(self.resend_url(failed.id), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(replay.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(sender.call_count, 2)
        replacement = ProfileInvitation.objects.get(replaces=failed)
        failed.refresh_from_db()
        self.assertEqual(failed.status, ProfileInvitation.Status.REVOKED)
        self.assertEqual(failed.delivery_status, ProfileInvitation.DeliveryStatus.FAILED)
        self.assertEqual(replacement.delivery_status, ProfileInvitation.DeliveryStatus.SENT)
        self.assertIsNotNone(replacement.delivered_at)
        self.assertNotEqual(replacement.id, failed.id)
        self.assertNotEqual(replacement.token_digest, old_digest)
        self.assertEqual(response.data["id"], str(replacement.id))
        self.assertEqual(ProfileInvitation.objects.count(), 2)
        self.assertEqual(ProfileInvitation.objects.filter(status="PENDING").count(), 1)
        listed = self.client.get(self.list_url())
        self.assertEqual({item["id"] for item in listed.data["results"]}, {
            str(failed.id), str(replacement.id),
        })

    def test_unavailable_resend_preserves_failed_row_and_audit_without_rotation(self):
        with self.settings(MAILERS=SMTP_MAILER), patch(
            "apps.common.email_delivery.EmailMessage.send", return_value=0,
        ):
            self.assert_unavailable(self.create())
        failed = ProfileInvitation.objects.get()
        fields = ("id", "status", "delivery_status", "token_digest", "updated_at", "replaces_id")
        before = ProfileInvitation.objects.values(*fields).get(id=failed.id)
        before_audit = AuditLog.objects.count()
        with self.settings(MAILERS={"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}), patch(
            "apps.workspace.invitation_services.secrets.token_urlsafe",
        ) as token, patch("apps.common.email_delivery.EmailMessage.send") as sender:
            response = self.client.post(self.resend_url(failed.id), {}, format="json")
        self.assert_unavailable(response)
        token.assert_not_called()
        sender.assert_not_called()
        self.assertEqual(ProfileInvitation.objects.values(*fields).get(id=failed.id), before)
        self.assertEqual(AuditLog.objects.count(), before_audit)
        self.assertEqual(ProfileInvitation.objects.count(), 1)

    @override_settings(MAILERS=SMTP_MAILER)
    def test_failed_records_remain_visible_with_tenant_and_admin_role_ceiling(self):
        with patch("apps.common.email_delivery.EmailMessage.send", return_value=0):
            self.assert_unavailable(self.create())
            self.assert_unavailable(self.create(
                recipient="admin-delivery-recipient@example.test", role=ProfileInvitation.Role.ADMIN,
            ))
        owner_rows = self.client.get(self.list_url()).data["results"]
        self.assertEqual(len(owner_rows), 2)
        self.assertTrue(all(row["delivery_status"] == "FAILED" for row in owner_rows))
        self.client.force_login(self.admin)
        admin_rows = self.client.get(self.list_url()).data["results"]
        self.assertEqual(len(admin_rows), 1)
        self.assertEqual(admin_rows[0]["requested_role"], "MEMBER")
        self.assertEqual(admin_rows[0]["delivery_status"], "FAILED")
        self.client.force_login(self.other_owner)
        self.assertEqual(self.client.get(self.list_url()).status_code, status.HTTP_404_NOT_FOUND)
        own_other = self.client.get(self.list_url(self.other_profile.id))
        self.assertEqual(own_other.data["results"], [])

    def test_auth_tenant_and_session_csrf_denials_happen_before_any_delivery(self):
        baseline_audit = AuditLog.objects.count()
        anonymous = APIClient()
        member_client = APIClient()
        member_client.force_login(self.member)
        outsider = APIClient()
        outsider.force_login(self.other_owner)
        csrf_client = APIClient(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner)
        with patch("apps.common.email_delivery.EmailMessage.send") as sender:
            for client, expected in (
                (anonymous, status.HTTP_403_FORBIDDEN),
                (member_client, status.HTTP_403_FORBIDDEN),
                (outsider, status.HTTP_404_NOT_FOUND),
                (csrf_client, status.HTTP_403_FORBIDDEN),
            ):
                with self.subTest(expected=expected):
                    self.assertEqual(self.create(client=client).status_code, expected)
            sender.assert_not_called()
        self.assertEqual(ProfileInvitation.objects.count(), 0)
        self.assertEqual(AuditLog.objects.count(), baseline_audit)
        csrf_response = csrf_client.get(reverse("accounts:csrf"))
        confirmed = csrf_client.post(self.list_url(), {
            "recipient_email": self.recipient, "requested_role": "MEMBER",
        }, format="json", HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"])
        self.assertEqual(confirmed.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(MAILERS=SMTP_MAILER)
    def test_failed_resend_keeps_replacement_visible_and_no_duplicate_pending(self):
        with patch("apps.common.email_delivery.EmailMessage.send", return_value=0) as sender:
            self.assert_unavailable(self.create())
            original = ProfileInvitation.objects.get()
            self.assert_unavailable(self.client.post(self.resend_url(original.id), {}, format="json"))
            replay = self.client.post(self.resend_url(original.id), {}, format="json")
        self.assertEqual(replay.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(sender.call_count, 2)
        replacement = ProfileInvitation.objects.get(replaces=original)
        original.refresh_from_db()
        self.assertEqual(original.status, ProfileInvitation.Status.REVOKED)
        self.assert_failed(replacement)
        self.assertEqual(ProfileInvitation.objects.count(), 2)
        self.assertEqual(ProfileInvitation.objects.filter(status="PENDING").count(), 1)
        listed = self.client.get(self.list_url())
        self.assertEqual(listed.data["count"], 2)
        self.assertTrue(all(row["delivery_status"] == "FAILED" for row in listed.data["results"]))
        self.assertTrue(AuditLog.objects.filter(
            entity_id=replacement.id, action="profile.invitation.resent",
        ).exists())
