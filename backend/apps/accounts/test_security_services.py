import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.db import IntegrityError, close_old_connections, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.workspace.invitation_services import (
    accept_profile_invitation,
    create_profile_invitation,
)
from apps.workspace.models import ProfileInvitation, ProfileMembership
from apps.workspace.services import create_profile_with_owner

from .email_delivery import AccountSecurityDeliveryUnavailable
from .models import AccountSecurityToken
from .security_services import (
    AccountSecurityConflict,
    confirm_email_verification,
    confirm_password_reset,
    request_email_verification,
    request_password_reset,
)
from .test_security_api import extract_latest_token


User = get_user_model()
CURRENT_PASSWORD = "Z3bra!River$9284"
NEW_PASSWORD = "V10let!Harbor$7316"
LOCMEM_MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    }
}


@override_settings(MAILERS=LOCMEM_MAILERS)
class AccountSecurityModelAndServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="security-service@example.test",
            username="security-service",
            password=CURRENT_PASSWORD,
        )
        self.other_user = User.objects.create_user(
            email="other-security-service@example.test",
            username="other-security-service",
            password=CURRENT_PASSWORD,
        )

    def issue_verification(self, user=None):
        with self.captureOnCommitCallbacks(execute=True):
            request_email_verification(user=user or self.user)
        record = AccountSecurityToken.objects.get(
            user=user or self.user,
            purpose=AccountSecurityToken.Purpose.EMAIL_VERIFICATION,
            status=AccountSecurityToken.Status.PENDING,
        )
        return record, extract_latest_token()

    def issue_reset(self, email=None):
        with self.captureOnCommitCallbacks(execute=True):
            request_password_reset(email=email or self.user.email)
        record = AccountSecurityToken.objects.get(
            user=self.user,
            purpose=AccountSecurityToken.Purpose.PASSWORD_RESET,
            status=AccountSecurityToken.Status.PENDING,
        )
        return record, extract_latest_token()

    def token_fields(self, *, suffix, **overrides):
        values = {
            "user": self.user,
            "purpose": AccountSecurityToken.Purpose.EMAIL_VERIFICATION,
            "email_normalized": self.user.email.strip().casefold(),
            "token_digest": hashlib.sha256(
                f"model-token-{suffix}".encode("utf-8")
            ).hexdigest(),
            "expires_at": timezone.now() + timedelta(hours=1),
            "delivery_status": AccountSecurityToken.DeliveryStatus.QUEUED,
        }
        values.update(overrides)
        if (
            values["purpose"] == AccountSecurityToken.Purpose.PASSWORD_RESET
            and "password_fingerprint" not in values
        ):
            values["password_fingerprint"] = hashlib.sha256(
                self.user.password.encode("utf-8")
            ).hexdigest()
        return values

    def test_legacy_user_starts_unverified_without_affecting_password(self):
        self.assertIsNone(self.user.email_verified_at)
        self.assertIsNone(self.user.verified_email_normalized)
        self.assertFalse(self.user.is_email_verified)
        self.assertTrue(self.user.check_password(CURRENT_PASSWORD))

    def test_issued_tokens_use_the_approved_purpose_ttls(self):
        verification, _ = self.issue_verification()
        reset, _ = self.issue_reset()

        self.assertAlmostEqual(
            (verification.expires_at - verification.created_at).total_seconds(),
            timedelta(hours=24).total_seconds(),
            delta=2,
        )
        self.assertAlmostEqual(
            (reset.expires_at - reset.created_at).total_seconds(),
            timedelta(hours=1).total_seconds(),
            delta=2,
        )

    def test_token_is_digest_only_and_audit_metadata_contains_no_secret(self):
        record, raw_token = self.issue_verification()

        self.assertEqual(len(record.token_digest), 64)
        self.assertNotEqual(record.token_digest, raw_token)
        self.assertNotIn(raw_token, record.token_digest)
        serialized_audit = json.dumps(
            list(
                AuditLog.objects.all().values(
                    "action",
                    "entity_name",
                    "entity_id",
                    "metadata",
                )
            ),
            default=str,
        )
        self.assertNotIn(raw_token, serialized_audit)
        self.assertNotIn(record.token_digest, serialized_audit)
        self.assertNotIn(self.user.email, serialized_audit)

    def test_user_verification_pair_constraint_rejects_partial_state(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.filter(id=self.user.id).update(
                    email_verified_at=timezone.now(),
                    verified_email_normalized=None,
                )

        self.user.refresh_from_db()
        self.assertIsNone(self.user.email_verified_at)
        self.assertIsNone(self.user.verified_email_normalized)

    def test_token_constraints_reject_duplicate_pending_and_invalid_terminal_state(self):
        AccountSecurityToken.objects.create(**self.token_fields(suffix="first"))

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AccountSecurityToken.objects.create(
                    **self.token_fields(suffix="duplicate-pending")
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AccountSecurityToken.objects.create(
                    **self.token_fields(
                        suffix="missing-consumed-at",
                        purpose=AccountSecurityToken.Purpose.PASSWORD_RESET,
                        status=AccountSecurityToken.Status.CONSUMED,
                        delivery_status=AccountSecurityToken.DeliveryStatus.SENT,
                        delivery_attempted_at=timezone.now(),
                        delivered_at=timezone.now(),
                    )
                )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AccountSecurityToken.objects.create(
                    **self.token_fields(
                        suffix="consume-without-delivery",
                        purpose=AccountSecurityToken.Purpose.PASSWORD_RESET,
                        status=AccountSecurityToken.Status.CONSUMED,
                        consumed_at=timezone.now(),
                    )
                )

    def test_cross_purpose_token_cannot_be_reused(self):
        _, verification_token = self.issue_verification()

        with self.assertRaises(AccountSecurityConflict):
            confirm_password_reset(
                raw_token=verification_token,
                new_password=NEW_PASSWORD,
            )

        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(CURRENT_PASSWORD))
        verification = AccountSecurityToken.objects.get(
            user=self.user,
            purpose=AccountSecurityToken.Purpose.EMAIL_VERIFICATION,
        )
        self.assertEqual(verification.status, AccountSecurityToken.Status.PENDING)

    def test_wrong_user_and_changed_email_cannot_confirm_verification(self):
        record, raw_token = self.issue_verification()

        with self.assertRaises(AccountSecurityConflict):
            confirm_email_verification(
                actor=self.other_user,
                raw_token=raw_token,
            )
        self.user.email = "changed-security-service@example.test"
        self.user.save(update_fields=("email", "updated_at"))
        with self.assertRaises(AccountSecurityConflict):
            confirm_email_verification(
                actor=self.user,
                raw_token=raw_token,
            )

        self.user.refresh_from_db()
        record.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)
        self.assertNotEqual(record.status, AccountSecurityToken.Status.CONSUMED)

    def test_ambiguous_verification_identity_fails_closed(self):
        ambiguous = User.objects.create_user(
            email="SECURITY-SERVICE@example.test",
            username="ambiguous-security-service",
            password=CURRENT_PASSWORD,
        )

        with self.assertRaises(AccountSecurityConflict):
            request_email_verification(user=ambiguous)

        self.assertFalse(
            AccountSecurityToken.objects.filter(user=ambiguous).exists()
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_email_change_clears_verification_and_revokes_pending_proof(self):
        _, raw_token = self.issue_verification()
        confirm_email_verification(actor=self.user, raw_token=raw_token)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

        pending = AccountSecurityToken.objects.create(
            **self.token_fields(suffix="post-verification-pending")
        )
        self.user.email = "changed-verified-security@example.test"
        self.user.save(update_fields=("email", "updated_at"))

        self.user.refresh_from_db()
        pending.refresh_from_db()
        self.assertIsNone(self.user.email_verified_at)
        self.assertIsNone(self.user.verified_email_normalized)
        self.assertFalse(self.user.is_email_verified)
        self.assertEqual(pending.status, AccountSecurityToken.Status.REVOKED)
        self.assertIsNotNone(pending.revoked_at)

    def test_email_change_permanently_revokes_old_password_reset_token(self):
        record, raw_token = self.issue_reset()
        original_email = self.user.email

        self.user.email = "changed-reset-identity@example.test"
        self.user.save(update_fields=("email", "updated_at"))
        self.user.email = original_email
        self.user.save(update_fields=("email", "updated_at"))

        record.refresh_from_db()
        self.assertEqual(record.status, AccountSecurityToken.Status.REVOKED)
        self.assertIsNotNone(record.revoked_at)
        with self.assertRaises(AccountSecurityConflict):
            confirm_password_reset(
                raw_token=raw_token,
                new_password=NEW_PASSWORD,
            )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(CURRENT_PASSWORD))

    def test_unsent_tokens_cannot_confirm(self):
        verification, verification_raw = self.issue_verification()
        AccountSecurityToken.objects.filter(id=verification.id).update(
            delivery_status=AccountSecurityToken.DeliveryStatus.QUEUED,
            delivery_attempted_at=None,
            delivered_at=None,
        )
        with self.assertRaises(AccountSecurityConflict):
            confirm_email_verification(
                actor=self.user,
                raw_token=verification_raw,
            )

        reset, reset_raw = self.issue_reset()
        AccountSecurityToken.objects.filter(id=reset.id).update(
            delivery_status=AccountSecurityToken.DeliveryStatus.FAILED,
            delivery_attempted_at=timezone.now(),
            delivered_at=None,
        )
        with self.assertRaises(AccountSecurityConflict):
            confirm_password_reset(
                raw_token=reset_raw,
                new_password=NEW_PASSWORD,
            )

        self.user.refresh_from_db()
        verification.refresh_from_db()
        reset.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)
        self.assertTrue(self.user.check_password(CURRENT_PASSWORD))
        self.assertEqual(
            verification.status,
            AccountSecurityToken.Status.PENDING,
        )
        self.assertEqual(reset.status, AccountSecurityToken.Status.PENDING)

    def test_password_reset_audit_failure_rolls_back_password_and_consumption(self):
        record, raw_token = self.issue_reset()

        with patch(
            "apps.accounts.security_services.AuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                confirm_password_reset(
                    raw_token=raw_token,
                    new_password=NEW_PASSWORD,
                )

        self.user.refresh_from_db()
        record.refresh_from_db()
        self.assertTrue(self.user.check_password(CURRENT_PASSWORD))
        self.assertEqual(record.status, AccountSecurityToken.Status.PENDING)
        self.assertIsNone(record.consumed_at)

    def test_verification_audit_failure_rolls_back_user_and_token(self):
        record, raw_token = self.issue_verification()

        with patch(
            "apps.accounts.security_services.AuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                confirm_email_verification(
                    actor=self.user,
                    raw_token=raw_token,
                )

        self.user.refresh_from_db()
        record.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)
        self.assertEqual(record.status, AccountSecurityToken.Status.PENDING)
        self.assertIsNone(record.consumed_at)

    def test_verification_delivery_failure_is_recorded_without_false_success(self):
        with patch(
            "apps.common.email_delivery.EmailMessage.send",
            side_effect=RuntimeError("test-only delivery failure"),
        ):
            with self.assertRaises(AccountSecurityDeliveryUnavailable):
                with self.captureOnCommitCallbacks(execute=True):
                    request_email_verification(user=self.user)

        record = AccountSecurityToken.objects.get(
            user=self.user,
            purpose=AccountSecurityToken.Purpose.EMAIL_VERIFICATION,
        )
        self.assertEqual(record.status, AccountSecurityToken.Status.PENDING)
        self.assertEqual(
            record.delivery_status,
            AccountSecurityToken.DeliveryStatus.FAILED,
        )
        self.assertIsNotNone(record.delivery_attempted_at)
        self.assertIsNone(record.delivered_at)

    def test_outer_rollback_discards_token_audit_and_delivery(self):
        initial_mail_count = len(mail.outbox)

        with self.assertRaises(RuntimeError):
            with self.captureOnCommitCallbacks(execute=True):
                with transaction.atomic():
                    request_email_verification(user=self.user)
                    raise RuntimeError("roll back outer transaction")

        self.assertFalse(
            AccountSecurityToken.objects.filter(user=self.user).exists()
        )
        self.assertFalse(
            AuditLog.objects.filter(
                action="account.email_verification.requested"
            ).exists()
        )
        self.assertEqual(len(mail.outbox), initial_mail_count)

    def test_manual_password_change_revokes_pending_reset_token(self):
        record, raw_token = self.issue_reset()
        manual_password = "M4nual!Password$927"

        self.user.set_password(manual_password)
        self.user.save(update_fields=("password", "updated_at"))

        record.refresh_from_db()
        self.assertEqual(record.status, AccountSecurityToken.Status.REVOKED)
        self.assertIsNotNone(record.revoked_at)
        with self.assertRaises(AccountSecurityConflict):
            confirm_password_reset(
                raw_token=raw_token,
                new_password=NEW_PASSWORD,
            )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(manual_password))

    def test_direct_password_update_invalidates_reset_fingerprint(self):
        record, raw_token = self.issue_reset()
        direct_password = "D1rect!Password$492"

        User.objects.filter(id=self.user.id).update(
            password=make_password(direct_password)
        )

        record.refresh_from_db()
        self.assertEqual(record.status, AccountSecurityToken.Status.PENDING)
        with self.assertRaises(AccountSecurityConflict):
            confirm_password_reset(
                raw_token=raw_token,
                new_password=NEW_PASSWORD,
            )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(direct_password))

    def test_unusable_password_transition_revokes_pending_reset_token(self):
        record, raw_token = self.issue_reset()

        self.user.set_unusable_password()
        self.user.save(update_fields=("password", "updated_at"))

        record.refresh_from_db()
        self.assertEqual(record.status, AccountSecurityToken.Status.REVOKED)
        with self.assertRaises(AccountSecurityConflict):
            confirm_password_reset(
                raw_token=raw_token,
                new_password=NEW_PASSWORD,
            )
        self.user.refresh_from_db()
        self.assertFalse(self.user.has_usable_password())

    def _issue_sent_invitation(self):
        owner = User.objects.create_user(
            email="security-invitation-owner@example.test",
            username="security-invitation-owner",
            password=CURRENT_PASSWORD,
        )
        profile = create_profile_with_owner(
            name="Account Security Compatibility",
            owner=owner,
        )
        captured = {}

        def capture_delivery(*, invitation, raw_token):
            captured["token"] = raw_token

        with patch(
            "apps.workspace.invitation_services.schedule_invitation_delivery",
            side_effect=capture_delivery,
        ):
            invitation = create_profile_invitation(
                actor=owner,
                profile_id=profile.id,
                recipient_email=self.user.email,
                requested_role=ProfileInvitation.Role.MEMBER,
            )
        now = timezone.now()
        ProfileInvitation.objects.filter(id=invitation.id).update(
            delivery_status=ProfileInvitation.DeliveryStatus.SENT,
            delivery_attempted_at=now,
            delivered_at=now,
        )
        invitation.refresh_from_db()
        return profile, invitation, captured["token"]

    def test_email_verification_does_not_accept_invitation_or_add_membership(self):
        profile, invitation, _ = self._issue_sent_invitation()
        _, verification_token = self.issue_verification()

        confirm_email_verification(
            actor=self.user,
            raw_token=verification_token,
        )

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProfileInvitation.Status.PENDING)
        self.assertFalse(
            ProfileMembership.objects.filter(
                profile=profile,
                user=self.user,
                is_active=True,
            ).exists()
        )

    def test_unverified_user_can_accept_invitation_without_becoming_verified(self):
        profile, invitation, invitation_token = self._issue_sent_invitation()

        membership = accept_profile_invitation(
            actor=self.user,
            token=invitation_token,
        )

        self.user.refresh_from_db()
        invitation.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)
        self.assertEqual(invitation.status, ProfileInvitation.Status.ACCEPTED)
        self.assertEqual(membership.profile_id, profile.id)
        self.assertEqual(membership.user_id, self.user.id)
        self.assertTrue(membership.is_active)

    def test_password_reset_does_not_accept_invitation_or_grant_membership(self):
        profile, invitation, _ = self._issue_sent_invitation()
        _, reset_token = self.issue_reset()

        confirm_password_reset(
            raw_token=reset_token,
            new_password=NEW_PASSWORD,
        )

        invitation.refresh_from_db()
        self.assertEqual(invitation.status, ProfileInvitation.Status.PENDING)
        self.assertFalse(
            ProfileMembership.objects.filter(
                profile=profile,
                user=self.user,
                is_active=True,
            ).exists()
        )


