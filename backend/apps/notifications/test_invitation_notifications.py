from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.workspace.models import Profile, ProfileInvitation, ProfileMembership
from apps.workspace.services import create_profile_with_owner

from .access import notifications_visible_to
from .models import Notification
from .services import emit_invitation_notification, mark_notification_read


class InvitationNotificationFixture:
    @classmethod
    def make_fixture(cls):
        for label in ("owner", "recipient", "outsider"):
            setattr(cls, label, get_user_model().objects.create_user(
                username=f"invite-notice-{label}", email=f"invite-notice-{label}@example.test",
                password=None,
            ))
        cls.profile = create_profile_with_owner(name="Invited organization", owner=cls.owner)
        cls.inviter = ProfileMembership.objects.get(profile=cls.profile, user=cls.owner)

    @classmethod
    def setUpTestData(cls):
        cls.make_fixture()

    def new_notice(self, *, profile=None, inviter=None, delivery_status="FAILED"):
        profile = profile or self.profile
        inviter = inviter or self.inviter
        now = timezone.now()
        invitation = ProfileInvitation.objects.create(
            profile=profile, recipient_user=self.recipient,
            recipient_email_normalized=self.recipient.email,
            invited_by_membership=inviter, requested_role="MEMBER",
            acceptance_kind=ProfileInvitation.AcceptanceKind.ACCOUNT,
            token_digest=None, expires_at=now + timedelta(days=7),
            delivery_status=delivery_status,
            delivery_attempted_at=now if delivery_status != "QUEUED" else None,
            delivered_at=now if delivery_status == "SENT" else None,
        )
        event = AuditLog.objects.create(
            user=inviter.user, action="profile.invitation.created", entity_name="ProfileInvitation",
            entity_id=invitation.pk,
            metadata={"profile_id": str(profile.pk), "requested_role": invitation.requested_role},
        )
        [notification] = emit_invitation_notification(event=event, actor=inviter.user, invitation=invitation)
        return invitation, event, notification

    def feed_url(self):
        return reverse("notifications:notification-list")

    def count_url(self):
        return reverse("notifications:notification-unread-count")

    def read_url(self, notification):
        return reverse("notifications:notification-read", kwargs={"notification_id": notification.pk})


