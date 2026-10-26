from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class NotificationMigrationTests(TransactionTestCase):
    before = [("notifications", "0001_initial"), ("tasks", "0004_task_comments")]
    after = [("notifications", "0002_notification_context"), ("tasks", "0004_task_comments")]

    def setUp(self):
        super().setUp()
        self.addCleanup(self.restore_latest)
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        self.old_apps = executor.loader.project_state(self.before).apps

    def restore_latest(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def forward(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.after)
        return executor.loader.project_state(self.after).apps

    def test_empty_schema_builds_context_constraints_and_lookup_index(self):
        apps = self.forward()
        self.assertEqual(apps.get_model("notifications", "Notification").objects.count(), 0)
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, "notifications_notification")
        self.assertTrue(constraints["notif_context_complete"]["check"])
        self.assertTrue(constraints["notif_valid_event_type"]["check"])
        self.assertTrue(constraints["uniq_notif_event_user"]["unique"])
        self.assertEqual(constraints["notif_user_read_created_idx"]["columns"],
                         ["user_id", "is_read", "created_at", "id"])

    def test_legacy_user_content_read_state_and_timestamps_are_not_mapped_or_rewritten(self):
        User = self.old_apps.get_model("accounts", "User")
        Notification = self.old_apps.get_model("notifications", "Notification")
        user = User.objects.create(username="notification-legacy", email="notification-legacy@example.test", password="!")
        legacy = Notification.objects.create(user=user, title="Legacy title", message="Legacy body", is_read=True)
        before = (legacy.user_id, legacy.title, legacy.message, legacy.is_read, legacy.created_at, legacy.updated_at)
        apps = self.forward()
        Current = apps.get_model("notifications", "Notification")
        row = Current.objects.get(pk=legacy.pk)
        self.assertEqual((row.user_id, row.title, row.message, row.is_read, row.created_at, row.updated_at), before)
        self.assertEqual((row.profile_id, row.workspace_id, row.task_id, row.event_id, row.event_type), (None,) * 5)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Current.objects.filter(pk=row.pk).update(event_type="TASK_ASSIGNED")
