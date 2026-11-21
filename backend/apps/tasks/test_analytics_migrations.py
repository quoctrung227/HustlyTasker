"""Snapshot migration preservation rehearsal on isolated PostgreSQL only."""
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


class ReviewCompensationSnapshotMigrationTests(TransactionTestCase):
    before = [("tasks", "0005_task_brief"), ("reviews", "0002_review_workflow_foundation")]
    after = [("tasks", "0005_task_brief"), ("reviews", "0003_review_compensation_snapshot")]

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

    def test_populated_legacy_reviews_are_preserved_as_explicit_unknown_not_backfilled(self):
        User = self.old_apps.get_model("accounts", "User")
        Profile = self.old_apps.get_model("workspace", "Profile")
        Membership = self.old_apps.get_model("workspace", "ProfileMembership")
        Workspace = self.old_apps.get_model("workspace", "Workspace")
        Task = self.old_apps.get_model("tasks", "Task")
        Deliverable = self.old_apps.get_model("reviews", "Deliverable")
        Review = self.old_apps.get_model("reviews", "Review")
        owner = User.objects.create(username="snapshot-legacy-owner", email="snapshot-legacy-owner@example.test", password="!")
        editor = User.objects.create(username="snapshot-legacy-editor", email="snapshot-legacy-editor@example.test", password="!")
        profile = Profile.objects.create(name="Legacy snapshot tenant")
        Membership.objects.create(profile=profile, user=owner, role="OWNER")
        workspace = Workspace.objects.create(profile=profile, owner=owner, name="Legacy month", period=date(2026, 11, 1))
        task = Task.objects.create(workspace=workspace, created_by=owner, title="Legacy approved", status="COMPLETED", estimated_compensation_vnd="999999")
        deliverable = Deliverable.objects.create(task=task, uploaded_by=editor, file_url="Legacy text reference", revision=1, status="APPROVED")
        review = Review.objects.create(deliverable=deliverable, reviewer=owner, status="APPROVED", comment="Keep original review")
        original = (review.pk, review.created_at, review.reviewer_id, review.comment, deliverable.uploaded_by_id)
        executor = MigrationExecutor(connection)
        self.assertEqual(
            [(migration.app_label, migration.name, backwards) for migration, backwards in executor.migration_plan(self.after)],
            [("reviews", "0003_review_compensation_snapshot", False)],
        )
        executor.migrate(self.after)
        apps = executor.loader.project_state(self.after).apps
        NewReview = apps.get_model("reviews", "Review")
        migrated = NewReview.objects.get(pk=review.pk)
        self.assertEqual((migrated.pk, migrated.created_at, migrated.reviewer_id, migrated.comment, migrated.deliverable.uploaded_by_id), original)
        self.assertFalse(migrated.compensation_snapshot_recorded)
        self.assertIsNone(migrated.compensation_snapshot_vnd)
        self.assertEqual(apps.get_model("reviews", "Deliverable").objects.get(pk=deliverable.pk).file_url, "Legacy text reference")
        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(cursor, "reviews_review")
        self.assertTrue(constraints["review_snapshot_nonnegative"]["check"])
        self.assertTrue(constraints["review_snapshot_recorded_pair"]["check"])
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_name, data_type, is_nullable, numeric_precision, numeric_scale "
                "FROM information_schema.columns WHERE table_schema='public' AND table_name='reviews_review' "
                "AND column_name IN ('compensation_snapshot_recorded', 'compensation_snapshot_vnd')"
            )
            columns = {row[0]: row[1:] for row in cursor.fetchall()}
            cursor.execute(
                "SELECT conname, convalidated FROM pg_constraint "
                "WHERE conrelid='reviews_review'::regclass AND conname IN "
                "('review_snapshot_nonnegative', 'review_snapshot_recorded_pair')"
            )
            self.assertEqual(dict(cursor.fetchall()), {
                "review_snapshot_nonnegative": True, "review_snapshot_recorded_pair": True,
            })
        self.assertEqual(columns["compensation_snapshot_recorded"][:2], ("boolean", "NO"))
        self.assertEqual(columns["compensation_snapshot_vnd"], ("numeric", "YES", 18, 0))
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name='reviews_review' "
                "AND column_name='compensation_snapshot_recorded'"
            )
            self.assertIsNone(cursor.fetchone()[0])
        # Existing old-model reads work, but an older writer omits this new
        # NOT NULL field: the migration's Python default is not a durable DB
        # default. Rollout therefore requires coordinated backend activation.
        self.assertEqual(Review.objects.get(pk=review.pk).comment, "Keep original review")
        next_product = Deliverable.objects.create(
            task=task, uploaded_by=editor, file_url="Second retained reference",
            revision=2, status="REJECTED",
        )
        before_count = NewReview.objects.count()
        with self.assertRaises(IntegrityError) as old_write_error, transaction.atomic():
            Review.objects.create(deliverable=next_product, reviewer=owner, status="REQUEST_CHANGE")
        self.assertEqual(old_write_error.exception.__cause__.sqlstate, "23502")
        self.assertEqual(old_write_error.exception.__cause__.diag.column_name, "compensation_snapshot_recorded")
        self.assertEqual(NewReview.objects.count(), before_count)
        new_writer = NewReview.objects.create(
            deliverable_id=next_product.pk, reviewer_id=owner.pk, status="REQUEST_CHANGE",
        )
        self.assertFalse(new_writer.compensation_snapshot_recorded)
        self.assertIsNone(new_writer.compensation_snapshot_vnd)
        with self.assertRaises(IntegrityError), transaction.atomic():
            NewReview.objects.filter(pk=review.pk).update(compensation_snapshot_recorded=False, compensation_snapshot_vnd=1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            NewReview.objects.filter(pk=review.pk).update(compensation_snapshot_recorded=True, compensation_snapshot_vnd=-1)
        NewReview.objects.filter(pk=review.pk).update(compensation_snapshot_recorded=True, compensation_snapshot_vnd=None)
        self.assertTrue(NewReview.objects.get(pk=review.pk).compensation_snapshot_recorded)
        self.assertIsNone(NewReview.objects.get(pk=review.pk).compensation_snapshot_vnd)
        NewReview.objects.filter(pk=review.pk).update(compensation_snapshot_recorded=True, compensation_snapshot_vnd=0)
        self.assertEqual(NewReview.objects.get(pk=review.pk).compensation_snapshot_vnd, 0)

    def test_isolated_reverse_preserves_review_but_drops_recorded_snapshot_irrecoverably(self):
        # This is a disposable test database rehearsal, never a recovery policy.
        User = self.old_apps.get_model("accounts", "User")
        Profile = self.old_apps.get_model("workspace", "Profile")
        Workspace = self.old_apps.get_model("workspace", "Workspace")
        Task = self.old_apps.get_model("tasks", "Task")
        Deliverable = self.old_apps.get_model("reviews", "Deliverable")
        Review = self.old_apps.get_model("reviews", "Review")
        user = User.objects.create(username="snapshot-reverse", email="snapshot-reverse@example.test", password="!")
        profile = Profile.objects.create(name="Snapshot reverse fixture")
        workspace = Workspace.objects.create(profile=profile, owner=user, name="Reverse month", period=date(2026, 11, 1))
        task = Task.objects.create(workspace=workspace, created_by=user, title="Preserved review")
        product = Deliverable.objects.create(task=task, uploaded_by=user, file_url="Legacy retained reference", status="APPROVED", revision=1)
        review = Review.objects.create(deliverable=product, reviewer=user, status="APPROVED", comment="Keep this history")
        original = (review.pk, review.status, review.comment, review.created_at, review.reviewer_id, review.deliverable_id)
        executor = MigrationExecutor(connection)
        executor.migrate(self.after)
        Current = executor.loader.project_state(self.after).apps.get_model("reviews", "Review")
        Current.objects.filter(pk=review.pk).update(compensation_snapshot_recorded=True, compensation_snapshot_vnd=500000)

        executor = MigrationExecutor(connection)
        self.assertEqual(
            [(migration.app_label, migration.name, backwards) for migration, backwards in executor.migration_plan(self.before)],
            [("reviews", "0003_review_compensation_snapshot", True)],
        )
        executor.migrate(self.before)
        Old = executor.loader.project_state(self.before).apps.get_model("reviews", "Review")
        retained = Old.objects.get(pk=review.pk)
        self.assertEqual((retained.pk, retained.status, retained.comment, retained.created_at, retained.reviewer_id, retained.deliverable_id), original)
        self.assertNotIn(("reviews", "0003_review_compensation_snapshot"), MigrationExecutor(connection).loader.applied_migrations)
        with connection.cursor() as cursor:
            columns = {column.name for column in connection.introspection.get_table_description(cursor, "reviews_review")}
        self.assertNotIn("compensation_snapshot_vnd", columns)
        self.assertNotIn("compensation_snapshot_recorded", columns)

        executor = MigrationExecutor(connection)
        executor.migrate(self.after)
        Reapplied = executor.loader.project_state(self.after).apps.get_model("reviews", "Review")
        row = Reapplied.objects.get(pk=review.pk)
        self.assertFalse(row.compensation_snapshot_recorded)
        self.assertIsNone(row.compensation_snapshot_vnd)
        self.assertEqual((row.pk, row.status, row.comment, row.created_at, row.reviewer_id, row.deliverable_id), original)

