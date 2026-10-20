from datetime import date

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class TaskWorkflowMigrationTests(TransactionTestCase):
    migrate_from = [
        ("workspace", "0003_workspace_lifecycle_and_period"),
        ("tasks", "0001_initial"),
        ("reviews", "0001_initial"),
    ]
    migrate_to = [
        ("workspace", "0003_workspace_lifecycle_and_period"),
        ("tasks", "0002_task_workflow_foundation"),
        ("reviews", "0002_review_workflow_foundation"),
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

    def test_legacy_history_is_preserved_without_guessing_active_assignment(self):
        OldUser = self.old_apps.get_model("accounts", "User")
        OldProfile = self.old_apps.get_model("workspace", "Profile")
        OldProfileMembership = self.old_apps.get_model(
            "workspace",
            "ProfileMembership",
        )
        OldWorkspace = self.old_apps.get_model("workspace", "Workspace")
        OldWorkspaceMember = self.old_apps.get_model(
            "workspace",
            "WorkspaceMember",
        )
        OldTask = self.old_apps.get_model("tasks", "Task")
        OldTaskAssignment = self.old_apps.get_model(
            "tasks",
            "TaskAssignment",
        )
        OldDeliverable = self.old_apps.get_model("reviews", "Deliverable")
        OldReview = self.old_apps.get_model("reviews", "Review")

        owner = OldUser.objects.create(
            username="task-migration-owner",
            email="task-migration-owner@example.test",
            password="!",
        )
        first_editor = OldUser.objects.create(
            username="task-migration-editor-one",
            email="task-migration-editor-one@example.test",
            password="!",
        )
        second_editor = OldUser.objects.create(
            username="task-migration-editor-two",
            email="task-migration-editor-two@example.test",
            password="!",
        )
        profile = OldProfile.objects.create(name="Task Migration Profile")
        OldProfileMembership.objects.create(
            profile=profile,
            user=owner,
            role="OWNER",
            is_active=True,
        )
        for editor in (first_editor, second_editor):
            OldProfileMembership.objects.create(
                profile=profile,
                user=editor,
                role="MEMBER",
                is_active=True,
            )
        workspace = OldWorkspace.objects.create(
            profile=profile,
            owner=owner,
            name="Task Migration Workspace",
            period=date(2026, 10, 1),
            status="ACTIVE",
        )
        for editor in (first_editor, second_editor):
            OldWorkspaceMember.objects.create(
                workspace=workspace,
                user=editor,
                role="MEMBER",
                is_active=True,
            )
        task = OldTask.objects.create(
            workspace=workspace,
            title="Legacy assigned task",
            status="ASSIGNED",
            priority="HIGH",
            created_by=owner,
        )
        first_assignment = OldTaskAssignment.objects.create(
            task=task,
            user=first_editor,
        )
        second_assignment = OldTaskAssignment.objects.create(
            task=task,
            user=second_editor,
        )
        deliverable = OldDeliverable.objects.create(
            task=task,
            file_url="https://example.test/legacy-deliverable",
            uploaded_by=first_editor,
            status="SUBMITTED",
        )
        review = OldReview.objects.create(
            deliverable=deliverable,
            reviewer=owner,
            status="APPROVED",
            comment="Legacy internal decision",
        )

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        new_apps = self.executor.loader.project_state(self.migrate_to).apps

        NewTask = new_apps.get_model("tasks", "Task")
        NewTaskAssignment = new_apps.get_model("tasks", "TaskAssignment")
        NewDeliverable = new_apps.get_model("reviews", "Deliverable")
        NewReview = new_apps.get_model("reviews", "Review")

        migrated_task = NewTask.objects.get(id=task.id)
        migrated_first = NewTaskAssignment.objects.get(id=first_assignment.id)
        migrated_second = NewTaskAssignment.objects.get(id=second_assignment.id)
        migrated_deliverable = NewDeliverable.objects.get(id=deliverable.id)

        self.assertEqual(migrated_task.status, "ASSIGNED")
        self.assertEqual(migrated_task.priority, "HIGH")
        self.assertFalse(migrated_first.is_active)
        self.assertFalse(migrated_second.is_active)
        self.assertIsNone(migrated_deliverable.revision)
        self.assertTrue(
            NewReview.objects.filter(
                id=review.id,
                deliverable_id=deliverable.id,
                status="APPROVED",
            ).exists()
        )

        migrated_first.is_active = True
        migrated_first.save(update_fields=("is_active",))
        migrated_second.is_active = True
        with self.assertRaises(IntegrityError), transaction.atomic():
            migrated_second.save(update_fields=("is_active",))
