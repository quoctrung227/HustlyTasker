from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ProfileWorkspaceFoundationMigrationTests(TransactionTestCase):

    migrate_from = [
        ("workspace", "0001_initial"),
        ("tasks", "0001_initial"),
        ("reviews", "0001_initial"),
    ]
    migrate_to = [
        ("workspace", "0002_profile_workspace_foundation"),
        ("tasks", "0001_initial"),
        ("reviews", "0001_initial"),
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

    def test_existing_related_data_is_preserved_without_guessed_tenant(self):
        User = self.old_apps.get_model("accounts", "User")
        Workspace = self.old_apps.get_model("workspace", "Workspace")
        WorkspaceMember = self.old_apps.get_model(
            "workspace",
            "WorkspaceMember",
        )
        Task = self.old_apps.get_model("tasks", "Task")
        Deliverable = self.old_apps.get_model("reviews", "Deliverable")
        Review = self.old_apps.get_model("reviews", "Review")

        owner = User.objects.create(
            username="migration-owner",
            email="migration-owner@example.test",
            password="!",
        )
        reviewer = User.objects.create(
            username="migration-reviewer",
            email="migration-reviewer@example.test",
            password="!",
        )
        workspace = Workspace.objects.create(
            name="Legacy October Workspace",
            owner=owner,
        )
        workspace_member = WorkspaceMember.objects.create(
            workspace=workspace,
            user=reviewer,
            role="MEMBER",
        )
        task = Task.objects.create(
            workspace=workspace,
            title="Legacy Task",
            created_by=owner,
        )
        deliverable = Deliverable.objects.create(
            task=task,
            file_url="https://example.test/test-only-deliverable",
            uploaded_by=reviewer,
        )
        review = Review.objects.create(
            deliverable=deliverable,
            reviewer=reviewer,
        )

        ids = {
            "owner": owner.id,
            "reviewer": reviewer.id,
            "workspace": workspace.id,
            "workspace_member": workspace_member.id,
            "task": task.id,
            "deliverable": deliverable.id,
            "review": review.id,
        }

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        new_apps = self.executor.loader.project_state(self.migrate_to).apps

        NewUser = new_apps.get_model("accounts", "User")
        NewProfile = new_apps.get_model("workspace", "Profile")
        NewProfileMembership = new_apps.get_model(
            "workspace",
            "ProfileMembership",
        )
        NewWorkspace = new_apps.get_model("workspace", "Workspace")
        NewWorkspaceMember = new_apps.get_model(
            "workspace",
            "WorkspaceMember",
        )
        NewTask = new_apps.get_model("tasks", "Task")
        NewDeliverable = new_apps.get_model("reviews", "Deliverable")
        NewReview = new_apps.get_model("reviews", "Review")

        migrated_workspace = NewWorkspace.objects.get(id=ids["workspace"])
        self.assertEqual(migrated_workspace.owner_id, ids["owner"])
        self.assertIsNone(migrated_workspace.profile_id)
        self.assertTrue(NewUser.objects.filter(id=ids["reviewer"]).exists())
        self.assertTrue(
            NewWorkspaceMember.objects.filter(
                id=ids["workspace_member"],
                workspace_id=ids["workspace"],
                user_id=ids["reviewer"],
            ).exists()
        )
        self.assertTrue(
            NewTask.objects.filter(
                id=ids["task"],
                workspace_id=ids["workspace"],
            ).exists()
        )
        self.assertTrue(
            NewDeliverable.objects.filter(
                id=ids["deliverable"],
                task_id=ids["task"],
            ).exists()
        )
        self.assertTrue(
            NewReview.objects.filter(
                id=ids["review"],
                deliverable_id=ids["deliverable"],
            ).exists()
        )
        self.assertEqual(NewProfile.objects.count(), 0)
        self.assertEqual(NewProfileMembership.objects.count(), 0)

        mapped_profile = NewProfile.objects.create(
            name="Explicit Test Mapping"
        )
        NewProfileMembership.objects.create(
            profile=mapped_profile,
            user_id=ids["owner"],
            role="OWNER",
            is_active=True,
        )
        migrated_workspace.profile = mapped_profile
        migrated_workspace.save(update_fields=("profile",))

        migrated_workspace.refresh_from_db()
        self.assertEqual(
            migrated_workspace.profile_id,
            mapped_profile.id,
        )
