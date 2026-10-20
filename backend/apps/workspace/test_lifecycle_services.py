from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase

from apps.audit.models import AuditLog

from .models import Profile, ProfileMembership, Workspace, WorkspaceMember
from .services import (
    WorkspaceMembershipConflict,
    WorkspacePeriodConflict,
    add_workspace_member,
    archive_profile,
    archive_workspace,
    create_profile_with_owner,
    create_workspace,
    restore_profile,
    restore_workspace,
    revoke_workspace_member,
)


User = get_user_model()


class LifecycleServiceDataMixin:

    def create_user(self, suffix):
        return User.objects.create_user(
            email=f"lifecycle-{suffix}@example.test",
            username=f"lifecycle-{suffix}",
            password="test-password-only",
        )

    def create_profile_owner(self, suffix):
        owner = self.create_user(f"{suffix}-owner")
        profile = create_profile_with_owner(
            name=f"{suffix} Profile",
            owner=owner,
        )
        return profile, owner


class LifecycleServiceAtomicityTests(LifecycleServiceDataMixin, TestCase):

    def setUp(self):
        self.profile, self.owner = self.create_profile_owner("atomicity")
        self.profile_admin = self.create_user("atomicity-profile-admin")
        self.target = self.create_user("atomicity-target")
        ProfileMembership.objects.create(
            profile=self.profile,
            user=self.profile_admin,
            role=ProfileMembership.Role.ADMIN,
        )
        self.target_profile_membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=self.target,
            role=ProfileMembership.Role.MEMBER,
        )
        self.workspace = Workspace.objects.create(
            profile=self.profile,
            owner=self.owner,
            name="Lifecycle Workspace",
            period=date(2026, 10, 1),
        )
        self.workspace_membership = WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.target,
            role=WorkspaceMember.Role.MEMBER,
        )

    def test_profile_lifecycle_is_owner_only_and_audited(self):
        with self.assertRaises(PermissionDenied):
            archive_profile(
                actor=self.profile_admin,
                profile_id=self.profile.id,
            )

        archived = archive_profile(
            actor=self.owner,
            profile_id=self.profile.id,
        )
        self.assertEqual(archived.status, Profile.Status.ARCHIVED)

        with self.assertRaises(PermissionDenied):
            restore_profile(
                actor=self.profile_admin,
                profile_id=self.profile.id,
            )

        restored = restore_profile(
            actor=self.owner,
            profile_id=self.profile.id,
        )
        self.assertEqual(restored.status, Profile.Status.ACTIVE)
        self.assertEqual(
            list(
                AuditLog.objects.filter(
                    entity_id=self.profile.id,
                    action__in=("profile.archived", "profile.restored"),
                )
                .order_by("created_at")
                .values_list("action", flat=True)
            ),
            ["profile.archived", "profile.restored"],
        )

    def test_profile_archive_and_restore_roll_back_with_audit_failure(self):
        with patch(
            "apps.workspace.services.AuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                archive_profile(
                    actor=self.owner,
                    profile_id=self.profile.id,
                )

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.status, Profile.Status.ACTIVE)
        self.assertFalse(
            AuditLog.objects.filter(
                entity_id=self.profile.id,
                action="profile.archived",
            ).exists()
        )

        archive_profile(actor=self.owner, profile_id=self.profile.id)
        with patch(
            "apps.workspace.services.AuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                restore_profile(
                    actor=self.owner,
                    profile_id=self.profile.id,
                )

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.status, Profile.Status.ARCHIVED)
        self.assertFalse(
            AuditLog.objects.filter(
                entity_id=self.profile.id,
                action="profile.restored",
            ).exists()
        )

    def test_workspace_archive_and_restore_roll_back_with_audit_failure(self):
        with patch(
            "apps.workspace.services.AuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                archive_workspace(
                    actor=self.profile_admin,
                    profile_id=self.profile.id,
                    workspace_id=self.workspace.id,
                )

        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.status, Workspace.Status.ACTIVE)
        self.assertFalse(
            AuditLog.objects.filter(
                entity_id=self.workspace.id,
                action="workspace.archived",
            ).exists()
        )

        archive_workspace(
            actor=self.profile_admin,
            profile_id=self.profile.id,
            workspace_id=self.workspace.id,
        )
        with patch(
            "apps.workspace.services.AuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                restore_workspace(
                    actor=self.profile_admin,
                    profile_id=self.profile.id,
                    workspace_id=self.workspace.id,
                )

        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.status, Workspace.Status.ARCHIVED)
        self.assertFalse(
            AuditLog.objects.filter(
                entity_id=self.workspace.id,
                action="workspace.restored",
            ).exists()
        )

    def test_member_revoke_and_reactivation_roll_back_with_audit_failure(self):
        with patch(
            "apps.workspace.services.AuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                revoke_workspace_member(
                    actor=self.owner,
                    profile_id=self.profile.id,
                    workspace_id=self.workspace.id,
                    membership_id=self.workspace_membership.id,
                )

        self.workspace_membership.refresh_from_db()
        self.assertTrue(self.workspace_membership.is_active)
        self.assertEqual(
            self.workspace_membership.role,
            WorkspaceMember.Role.MEMBER,
        )
        self.assertFalse(
            AuditLog.objects.filter(
                entity_id=self.workspace_membership.id,
                action="workspace.membership.revoked",
            ).exists()
        )

        revoke_workspace_member(
            actor=self.owner,
            profile_id=self.profile.id,
            workspace_id=self.workspace.id,
            membership_id=self.workspace_membership.id,
        )
        with patch(
            "apps.workspace.services.AuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                add_workspace_member(
                    actor=self.owner,
                    profile_id=self.profile.id,
                    workspace_id=self.workspace.id,
                    target_profile_membership_id=(
                        self.target_profile_membership.id
                    ),
                    role=WorkspaceMember.Role.ADMIN,
                )

        self.workspace_membership.refresh_from_db()
        self.assertFalse(self.workspace_membership.is_active)
        self.assertEqual(
            self.workspace_membership.role,
            WorkspaceMember.Role.MEMBER,
        )
        self.assertFalse(
            AuditLog.objects.filter(
                entity_id=self.workspace_membership.id,
                action="workspace.membership.reactivated",
            ).exists()
        )


