import hashlib
from datetime import timedelta

from django.contrib.auth.hashers import check_password, make_password
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class AccountSecurityMigrationTests(TransactionTestCase):
    migrate_from = [("accounts", "0001_initial")]
    migrate_to = [
        ("accounts", "0002_accountsecuritytoken_user_email_verification")
    ]

    def setUp(self):
        super().setUp()
        self._schema_needs_restore = True
        self.addCleanup(self._restore_latest_schema)
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        self.old_apps = self.executor.loader.project_state(
            self.migrate_from
        ).apps

    def tearDown(self):
        self._restore_latest_schema()
        super().tearDown()

    def _restore_latest_schema(self):
        if not getattr(self, "_schema_needs_restore", False):
            return
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        self._schema_needs_restore = False

    def test_migration_preserves_legacy_users_as_unverified_without_backfill(self):
        OldUser = self.old_apps.get_model("accounts", "User")
        password_hash = make_password("Legacy!Password$492")
        first = OldUser.objects.create(
            username="legacy-security-first",
            email="Legacy.Security@example.test",
            password=password_hash,
            is_active=True,
        )
        second = OldUser.objects.create(
            username="legacy-security-second",
            email="legacy.security@example.test",
            password=make_password("Other!Password$731"),
            is_active=True,
        )

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        new_apps = self.executor.loader.project_state(self.migrate_to).apps
        NewUser = new_apps.get_model("accounts", "User")
        AccountSecurityToken = new_apps.get_model(
            "accounts",
            "AccountSecurityToken",
        )

        migrated_first = NewUser.objects.get(id=first.id)
        migrated_second = NewUser.objects.get(id=second.id)
        self.assertEqual(migrated_first.email, "Legacy.Security@example.test")
        self.assertEqual(migrated_second.email, "legacy.security@example.test")
        self.assertIsNone(migrated_first.email_verified_at)
        self.assertIsNone(migrated_first.verified_email_normalized)
        self.assertIsNone(migrated_second.email_verified_at)
        self.assertIsNone(migrated_second.verified_email_normalized)
        self.assertEqual(migrated_first.password, password_hash)
        self.assertTrue(check_password("Legacy!Password$492", password_hash))
        self.assertEqual(AccountSecurityToken.objects.count(), 0)

        now = timezone.now()
        token = AccountSecurityToken.objects.create(
            user_id=first.id,
            purpose="EMAIL_VERIFICATION",
            email_normalized="legacy.security@example.test",
            token_digest=hashlib.sha256(b"migration-security-token").hexdigest(),
            status="PENDING",
            expires_at=now + timedelta(hours=24),
            delivery_status="QUEUED",
        )
        self.assertEqual(token.user_id, first.id)
        self.assertEqual(token.status, "PENDING")

    def test_migration_creates_expected_constraints_and_indexes(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)

        with connection.cursor() as cursor:
            user_constraints = connection.introspection.get_constraints(
                cursor,
                "accounts_user",
            )
            token_constraints = connection.introspection.get_constraints(
                cursor,
                "accounts_accountsecuritytoken",
            )

        expected_user_constraints = {
            "acct_verified_email_pair",
            "uniq_verified_email_identity",
        }
        expected_token_constraints = {
            "acctok_valid_purpose",
            "acctok_valid_status",
            "acctok_valid_delivery",
            "acctok_fingerprint_by_purpose",
            "acctok_terminal_state_valid",
            "acctok_consume_requires_sent",
            "acctok_expiry_after_created",
            "acctok_delivery_state_valid",
            "acctok_not_self_replacement",
            "uniq_pending_user_acctok_purpose",
        }
        expected_token_indexes = {
            "acctok_user_purpose_status_idx",
            "acctok_email_purpose_idx",
            "acctok_expiry_status_idx",
        }

        self.assertTrue(expected_user_constraints.issubset(user_constraints))
        self.assertTrue(expected_token_constraints.issubset(token_constraints))
        self.assertTrue(expected_token_indexes.issubset(token_constraints))
        for name in expected_user_constraints:
            self.assertTrue(
                user_constraints[name]["check"]
                or user_constraints[name]["unique"],
                name,
            )
        for name in expected_token_constraints:
            self.assertTrue(
                token_constraints[name]["check"]
                or token_constraints[name]["unique"],
                name,
            )
        for name in expected_token_indexes:
            self.assertTrue(token_constraints[name]["index"], name)
