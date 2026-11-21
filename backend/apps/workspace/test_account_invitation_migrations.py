"""Additive V2 rollout preserves real legacy identity/expiry, without backfill."""
from datetime import timedelta
import hashlib

from django.db import connection, IntegrityError, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class AccountInvitationMigrationTests(TransactionTestCase):
    before = [("workspace", "0004_profileinvitation"), ("notifications", "0003_task_unassigned")]
    after = [("workspace", "0005_account_invitations"), ("notifications", "0003_task_unassigned")]

    def setUp(self):
        self.addCleanup(self.restore_latest)
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.before)
        old = self.executor.loader.project_state(self.before).apps
        User = old.get_model("accounts", "User")
        Profile = old.get_model("workspace", "Profile")
        Membership = old.get_model("workspace", "ProfileMembership")
        Invitation = old.get_model("workspace", "ProfileInvitation")
        self.owner = User.objects.create(username="migration-account-owner", email="migration-owner@example.test", password="!")
        self.recipient = User.objects.create(username="migration-account-recipient", email="migration-recipient@example.test", password="!")
        self.profile = Profile.objects.create(name="Preserved legacy Profile")
        self.membership = Membership.objects.create(profile=self.profile, user=self.owner, role="OWNER")
        self.digest = hashlib.sha256(b"synthetic-existing-legacy-credential-only").hexdigest()
        self.expiry = timezone.now()+timedelta(days=3)
        self.legacy = Invitation.objects.create(profile=self.profile, invited_by_membership=self.membership,
            recipient_email_normalized="historical-unregistered@example.test", token_digest=self.digest, expires_at=self.expiry)
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.after)
        self.apps = self.executor.loader.project_state(self.after).apps

    def restore_latest(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_legacy_kind_digest_expiry_unbound_recipient_and_related_rows_are_preserved(self):
        Invitation = self.apps.get_model("workspace", "ProfileInvitation")
        row = Invitation.objects.get(pk=self.legacy.pk)
        self.assertEqual(row.acceptance_kind, "EMAIL_TOKEN")
        self.assertIsNone(row.recipient_user_id)
        self.assertEqual(row.token_digest, self.digest)
        self.assertEqual(row.expires_at, self.expiry)
        self.assertEqual(row.status, "PENDING")
        self.assertEqual(self.apps.get_model("workspace", "ProfileMembership").objects.count(), 1)
        self.assertEqual(self.apps.get_model("workspace", "InvitationEmailAttempt").objects.count(), 0)
        self.assertEqual(self.apps.get_model("workspace", "InvitationDirectoryAccess").objects.count(), 0)

    def test_account_failed_delivery_can_be_accepted_but_legacy_cannot_bypass_sent_check(self):
        Invitation = self.apps.get_model("workspace", "ProfileInvitation")
        now = timezone.now()
        account = Invitation.objects.create(profile_id=self.profile.pk, invited_by_membership_id=self.membership.pk,
            recipient_user_id=self.recipient.pk, recipient_email_normalized=self.recipient.email,
            acceptance_kind="ACCOUNT", token_digest=None, expires_at=now+timedelta(days=7),
            status="ACCEPTED", accepted_at=now, accepted_by_id=self.recipient.pk,
            delivery_status="FAILED", delivery_attempted_at=now)
        self.assertIsNone(account.token_digest)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invitation.objects.filter(pk=self.legacy.pk).update(status="ACCEPTED", accepted_at=now,
                accepted_by_id=self.recipient.pk, delivery_status="FAILED", delivery_attempted_at=now)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Invitation.objects.filter(pk=account.pk).update(recipient_user_id=None)

    def test_reverse_with_account_data_is_rejected_atomically_instead_of_losing_identity(self):
        Invitation = self.apps.get_model("workspace", "ProfileInvitation")
        account = Invitation.objects.create(profile_id=self.profile.pk, invited_by_membership_id=self.membership.pk,
            recipient_user_id=self.recipient.pk, recipient_email_normalized=self.recipient.email,
            acceptance_kind="ACCOUNT", token_digest=None, expires_at=timezone.now()+timedelta(days=7))
        with self.assertRaises(IntegrityError):
            MigrationExecutor(connection).migrate(self.before)
        self.assertTrue(Invitation.objects.filter(pk=account.pk, acceptance_kind="ACCOUNT").exists())
        self.assertIn(("workspace", "0005_account_invitations"), MigrationExecutor(connection).loader.applied_migrations)