class LifecycleServiceConcurrencyTests(
    LifecycleServiceDataMixin,
    TransactionTestCase,
):

    reset_sequences = False

    def test_concurrent_same_period_creation_has_one_winner_and_one_audit(self):
        profile, owner = self.create_profile_owner("period-race")
        period = date(2026, 11, 1)
        barrier = Barrier(2)

        def create(label):
            close_old_connections()
            try:
                actor = User.objects.get(id=owner.id)
                barrier.wait(timeout=10)
                try:
                    workspace = create_workspace(
                        actor=actor,
                        profile_id=profile.id,
                        name=f"Concurrent Workspace {label}",
                        period=period,
                    )
                except WorkspacePeriodConflict:
                    return "conflict", None
                return "created", workspace.id
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(create, "first"),
                executor.submit(create, "second"),
            )
            results = [future.result(timeout=20) for future in futures]

        outcomes = [outcome for outcome, _ in results]
        self.assertCountEqual(outcomes, ("created", "conflict"))
        created_id = next(
            workspace_id
            for outcome, workspace_id in results
            if outcome == "created"
        )
        self.assertEqual(
            Workspace.objects.filter(profile=profile, period=period).count(),
            1,
        )
        self.assertEqual(
            AuditLog.objects.filter(
                entity_id=created_id,
                action="workspace.created",
            ).count(),
            1,
        )

    def test_concurrent_reactivation_reuses_one_row_without_role_overwrite(self):
        profile, owner = self.create_profile_owner("reactivation-race")
        target = self.create_user("reactivation-race-target")
        target_profile_membership = ProfileMembership.objects.create(
            profile=profile,
            user=target,
            role=ProfileMembership.Role.MEMBER,
        )
        workspace = Workspace.objects.create(
            profile=profile,
            owner=owner,
            name="Reactivation Race Workspace",
            period=date(2026, 12, 1),
        )
        historical_membership = WorkspaceMember.objects.create(
            workspace=workspace,
            user=target,
            role=WorkspaceMember.Role.VIEWER,
            is_active=False,
        )
        barrier = Barrier(2)

        def reactivate(role):
            close_old_connections()
            try:
                actor = User.objects.get(id=owner.id)
                barrier.wait(timeout=10)
                try:
                    membership = add_workspace_member(
                        actor=actor,
                        profile_id=profile.id,
                        workspace_id=workspace.id,
                        target_profile_membership_id=(
                            target_profile_membership.id
                        ),
                        role=role,
                    )
                except WorkspaceMembershipConflict:
                    return "conflict", role
                return "reactivated", membership.role
            finally:
                close_old_connections()

        requested_roles = (
            WorkspaceMember.Role.MEMBER,
            WorkspaceMember.Role.ADMIN,
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = tuple(
                executor.submit(reactivate, role)
                for role in requested_roles
            )
            results = [future.result(timeout=20) for future in futures]

        outcomes = [outcome for outcome, _ in results]
        self.assertCountEqual(outcomes, ("reactivated", "conflict"))
        winning_role = next(
            role for outcome, role in results if outcome == "reactivated"
        )
        historical_membership.refresh_from_db()
        self.assertTrue(historical_membership.is_active)
        self.assertEqual(historical_membership.role, winning_role)
        self.assertIn(historical_membership.role, requested_roles)
        self.assertEqual(
            WorkspaceMember.objects.filter(
                workspace=workspace,
                user=target,
            ).count(),
            1,
        )
        reactivation_audit = AuditLog.objects.get(
            entity_id=historical_membership.id,
            action="workspace.membership.reactivated",
        )
        self.assertEqual(
            reactivation_audit.metadata["after"]["role"],
            winning_role,
        )
        self.assertFalse(
            AuditLog.objects.filter(
                entity_id=historical_membership.id,
                action="workspace.membership.created",
            ).exists()
        )

    def test_concurrent_reactivation_cannot_exceed_workspace_admin_ceiling(self):
        profile, owner = self.create_profile_owner("role-ceiling-race")
        workspace_admin = self.create_user("role-ceiling-race-admin")
        target = self.create_user("role-ceiling-race-target")
        ProfileMembership.objects.create(
            profile=profile,
            user=workspace_admin,
            role=ProfileMembership.Role.MEMBER,
        )
        target_profile_membership = ProfileMembership.objects.create(
            profile=profile,
            user=target,
            role=ProfileMembership.Role.MEMBER,
        )
        workspace = Workspace.objects.create(
            profile=profile,
            owner=owner,
            name="Role Ceiling Race Workspace",
            period=date(2027, 1, 1),
        )
        WorkspaceMember.objects.create(
            workspace=workspace,
            user=workspace_admin,
            role=WorkspaceMember.Role.ADMIN,
        )
        historical_membership = WorkspaceMember.objects.create(
            workspace=workspace,
            user=target,
            role=WorkspaceMember.Role.VIEWER,
            is_active=False,
        )
        barrier = Barrier(2)

        def reactivate(role):
            close_old_connections()
            try:
                actor = User.objects.get(id=workspace_admin.id)
                barrier.wait(timeout=10)
                try:
                    add_workspace_member(
                        actor=actor,
                        profile_id=profile.id,
                        workspace_id=workspace.id,
                        target_profile_membership_id=(
                            target_profile_membership.id
                        ),
                        role=role,
                    )
                except PermissionDenied:
                    return "denied"
                except WorkspaceMembershipConflict:
                    return "conflict"
                return "reactivated"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(reactivate, WorkspaceMember.Role.MEMBER),
                executor.submit(reactivate, WorkspaceMember.Role.ADMIN),
            )
            results = [future.result(timeout=20) for future in futures]

        self.assertCountEqual(results, ("reactivated", "denied"))
        historical_membership.refresh_from_db()
        self.assertTrue(historical_membership.is_active)
        self.assertEqual(
            historical_membership.role,
            WorkspaceMember.Role.MEMBER,
        )
        self.assertEqual(
            WorkspaceMember.objects.filter(
                workspace=workspace,
                user=target,
            ).count(),
            1,
        )
        self.assertEqual(
            AuditLog.objects.filter(
                entity_id=historical_membership.id,
                action="workspace.membership.reactivated",
            ).count(),
            1,
        )
