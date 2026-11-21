from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


def applied_leaf_targets(executor):
    applied = set(executor.loader.applied_migrations)
    return sorted(key for key, node in executor.loader.graph.node_map.items()
                  if key in applied and not any(child.key in applied for child in node.children))


class InvitationNotificationMigrationTests(TransactionTestCase):
    before = [("notifications", "0003_task_unassigned"), ("workspace", "0005_account_invitations")]
    after = [("notifications", "0004_invitation_context"), ("workspace", "0005_account_invitations")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        self.original_targets = applied_leaf_targets(executor)
        self.addCleanup(self.restore_original)
        executor.migrate(self.before)
        self.old_apps = executor.loader.project_state(self.before).apps

    def restore_original(self):
        MigrationExecutor(connection).migrate(self.original_targets)

    def forward(self):
        executor = MigrationExecutor(connection)
        self.assertEqual([(migration.app_label, migration.name, backwards)
                          for migration, backwards in executor.migration_plan(self.after)],
                         [("notifications", "0004_invitation_context", False)])
        executor.migrate(self.after)
        return executor.loader.project_state(self.after).apps

    def fixture(self, apps):
        User = apps.get_model("accounts", "User")
        owner = User.objects.create(username="invitation-schema-owner", email="schema-owner@example.test", password="!")
        recipient = User.objects.create(username="invitation-schema-recipient", email="schema-recipient@example.test", password="!")
        profile = apps.get_model("workspace", "Profile").objects.create(name="Retained invitation organization")
        inviter = apps.get_model("workspace", "ProfileMembership").objects.create(profile=profile, user=owner, role="OWNER")
        invitation = apps.get_model("workspace", "ProfileInvitation").objects.create(
            profile=profile, recipient_user=recipient, recipient_email_normalized=recipient.email,
            invited_by_membership=inviter, requested_role="MEMBER", acceptance_kind="ACCOUNT", token_digest=None,
        )
        event = apps.get_model("audit", "AuditLog").objects.create(
            user=owner, action="profile.invitation.created", entity_name="ProfileInvitation",
            entity_id=invitation.pk,
            metadata={"profile_id": str(profile.pk), "requested_role": "MEMBER"},
        )
        return owner, recipient, profile, invitation, event

    def test_additive_target_column_preserves_legacy_content_and_existing_guards(self):
        User = self.old_apps.get_model("accounts", "User")
        Old = self.old_apps.get_model("notifications", "Notification")
        user = User.objects.create(username="invitation-legacy-notice", email="legacy-notice@example.test", password="!")
        legacy = Old.objects.create(user=user, title="Legacy title", message="Retained legacy content", is_read=True)
        before = (legacy.user_id, legacy.title, legacy.message, legacy.is_read, legacy.created_at, legacy.updated_at)
        apps = self.forward()
        Current = apps.get_model("notifications", "Notification")
        row = Current.objects.get(pk=legacy.pk)
        self.assertEqual((row.user_id, row.title, row.message, row.is_read, row.created_at, row.updated_at), before)
        self.assertIsNone(row.invitation_id)
        self.assertEqual((row.profile_id, row.workspace_id, row.task_id, row.event_id, row.event_type), (None,) * 5)
        with connection.cursor() as cursor:
            guards = connection.introspection.get_constraints(cursor, "notifications_notification")
            cursor.execute("SELECT convalidated FROM pg_constraint WHERE conrelid='notifications_notification'::regclass")
            self.assertTrue(all(validated for (validated,) in cursor.fetchall()))
        self.assertTrue(guards["notif_context_complete"]["check"])
        self.assertTrue(guards["notif_valid_event_type"]["check"])
        self.assertTrue(guards["uniq_notif_event_user"]["unique"])
        self.assertTrue(guards["notif_user_read_created_idx"]["index"])
        self.assertTrue(any(item["foreign_key"] == ("workspace_profileinvitation", "id") for item in guards.values()))

    def test_invitation_context_requires_profile_event_target_and_excludes_fake_task_shape(self):
        apps = self.forward()
        _, recipient, profile, invitation, event = self.fixture(apps)
        Current = apps.get_model("notifications", "Notification")
        notice = Current.objects.create(user=recipient, title="Invitation", message="Safe", profile=profile,
            event=event, invitation=invitation, event_type="PROFILE_INVITED")
        self.assertEqual((notice.workspace_id, notice.task_id), (None, None))
        for change in ({"invitation_id": None}, {"profile_id": None}, {"event_id": None}, {"event_type": None},
                       {"event_type": "TASK_ASSIGNED"}):
            with self.subTest(change=change), self.assertRaises(IntegrityError), transaction.atomic():
                Current.objects.filter(pk=notice.pk).update(**change)

    def test_reverse_with_invitation_rows_fails_atomically_without_deleting_history(self):
        apps = self.forward()
        _, recipient, profile, invitation, event = self.fixture(apps)
        Current = apps.get_model("notifications", "Notification")
        notice = Current.objects.create(user=recipient, title="Retained invitation", message="Retained content",
            is_read=True, profile=profile, event=event, invitation=invitation, event_type="PROFILE_INVITED")
        original = (notice.invitation_id, notice.event_type, notice.message, notice.is_read, notice.created_at)
        with self.assertRaises(IntegrityError):
            MigrationExecutor(connection).migrate(self.before)
        self.assertIn(("notifications", "0004_invitation_context"), MigrationExecutor(connection).loader.applied_migrations)
        retained = Current.objects.get(pk=notice.pk)
        self.assertEqual((retained.invitation_id, retained.event_type, retained.message,
                          retained.is_read, retained.created_at), original)
