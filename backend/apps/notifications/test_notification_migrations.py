from datetime import date

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


def _applied_leaf_targets(executor):
    applied = set(executor.loader.applied_migrations)
    return sorted(
        key for key, node in executor.loader.graph.node_map.items()
        if key in applied and not any(child.key in applied for child in node.children)
    )


class NotificationMigrationTests(TransactionTestCase):
    before = [("notifications", "0001_initial"), ("tasks", "0004_task_comments")]
    after = [("notifications", "0002_notification_context"), ("tasks", "0004_task_comments")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        self.original_targets = _applied_leaf_targets(executor)
        self.addCleanup(self.restore_original)
        executor.migrate(self.before)
        self.old_apps = executor.loader.project_state(self.before).apps

    def restore_original(self):
        executor = MigrationExecutor(connection)
        self.assertNotIn(
            ("ai", "0002_dispatch_governance", False),
            [(migration.app_label, migration.name, backwards) for migration, backwards in executor.migration_plan(self.original_targets)],
        )
        executor.migrate(self.original_targets)

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


class AssignmentRemovalNotificationMigrationTests(TransactionTestCase):
    before = [("notifications", "0002_notification_context")]
    after = [("notifications", "0003_task_unassigned")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        self.original_targets = _applied_leaf_targets(executor)
        self.addCleanup(self.restore_original)
        executor.migrate(self.before)
        self.old_apps = executor.loader.project_state(self.before).apps

    def restore_original(self):
        executor = MigrationExecutor(connection)
        self.assertNotIn(
            ("ai", "0002_dispatch_governance", False),
            [(migration.app_label, migration.name, backwards) for migration, backwards in executor.migration_plan(self.original_targets)],
        )
        executor.migrate(self.original_targets)

    def forward(self):
        executor = MigrationExecutor(connection)
        self.assertEqual(
            [(migration.app_label, migration.name, backwards) for migration, backwards in executor.migration_plan(self.after)],
            [("notifications", "0003_task_unassigned", False)],
        )
        executor.migrate(self.after)
        return executor.loader.project_state(self.after).apps

    def contextual_notification(self, apps, event_type):
        User = apps.get_model("accounts", "User")
        Profile = apps.get_model("workspace", "Profile")
        Workspace = apps.get_model("workspace", "Workspace")
        Task = apps.get_model("tasks", "Task")
        Audit = apps.get_model("audit", "AuditLog")
        Notification = apps.get_model("notifications", "Notification")
        user = User.objects.create(username="event-reverse", email="event-reverse@example.test", password="!")
        profile = Profile.objects.create(name="Event reverse fixture")
        workspace = Workspace.objects.create(profile=profile, owner=user, name="Reverse month", period=date(2026, 11, 1))
        task = Task.objects.create(workspace=workspace, created_by=user, title="Retained notification target")
        event = Audit.objects.create(user=user, action="test.fixture", entity_name="Task", entity_id=task.pk)
        return Notification.objects.create(
            user=user, title="Retained event", message="Synthetic isolated fixture", is_read=True,
            event_type=event_type, profile=profile, workspace=workspace, task=task, event=event,
        )

    def test_additive_event_choice_preserves_legacy_rows_and_existing_guards(self):
        User = self.old_apps.get_model("accounts", "User")
        Old = self.old_apps.get_model("notifications", "Notification")
        user = User.objects.create(username="removal-legacy", email="removal-legacy@example.test", password="!")
        row = Old.objects.create(user=user, title="Retained legacy", message="Retained content", is_read=True)
        before = (row.user_id, row.title, row.message, row.is_read, row.created_at, row.updated_at)
        apps = self.forward()
        Current = apps.get_model("notifications", "Notification")
        retained = Current.objects.get(pk=row.pk)
        self.assertEqual((retained.user_id, retained.title, retained.message, retained.is_read, retained.created_at, retained.updated_at), before)
        self.assertIsNone(retained.event_type)
        with connection.cursor() as cursor:
            guards = connection.introspection.get_constraints(cursor, "notifications_notification")
            cursor.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname = 'notif_valid_event_type'")
            definition = cursor.fetchone()[0]
        self.assertIn("TASK_UNASSIGNED", definition)
        self.assertTrue(guards["notif_context_complete"]["check"])
        self.assertTrue(guards["uniq_notif_event_user"]["unique"])
        self.assertTrue(guards["notif_user_read_created_idx"]["index"])

    def test_isolated_reverse_without_new_event_types_preserves_context_and_data(self):
        row = self.contextual_notification(self.old_apps, "TASK_ASSIGNED")
        original = (row.user_id, row.title, row.message, row.is_read, row.created_at, row.updated_at,
                    row.profile_id, row.workspace_id, row.task_id, row.event_id, row.event_type)
        self.forward()
        executor = MigrationExecutor(connection)
        self.assertEqual(
            [(migration.app_label, migration.name, backwards) for migration, backwards in executor.migration_plan(self.before)],
            [("notifications", "0003_task_unassigned", True)],
        )
        executor.migrate(self.before)
        Old = executor.loader.project_state(self.before).apps.get_model("notifications", "Notification")
        retained = Old.objects.get(pk=row.pk)
        self.assertEqual((retained.user_id, retained.title, retained.message, retained.is_read, retained.created_at, retained.updated_at,
                          retained.profile_id, retained.workspace_id, retained.task_id, retained.event_id, retained.event_type), original)
        self.assertNotIn(("notifications", "0003_task_unassigned"), MigrationExecutor(connection).loader.applied_migrations)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_get_constraintdef(oid), convalidated FROM pg_constraint WHERE conname='notif_valid_event_type' AND conrelid='notifications_notification'::regclass")
            definition, validated = cursor.fetchone()
        self.assertNotIn("TASK_UNASSIGNED", definition)
        self.assertTrue(validated)

    def test_isolated_reverse_with_new_event_rows_fails_atomically_without_deleting_history(self):
        apps = self.forward()
        row = self.contextual_notification(apps, "TASK_UNASSIGNED")
        original = (row.user_id, row.title, row.message, row.is_read, row.created_at, row.updated_at,
                    row.profile_id, row.workspace_id, row.task_id, row.event_id, row.event_type)
        with self.assertRaises(IntegrityError):
            MigrationExecutor(connection).migrate(self.before)
        self.assertIn(("notifications", "0003_task_unassigned"), MigrationExecutor(connection).loader.applied_migrations)
        retained = apps.get_model("notifications", "Notification").objects.get(pk=row.pk)
        self.assertEqual((retained.user_id, retained.title, retained.message, retained.is_read, retained.created_at, retained.updated_at,
                          retained.profile_id, retained.workspace_id, retained.task_id, retained.event_id, retained.event_type), original)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_get_constraintdef(oid), convalidated FROM pg_constraint WHERE conname='notif_valid_event_type' AND conrelid='notifications_notification'::regclass")
            definition, validated = cursor.fetchone()
            guards = connection.introspection.get_constraints(cursor, "notifications_notification")
        self.assertIn("TASK_UNASSIGNED", definition)
        self.assertTrue(validated)
        self.assertTrue(guards["notif_context_complete"]["check"])
        self.assertTrue(guards["uniq_notif_event_user"]["unique"])
        self.assertTrue(guards["notif_user_read_created_idx"]["index"])
