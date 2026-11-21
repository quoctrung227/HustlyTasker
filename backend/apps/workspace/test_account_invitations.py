"""ACCOUNT V2 permission, lifecycle, privacy and shared quota regression."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch
import json
import hashlib

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from .account_invitations import create_account_invitation, respond_account_invitation, resend_account_invitation, invitation_candidates
from .invitation_services import InvitationConflict, InvitationRateLimitExceeded
from .models import (InvitationDirectoryAccess, InvitationEmailAttempt, ProfileInvitation,
                     ProfileMembership, Workspace, WorkspaceMember)
from .services import create_profile_with_owner

User = get_user_model()


class AccountInvitationFixture:
    def build_fixture(self):
        for label in ("owner", "admin", "member", "recipient", "second", "outsider"):
            setattr(self, label, User.objects.create_user(username="account-"+label, email="account-"+label+"@example.test", password=None))
        self.profile = create_profile_with_owner(name="ACCOUNT invitation Profile", owner=self.owner)
        self.owner_membership = ProfileMembership.objects.get(profile=self.profile, user=self.owner)
        self.admin_membership = ProfileMembership.objects.create(profile=self.profile, user=self.admin, role="ADMIN")
        ProfileMembership.objects.create(profile=self.profile, user=self.member, role="MEMBER")
        self.current_workspace = Workspace.objects.create(profile=self.profile, owner=self.owner,
            name="Actual current month", period=timezone.localdate().replace(day=1))
        self.other_profile = create_profile_with_owner(name="Other ACCOUNT Profile", owner=self.outsider)
        self.client = APIClient()

    def list_url(self, profile=None):
        return reverse("workspace:profile-invitation-list", kwargs={"profile_id": (profile or self.profile).pk})

    def candidate_url(self, profile=None):
        return reverse("workspace:profile-invitation-candidate-list", kwargs={"profile_id": (profile or self.profile).pk})

    def action_url(self, invitation, action="accept"):
        return reverse("workspace:profile-invitation-account-"+action, kwargs={"invitation_id": invitation.pk})

    def issue(self, target=None, role="MEMBER"):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.list_url(), {"recipient_user_id": str((target or self.recipient).pk), "requested_role": role}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return ProfileInvitation.objects.get(pk=response.data["id"])


class AccountInvitationApiTests(AccountInvitationFixture, TestCase):
    def setUp(self):
        self.build_fixture()

    def test_create_is_account_only_and_does_not_create_membership_or_workspace_access(self):
        self.client.force_authenticate(self.owner)
        legacy = self.client.post(self.list_url(), {"recipient_email": self.recipient.email}, format="json")
        self.assertEqual(legacy.status_code, 400)
        invitation = self.issue()
        self.assertEqual(invitation.acceptance_kind, "ACCOUNT")
        self.assertIsNone(invitation.token_digest)
        self.assertFalse(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient).exists())
        self.assertFalse(WorkspaceMember.objects.filter(user=self.recipient).exists())
        self.assertTrue(Notification.objects.filter(invitation=invitation, user=self.recipient).exists())

    def test_directory_denies_ordinary_member_staff_and_other_tenant(self):
        for actor, expected in ((self.member, 403), (self.outsider, 404)):
            actor.is_staff = True
            actor.save(update_fields=("is_staff",))
            self.client.force_authenticate(actor)
            self.assertEqual(self.client.get(self.candidate_url()).status_code, expected)
        self.assertEqual(InvitationDirectoryAccess.objects.count(), 0)

    def test_directory_pages_twenty_searches_server_side_and_bounds_queries(self):
        User.objects.bulk_create([User(username=f"scale-{i:04}", email=f"scale-{i}@example.test",
            first_name="Scale", last_name=f"Person {i:04}", password="!") for i in range(1000)])
        self.client.force_authenticate(self.owner)
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(self.candidate_url(), {"search": "Scale"})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["count"], 1000)
            self.assertEqual(len(response.data["results"]), 20)
        self.assertLessEqual(len(queries), 20)
        exact = self.client.get(self.candidate_url(), {"search": "Person 0042"})
        self.assertEqual(exact.data["count"], 1)
        self.assertEqual(exact.data["results"][0]["display_label"], "Scale Person 0042")
        self.assertEqual(self.client.get(self.candidate_url(), {"page_size": 100}).status_code, 400)

    def test_directory_only_exposes_approved_fields_and_safe_current_relation(self):
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.candidate_url(), {"search": "account-recipient"})
        row = response.data["results"][0]
        self.assertEqual(set(row), {"id", "display_label", "username", "masked_email", "relation", "can_invite"})
        self.assertEqual(row["username"], "account-recipient")
        self.assertIsNone(row["masked_email"])
        self.assertTrue(row["can_invite"])
        serialized = json.dumps(response.data)
        for private in (self.recipient.email, "is_staff", "email_verified", "phone", str(self.other_profile.pk)):
            self.assertNotIn(private, serialized)

    def test_masked_email_fallback_rejects_ambiguous_same_name_without_exposing_contact(self):
        for user, email in ((self.recipient, "same-one@example.test"), (self.second, "same-two@example.test")):
            user.username = email
            user.first_name = "Same"
            user.last_name = "Name"
            user.email = email
            user.save()
        self.client.force_authenticate(self.owner)
        response = self.client.get(self.candidate_url(), {"search": "Same Name"})
        self.assertEqual(len(response.data["results"]), 2)
        for row in response.data["results"]:
            self.assertIsNone(row["username"])
            self.assertEqual(row["masked_email"], "s***@e***")
            self.assertFalse(row["can_invite"])
        denied = self.client.post(self.list_url(), {"recipient_user_id": str(self.recipient.pk)}, format="json")
        self.assertEqual(denied.status_code, 409)

    def test_directory_rejects_invalid_unicode_control_and_oversize_query(self):
        self.client.force_authenticate(self.owner)
        for query in ("x"*101, "\x00", "\nname", "\ud800"):
            with self.subTest(query=repr(query)):
                response = self.client.get(self.candidate_url()+"?search="+__import__('urllib.parse', fromlist=['quote']).quote(query, errors="surrogatepass"))
                self.assertEqual(response.status_code, 400)

    def test_search_rolling_limit_is_durable_and_shared_between_profiles(self):
        other = create_profile_with_owner(name="Same owner second Profile", owner=self.owner)
        self.client.force_authenticate(self.owner)
        for _ in range(30):
            self.assertEqual(self.client.get(self.candidate_url()).status_code, 200)
        self.assertEqual(self.client.get(self.candidate_url(other)).status_code, 429)
        self.assertEqual(InvitationDirectoryAccess.objects.filter(user=self.owner).count(), 30)
        InvitationDirectoryAccess.objects.filter(user=self.owner).update(created_at=timezone.now()-timedelta(seconds=61))
        self.assertEqual(self.client.get(self.candidate_url(other)).status_code, 200)

    def test_role_ceiling_and_no_mass_assignment(self):
        self.client.force_authenticate(self.admin)
        denied = self.client.post(self.list_url(), {"recipient_user_id": str(self.recipient.pk), "requested_role": "ADMIN"}, format="json")
        self.assertEqual(denied.status_code, 403)
        for extra in ({"requested_role": "OWNER"}, {"owner_id": str(self.outsider.pk)}, {"status": "ACCEPTED"}, {"recipient_email": self.recipient.email}):
            response = self.client.post(self.list_url(), {"recipient_user_id": str(self.recipient.pk), **extra}, format="json")
            self.assertEqual(response.status_code, 400)
        response = self.client.post(self.list_url(), {"recipient_user_id": str(self.recipient.pk), "requested_role": "MEMBER"}, format="json")
        self.assertEqual(response.status_code, 201)

    def test_unrelated_actor_and_legacy_id_are_not_visible_in_account_inbox(self):
        invitation = self.issue()
        self.client.force_authenticate(self.outsider)
        self.assertEqual(self.client.get(reverse("workspace:profile-invitation-recipient-list")).data["count"], 0)
        self.assertEqual(self.client.post(self.action_url(invitation), {}, format="json").status_code, 404)
        self.client.force_authenticate(self.recipient)
        self.assertEqual(self.client.get(reverse("workspace:profile-invitation-recipient-list")).data["count"], 1)
        self.assertFalse(ProfileMembership.objects.filter(user=self.recipient).exists())

    def test_correct_account_can_accept_failed_mail_after_email_change_and_join_current_month(self):
        invitation = self.issue()
        ProfileInvitation.objects.filter(pk=invitation.pk).update(delivery_status="FAILED", delivery_attempted_at=timezone.now())
        self.recipient.email = "recipient-new@example.test"
        self.recipient.save()
        self.client.force_authenticate(self.recipient)
        response = self.client.post(self.action_url(invitation), {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "ACCEPTED")
        self.assertTrue(response.data["can_open_profile"])
        self.assertTrue(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient, role="MEMBER", is_active=True).exists())
        self.assertTrue(WorkspaceMember.objects.filter(workspace=self.current_workspace, user=self.recipient, role="MEMBER", is_active=True).exists())

    def test_replay_after_membership_revoke_does_not_restore_access_or_write_audit(self):
        invitation = self.issue()
        self.client.force_authenticate(self.recipient)
        self.assertEqual(self.client.post(self.action_url(invitation), {}, format="json").status_code, 200)
        ProfileMembership.objects.filter(profile=self.profile, user=self.recipient).update(is_active=False)
        before = AuditLog.objects.count()
        response = self.client.post(self.action_url(invitation), {}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["can_open_profile"])
        self.assertEqual(AuditLog.objects.count(), before)
        self.assertEqual(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient).count(), 1)
        self.assertFalse(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient, is_active=True).exists())

    def test_decline_is_independent_of_read_and_does_not_create_membership(self):
        invitation = self.issue()
        self.client.force_authenticate(self.recipient)
        self.admin_membership.is_active = False
        self.admin_membership.save()
        self.assertEqual(self.client.post(self.action_url(invitation, "decline"), {}, format="json").status_code, 200)
        self.assertFalse(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient).exists())
        self.assertFalse(Notification.objects.get(invitation=invitation).is_read)

    def test_inviter_revocation_expiry_and_archive_block_accept(self):
        invitation = self.issue()
        self.client.force_authenticate(self.recipient)
        self.owner_membership.is_active = False
        ProfileMembership.objects.filter(pk=self.owner_membership.pk).update(is_active=False)
        self.assertEqual(self.client.post(self.action_url(invitation), {}, format="json").status_code, 409)
        ProfileMembership.objects.filter(pk=self.owner_membership.pk).update(is_active=True)
        ProfileInvitation.objects.filter(pk=invitation.pk).update(expires_at=timezone.now()+timedelta(seconds=1))
        with patch("apps.workspace.account_invitations.timezone.now", return_value=timezone.now()+timedelta(seconds=2)):
            self.assertEqual(self.client.post(self.action_url(invitation), {}, format="json").status_code, 409)
        self.assertEqual(ProfileInvitation.objects.get(pk=invitation.pk).status, "EXPIRED")
        self.assertFalse(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient).exists())

    def test_rejoin_retains_role_cleanup_and_never_reactivates_revoked_workspace_row(self):
        old = ProfileMembership.objects.create(profile=self.profile, user=self.recipient, role="MEMBER", is_active=False)
        stale = WorkspaceMember.objects.create(workspace=self.current_workspace, user=self.recipient, role="MEMBER", is_active=False)
        WorkspaceMember.objects.filter(pk=stale.pk).update(is_active=True)
        invitation = self.issue()
        self.client.force_authenticate(self.recipient)
        self.assertEqual(self.client.post(self.action_url(invitation), {}, format="json").status_code, 200)
        old.refresh_from_db(); stale.refresh_from_db()
        self.assertTrue(old.is_active)
        self.assertFalse(stale.is_active)
        self.assertEqual(WorkspaceMember.objects.filter(workspace=self.current_workspace, user=self.recipient).count(), 1)

    def test_ambiguous_rejoin_is_fail_closed(self):
        for _ in range(2):
            ProfileMembership.objects.create(profile=self.profile, user=self.recipient, role="MEMBER", is_active=False)
        invitation = self.issue()
        self.client.force_authenticate(self.recipient)
        self.assertEqual(self.client.post(self.action_url(invitation), {}, format="json").status_code, 409)
        self.assertFalse(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient, is_active=True).exists())

    def test_email_retry_reserves_only_three_attempts_on_same_invitation_and_expiry(self):
        invitation = self.issue()
        expiry = invitation.expires_at
        url = reverse("workspace:profile-invitation-resend", kwargs={"profile_id": self.profile.pk, "invitation_id": invitation.pk})
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 200)
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 200)
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 429)
        self.assertEqual(InvitationEmailAttempt.objects.filter(invitation=invitation).count(), 3)
        self.assertEqual(ProfileInvitation.objects.count(), 1)
        invitation.refresh_from_db()
        self.assertEqual(invitation.expires_at, expiry)
        self.assertEqual(Notification.objects.filter(invitation=invitation).count(), 1)

    def test_notification_failure_rolls_back_invitation_audit_and_attempt(self):
        before = AuditLog.objects.count()
        with patch("apps.notifications.services.emit_invitation_notification", side_effect=RuntimeError("synthetic rollback")):
            with self.assertRaises(RuntimeError):
                create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=self.recipient.pk)
        self.assertFalse(ProfileInvitation.objects.exists())
        self.assertFalse(InvitationEmailAttempt.objects.exists())
        self.assertEqual(AuditLog.objects.count(), before)

    def test_account_email_reuse_does_not_transfer_or_block_other_account_invitation(self):
        old_email = self.recipient.email
        first = self.issue()
        self.recipient.email = "account-new-address@example.test"
        self.recipient.save()
        self.second.email = old_email
        self.second.save()
        second = self.issue(self.second)
        self.assertEqual(first.recipient_email_normalized, second.recipient_email_normalized)
        self.client.force_authenticate(self.second)
        self.assertEqual(self.client.post(self.action_url(first), {}, format="json").status_code, 404)
        self.assertEqual(self.client.post(self.action_url(second), {}, format="json").status_code, 200)
        self.client.force_authenticate(self.recipient)
        self.assertEqual(self.client.post(self.action_url(first), {}, format="json").status_code, 200)
        self.assertEqual(ProfileMembership.objects.filter(profile=self.profile, user__in=(self.recipient, self.second), is_active=True).count(), 2)

    def test_bound_legacy_address_reuse_allows_new_account_but_never_old_token_takeover(self):
        now = timezone.now()
        raw = "synthetic-bound-legacy-token-with-entropy-only"
        legacy = ProfileInvitation.objects.create(profile=self.profile, invited_by_membership=self.owner_membership,
            recipient_user=self.recipient, recipient_email_normalized=self.recipient.email,
            token_digest=hashlib.sha256(raw.encode()).hexdigest(), expires_at=now+timedelta(days=7),
            delivery_status="SENT", delivery_attempted_at=now, delivered_at=now)
        old_email = self.recipient.email
        self.recipient.email = "bound-legacy-user-new@example.test"
        self.recipient.save()
        self.second.email = old_email
        self.second.save()
        account = self.issue(self.second)
        self.client.force_authenticate(self.second)
        denied = self.client.post(reverse("workspace:profile-invitation-accept"), {"token": raw}, format="json")
        self.assertEqual(denied.status_code, 409)
        self.assertEqual(self.client.post(self.action_url(account), {}, format="json").status_code, 200)
        legacy.refresh_from_db()
        self.assertEqual(legacy.recipient_user_id, self.recipient.pk)
        self.assertEqual(legacy.status, "PENDING")

    def test_unbound_legacy_matching_email_blocks_duplicate_without_binding_or_exposing_record(self):
        now = timezone.now()
        legacy = ProfileInvitation.objects.create(profile=self.profile, invited_by_membership=self.owner_membership,
            recipient_email_normalized=self.recipient.email, requested_role="ADMIN",
            token_digest=hashlib.sha256(b"synthetic-unbound-legacy-token").hexdigest(), expires_at=now+timedelta(days=7))
        self.client.force_authenticate(self.admin)
        directory = self.client.get(self.candidate_url(), {"search": "account-recipient"})
        row = directory.data["results"][0]
        self.assertEqual(row["relation"], "UNAVAILABLE")
        self.assertFalse(row["can_invite"])
        self.assertNotIn(str(legacy.pk), json.dumps(directory.data))
        response = self.client.post(self.list_url(), {"recipient_user_id": str(self.recipient.pk)}, format="json")
        self.assertEqual(response.status_code, 409)
        legacy.refresh_from_db()
        self.assertIsNone(legacy.recipient_user_id)
        self.assertEqual(ProfileInvitation.objects.count(), 1)


class AccountInvitationConcurrencyTests(AccountInvitationFixture, TransactionTestCase):
    def setUp(self):
        self.build_fixture()

    def run_race(self, callbacks):
        barrier = Barrier(len(callbacks))
        def run(callback):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    callback()
                    return "ok"
                except InvitationConflict:
                    return "conflict"
                except InvitationRateLimitExceeded:
                    return "rate"
            finally:
                close_old_connections()
        with patch("apps.workspace.account_invitation_delivery.schedule_account_invitation_delivery"):
            with ThreadPoolExecutor(max_workers=len(callbacks)) as pool:
                futures = [pool.submit(run, callback) for callback in callbacks]
                return [future.result(timeout=30) for future in futures]

    def test_concurrent_duplicate_invite_has_exactly_one_pending_notification(self):
        def issue():
            create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=self.recipient.pk)
        self.assertCountEqual(self.run_race([issue, issue]), ["ok", "conflict"])
        self.assertEqual(ProfileInvitation.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(event_type="PROFILE_INVITED").count(), 1)

    def test_concurrent_accept_is_replay_safe_without_duplicate_audit(self):
        with patch("apps.workspace.account_invitation_delivery.schedule_account_invitation_delivery"):
            invitation = create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=self.recipient.pk)
        def accept():
            respond_account_invitation(actor=self.recipient, invitation_id=invitation.pk, accept=True)
        self.assertEqual(self.run_race([accept, accept]), ["ok", "ok"])
        self.assertEqual(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="profile.invitation.accepted").count(), 1)

    def test_cross_profile_reciprocal_invites_do_not_deadlock(self):
        def first():
            create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=self.outsider.pk)
        def second():
            create_account_invitation(actor=self.outsider, profile_id=self.other_profile.pk, recipient_user_id=self.owner.pk)
        self.assertEqual(self.run_race([first, second]), ["ok", "ok"])

    def test_cross_profile_create_and_accept_use_same_user_lock_order(self):
        with patch("apps.workspace.account_invitation_delivery.schedule_account_invitation_delivery"):
            invitation = create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=self.outsider.pk)
        def create():
            create_account_invitation(actor=self.outsider, profile_id=self.other_profile.pk, recipient_user_id=self.owner.pk)
        def accept():
            respond_account_invitation(actor=self.outsider, invitation_id=invitation.pk, accept=True)
        self.assertEqual(self.run_race([create, accept]), ["ok", "ok"])

    def test_cross_profile_reciprocal_email_retries_do_not_deadlock(self):
        with patch("apps.workspace.account_invitation_delivery.schedule_account_invitation_delivery"):
            first = create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=self.outsider.pk)
            second = create_account_invitation(actor=self.outsider, profile_id=self.other_profile.pk, recipient_user_id=self.owner.pk)
        callbacks = [
            lambda: resend_account_invitation(actor=self.owner, profile_id=self.profile.pk, invitation_id=first.pk),
            lambda: resend_account_invitation(actor=self.outsider, profile_id=self.other_profile.pk, invitation_id=second.pk),
        ]
        self.assertEqual(self.run_race(callbacks), ["ok", "ok"])
        self.assertEqual(InvitationEmailAttempt.objects.count(), 4)

    def test_recipient_last_daily_slot_is_shared_across_concurrent_profiles_and_inviters(self):
        now = timezone.now()
        for _ in range(4):
            ProfileInvitation.objects.create(profile=self.profile, invited_by_membership=self.owner_membership,
                recipient_user=self.recipient, recipient_email_normalized=self.recipient.email,
                acceptance_kind="ACCOUNT", token_digest=None, expires_at=now+timedelta(days=7),
                status="REVOKED", revoked_at=now, revoked_by=self.owner)
        callbacks = [
            lambda: create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=self.recipient.pk),
            lambda: create_account_invitation(actor=self.outsider, profile_id=self.other_profile.pk, recipient_user_id=self.recipient.pk),
        ]
        self.assertCountEqual(self.run_race(callbacks), ["ok", "rate"])
        self.assertEqual(ProfileInvitation.objects.filter(recipient_user=self.recipient).count(), 5)

    def test_search_last_minute_slot_is_shared_across_concurrent_profiles(self):
        second_profile = create_profile_with_owner(name="Concurrent second owned Profile", owner=self.owner)
        InvitationDirectoryAccess.objects.bulk_create([InvitationDirectoryAccess(user=self.owner) for _ in range(29)])
        callbacks = [
            lambda: invitation_candidates(actor=self.owner, profile_id=self.profile.pk),
            lambda: invitation_candidates(actor=self.owner, profile_id=second_profile.pk),
        ]
        self.assertCountEqual(self.run_race(callbacks), ["ok", "rate"])
        self.assertEqual(InvitationDirectoryAccess.objects.filter(user=self.owner).count(), 30)

    def test_email_last_attempt_slot_is_shared_between_concurrent_retries(self):
        with patch("apps.workspace.account_invitation_delivery.schedule_account_invitation_delivery"):
            invitation = create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=self.recipient.pk)
        InvitationEmailAttempt.objects.create(invitation=invitation, status="FAILED", finished_at=timezone.now())
        callback = lambda: resend_account_invitation(actor=self.owner, profile_id=self.profile.pk, invitation_id=invitation.pk)
        self.assertCountEqual(self.run_race([callback, callback]), ["ok", "rate"])
        self.assertEqual(InvitationEmailAttempt.objects.filter(invitation=invitation).count(), 3)
