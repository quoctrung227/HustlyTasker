import hashlib
from datetime import date, timedelta

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class ProfileInvitationMigrationTests(TransactionTestCase):
    migrate_from = [
        ("workspace", "0003_workspace_lifecycle_and_period"),
        ("tasks", "0002_task_workflow_foundation"),
        ("reviews", "0002_review_workflow_foundation"),
    ]
    migrate_to = [
        ("workspace", "0004_profileinvitation"),
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

    def test_migration_is_additive_and_preserves_related_business_rows(self):
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
            username="invitation-migration-owner",
            email="invitation-migration-owner@example.test",
            password="!",
        )
        member = OldUser.objects.create(
            username="invitation-migration-member",
            email="invitation-migration-member@example.test",
            password="!",
        )
        profile = OldProfile.objects.create(
            name="Invitation Migration Profile",
            status="ACTIVE",
        )
        owner_membership = OldProfileMembership.objects.create(
            profile=profile,
            user=owner,
            role="OWNER",
            is_active=True,
        )
        member_membership = OldProfileMembership.objects.create(
            profile=profile,
            user=member,
            role="MEMBER",
            is_active=True,
        )
        workspace = OldWorkspace.objects.create(
            profile=profile,
            owner=owner,
            name="Invitation Migration Workspace",
            period=date(2026, 10, 1),
            status="ACTIVE",
        )
        workspace_membership = OldWorkspaceMember.objects.create(
            workspace=workspace,
            user=member,
            role="MEMBER",
            is_active=True,
        )
        task = OldTask.objects.create(
            workspace=workspace,
            title="Invitation migration task",
            created_by=owner,
            status="PENDING",
            priority="MEDIUM",
        )
        deliverable = OldDeliverable.objects.create(
            task=task,
            file_url="https://example.test/invitation-migration-only",
            uploaded_by=member,
            status="SUBMITTED",
            revision=1,
        )
        review = OldReview.objects.create(
            deliverable=deliverable,
            reviewer=owner,
            status="APPROVED",
        )

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        new_apps = self.executor.loader.project_state(self.migrate_to).apps

        NewProfile = new_apps.get_model("workspace", "Profile")
        NewProfileMembership = new_apps.get_model(
            "workspace",
            "ProfileMembership",
        )
        NewProfileInvitation = new_apps.get_model(
            "workspace",
            "ProfileInvitation",
        )
        NewWorkspace = new_apps.get_model("workspace", "Workspace")
        NewWorkspaceMember = new_apps.get_model(
            "workspace",
            "WorkspaceMember",
        )
        NewTask = new_apps.get_model("tasks", "Task")
        NewDeliverable = new_apps.get_model("reviews", "Deliverable")
        NewReview = new_apps.get_model("reviews", "Review")

        self.assertTrue(NewProfile.objects.filter(id=profile.id).exists())
        self.assertTrue(
            NewProfileMembership.objects.filter(
                id=owner_membership.id,
                profile_id=profile.id,
                user_id=owner.id,
                role="OWNER",
                is_active=True,
            ).exists()
        )
        self.assertTrue(
            NewProfileMembership.objects.filter(
                id=member_membership.id,
                role="MEMBER",
                is_active=True,
            ).exists()
        )
        self.assertTrue(
            NewWorkspace.objects.filter(
                id=workspace.id,
                profile_id=profile.id,
            ).exists()
        )
        self.assertTrue(
            NewWorkspaceMember.objects.filter(
                id=workspace_membership.id,
                workspace_id=workspace.id,
                user_id=member.id,
                is_active=True,
            ).exists()
        )
        self.assertTrue(
            NewTask.objects.filter(id=task.id, workspace_id=workspace.id).exists()
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
        self.assertEqual(NewProfileInvitation.objects.count(), 0)

        now = timezone.now()
        invitation = NewProfileInvitation.objects.create(
            profile_id=profile.id,
            recipient_email_normalized="new-recipient@example.test",
            requested_role="MEMBER",
            invited_by_membership_id=owner_membership.id,
            token_digest=hashlib.sha256(
                b"migration-test-token"
            ).hexdigest(),
            status="PENDING",
            expires_at=now + timedelta(days=7),
            delivery_status="QUEUED",
        )
        self.assertEqual(invitation.profile_id, profile.id)
        self.assertEqual(invitation.requested_role, "MEMBER")

    def test_migration_creates_expected_constraints_and_indexes(self):
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)

        with connection.cursor() as cursor:
            constraints = connection.introspection.get_constraints(
                cursor,
                "workspace_profileinvitation",
            )

        expected_constraints = {
            "pinv_valid_role",
            "pinv_valid_status",
            "pinv_valid_delivery",
            "pinv_terminal_state_valid",
            "pinv_use_requires_sent",
            "pinv_expiry_after_created",
            "pinv_delivery_state_valid",
            "uniq_pending_profile_email",
            "uniq_pending_profile_user",
        }
        expected_indexes = {
            "pinv_prof_status_created_idx",
            "pinv_email_status_idx",
            "pinv_inviter_created_idx",
            "pinv_expiry_status_idx",
        }
        self.assertTrue(expected_constraints.issubset(constraints))
        self.assertTrue(expected_indexes.issubset(constraints))
        for name in expected_constraints:
            self.assertTrue(
                constraints[name]["check"] or constraints[name]["unique"],
                name,
            )
        for name in expected_indexes:
            self.assertTrue(constraints[name]["index"], name)
