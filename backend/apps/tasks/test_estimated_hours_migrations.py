"""Estimated-hours forward rehearsal on the owned PostgreSQL database."""

from datetime import date
from decimal import Decimal

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class TaskEstimatedHoursMigrationTests(TransactionTestCase):
    before = [("tasks", "0006_soft_delete"), ("reviews", "0003_review_compensation_snapshot")]
    after = [("tasks", "0007_task_estimated_hours"), ("reviews", "0003_review_compensation_snapshot")]

    def restore_latest(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def test_populated_forward_preserves_task_workflow_and_adds_nullable_decimal(self):
        self.addCleanup(self.restore_latest)
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        old = executor.loader.project_state(self.before).apps
        User = old.get_model("accounts", "User")
        owner = User.objects.create(username="estimate-legacy-owner", email="owner@example.test", password="!")
        editor = User.objects.create(username="estimate-legacy-editor", email="editor@example.test", password="!")
        profile = old.get_model("workspace", "Profile").objects.create(name="Estimate legacy tenant")
        workspace = old.get_model("workspace", "Workspace").objects.create(
            profile=profile, owner=owner, name="Legacy workspace", period=date(2026, 11, 1),
        )
        task = old.get_model("tasks", "Task").objects.create(
            workspace=workspace, created_by=owner, title="Completed legacy task",
            description="Retain work", status="COMPLETED", estimated_compensation_vnd=Decimal("500000"),
        )
        assignment = old.get_model("tasks", "TaskAssignment").objects.create(task=task, user=editor, is_active=True)
        deliverable = old.get_model("reviews", "Deliverable").objects.create(
            task=task, uploaded_by=editor, revision=1, status="APPROVED", file_url="https://example.test/deliverable",
        )
        review = old.get_model("reviews", "Review").objects.create(
            deliverable=deliverable, reviewer=owner, status="APPROVED", comment="Legacy feedback",
            compensation_snapshot_recorded=True, compensation_snapshot_vnd=Decimal("500000"),
        )

        executor = MigrationExecutor(connection)
        self.assertEqual([(step.name, backwards) for step, backwards in executor.migration_plan(self.after)],
                         [("0007_task_estimated_hours", False)])
        executor.migrate(self.after)
        migrated = executor.loader.project_state(self.after).apps
        Task = migrated.get_model("tasks", "Task")
        preserved = Task.objects.get(pk=task.pk)
        self.assertIsNone(preserved.estimated_hours)
        self.assertEqual((preserved.title, preserved.description, preserved.status, preserved.estimated_compensation_vnd),
                         (task.title, task.description, task.status, Decimal("500000")))
        self.assertTrue(migrated.get_model("tasks", "TaskAssignment").objects.filter(
            pk=assignment.pk, task_id=task.pk, user_id=editor.pk, is_active=True,
        ).exists())
        self.assertTrue(migrated.get_model("reviews", "Review").objects.filter(
            pk=review.pk, deliverable_id=deliverable.pk, deliverable__task_id=task.pk,
            status="APPROVED", comment="Legacy feedback", compensation_snapshot_recorded=True,
            compensation_snapshot_vnd=Decimal("500000"),
        ).exists())
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT data_type, numeric_precision, numeric_scale, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'tasks_task' AND column_name = 'estimated_hours'
            """)
            self.assertEqual(cursor.fetchone(), ("numeric", 6, 2, "YES", None))

        for value in (Decimal("0.01"), Decimal("1000.00")):
            with self.subTest(valid=value):
                Task.objects.filter(pk=task.pk).update(estimated_hours=value)
                self.assertEqual(Task.objects.get(pk=task.pk).estimated_hours, value)
        for value in (Decimal("-0.01"), Decimal("0"), Decimal("1000.01")):
            with self.subTest(invalid=value), self.assertRaises(IntegrityError), transaction.atomic():
                Task.objects.filter(pk=task.pk).update(estimated_hours=value)
