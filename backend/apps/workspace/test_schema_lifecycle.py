from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from .models import Profile, ProfileMembership, Workspace, WorkspaceMember


User = get_user_model()


class WorkspaceLifecycleSchemaTests(TestCase):

    def setUp(self):
        self.owner = User.objects.create_user(
            email="schema-owner@example.test",
            username="schema-owner",
            password="test-password-only",
        )
        self.member = User.objects.create_user(
            email="schema-member@example.test",
            username="schema-member",
            password="test-password-only",
        )
        self.profile = Profile.objects.create(name="Schema Profile")
        ProfileMembership.objects.create(
            profile=self.profile,
            user=self.owner,
            role=ProfileMembership.Role.OWNER,
        )
        ProfileMembership.objects.create(
            profile=self.profile,
            user=self.member,
            role=ProfileMembership.Role.MEMBER,
        )

    def create_workspace(self, *, period, status=Workspace.Status.ACTIVE):
        return Workspace.objects.create(
            profile=self.profile,
            owner=self.owner,
            name=f"Workspace {period}",
            period=period,
            status=status,
        )

    def test_lifecycle_fields_default_to_active(self):
        workspace = self.create_workspace(period=date(2026, 10, 1))
        membership = WorkspaceMember.objects.create(
            workspace=workspace,
            user=self.member,
            role=WorkspaceMember.Role.MEMBER,
        )

        self.profile.refresh_from_db()
        workspace.refresh_from_db()
        membership.refresh_from_db()

        self.assertEqual(self.profile.status, Profile.Status.ACTIVE)
        self.assertEqual(workspace.status, Workspace.Status.ACTIVE)
        self.assertTrue(membership.is_active)

    def test_workspace_rejects_noncanonical_month(self):
        workspace = Workspace(
            profile=self.profile,
            owner=self.owner,
            name="Invalid period",
            period=date(2026, 10, 2),
        )

        with self.assertRaises(ValidationError) as raised:
            workspace.full_clean()

        self.assertIn("period", raised.exception.message_dict)

    def test_database_rejects_noncanonical_month(self):
        workspace = self.create_workspace(period=date(2026, 10, 1))

        with self.assertRaises(IntegrityError), transaction.atomic():
            Workspace.objects.filter(id=workspace.id).update(
                period=date(2026, 10, 2)
            )

    def test_period_is_unique_per_profile_even_when_archived(self):
        self.create_workspace(
            period=date(2026, 10, 1),
            status=Workspace.Status.ARCHIVED,
        )

        duplicate = Workspace(
            profile=self.profile,
            owner=self.owner,
            name="Duplicate active period",
            period=date(2026, 10, 1),
            status=Workspace.Status.ACTIVE,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            Workspace.objects.bulk_create((duplicate,))

    def test_same_period_is_allowed_in_a_different_profile(self):
        period = date(2026, 10, 1)
        self.create_workspace(period=period)

        other_profile = Profile.objects.create(name="Other Schema Profile")
        ProfileMembership.objects.create(
            profile=other_profile,
            user=self.owner,
            role=ProfileMembership.Role.OWNER,
        )
        other_workspace = Workspace.objects.create(
            profile=other_profile,
            owner=self.owner,
            name="Other tenant period",
            period=period,
        )

        self.assertEqual(other_workspace.period, period)

    def test_new_workspace_requires_an_explicit_period(self):
        with self.assertRaises(ValidationError) as raised:
            Workspace.objects.create(
                profile=self.profile,
                owner=self.owner,
                name="Missing period",
            )

        self.assertIn("period", raised.exception.message_dict)

    def test_workspace_period_is_immutable_after_creation(self):
        workspace = self.create_workspace(period=date(2026, 10, 1))

        workspace.period = date(2026, 11, 1)
        with self.assertRaises(ValidationError) as raised:
            workspace.save(update_fields=("period",))

        self.assertIn("period", raised.exception.message_dict)
        workspace.refresh_from_db()
        self.assertEqual(workspace.period, date(2026, 10, 1))

    def test_database_rejects_unknown_lifecycle_statuses(self):
        workspace = self.create_workspace(period=date(2026, 10, 1))

        with self.assertRaises(IntegrityError), transaction.atomic():
            Profile.objects.filter(id=self.profile.id).update(
                status="UNKNOWN"
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Workspace.objects.filter(id=workspace.id).update(
                status="UNKNOWN"
            )

    def test_inactive_workspace_membership_is_retained_and_reactivated(self):
        workspace = self.create_workspace(period=date(2026, 10, 1))
        membership = WorkspaceMember.objects.create(
            workspace=workspace,
            user=self.member,
            role=WorkspaceMember.Role.VIEWER,
        )
        original_id = membership.id

        WorkspaceMember.objects.filter(id=membership.id).update(
            is_active=False
        )
        membership.refresh_from_db()
        self.assertFalse(membership.is_active)

        duplicate = WorkspaceMember(
            workspace=workspace,
            user=self.member,
            role=WorkspaceMember.Role.MEMBER,
            is_active=True,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            WorkspaceMember.objects.bulk_create((duplicate,))

        WorkspaceMember.objects.filter(id=membership.id).update(
            is_active=True
        )
        membership.refresh_from_db()

        self.assertEqual(membership.id, original_id)
        self.assertTrue(membership.is_active)
        self.assertEqual(
            WorkspaceMember.objects.filter(
                workspace=workspace,
                user=self.member,
            ).count(),
            1,
        )


class WorkspaceLifecycleMigrationTests(TransactionTestCase):

    migrate_from = [
        ("workspace", "0002_profile_workspace_foundation"),
        ("tasks", "0001_initial"),
        ("reviews", "0001_initial"),
    ]
    migrate_to = [
        ("workspace", "0003_workspace_lifecycle_and_period"),
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

    def test_existing_rows_gain_safe_defaults_without_guessed_period(self):
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
        OldDeliverable = self.old_apps.get_model("reviews", "Deliverable")
        OldReview = self.old_apps.get_model("reviews", "Review")

        owner = OldUser.objects.create(
            username="migration-lifecycle-owner",
            email="migration-lifecycle-owner@example.test",
            password="!",
        )
        member = OldUser.objects.create(
            username="migration-lifecycle-member",
            email="migration-lifecycle-member@example.test",
            password="!",
        )
        profile = OldProfile.objects.create(name="Legacy Profile")
        OldProfileMembership.objects.create(
            profile=profile,
            user=owner,
            role="OWNER",
            is_active=True,
        )
        OldProfileMembership.objects.create(
            profile=profile,
            user=member,
            role="MEMBER",
            is_active=True,
        )
        first_workspace = OldWorkspace.objects.create(
            profile=profile,
            owner=owner,
            name="Legacy Workspace One",
        )
        second_workspace = OldWorkspace.objects.create(
            profile=profile,
            owner=owner,
            name="Legacy Workspace Two",
        )
        workspace_membership = OldWorkspaceMember.objects.create(
            workspace=first_workspace,
            user=member,
            role="MEMBER",
        )
        task = OldTask.objects.create(
            workspace=first_workspace,
            title="Legacy lifecycle task",
            created_by=owner,
        )
        deliverable = OldDeliverable.objects.create(
            task=task,
            file_url="https://example.test/lifecycle-migration-only",
            uploaded_by=member,
        )
        review = OldReview.objects.create(
            deliverable=deliverable,
            reviewer=member,
        )

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        new_apps = self.executor.loader.project_state(self.migrate_to).apps

        NewProfile = new_apps.get_model("workspace", "Profile")
        NewWorkspace = new_apps.get_model("workspace", "Workspace")
        NewWorkspaceMember = new_apps.get_model(
            "workspace",
            "WorkspaceMember",
        )
        NewTask = new_apps.get_model("tasks", "Task")
        NewDeliverable = new_apps.get_model("reviews", "Deliverable")
        NewReview = new_apps.get_model("reviews", "Review")

        migrated_profile = NewProfile.objects.get(id=profile.id)
        migrated_first = NewWorkspace.objects.get(id=first_workspace.id)
        migrated_second = NewWorkspace.objects.get(id=second_workspace.id)
        migrated_membership = NewWorkspaceMember.objects.get(
            id=workspace_membership.id
        )

        self.assertEqual(migrated_profile.status, "ACTIVE")
        self.assertEqual(migrated_first.status, "ACTIVE")
        self.assertEqual(migrated_second.status, "ACTIVE")
        self.assertIsNone(migrated_first.period)
        self.assertIsNone(migrated_second.period)
        self.assertTrue(migrated_membership.is_active)
        self.assertEqual(migrated_first.owner_id, owner.id)
        self.assertEqual(migrated_first.profile_id, profile.id)
        self.assertTrue(
            NewTask.objects.filter(
                id=task.id,
                workspace_id=first_workspace.id,
            ).exists()
        )
        self.assertTrue(
            NewDeliverable.objects.filter(
                id=deliverable.id,
                task_id=task.id,
            ).exists()
        )
        self.assertTrue(
            NewReview.objects.filter(
                id=review.id,
                deliverable_id=deliverable.id,
            ).exists()
        )