class InvitationNotificationTests(InvitationNotificationFixture, APITestCase):
    def setUp(self):
        self.client.force_login(self.recipient)

    def test_nonmember_recipient_sees_typed_failed_mail_invitation_and_no_private_identity(self):
        invitation, _, notification = self.new_notice()
        self.assertFalse(ProfileMembership.objects.filter(user=self.recipient).exists())
        response = self.client.get(self.feed_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["target_type"], "PROFILE_INVITATION")
        self.assertEqual(str(row["invitation_id"]), str(invitation.pk))
        self.assertIsNone(row["task_id"])
        self.assertIsNone(row["workspace_id"])
        self.assertEqual(row["target_url"], reverse("workspace:profile-invitation-recipient-detail", kwargs={"invitation_id": invitation.pk}))
        data = row["invitation"]
        self.assertEqual(data["profile_name"], self.profile.name)
        self.assertEqual((data["status"], data["requested_role"]), ("PENDING", "MEMBER"))
        self.assertTrue(data["can_accept"])
        self.assertTrue(data["can_decline"])
        self.assertFalse(data["can_open_profile"])
        self.assertNotIn(self.owner.email, str(response.data))
        self.assertNotIn(self.recipient.email, str(response.data))
        self.assertFalse({"recipient_user_id", "recipient_email", "token", "token_digest", "event_id", "user_id"} & set(data))
        self.assertEqual(self.client.get(self.count_url()).data, {"unread_count": 1})
        invitation.refresh_from_db()
        self.assertEqual(invitation.delivery_status, "FAILED")

    def test_mark_read_is_independent_idempotent_and_does_not_grant_membership(self):
        invitation, event, notification = self.new_notice()
        before = AuditLog.objects.count()
        first = self.client.post(self.read_url(notification), {}, format="json")
        second = self.client.post(self.read_url(notification), {}, format="json")
        self.assertEqual((first.status_code, second.status_code), (200, 200))
        self.assertEqual(first.data, second.data)
        self.assertTrue(second.data["is_read"])
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "PENDING")
        self.assertFalse(ProfileMembership.objects.filter(user=self.recipient).exists())
        self.assertEqual(AuditLog.objects.count(), before)
        emit_invitation_notification(event=event, actor=self.owner, invitation=invitation)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertEqual(Notification.objects.count(), 1)

    def test_wrong_account_get_count_and_mark_read_are_denied_even_with_known_uuid(self):
        _, _, notification = self.new_notice()
        for actor in (self.owner, self.outsider):
            self.client.force_login(actor)
            self.assertEqual(self.client.get(self.feed_url()).data["count"], 0)
            self.assertEqual(self.client.get(self.count_url()).data, {"unread_count": 0})
            self.assertEqual(self.client.post(self.read_url(notification), {}, format="json").status_code, 404)
        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_other_selected_profile_does_not_change_personal_invitation_scope(self):
        invitation, _, _ = self.new_notice()
        other = create_profile_with_owner(name="Recipient own profile", owner=self.recipient)
        response = self.client.get(self.feed_url(), {"profile_id": str(other.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(response.data["results"][0]["invitation_id"]), str(invitation.pk))
        self.assertEqual(response.data["count"], 1)

    def test_archived_and_terminal_notices_only_expose_the_own_minimum_state(self):
        invitation, _, notification = self.new_notice()
        Profile.objects.filter(pk=self.profile.pk).update(status="ARCHIVED")
        row = self.client.get(self.feed_url()).data["results"][0]
        self.assertFalse(row["invitation"]["can_accept"])
        self.assertFalse(row["invitation"]["can_open_profile"])
        self.assertEqual(self.client.post(self.read_url(notification), {}, format="json").status_code, 200)
        ProfileInvitation.objects.filter(pk=invitation.pk).update(status="REVOKED", revoked_at=timezone.now(), revoked_by=self.owner)
        row = self.client.get(self.feed_url()).data["results"][0]
        self.assertEqual(row["invitation"]["status"], "REVOKED")
        self.assertFalse(row["invitation"]["can_accept"])
        self.assertFalse(row["invitation"]["can_decline"])

    def test_inviter_loses_authority_without_hiding_recipient_notice_or_granting_access(self):
        _, _, _ = self.new_notice()
        ProfileMembership.objects.filter(pk=self.inviter.pk).update(is_active=False)
        row = self.client.get(self.feed_url()).data["results"][0]
        self.assertFalse(row["invitation"]["can_accept"])
        self.assertFalse(row["invitation"]["can_open_profile"])

    def test_inactive_recipient_and_staff_without_recipient_match_have_no_access(self):
        _, _, notification = self.new_notice()
        get_user_model().objects.filter(pk=self.recipient.pk).update(is_active=False)
        self.assertFalse(notifications_visible_to(self.recipient).exists())
        self.assertEqual(self.client.get(self.feed_url()).status_code, 403)
        self.outsider.is_staff = True
        self.outsider.save(update_fields=("is_staff",))
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(self.feed_url()).data["count"], 0)
        self.assertEqual(self.client.post(self.read_url(notification), {}, format="json").status_code, 404)

    def test_canonical_target_and_audit_scope_are_revalidated_for_feed_and_mark_read(self):
        _, event, notification = self.new_notice()
        other = create_profile_with_owner(name="Other private organization", owner=self.outsider)
        Notification.objects.filter(pk=notification.pk).update(profile=other)
        self.assertEqual(self.client.get(self.feed_url()).data["count"], 0)
        self.assertEqual(self.client.post(self.read_url(notification), {}, format="json").status_code, 404)
        Notification.objects.filter(pk=notification.pk).update(profile=self.profile)
        for change in ({"entity_id": uuid4()}, {"user_id": self.outsider.pk}, {"action": "unrelated.event"}):
            original = {key: getattr(event, key) for key in change}
            AuditLog.objects.filter(pk=event.pk).update(**change)
            self.assertFalse(notifications_visible_to(self.recipient).exists())
            self.assertEqual(self.client.post(self.read_url(notification), {}, format="json").status_code, 404)
            AuditLog.objects.filter(pk=event.pk).update(**original)

    def test_legacy_email_token_record_cannot_be_exposed_by_forged_invitation_notice(self):
        invitation, _, _ = self.new_notice()
        ProfileInvitation.objects.filter(pk=invitation.pk).update(acceptance_kind="EMAIL_TOKEN", token_digest="c" * 64)
        self.assertEqual(self.client.get(self.feed_url()).data["count"], 0)
        self.assertEqual(self.client.get(self.count_url()).data, {"unread_count": 0})

    def test_notification_context_database_guards_and_model_recipient_validation(self):
        invitation, event, notification = self.new_notice()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Notification.objects.create(user=self.outsider, title="Invalid", message="", event=event,
                event_type="PROFILE_INVITED", profile=self.profile)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Notification.objects.create(user=self.outsider, title="Invalid", message="", event=event,
                event_type="TASK_ASSIGNED", profile=self.profile, invitation=invitation)
        notification.user = self.outsider
        with self.assertRaises(ValidationError):
            notification.full_clean()

    def test_invalid_event_proof_and_mutable_instances_cannot_spoof_target(self):
        invitation, event, _ = self.new_notice()
        event.entity_id = uuid4()
        emit_invitation_notification(event=event, actor=self.owner, invitation=invitation)
        self.assertEqual(Notification.objects.count(), 1)
        AuditLog.objects.filter(pk=event.pk).update(entity_id=uuid4())
        with self.assertRaises(ValidationError):
            emit_invitation_notification(event=event, actor=self.owner, invitation=invitation)

    def test_outer_transaction_rolls_back_invitation_audit_and_notification_together(self):
        before = (ProfileInvitation.objects.count(), AuditLog.objects.count(), Notification.objects.count())
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.new_notice()
                raise RuntimeError("Synthetic transaction failure")
        self.assertEqual((ProfileInvitation.objects.count(), AuditLog.objects.count(), Notification.objects.count()), before)

    def test_expired_or_revoked_invitation_event_replay_creates_nothing(self):
        invitation, event, notification = self.new_notice()
        Notification.objects.filter(pk=notification.pk).delete()
        with patch("apps.notifications.services.timezone.now", return_value=invitation.expires_at + timedelta(seconds=1)):
            self.assertEqual(emit_invitation_notification(event=event, actor=self.owner, invitation=invitation), [])
        self.assertFalse(Notification.objects.exists())

    def test_notification_mark_read_keeps_csrf_strict_inputs_and_no_public_access(self):
        _, _, notification = self.new_notice()
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.recipient)
        self.assertEqual(client.post(self.read_url(notification), {}, format="json").status_code, 403)
        token = client.get(reverse("accounts:csrf")).data["csrf_token"]
        self.assertEqual(client.post(self.read_url(notification), {"invitation_id": str(notification.invitation_id)}, format="json", HTTP_X_CSRFTOKEN=token).status_code, 400)
        self.assertEqual(client.post(self.read_url(notification), {}, format="json", HTTP_X_CSRFTOKEN=token).status_code, 200)
        client.logout()
        self.assertEqual(client.get(self.feed_url()).status_code, 403)

    def test_invitation_notice_page_does_not_grow_database_queries_per_notice(self):
        self.new_notice()
        with CaptureQueriesContext(connection) as small:
            first = self.client.get(self.feed_url())
        self.assertEqual(first.data["count"], 1)
        for number in range(8):
            profile = create_profile_with_owner(name=f"Additional invitation {number}", owner=self.owner)
            inviter = ProfileMembership.objects.get(profile=profile, user=self.owner)
            self.new_notice(profile=profile, inviter=inviter)
        with CaptureQueriesContext(connection) as large:
            response = self.client.get(self.feed_url())
        self.assertEqual(response.data["count"], 9)
        self.assertLessEqual(len(large), len(small) + 2)


