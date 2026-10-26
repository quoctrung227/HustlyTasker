from datetime import date

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class TaskCommentMigrationTests(TransactionTestCase):
    before = [("tasks", "0003_task_hierarchy")]
    after = [("tasks", "0004_task_comments")]

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

    def test_empty_schema_adds_nullable_lifecycle_and_history_index(self):
        apps = self.migrate_forward()
        Comment = apps.get_model("tasks", "TaskComment")
        self.assertEqual(Comment.objects.count(), 0)
        self.assertTrue(Comment._meta.get_field("edited_at").null)
        self.assertTrue(Comment._meta.get_field("deleted_at").null)
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, "tasks_taskcomment")
        self.assertTrue(constraints["comment_edit_after_create"]["check"])
        self.assertTrue(constraints["comment_delete_after_create"]["check"])
        self.assertEqual(constraints["comment_task_created_id_idx"]["columns"], ["task_id", "created_at", "id"])

    def test_legacy_oversized_body_author_task_and_timestamps_are_preserved(self):
        User = self.old_apps.get_model("accounts", "User")
        Profile = self.old_apps.get_model("workspace", "Profile")
        Workspace = self.old_apps.get_model("workspace", "Workspace")
        Task = self.old_apps.get_model("tasks", "Task")
        Comment = self.old_apps.get_model("tasks", "TaskComment")
        author = User.objects.create(username="comment-migration-author", email="comment-migration@example.test", password="!")
        profile = Profile.objects.create(name="Legacy discussion")
        workspace = Workspace.objects.create(profile=profile, owner=author, name="Legacy month", period=date(2026, 10, 1))
        task = Task.objects.create(workspace=workspace, created_by=author, title="Legacy task")
        comment = Comment.objects.create(task=task, user=author, content="Legacy text " * 500)
        timestamps = (comment.created_at, comment.updated_at)
        apps = self.migrate_forward()
        NewComment = apps.get_model("tasks", "TaskComment")
        migrated = NewComment.objects.get(pk=comment.pk)
        self.assertEqual(migrated.content, comment.content)
        self.assertEqual((migrated.task_id, migrated.user_id), (task.id, author.id))
        self.assertEqual((migrated.created_at, migrated.updated_at), timestamps)
        self.assertIsNone(migrated.edited_at)
        self.assertIsNone(migrated.deleted_at)
        with self.assertRaises(IntegrityError), transaction.atomic():
            NewComment.objects.filter(pk=comment.pk).update(edited_at="2000-01-01T00:00:00Z")