@override_settings(MAILERS=LOCMEM_MAILERS)
class AccountSecurityConcurrencyTests(TransactionTestCase):
    reset_sequences = False

    def setUp(self):
        self.user = User.objects.create_user(
            email="security-concurrency@example.test",
            username="security-concurrency",
            password=CURRENT_PASSWORD,
        )

    def test_concurrent_verification_confirmation_has_one_winner(self):
        request_email_verification(user=self.user)
        raw_token = extract_latest_token()
        barrier = Barrier(2)

        def confirm():
            close_old_connections()
            try:
                actor = User.objects.get(id=self.user.id)
                barrier.wait(timeout=10)
                try:
                    confirm_email_verification(
                        actor=actor,
                        raw_token=raw_token,
                    )
                except AccountSecurityConflict:
                    return "conflict"
                return "confirmed"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (executor.submit(confirm), executor.submit(confirm))
            results = [future.result(timeout=20) for future in futures]

        self.assertCountEqual(results, ("confirmed", "conflict"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)
        self.assertEqual(
            AccountSecurityToken.objects.filter(
                user=self.user,
                purpose=AccountSecurityToken.Purpose.EMAIL_VERIFICATION,
                status=AccountSecurityToken.Status.CONSUMED,
            ).count(),
            1,
        )

    def test_concurrent_password_reset_confirmation_has_one_winner(self):
        request_password_reset(email=self.user.email)
        raw_token = extract_latest_token()
        barrier = Barrier(2)

        def confirm():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                try:
                    confirm_password_reset(
                        raw_token=raw_token,
                        new_password=NEW_PASSWORD,
                    )
                except AccountSecurityConflict:
                    return "conflict"
                return "reset"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (executor.submit(confirm), executor.submit(confirm))
            results = [future.result(timeout=20) for future in futures]

        self.assertCountEqual(results, ("reset", "conflict"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertEqual(
            AccountSecurityToken.objects.filter(
                user=self.user,
                purpose=AccountSecurityToken.Purpose.PASSWORD_RESET,
                status=AccountSecurityToken.Status.CONSUMED,
            ).count(),
            1,
        )
