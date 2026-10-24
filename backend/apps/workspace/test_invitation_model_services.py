import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.audit.models import AuditLog

from .invitation_delivery import InvitationDeliveryUnavailable
from .invitation_services import (
    InvitationConflict,
    InvitationRateLimitExceeded,
    accept_profile_invitation,
    create_profile_invitation,
    decline_profile_invitation,
    resend_profile_invitation,
    revoke_profile_invitation,
)
from .models import (
    Profile,
    ProfileInvitation,
    ProfileMembership,
    Workspace,
    WorkspaceMember,
)
from .services import create_profile_with_owner


User = get_user_model()
LOCMEM_MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    }
}


@override_settings(MAILERS=LOCMEM_MAILERS)
class ProfileInvitationModelAndServiceTests(TestCase):
    def setUp(self):
        self.owner = self.create_user("owner")
        self.admin = self.create_user("admin")
        self.member = self.create_user("member")
        self.recipient = self.create_user("recipient")
        self.wrong_recipient = self.create_user("wrong-recipient")
        self.other_owner = self.create_user("other-owner")

        self.profile = create_profile_with_owner(
            name="Invitation Profile",
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
        self.other_profile = create_profile_with_owner(
            name="Other Profile",
            owner=self.other_owner,
        )

    def create_user(self, suffix, *, email=None):
        return User.objects.create_user(
            email=email or f"inv-{suffix}@example.test",
            username=f"inv-{suffix}",
            password="test-password-only",
        )

    def issue(
        self,
        *,
        actor=None,
        profile=None,
        recipient=None,
        recipient_email=None,
        requested_role=ProfileInvitation.Role.MEMBER,
    ):
        captured = {}

        def capture_delivery(*, invitation, raw_token):
            captured["invitation_id"] = invitation.id
            captured["token"] = raw_token

        recipient_email = recipient_email or recipient.email
        with patch(
            "apps.workspace.invitation_services.schedule_invitation_delivery",
            side_effect=capture_delivery,
        ):
            invitation = create_profile_invitation(
                actor=actor or self.owner,
                profile_id=(profile or self.profile).id,
                recipient_email=recipient_email,
                requested_role=requested_role,
            )
        return invitation, captured["token"]

    def mark_sent(self, invitation):
        now = timezone.now()
        ProfileInvitation.objects.filter(id=invitation.id).update(
            delivery_status=ProfileInvitation.DeliveryStatus.SENT,
            delivery_attempted_at=now,
            delivered_at=now,
        )
        invitation.refresh_from_db()

    def test_create_normalizes_hashes_and_never_audits_raw_token(self):
        started_at = timezone.now()
        invitation, raw_token = self.issue(
            recipient_email=f"  {self.recipient.email.upper()}  ",
        )

        self.assertEqual(
            invitation.recipient_email_normalized,
            self.recipient.email,
        )
        self.assertEqual(invitation.recipient_user_id, self.recipient.id)
        self.assertEqual(
            invitation.requested_role,
            ProfileInvitation.Role.MEMBER,
        )
        self.assertEqual(invitation.status, ProfileInvitation.Status.PENDING)
        self.assertEqual(
            invitation.token_digest,
            hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(invitation.token_digest, raw_token)
        self.assertGreaterEqual(len(raw_token), 43)
        self.assertAlmostEqual(
            (invitation.expires_at - started_at).total_seconds(),
            timedelta(days=7).total_seconds(),
            delta=5,
        )
        self.assertFalse(
            ProfileMembership.objects.filter(
                profile=self.profile,
                user=self.recipient,
                is_active=True,
            ).exists()
        )

        audit = AuditLog.objects.get(
            action="profile.invitation.created",
            entity_id=invitation.id,
        )
        self.assertNotIn(raw_token, json.dumps(audit.metadata))
        self.assertNotIn(self.recipient.email, json.dumps(audit.metadata))

    def test_model_validation_and_database_constraints_fail_closed(self):
        invitation, _ = self.issue(recipient=self.recipient)

        malformed_email = ProfileInvitation(
            profile=self.profile,
            invited_by_membership=self.owner_membership,
            recipient_email_normalized="MixedCase@example.test",
            token_digest="b" * 64,
        )
        with self.assertRaises(ValidationError) as raised:
            malformed_email.full_clean()
        self.assertIn("recipient_email_normalized", raised.exception.message_dict)

        malformed_digest = ProfileInvitation(
            profile=self.profile,
            invited_by_membership=self.owner_membership,
            recipient_email_normalized="normalized@example.test",
            token_digest="not-a-sha256-digest",
        )
        with self.assertRaises(ValidationError) as raised:
            malformed_digest.full_clean()
        self.assertIn("token_digest", raised.exception.message_dict)

        duplicate = ProfileInvitation(
            profile=self.profile,
            invited_by_membership=self.owner_membership,
            recipient_email_normalized=invitation.recipient_email_normalized,
            recipient_user=self.recipient,
            token_digest="a" * 64,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ProfileInvitation.objects.bulk_create((duplicate,))

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProfileInvitation.objects.filter(id=invitation.id).update(
                status=ProfileInvitation.Status.ACCEPTED,
            )

    def test_owner_admin_member_role_ceiling_and_archived_profile(self):
        owner_admin_target = self.create_user("owner-admin-target")
        owner_admin_invitation, _ = self.issue(
            recipient=owner_admin_target,
            requested_role=ProfileInvitation.Role.ADMIN,
        )
        self.assertEqual(
            owner_admin_invitation.requested_role,
            ProfileInvitation.Role.ADMIN,
        )

        admin_target = self.create_user("admin-member-target")
        admin_invitation, _ = self.issue(
            actor=self.admin,
            recipient=admin_target,
        )
        self.assertEqual(
            admin_invitation.requested_role,
            ProfileInvitation.Role.MEMBER,
        )

        with self.assertRaises(PermissionDenied):
            self.issue(
                actor=self.admin,
                recipient=self.create_user("admin-admin-target"),
                requested_role=ProfileInvitation.Role.ADMIN,
            )
        with self.assertRaises(PermissionDenied):
            self.issue(
                actor=self.member,
                recipient=self.create_user("member-target"),
            )
        with self.assertRaises(ValidationError):
            self.issue(
                recipient=self.create_user("owner-target"),
                requested_role=ProfileMembership.Role.OWNER,
            )

        Profile.objects.filter(id=self.profile.id).update(
            status=Profile.Status.ARCHIVED,
        )
        with self.assertRaises(PermissionDenied):
            self.issue(recipient=self.create_user("archived-target"))

    def test_accept_creates_membership_without_disturbing_other_profile(self):
        other_membership = ProfileMembership.objects.create(
            profile=self.other_profile,
            user=self.recipient,
            role=ProfileMembership.Role.ADMIN,
        )
        invitation, raw_token = self.issue(
            recipient=self.recipient,
            requested_role=ProfileInvitation.Role.ADMIN,
        )
        self.mark_sent(invitation)

        membership = accept_profile_invitation(
            actor=self.recipient,
            token=raw_token,
        )

        invitation.refresh_from_db()
        other_membership.refresh_from_db()
        self.assertEqual(invitation.status, ProfileInvitation.Status.ACCEPTED)
        self.assertEqual(invitation.accepted_by_id, self.recipient.id)
        self.assertEqual(membership.role, ProfileMembership.Role.ADMIN)
        self.assertTrue(membership.is_active)
        self.assertTrue(other_membership.is_active)
        self.assertEqual(other_membership.role, ProfileMembership.Role.ADMIN)
        self.assertEqual(
            ProfileMembership.objects.filter(
                profile=self.profile,
                user=self.recipient,
                is_active=True,
            ).count(),
            1,
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="profile.membership.created_by_invitation",
                entity_id=membership.id,
            ).exists()
        )

        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=self.recipient,
                token=raw_token,
            )

    def test_accept_reactivates_matching_history_and_revokes_workspace_access(self):
        invitation, raw_token = self.issue(recipient=self.recipient)
        self.mark_sent(invitation)
        historical = ProfileMembership.objects.create(
            profile=self.profile,
            user=self.recipient,
            role=ProfileMembership.Role.MEMBER,
            is_active=True,
        )
        workspace = Workspace.objects.create(
            profile=self.profile,
            owner=self.owner,
            name="Historical Workspace",
            period=date(2026, 11, 1),
        )
        workspace_membership = WorkspaceMember.objects.create(
            workspace=workspace,
            user=self.recipient,
            role=WorkspaceMember.Role.ADMIN,
            is_active=True,
        )
        ProfileMembership.objects.filter(id=historical.id).update(
            is_active=False,
        )

        membership = accept_profile_invitation(
            actor=self.recipient,
            token=raw_token,
        )

        historical.refresh_from_db()
        workspace_membership.refresh_from_db()
        self.assertEqual(membership.id, historical.id)
        self.assertTrue(historical.is_active)
        self.assertFalse(workspace_membership.is_active)
        self.assertEqual(
            ProfileMembership.objects.filter(
                profile=self.profile,
                user=self.recipient,
            ).count(),
            1,
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="profile.membership.reactivated_by_invitation",
                entity_id=historical.id,
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                action="workspace.membership.revoked_on_profile_rejoin",
                entity_id=workspace_membership.id,
            ).exists()
        )

    def test_accept_does_not_change_active_member_role(self):
        invitation, raw_token = self.issue(recipient=self.recipient)
        self.mark_sent(invitation)
        membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=self.recipient,
            role=ProfileMembership.Role.ADMIN,
            is_active=True,
        )

        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=self.recipient,
                token=raw_token,
            )

        membership.refresh_from_db()
        invitation.refresh_from_db()
        self.assertEqual(membership.role, ProfileMembership.Role.ADMIN)
        self.assertTrue(membership.is_active)
        self.assertEqual(invitation.status, ProfileInvitation.Status.PENDING)

    def test_inactive_membership_role_mismatch_fails_without_reactivation(self):
        invitation, raw_token = self.issue(
            recipient=self.recipient,
            requested_role=ProfileInvitation.Role.ADMIN,
        )
        self.mark_sent(invitation)
        historical = ProfileMembership.objects.create(
            profile=self.profile,
            user=self.recipient,
            role=ProfileMembership.Role.MEMBER,
            is_active=False,
        )

        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=self.recipient,
                token=raw_token,
            )

        historical.refresh_from_db()
        invitation.refresh_from_db()
        self.assertFalse(historical.is_active)
        self.assertEqual(invitation.status, ProfileInvitation.Status.PENDING)

    def test_wrong_recipient_and_revoked_inviter_cannot_accept(self):
        invitation, raw_token = self.issue(recipient=self.recipient)
        self.mark_sent(invitation)

        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=self.wrong_recipient,
                token=raw_token,
            )

        ProfileMembership.objects.filter(id=self.owner_membership.id).update(
            is_active=False,
        )
        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=self.recipient,
                token=raw_token,
            )
        self.assertFalse(
            ProfileMembership.objects.filter(
                profile=self.profile,
                user=self.recipient,
                is_active=True,
            ).exists()
        )

    def test_ambiguous_or_changed_account_email_fails_closed(self):
        collision_email = "identity-collision@example.test"
        self.create_user("collision-lower", email=collision_email)
        self.create_user(
            "collision-upper",
            email="IDENTITY-COLLISION@example.test",
        )
        with self.assertRaises(InvitationConflict):
            self.issue(recipient_email=collision_email)

        invitation, raw_token = self.issue(recipient=self.recipient)
        self.mark_sent(invitation)
        User.objects.filter(id=self.recipient.id).update(
            email="recipient-changed@example.test",
        )
        self.recipient.refresh_from_db()

        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=self.recipient,
                token=raw_token,
            )

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProfileInvitation.Status.PENDING)

    def test_ambiguous_or_owner_membership_history_cannot_reactivate(self):
        ambiguous_user = self.create_user("ambiguous-history")
        ambiguous_invitation, ambiguous_token = self.issue(
            recipient=ambiguous_user,
        )
        self.mark_sent(ambiguous_invitation)
        for _ in range(2):
            ProfileMembership.objects.create(
                profile=self.profile,
                user=ambiguous_user,
                role=ProfileMembership.Role.MEMBER,
                is_active=False,
            )

        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=ambiguous_user,
                token=ambiguous_token,
            )

        former_owner = self.create_user("former-owner")
        owner_invitation, owner_token = self.issue(recipient=former_owner)
        self.mark_sent(owner_invitation)
        ProfileMembership.objects.create(
            profile=self.profile,
            user=former_owner,
            role=ProfileMembership.Role.OWNER,
            is_active=False,
        )

        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=former_owner,
                token=owner_token,
            )

        self.assertFalse(
            ProfileMembership.objects.filter(
                profile=self.profile,
                user__in=(ambiguous_user, former_owner),
                is_active=True,
            ).exists()
        )

    def test_decline_revoke_expire_and_replay_are_terminal(self):
        decline_target = self.create_user("decline-target")
        declined, declined_token = self.issue(recipient=decline_target)
        self.mark_sent(declined)
        decline_profile_invitation(
            actor=decline_target,
            token=declined_token,
        )
        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=decline_target,
                token=declined_token,
            )

        revoke_target = self.create_user("revoke-target")
        revoked, revoked_token = self.issue(recipient=revoke_target)
        self.mark_sent(revoked)
        revoke_profile_invitation(
            actor=self.owner,
            profile_id=self.profile.id,
            invitation_id=revoked.id,
        )
        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=revoke_target,
                token=revoked_token,
            )

        expired_target = self.create_user("expired-target")
        expired, expired_token = self.issue(recipient=expired_target)
        self.mark_sent(expired)
        now = timezone.now()
        ProfileInvitation.objects.filter(id=expired.id).update(
            created_at=now - timedelta(days=8),
            expires_at=now - timedelta(days=1),
        )
        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=expired_target,
                token=expired_token,
            )
        expired.refresh_from_db()
        self.assertEqual(expired.status, ProfileInvitation.Status.EXPIRED)
        self.assertIsNotNone(expired.expired_at)

        accepted_target = self.create_user("replay-target")
        accepted, accepted_token = self.issue(recipient=accepted_target)
        self.mark_sent(accepted)
        accept_profile_invitation(actor=accepted_target, token=accepted_token)
        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(actor=accepted_target, token=accepted_token)

    def test_resend_rotates_credential_and_invalidates_old_token(self):
        invitation, old_token = self.issue(recipient=self.recipient)
        self.mark_sent(invitation)
        captured = {}

        def capture_delivery(*, invitation, raw_token):
            captured["id"] = invitation.id
            captured["token"] = raw_token

        with patch(
            "apps.workspace.invitation_services.schedule_invitation_delivery",
            side_effect=capture_delivery,
        ):
            replacement = resend_profile_invitation(
                actor=self.owner,
                profile_id=self.profile.id,
                invitation_id=invitation.id,
            )

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProfileInvitation.Status.REVOKED)
        self.assertEqual(replacement.replaces_id, invitation.id)
        self.assertNotEqual(replacement.token_digest, invitation.token_digest)
        self.assertNotEqual(captured["token"], old_token)

        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=self.recipient,
                token=old_token,
            )
        self.mark_sent(replacement)
        membership = accept_profile_invitation(
            actor=self.recipient,
            token=captured["token"],
        )
        self.assertTrue(membership.is_active)

    def test_archived_profile_blocks_accept_and_invitation_mutations(self):
        invitation, raw_token = self.issue(recipient=self.recipient)
        self.mark_sent(invitation)
        Profile.objects.filter(id=self.profile.id).update(
            status=Profile.Status.ARCHIVED,
        )

        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(
                actor=self.recipient,
                token=raw_token,
            )
        with self.assertRaises(PermissionDenied):
            revoke_profile_invitation(
                actor=self.owner,
                profile_id=self.profile.id,
                invitation_id=invitation.id,
            )
        with self.assertRaises(PermissionDenied):
            resend_profile_invitation(
                actor=self.owner,
                profile_id=self.profile.id,
                invitation_id=invitation.id,
            )

    def test_audit_failure_rolls_back_invitation(self):
        with patch(
            "apps.workspace.invitation_services._write_invitation_audit",
            side_effect=RuntimeError("test-only audit failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.issue(recipient=self.recipient)

        self.assertFalse(
            ProfileInvitation.objects.filter(
                profile=self.profile,
                recipient_email_normalized=self.recipient.email,
            ).exists()
        )
        self.assertFalse(
            ProfileMembership.objects.filter(
                profile=self.profile,
                user=self.recipient,
                is_active=True,
            ).exists()
        )

    def test_delivery_runs_only_after_commit_and_records_success(self):
        mail.outbox.clear()
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            invitation = create_profile_invitation(
                actor=self.owner,
                profile_id=self.profile.id,
                recipient_email=self.recipient.email,
            )
            self.assertEqual(len(mail.outbox), 0)

        invitation.refresh_from_db()
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.recipient.email])
        self.assertEqual(
            invitation.delivery_status,
            ProfileInvitation.DeliveryStatus.SENT,
        )
        self.assertIsNotNone(invitation.delivered_at)
        self.assertNotIn(invitation.token_digest, mail.outbox[0].body)

    def test_delivery_failure_is_recorded_without_false_success(self):
        with patch(
            "apps.common.email_delivery.EmailMessage.send",
            side_effect=RuntimeError("test-only delivery failure"),
        ):
            with self.assertRaises(InvitationDeliveryUnavailable):
                with self.captureOnCommitCallbacks(execute=True):
                    invitation = create_profile_invitation(
                        actor=self.owner,
                        profile_id=self.profile.id,
                        recipient_email=self.recipient.email,
                    )

        invitation.refresh_from_db()
        self.assertEqual(
            invitation.delivery_status,
            ProfileInvitation.DeliveryStatus.FAILED,
        )
        self.assertIsNotNone(invitation.delivery_attempted_at)
        self.assertIsNone(invitation.delivered_at)
        self.assertFalse(
            ProfileMembership.objects.filter(
                profile=self.profile,
                user=self.recipient,
                is_active=True,
            ).exists()
        )

    def test_failed_delivery_recovers_only_through_rotated_resend(self):
        failed_token = "F" * 43
        with patch(
            "apps.workspace.invitation_services.secrets.token_urlsafe",
            return_value=failed_token,
        ), patch(
            "apps.common.email_delivery.EmailMessage.send",
            side_effect=RuntimeError("test-only delivery failure"),
        ):
            with self.assertRaises(InvitationDeliveryUnavailable):
                with self.captureOnCommitCallbacks(execute=True):
                    failed = create_profile_invitation(
                        actor=self.owner,
                        profile_id=self.profile.id,
                        recipient_email=self.recipient.email,
                    )

        replacement_token = "R" * 43
        with patch(
            "apps.workspace.invitation_services.secrets.token_urlsafe",
            return_value=replacement_token,
        ), patch(
            "apps.workspace.invitation_services.schedule_invitation_delivery"
        ):
            replacement = resend_profile_invitation(
                actor=self.owner,
                profile_id=self.profile.id,
                invitation_id=failed.id,
            )

        failed.refresh_from_db()
        self.assertEqual(failed.status, ProfileInvitation.Status.REVOKED)
        self.assertEqual(replacement.replaces_id, failed.id)
        self.assertEqual(
            replacement.token_digest,
            hashlib.sha256(replacement_token.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(replacement.token_digest, failed.token_digest)

    def test_outer_transaction_rollback_discards_delivery_callback(self):
        mail.outbox.clear()
        baseline = ProfileInvitation.objects.count()
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            try:
                with transaction.atomic():
                    create_profile_invitation(
                        actor=self.owner,
                        profile_id=self.profile.id,
                        recipient_email=self.recipient.email,
                    )
                    raise RuntimeError("test-only rollback")
            except RuntimeError:
                pass

        self.assertEqual(callbacks, [])
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(ProfileInvitation.objects.count(), baseline)

    def test_durable_recipient_rate_limit_counts_rotated_history(self):
        first, _ = self.issue(recipient=self.recipient)
        revoke_profile_invitation(
            actor=self.owner,
            profile_id=self.profile.id,
            invitation_id=first.id,
        )

        with patch(
            "apps.workspace.invitation_services.MAX_INVITATIONS_PER_RECIPIENT",
            1,
        ):
            with self.assertRaises(InvitationRateLimitExceeded):
                self.issue(
                    actor=self.other_owner,
                    profile=self.other_profile,
                    recipient=self.recipient,
                )


@override_settings(MAILERS=LOCMEM_MAILERS)
class ProfileInvitationConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.owner = User.objects.create_user(
            email="inv-concurrency-owner@example.test",
            username="inv-concurrency-owner",
            password="test-password-only",
        )
        self.recipient = User.objects.create_user(
            email="inv-concurrency-recipient@example.test",
            username="inv-concurrency-recipient",
            password="test-password-only",
        )
        self.profile = create_profile_with_owner(
            name="Concurrency Profile",
            owner=self.owner,
        )
        self.owner_membership = ProfileMembership.objects.get(
            profile=self.profile,
            user=self.owner,
        )

    def create_sent_invitation(self, raw_token):
        now = timezone.now()
        return ProfileInvitation.objects.create(
            profile=self.profile,
            recipient_email_normalized=self.recipient.email,
            recipient_user=self.recipient,
            requested_role=ProfileInvitation.Role.MEMBER,
            invited_by_membership=self.owner_membership,
            token_digest=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            status=ProfileInvitation.Status.PENDING,
            expires_at=now + timedelta(days=7),
            delivery_status=ProfileInvitation.DeliveryStatus.SENT,
            delivery_attempted_at=now,
            delivered_at=now,
        )

    def test_concurrent_accept_creates_exactly_one_membership(self):
        raw_token = "concurrency-test-token-with-at-least-256-bits-of-test-data"
        invitation = self.create_sent_invitation(raw_token)
        barrier = Barrier(2)

        def accept_once():
            close_old_connections()
            try:
                actor = User.objects.get(id=self.recipient.id)
                barrier.wait(timeout=10)
                try:
                    accept_profile_invitation(actor=actor, token=raw_token)
                except InvitationConflict:
                    return "conflict"
                return "accepted"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(accept_once) for _ in range(2)]
            results = [future.result(timeout=20) for future in futures]

        self.assertCountEqual(results, ("accepted", "conflict"))
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProfileInvitation.Status.ACCEPTED)
        self.assertEqual(
            ProfileMembership.objects.filter(
                profile=self.profile,
                user=self.recipient,
                is_active=True,
            ).count(),
            1,
        )
        self.assertEqual(
            AuditLog.objects.filter(
                action="profile.invitation.accepted",
                entity_id=invitation.id,
            ).count(),
            1,
        )

    def test_concurrent_revoke_and_resend_have_one_winner(self):
        invitation = self.create_sent_invitation(
            "concurrency-manager-action-token-with-test-entropy-only"
        )
        barrier = Barrier(2)

        def mutate(action):
            close_old_connections()
            try:
                actor = User.objects.get(id=self.owner.id)
                barrier.wait(timeout=10)
                try:
                    if action == "revoke":
                        revoke_profile_invitation(
                            actor=actor,
                            profile_id=self.profile.id,
                            invitation_id=invitation.id,
                        )
                    else:
                        resend_profile_invitation(
                            actor=actor,
                            profile_id=self.profile.id,
                            invitation_id=invitation.id,
                        )
                except InvitationConflict:
                    return "conflict"
                return action
            finally:
                close_old_connections()

        with patch(
            "apps.workspace.invitation_services.schedule_invitation_delivery"
        ):
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = (
                    executor.submit(mutate, "revoke"),
                    executor.submit(mutate, "resend"),
                )
                results = [future.result(timeout=20) for future in futures]

        self.assertIn("conflict", results)
        self.assertEqual(results.count("conflict"), 1)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProfileInvitation.Status.REVOKED)
        self.assertLessEqual(
            ProfileInvitation.objects.filter(replaces=invitation).count(),
            1,
        )

    def test_concurrent_accept_and_revoke_have_one_terminal_winner(self):
        raw_token = "accept-revoke-race-token-with-test-entropy-only-0001"
        invitation = self.create_sent_invitation(raw_token)
        barrier = Barrier(2)

        def mutate(action):
            close_old_connections()
            try:
                actor_id = (
                    self.recipient.id if action == "accept" else self.owner.id
                )
                actor = User.objects.get(id=actor_id)
                barrier.wait(timeout=10)
                try:
                    if action == "accept":
                        accept_profile_invitation(actor=actor, token=raw_token)
                    else:
                        revoke_profile_invitation(
                            actor=actor,
                            profile_id=self.profile.id,
                            invitation_id=invitation.id,
                        )
                except InvitationConflict:
                    return "conflict"
                return action
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(mutate, "accept"),
                executor.submit(mutate, "revoke"),
            )
            results = [future.result(timeout=20) for future in futures]

        self.assertEqual(results.count("conflict"), 1)
        invitation.refresh_from_db()
        self.assertIn(
            invitation.status,
            (
                ProfileInvitation.Status.ACCEPTED,
                ProfileInvitation.Status.REVOKED,
            ),
        )
        active_memberships = ProfileMembership.objects.filter(
            profile=self.profile,
            user=self.recipient,
            is_active=True,
        ).count()
        self.assertEqual(
            active_memberships,
            1 if invitation.status == ProfileInvitation.Status.ACCEPTED else 0,
        )