class ConcurrentInvitationNotificationTests(InvitationNotificationFixture, TransactionTestCase):
    def setUp(self):
        self.make_fixture()

    def parallel(self, callback):
        barrier = Barrier(2)
        def execute(number):
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout='15000ms'")
                barrier.wait(timeout=10)
                return callback(number)
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(execute, (0, 1)))

    def test_same_invitation_event_concurrent_retry_deduplicates_one_personal_notice(self):
        invitation, event, notification = self.new_notice()
        Notification.objects.filter(pk=notification.pk).delete()
        def emit(_):
            return len(emit_invitation_notification(
                event=AuditLog.objects.get(pk=event.pk),
                actor=get_user_model().objects.get(pk=self.owner.pk),
                invitation=ProfileInvitation.objects.get(pk=invitation.pk),
            ))
        self.assertEqual(self.parallel(emit), [1, 1])
        self.assertEqual(Notification.objects.filter(invitation=invitation).count(), 1)

    def test_concurrent_mark_read_is_consistent_before_profile_membership(self):
        _, _, notification = self.new_notice()
        def read(_):
            row = mark_notification_read(actor=get_user_model().objects.get(pk=self.recipient.pk), notification_id=notification.pk)
            return row.is_read, row.updated_at
        results = self.parallel(read)
        self.assertEqual(results[0], results[1])
        self.assertTrue(results[0][0])
        self.assertFalse(ProfileMembership.objects.filter(user=self.recipient).exists())
