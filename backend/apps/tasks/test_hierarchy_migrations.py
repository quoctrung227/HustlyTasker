from datetime import date, datetime, timezone

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class TaskHierarchyMigrationTests(TransactionTestCase):
    before = [("tasks", "0002_task_workflow_foundation"),
              ("reviews", "0002_review_workflow_foundation")]
    after = [("tasks", "0003_task_hierarchy"),
             ("reviews", "0002_review_workflow_foundation")]

    def setUp(self):
        super().setUp()
        self.addCleanup(self.restore_latest)
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        self.old_apps = executor.loader.project_state(self.before).apps

    def restore_latest(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def migrate_forward(self):
        executor = MigrationExecutor(connection)
        executor.migrate(self.after)
        return executor.loader.project_state(self.after).apps

    def test_empty_database_schema_and_self_parent_constraint(self):
        apps = self.migrate_forward()
        Task = apps.get_model("tasks", "Task")
        self.assertEqual(Task.objects.count(), 0)
        self.assertTrue(Task._meta.get_field("parent").null)
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, "tasks_task")
        self.assertTrue(constraints["task_not_own_parent"]["check"])
        self.assertEqual(constraints["task_ws_parent_created_idx"]["columns"],
                         ["workspace_id", "parent_id", "created_at"])

    def test_related_legacy_history_is_preserved_as_roots(self):
        User = self.old_apps.get_model("accounts", "User")
        Profile = self.old_apps.get_model("workspace", "Profile")
        Workspace = self.old_apps.get_model("workspace", "Workspace")
        Task = self.old_apps.get_model("tasks", "Task")
        Assignment = self.old_apps.get_model("tasks", "TaskAssignment")
        Deliverable = self.old_apps.get_model("reviews", "Deliverable")
        Review = self.old_apps.get_model("reviews", "Review")
        owner = User.objects.create(username="hierarchy-migration-owner",
                                    email="hierarchy-owner@example.test", password="!")
        editor = User.objects.create(username="hierarchy-migration-editor",
                                     email="hierarchy-editor@example.test", password="!")
        profile = Profile.objects.create(name="Legacy hierarchy profile")
        workspace = Workspace.objects.create(profile=profile, owner=owner,
                                             name="Legacy workspace", period=date(2026, 10, 1))
        deadline = datetime(2026, 11, 2, 9, tzinfo=timezone.utc)
        task = Task.objects.create(workspace=workspace, created_by=owner,
                                   title="Legacy approved", status="COMPLETED",
                                   priority="HIGH", deadline=deadline)
        no_deadline = Task.objects.create(workspace=workspace, created_by=owner,
                                          title="Legacy nullable deadline")
        assignment = Assignment.objects.create(task=task, user=editor, is_active=True)
        deliverable = Deliverable.objects.create(task=task, uploaded_by=editor,
                                                 file_url="https://example.test/legacy",
                                                 status="APPROVED", revision=1)
        review = Review.objects.create(deliverable=deliverable, reviewer=owner,
                                       status="APPROVED", comment="Legacy approval")
        apps = self.migrate_forward()
        NewTask = apps.get_model("tasks", "Task")
        migrated = NewTask.objects.get(pk=task.pk)
        self.assertIsNone(migrated.parent_id)
        self.assertEqual((migrated.workspace_id, migrated.created_by_id, migrated.status,
                          migrated.priority, migrated.deadline),
                         (workspace.id, owner.id, "COMPLETED", "HIGH", deadline))
        legacy_root = NewTask.objects.get(pk=no_deadline.pk)
        self.assertIsNone(legacy_root.parent_id)
        self.assertIsNone(legacy_root.deadline)
        self.assertEqual(legacy_root.priority, "MEDIUM")
        self.assertTrue(apps.get_model("tasks", "TaskAssignment").objects.filter(
            pk=assignment.pk, task_id=task.id, user_id=editor.id, is_active=True).exists())
        self.assertTrue(apps.get_model("reviews", "Deliverable").objects.filter(
            pk=deliverable.pk, task_id=task.id, revision=1, status="APPROVED").exists())
        self.assertTrue(apps.get_model("reviews", "Review").objects.filter(
            pk=review.pk, deliverable_id=deliverable.id, status="APPROVED").exists())
        with self.assertRaises(IntegrityError), transaction.atomic():
            NewTask.objects.filter(pk=task.pk).update(parent_id=task.pk)
