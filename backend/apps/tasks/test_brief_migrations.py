"""Forward/reverse rehearsal only on the shared owned PostgreSQL test DB.

Reversal discards newly-added brief metadata; it is not a development rollback
plan. Existing Task/Subtask and workflow references must survive either state.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

from django.db import DataError, IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


URL_FIELDS = ("raw_video_url", "reference_video_url", "template_project_url", "script_url")


class TaskBriefMigrationTests(TransactionTestCase):
    before = [("tasks", "0004_task_comments"), ("reviews", "0002_review_workflow_foundation")]
    after = [("tasks", "0005_task_brief"), ("reviews", "0002_review_workflow_foundation")]

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

    def legacy_fixture(self):
        User = self.old_apps.get_model("accounts", "User")
        Profile = self.old_apps.get_model("workspace", "Profile")
        Membership = self.old_apps.get_model("workspace", "ProfileMembership")
        Workspace = self.old_apps.get_model("workspace", "Workspace")
        Task = self.old_apps.get_model("tasks", "Task")
        Assignment = self.old_apps.get_model("tasks", "TaskAssignment")
        Deliverable = self.old_apps.get_model("reviews", "Deliverable")
        Review = self.old_apps.get_model("reviews", "Review")
        owner = User.objects.create(username="brief-migration-owner", email="brief-migration-owner@example.test", password="!")
        editor = User.objects.create(username="brief-migration-editor", email="brief-migration-editor@example.test", password="!")
        profile = Profile.objects.create(name="Legacy brief migration")
        Membership.objects.create(profile=profile, user=owner, role="OWNER")
        Membership.objects.create(profile=profile, user=editor, role="MEMBER")
        workspace = Workspace.objects.create(profile=profile, owner=owner, name="Legacy month", period=date(2026, 11, 1))
        deadline = datetime(2026, 11, 20, 18, 30, 17, tzinfo=timezone.utc)
        parent = Task.objects.create(workspace=workspace, created_by=owner, title="Legacy root", description="Keep original description", deadline=deadline, priority="HIGH")
        child = Task.objects.create(workspace=workspace, created_by=owner, title="Legacy approved child", parent=parent, status="COMPLETED")
        assignment = Assignment.objects.create(task=child, user=editor, is_active=True)
        deliverable = Deliverable.objects.create(task=child, uploaded_by=editor, revision=1, status="APPROVED", file_url="https://example.test/legacy-deliverable")
        review = Review.objects.create(deliverable=deliverable, reviewer=owner, status="APPROVED", comment="Legacy feedback")
        return parent, child, assignment, deliverable, review

    def test_empty_chain_adds_nullable_fields_exact_numeric_column_and_check(self):
        apps = self.forward()
        Task = apps.get_model("tasks", "Task")
        self.assertEqual(Task.objects.count(), 0)
        for field in (*URL_FIELDS, "estimated_compensation_vnd"):
            self.assertTrue(Task._meta.get_field(field).null)
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, "tasks_task")
            cursor.execute(
                "SELECT data_type,numeric_precision,numeric_scale,is_nullable "
                "FROM information_schema.columns WHERE table_name='tasks_task' "
                "AND column_name='estimated_compensation_vnd'"
            )
            self.assertEqual(cursor.fetchone(), ("numeric", 18, 0, "YES"))
        self.assertTrue(constraints["task_compensation_vnd_nonnegative"]["check"])
        self.assertTrue(constraints["task_not_own_parent"]["check"])
        self.assertEqual(constraints["task_ws_parent_created_idx"]["columns"], ["workspace_id", "parent_id", "created_at"])

    def test_populated_forward_preserves_hierarchy_deadline_and_workflow_with_null_defaults(self):
        parent, child, assignment, deliverable, review = self.legacy_fixture()
        apps = self.forward()
        Task = apps.get_model("tasks", "Task")
        root = Task.objects.get(pk=parent.id)
        descendant = Task.objects.get(pk=child.id)
        self.assertEqual(Task.objects.count(), 2)
        self.assertEqual((root.title, root.description, root.deadline, root.priority), (parent.title, parent.description, parent.deadline, parent.priority))
        self.assertEqual((descendant.parent_id, descendant.status, descendant.created_by_id), (parent.id, "COMPLETED", child.created_by_id))
        for instance in (root, descendant):
            for field in (*URL_FIELDS, "estimated_compensation_vnd"):
                self.assertIsNone(getattr(instance, field))
        self.assertTrue(apps.get_model("tasks", "TaskAssignment").objects.filter(pk=assignment.id, task_id=child.id, is_active=True).exists())
        self.assertTrue(apps.get_model("reviews", "Deliverable").objects.filter(pk=deliverable.id, task_id=child.id, status="APPROVED").exists())
        self.assertTrue(apps.get_model("reviews", "Review").objects.filter(pk=review.id, deliverable_id=deliverable.id, status="APPROVED").exists())
        Task.objects.filter(pk=root.id).update(estimated_compensation_vnd=Decimal("999999999999999999"))
        self.assertEqual(Task.objects.get(pk=root.id).estimated_compensation_vnd, Decimal("999999999999999999"))
        with self.assertRaises(IntegrityError), transaction.atomic():
            Task.objects.filter(pk=root.id).update(estimated_compensation_vnd=-1)
        with self.assertRaises((DataError, IntegrityError)), transaction.atomic():
            Task.objects.filter(pk=root.id).update(estimated_compensation_vnd=Decimal("1000000000000000000"))

    def test_isolated_reverse_preserves_original_rows_and_only_removes_candidate_metadata(self):
        parent, child, assignment, deliverable, review = self.legacy_fixture()
        apps = self.forward()
        Task = apps.get_model("tasks", "Task")
        Task.objects.filter(pk=parent.id).update(script_url="https://example.test/new-brief", estimated_compensation_vnd=500000)
        executor = MigrationExecutor(connection)
        executor.migrate(self.before)
        old = executor.loader.project_state(self.before).apps
        OldTask = old.get_model("tasks", "Task")
        self.assertEqual(OldTask.objects.count(), 2)
        self.assertNotIn("script_url", {field.name for field in OldTask._meta.fields})
        self.assertEqual(OldTask.objects.get(pk=parent.id).description, parent.description)
        self.assertEqual(OldTask.objects.get(pk=parent.id).deadline, parent.deadline)
        self.assertEqual(OldTask.objects.get(pk=child.id).parent_id, parent.id)
        self.assertTrue(old.get_model("tasks", "TaskAssignment").objects.filter(pk=assignment.id).exists())
        self.assertTrue(old.get_model("reviews", "Deliverable").objects.filter(pk=deliverable.id).exists())
        self.assertTrue(old.get_model("reviews", "Review").objects.filter(pk=review.id).exists())
