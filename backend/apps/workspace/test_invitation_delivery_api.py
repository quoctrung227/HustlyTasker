"""Real-commit ACCOUNT invitation mail tests; transport is locmem/mock only."""
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.db import connection, transaction
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient, APITransactionTestCase

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from .account_invitations import create_account_invitation
from .models import InvitationEmailAttempt, ProfileInvitation, ProfileMembership
from .services import create_profile_with_owner

User = get_user_model()
LOCMEM_MAILER = {"default": {"BACKEND": "django.core.mail.backends.locmem.EmailBackend"}}
SMTP_MAILER = {"default": {"BACKEND": "django.core.mail.backends.smtp.EmailBackend"}}


@override_settings(MAILERS=LOCMEM_MAILER, DEFAULT_FROM_EMAIL="robot@example.test")
class InvitationDeliveryApiTests(APITransactionTestCase):
    def setUp(self):
        cache.clear()
        mail.outbox = []
        self.owner = self.user("owner")
        self.admin = self.user("admin")
        self.member = self.user("member")
        self.other_owner = self.user("other-owner")
        self.recipient_user = self.user("recipient")
        self.recipient = self.recipient_user.email
        self.profile = create_profile_with_owner(name="Delivery API isolated Profile", owner=self.owner)
        self.other_profile = create_profile_with_owner(name="Delivery API other Profile", owner=self.other_owner)
        ProfileMembership.objects.create(profile=self.profile, user=self.admin, role="ADMIN")
        ProfileMembership.objects.create(profile=self.profile, user=self.member, role="MEMBER")
        self.client.force_login(self.owner)
        guard = patch("django.core.mail.backends.smtp.EmailBackend.open", side_effect=AssertionError("Live SMTP forbidden in isolated tests"))
        self.smtp_open = guard.start()
        self.addCleanup(guard.stop)
        self.addCleanup(self.smtp_open.assert_not_called)
        self.assertFalse(connection.in_atomic_block)

    @staticmethod
    def user(suffix):
        return User.objects.create_user(username=f"delivery-api-{suffix}", email=f"delivery-api-{suffix}@example.test")

    def list_url(self, profile_id=None):
        return reverse("workspace:profile-invitation-list", kwargs={"profile_id": profile_id or self.profile.pk})

    def resend_url(self, invitation_id):
        return reverse("workspace:profile-invitation-resend", kwargs={"profile_id": self.profile.pk, "invitation_id": invitation_id})

    def create(self, *, recipient=None, role="MEMBER", client=None):
        target = self.recipient_user
        if recipient and recipient != target.email:
            target = User.objects.create_user(username="delivery-target-"+str(User.objects.count()), email=recipient)
        return (client or self.client).post(self.list_url(), {"recipient_user_id": str(target.pk), "requested_role": role}, format="json")

    def assert_failed(self, invitation):
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "PENDING")
        self.assertEqual(invitation.delivery_status, "FAILED")
        self.assertIsNotNone(invitation.delivery_attempted_at)
        self.assertIsNone(invitation.delivered_at)

    def test_unsafe_development_backends_keep_web_invitation_and_never_issue_token_or_send(self):
        with patch("apps.workspace.invitation_services.secrets.token_urlsafe") as token, patch("apps.common.email_delivery.EmailMessage.send") as sender:
            for index, backend in enumerate(("console", "dummy", "filebased")):
                with self.subTest(backend=backend), self.settings(MAILERS={"default": {"BACKEND": f"django.core.mail.backends.{backend}.EmailBackend"}}):
                    response = self.create(recipient=f"unavailable-{index}@example.test")
                    self.assertEqual(response.status_code, 201)
                    self.assertEqual(response.data["delivery_status"], "FAILED")
                    self.assertIn("no-store", response.headers["Cache-Control"])
            token.assert_not_called()
            sender.assert_not_called()
        self.assertEqual(ProfileInvitation.objects.count(), 3)
        self.assertEqual(Notification.objects.filter(event_type="PROFILE_INVITED").count(), 3)
        self.assertTrue(all(row["delivery_status"] == "FAILED" for row in self.client.get(self.list_url()).data["results"]))

    def test_locmem_success_commits_sent_notification_only_mail_and_no_credential(self):
        with patch("apps.workspace.invitation_services.secrets.token_urlsafe") as token:
            response = self.create()
        self.assertEqual(response.status_code, 201)
        invitation = ProfileInvitation.objects.get()
        self.assertEqual(invitation.delivery_status, "SENT")
        self.assertIsNotNone(invitation.delivered_at)
        self.assertIsNone(invitation.token_digest)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.recipient])
        self.assertIn("/invitations", mail.outbox[0].body)
        self.assertNotIn("token", mail.outbox[0].body.lower())
        self.assertNotIn("/accept", mail.outbox[0].body)
        self.assertNotIn("token_digest", response.data)
        self.assertIsNone(response.data["recipient_email"])
        token.assert_not_called()

    @override_settings(MAILERS=SMTP_MAILER)
    def test_transport_failure_after_business_commit_returns_created_and_persists_web_notification(self):
        observed = []
        def fail_after_business_commit(*args, **kwargs):
            # Delivery uses its own bounded atomic section; prove the earlier
            # business commit is visible from an independent test connection.
            observer = connection.copy(alias="invitation_mail_commit_observer")
            try:
                with observer.cursor() as cursor:
                    cursor.execute("SELECT count(*) FROM workspace_profileinvitation")
                    invitations = cursor.fetchone()[0]
                    cursor.execute("SELECT count(*) FROM notifications_notification WHERE event_type='PROFILE_INVITED'")
                    notifications = cursor.fetchone()[0]
                observed.append((invitations, notifications))
            finally:
                observer.close()
            raise RuntimeError("synthetic-private-provider-diagnostic")
        with patch("apps.common.email_delivery.EmailMessage.send", side_effect=fail_after_business_commit) as sender:
            response = self.create()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(observed, [(1, 1)])
        sender.assert_called_once_with(fail_silently=False, using="default")
        self.assert_failed(ProfileInvitation.objects.get())
        self.assertNotIn("synthetic-private-provider-diagnostic", json.dumps(response.data))
        self.assertIsNone(response.data["recipient_email"])
        self.client.force_login(self.recipient_user)
        rows = self.client.get(reverse("workspace:profile-invitation-recipient-list"))
        self.assertEqual(rows.data["count"], 1)
        self.assertTrue(rows.data["results"][0]["can_accept"])

    @override_settings(MAILERS=SMTP_MAILER)
    def test_zero_messages_is_failed_delivery_but_still_web_created(self):
        with patch("apps.common.email_delivery.EmailMessage.send", return_value=0) as sender:
            response = self.create()
        self.assertEqual(response.status_code, 201)
        self.assert_failed(ProfileInvitation.objects.get())
        sender.assert_called_once_with(fail_silently=False, using="default")

    @override_settings(MAILERS=SMTP_MAILER)
    def test_repeated_create_after_mail_failure_conflicts_without_duplicate_notification(self):
        with patch("apps.common.email_delivery.EmailMessage.send", side_effect=RuntimeError("synthetic failure")) as sender:
            self.assertEqual(self.create().status_code, 201)
            self.assertEqual(self.create().status_code, 409)
        self.assertEqual(sender.call_count, 1)
        self.assertEqual(ProfileInvitation.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(event_type="PROFILE_INVITED").count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="profile.invitation.created").count(), 1)

    @override_settings(MAILERS=SMTP_MAILER)
    def test_successful_retry_keeps_same_invitation_expiry_and_notification_read_state(self):
        with patch("apps.common.email_delivery.EmailMessage.send", side_effect=[RuntimeError("synthetic failure"), 1]) as sender:
            self.assertEqual(self.create().status_code, 201)
            invitation = ProfileInvitation.objects.get()
            expiry = invitation.expires_at
            Notification.objects.filter(invitation=invitation).update(is_read=True)
            response = self.client.post(self.resend_url(invitation.pk), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(sender.call_count, 2)
        invitation.refresh_from_db()
        self.assertEqual(invitation.delivery_status, "SENT")
        self.assertEqual(invitation.expires_at, expiry)
        self.assertEqual(response.data["id"], str(invitation.pk))
        self.assertEqual(ProfileInvitation.objects.count(), 1)
        self.assertEqual(InvitationEmailAttempt.objects.count(), 2)
        self.assertTrue(Notification.objects.get(invitation=invitation).is_read)

    def test_unavailable_retry_records_truthful_failure_and_uses_bounded_attempts(self):
        self.assertEqual(self.create().status_code, 201)
        invitation = ProfileInvitation.objects.get()
        with self.settings(MAILERS={"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}), patch("apps.common.email_delivery.EmailMessage.send") as sender:
            self.assertEqual(self.client.post(self.resend_url(invitation.pk), {}, format="json").status_code, 200)
            self.assertEqual(self.client.post(self.resend_url(invitation.pk), {}, format="json").status_code, 200)
            self.assertEqual(self.client.post(self.resend_url(invitation.pk), {}, format="json").status_code, 429)
            sender.assert_not_called()
        self.assert_failed(invitation)
        self.assertEqual(InvitationEmailAttempt.objects.count(), 3)
        self.assertEqual(ProfileInvitation.objects.count(), 1)

    @override_settings(MAILERS=SMTP_MAILER)
    def test_failed_rows_retain_tenant_and_admin_role_ceiling(self):
        with patch("apps.common.email_delivery.EmailMessage.send", return_value=0):
            self.assertEqual(self.create().status_code, 201)
            self.assertEqual(self.create(recipient="admin-delivery-target@example.test", role="ADMIN").status_code, 201)
        self.assertEqual(self.client.get(self.list_url()).data["count"], 2)
        self.client.force_login(self.admin)
        rows = self.client.get(self.list_url()).data["results"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["requested_role"], "MEMBER")
        self.assertEqual(rows[0]["delivery_status"], "FAILED")
        self.client.force_login(self.other_owner)
        self.assertEqual(self.client.get(self.list_url()).status_code, 404)

    def test_auth_tenant_and_csrf_denials_precede_email(self):
        baseline = AuditLog.objects.count()
        anonymous, member, outsider, csrf = APIClient(), APIClient(), APIClient(), APIClient(enforce_csrf_checks=True)
        member.force_login(self.member); outsider.force_login(self.other_owner); csrf.force_login(self.owner)
        with patch("apps.common.email_delivery.EmailMessage.send") as sender:
            for client, code in ((anonymous, 403), (member, 403), (outsider, 404), (csrf, 403)):
                self.assertEqual(self.create(client=client).status_code, code)
            sender.assert_not_called()
        self.assertEqual(AuditLog.objects.count(), baseline)
        token = csrf.get(reverse("accounts:csrf")).data["csrf_token"]
        response = csrf.post(self.list_url(), {"recipient_user_id": str(self.recipient_user.pk)}, format="json", HTTP_X_CSRFTOKEN=token)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(mail.outbox), 1)

    @override_settings(MAILERS=SMTP_MAILER)
    def test_failed_retries_never_rotate_or_create_duplicate_pending_rows(self):
        with patch("apps.common.email_delivery.EmailMessage.send", return_value=0) as sender:
            self.assertEqual(self.create().status_code, 201)
            invitation = ProfileInvitation.objects.get()
            self.assertEqual(self.client.post(self.resend_url(invitation.pk), {}, format="json").status_code, 200)
            self.assertEqual(self.client.post(self.resend_url(invitation.pk), {}, format="json").status_code, 200)
            self.assertEqual(self.client.post(self.resend_url(invitation.pk), {}, format="json").status_code, 429)
        self.assertEqual(sender.call_count, 3)
        self.assertEqual(ProfileInvitation.objects.filter(status="PENDING").count(), 1)
        self.assertEqual(ProfileInvitation.objects.count(), 1)
        self.assert_failed(invitation)

    def test_callback_revalidates_current_email_and_active_account(self):
        with transaction.atomic():
            invitation = create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=self.recipient_user.pk)
            self.recipient_user.email = "updated-recipient@example.test"
            self.recipient_user.save()
        self.assertEqual(mail.outbox[-1].to, ["updated-recipient@example.test"])
        other = self.user("deactivated-before-callback")
        with patch("apps.common.email_delivery.EmailMessage.send") as sender:
            with transaction.atomic():
                inactive = create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=other.pk)
                other.is_active = False
                other.save(update_fields=("is_active",))
            sender.assert_not_called()
        self.assert_failed(inactive)
        self.assertTrue(Notification.objects.filter(invitation=invitation).exists())
