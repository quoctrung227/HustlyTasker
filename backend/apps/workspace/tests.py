from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import (
    IntegrityError,
    OperationalError,
    close_old_connections,
    connection,
    models,
    transaction,
)
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase

from apps.audit.models import AuditLog

from .models import Profile, ProfileMembership, Workspace, WorkspaceMember
from .services import (
    LastActiveProfileOwnerError,
    add_workspace_member,
    create_profile_with_owner,
    update_profile_membership,
)


User = get_user_model()


class WorkspaceTestDataMixin:

    def create_user(self, suffix, *, is_active=True):
        return User.objects.create_user(
            email=f"user-{suffix}@example.test",
            username=f"user-{suffix}",
            password="test-password-only",
            is_active=is_active,
        )


class ProfileFoundationTests(WorkspaceTestDataMixin, TestCase):

    def test_create_profile_creates_active_owner_and_audit_event(self):
        owner = self.create_user("owner")

        profile = create_profile_with_owner(
            name="  Example Company  ",
            owner=owner,
        )

        self.assertEqual(profile.name, "Example Company")
        membership = ProfileMembership.objects.get(
            profile=profile,
            user=owner,
        )
        self.assertEqual(membership.role, ProfileMembership.Role.OWNER)
        self.assertTrue(membership.is_active)

        audit = AuditLog.objects.get(
            action="profile.membership.created",
            entity_id=membership.id,
        )
        self.assertEqual(audit.user, owner)
        self.assertEqual(audit.metadata["profile_id"], str(profile.id))
        self.assertNotIn("email", audit.metadata)

    def test_active_user_can_own_multiple_profiles(self):
        owner = self.create_user("multi-profile-owner")

        first_profile = create_profile_with_owner(
            name="First Company",
            owner=owner,
        )
        second_profile = create_profile_with_owner(
            name="Second Company",
            owner=owner,
        )

        self.assertNotEqual(first_profile.id, second_profile.id)
        self.assertEqual(
            ProfileMembership.objects.filter(
                user=owner,
                role=ProfileMembership.Role.OWNER,
                is_active=True,
            ).count(),
            2,
        )

    def test_inactive_user_cannot_be_initial_profile_owner(self):
        inactive_user = self.create_user("inactive", is_active=False)

        with self.assertRaises(ValidationError):
            create_profile_with_owner(
                name="Invalid Company",
                owner=inactive_user,
            )

        self.assertFalse(Profile.objects.exists())

    def test_database_rejects_duplicate_profile_membership(self):
        owner = self.create_user("duplicate")
        profile = create_profile_with_owner(name="Company", owner=owner)

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProfileMembership.objects.create(
                profile=profile,
                user=owner,
                role=ProfileMembership.Role.MEMBER,
            )

    def test_database_allows_membership_history_but_only_one_active_row(self):
        owner = self.create_user("membership-history-owner")
        member = self.create_user("membership-history-member")
        profile = create_profile_with_owner(name="Company", owner=owner)

        ProfileMembership.objects.create(
            profile=profile,
            user=member,
            role=ProfileMembership.Role.MEMBER,
            is_active=False,
        )
        ProfileMembership.objects.create(
            profile=profile,
            user=member,
            role=ProfileMembership.Role.MEMBER,
            is_active=False,
        )
        ProfileMembership.objects.create(
            profile=profile,
            user=member,
            role=ProfileMembership.Role.MEMBER,
            is_active=True,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProfileMembership.objects.create(
                profile=profile,
                user=member,
                role=ProfileMembership.Role.ADMIN,
                is_active=True,
            )

    def test_database_rejects_unknown_profile_role(self):
        owner = self.create_user("role-owner")
        member = self.create_user("invalid-role")
        profile = create_profile_with_owner(name="Company", owner=owner)

        with self.assertRaises(IntegrityError), transaction.atomic():
            ProfileMembership.objects.create(
                profile=profile,
                user=member,
                role="UNKNOWN",
            )

    def test_multiple_active_profile_owners_are_supported(self):
        first_owner = self.create_user("first-owner")
        second_owner = self.create_user("second-owner")
        profile = create_profile_with_owner(
            name="Multi-owner Company",
            owner=first_owner,
        )

        ProfileMembership.objects.create(
            profile=profile,
            user=second_owner,
            role=ProfileMembership.Role.OWNER,
            is_active=True,
        )

        self.assertEqual(
            ProfileMembership.objects.filter(
                profile=profile,
                role=ProfileMembership.Role.OWNER,
                is_active=True,
            ).count(),
            2,
        )

    def test_active_owner_membership_requires_active_user_account(self):
        initial_owner = self.create_user("active-initial-owner")
        inactive_user = self.create_user(
            "inactive-additional-owner",
            is_active=False,
        )
        profile = create_profile_with_owner(
            name="Owner Account Validation",
            owner=initial_owner,
        )

        membership = ProfileMembership(
            profile=profile,
            user=inactive_user,
            role=ProfileMembership.Role.OWNER,
            is_active=True,
        )
        with self.assertRaises(ValidationError):
            membership.full_clean()


class ProfileMembershipServiceTests(WorkspaceTestDataMixin, TestCase):

    def setUp(self):
        self.owner = self.create_user("service-owner")
        self.admin = self.create_user("service-admin")
        self.member = self.create_user("service-member")
        self.profile = create_profile_with_owner(
            name="Service Company",
            owner=self.owner,
        )
        self.owner_membership = ProfileMembership.objects.get(
            profile=self.profile,
            user=self.owner,
        )
        self.admin_membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=self.admin,
            role=ProfileMembership.Role.ADMIN,
        )
        self.member_membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=self.member,
            role=ProfileMembership.Role.MEMBER,
        )

    def test_last_active_owner_cannot_be_deactivated_or_demoted(self):
        with self.assertRaises(LastActiveProfileOwnerError):
            update_profile_membership(
                membership_id=self.owner_membership.id,
                actor=self.owner,
                is_active=False,
            )

        with self.assertRaises(LastActiveProfileOwnerError):
            update_profile_membership(
                membership_id=self.owner_membership.id,
                actor=self.owner,
                role=ProfileMembership.Role.ADMIN,
            )

        self.owner_membership.refresh_from_db()
        self.assertTrue(self.owner_membership.is_active)
        self.assertEqual(
            self.owner_membership.role,
            ProfileMembership.Role.OWNER,
        )

    def test_owner_can_promote_second_owner_then_deactivate_self(self):
        update_profile_membership(
            membership_id=self.member_membership.id,
            actor=self.owner,
            role=ProfileMembership.Role.OWNER,
        )
        update_profile_membership(
            membership_id=self.owner_membership.id,
            actor=self.owner,
            is_active=False,
        )

        self.owner_membership.refresh_from_db()
        self.member_membership.refresh_from_db()
        self.assertFalse(self.owner_membership.is_active)
        self.assertTrue(self.member_membership.is_active)
        self.assertEqual(
            self.member_membership.role,
            ProfileMembership.Role.OWNER,
        )
        self.assertEqual(
            AuditLog.objects.filter(
                action="profile.membership.updated"
            ).count(),
            2,
        )

    def test_admin_cannot_appoint_or_modify_owner(self):
        with self.assertRaises(PermissionDenied):
            update_profile_membership(
                membership_id=self.member_membership.id,
                actor=self.admin,
                role=ProfileMembership.Role.OWNER,
            )

        with self.assertRaises(PermissionDenied):
            update_profile_membership(
                membership_id=self.owner_membership.id,
                actor=self.admin,
                is_active=False,
            )

    def test_non_manager_cannot_change_profile_membership(self):
        with self.assertRaises(PermissionDenied):
            update_profile_membership(
                membership_id=self.admin_membership.id,
                actor=self.member,
                is_active=False,
            )

    def test_manager_role_does_not_apply_to_another_profile(self):
        other_owner = self.create_user("other-profile-owner")
        create_profile_with_owner(
            name="Other Profile",
            owner=other_owner,
        )

        with self.assertRaises(PermissionDenied):
            update_profile_membership(
                membership_id=self.member_membership.id,
                actor=other_owner,
                role=ProfileMembership.Role.ADMIN,
            )

        self.member_membership.refresh_from_db()
        self.assertEqual(
            self.member_membership.role,
            ProfileMembership.Role.MEMBER,
        )

    def test_inactive_account_cannot_act_or_be_promoted_to_active_owner(self):
        self.admin.is_active = False
        self.admin.save(update_fields=("is_active",))

        with self.assertRaises(PermissionDenied):
            update_profile_membership(
                membership_id=self.member_membership.id,
                actor=self.admin,
                role=ProfileMembership.Role.ADMIN,
            )

        self.member.is_active = False
        self.member.save(update_fields=("is_active",))
        with self.assertRaises(ValidationError):
            update_profile_membership(
                membership_id=self.member_membership.id,
                actor=self.owner,
                role=ProfileMembership.Role.OWNER,
            )

    def test_inactive_owner_is_not_counted_as_last_owner_replacement(self):
        inactive_owner = self.create_user("inactive-second-owner")
        ProfileMembership.objects.create(
            profile=self.profile,
            user=inactive_owner,
            role=ProfileMembership.Role.OWNER,
            is_active=True,
        )
        inactive_owner.is_active = False
        inactive_owner.save(update_fields=("is_active",))

        with self.assertRaises(LastActiveProfileOwnerError):
            update_profile_membership(
                membership_id=self.owner_membership.id,
                actor=self.owner,
                is_active=False,
            )

    def test_generic_update_cannot_reactivate_membership(self):
        inactive_member = self.create_user("inactive-membership")
        membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=inactive_member,
            role=ProfileMembership.Role.MEMBER,
            is_active=False,
        )

        with self.assertRaises(ValidationError):
            update_profile_membership(
                membership_id=membership.id,
                actor=self.owner,
                is_active=True,
            )

    def test_workspace_owner_must_be_reassigned_before_manager_deactivation(self):
        second_owner = self.create_user("workspace-transition-owner")
        second_membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=second_owner,
            role=ProfileMembership.Role.OWNER,
            is_active=True,
        )
        workspace = Workspace.objects.create(
            name="Manager Transition Workspace",
            profile=self.profile,
            owner=second_owner,
        )

        with self.assertRaises(ValidationError):
            update_profile_membership(
                membership_id=second_membership.id,
                actor=self.owner,
                is_active=False,
            )

        workspace.owner = self.owner
        workspace.save(update_fields=("owner",))
        updated_membership = update_profile_membership(
            membership_id=second_membership.id,
            actor=self.owner,
            is_active=False,
        )
        self.assertFalse(updated_membership.is_active)


class WorkspaceTenantValidationTests(WorkspaceTestDataMixin, TestCase):

    def setUp(self):
        self.owner = self.create_user("workspace-owner")
        self.member = self.create_user("workspace-member")
        self.outsider = self.create_user("workspace-outsider")
        self.profile = create_profile_with_owner(
            name="Workspace Company",
            owner=self.owner,
        )
        ProfileMembership.objects.create(
            profile=self.profile,
            user=self.member,
            role=ProfileMembership.Role.MEMBER,
        )

    def test_new_workspace_requires_profile_and_profile_manager_owner(self):
        workspace = Workspace(
            name="October 2026",
            profile=self.profile,
            owner=self.owner,
        )
        workspace.full_clean()
        workspace.save()

        self.assertEqual(workspace.profile, self.profile)

        with self.assertRaises(ValidationError):
            Workspace.objects.create(
                name="Missing Profile",
                owner=self.owner,
            )

        with self.assertRaises(ValidationError):
            Workspace(
                name="Invalid Manager",
                profile=self.profile,
                owner=self.member,
            ).full_clean()

    def test_workspace_cannot_be_moved_to_another_profile(self):
        workspace = Workspace.objects.create(
            name="October 2026",
            profile=self.profile,
            owner=self.owner,
        )
        other_profile = create_profile_with_owner(
            name="Other Company",
            owner=self.owner,
        )

        workspace.profile = other_profile
        with self.assertRaises(ValidationError):
            workspace.save(update_fields=("profile",))

        workspace.refresh_from_db()
        self.assertEqual(workspace.profile, self.profile)

    def test_legacy_workspace_mapping_requires_every_member_in_profile(self):
        legacy_workspace = Workspace(
            name="Legacy Workspace",
            owner=self.owner,
        )
        Workspace.objects.bulk_create((legacy_workspace,))
        legacy_membership = WorkspaceMember(
            workspace=legacy_workspace,
            user=self.outsider,
            role=WorkspaceMember.Role.MEMBER,
        )
        WorkspaceMember.objects.bulk_create((legacy_membership,))

        legacy_workspace.profile = self.profile
        with self.assertRaises(ValidationError):
            legacy_workspace.save(update_fields=("profile",))

        ProfileMembership.objects.create(
            profile=self.profile,
            user=self.outsider,
            role=ProfileMembership.Role.MEMBER,
        )
        legacy_workspace.save(update_fields=("profile",))
        legacy_workspace.refresh_from_db()
        self.assertEqual(legacy_workspace.profile, self.profile)

    def test_workspace_member_requires_active_membership_in_same_profile(self):
        workspace = Workspace.objects.create(
            name="October 2026",
            profile=self.profile,
            owner=self.owner,
        )

        valid_membership = WorkspaceMember(
            workspace=workspace,
            user=self.member,
            role=WorkspaceMember.Role.MEMBER,
        )
        valid_membership.save()

        with self.assertRaises(ValidationError):
            WorkspaceMember.objects.create(
                workspace=workspace,
                user=self.outsider,
                role=WorkspaceMember.Role.MEMBER,
            )

        other_profile = create_profile_with_owner(
            name="Other Company",
            owner=self.outsider,
        )
        self.assertNotEqual(other_profile.id, self.profile.id)

        with self.assertRaises(ValidationError):
            WorkspaceMember(
                workspace=workspace,
                user=self.outsider,
                role=WorkspaceMember.Role.MEMBER,
            ).full_clean()

    def test_workspace_member_requires_active_profile_membership(self):
        workspace = Workspace.objects.create(
            name="October 2026",
            profile=self.profile,
            owner=self.owner,
        )
        profile_membership = ProfileMembership.objects.get(
            profile=self.profile,
            user=self.member,
        )
        profile_membership.is_active = False
        profile_membership.save(update_fields=("is_active", "updated_at"))

        with self.assertRaises(ValidationError):
            WorkspaceMember.objects.create(
                workspace=workspace,
                user=self.member,
                role=WorkspaceMember.Role.MEMBER,
            )

    def test_profile_manager_can_directly_add_existing_profile_member(self):
        workspace = Workspace.objects.create(
            name="October 2026",
            profile=self.profile,
            owner=self.owner,
        )

        membership = add_workspace_member(
            workspace_id=workspace.id,
            user=self.member,
            role=WorkspaceMember.Role.MEMBER,
            actor=self.owner,
        )

        self.assertEqual(membership.workspace, workspace)
        audit = AuditLog.objects.get(
            action="workspace.membership.created",
            entity_id=membership.id,
        )
        self.assertEqual(audit.entity_name, "WorkspaceMember")
        self.assertEqual(audit.metadata["profile_id"], str(self.profile.id))

    def test_profile_admin_can_directly_add_existing_profile_member(self):
        admin_user = self.create_user("workspace-profile-admin")
        ProfileMembership.objects.create(
            profile=self.profile,
            user=admin_user,
            role=ProfileMembership.Role.ADMIN,
        )
        workspace = Workspace.objects.create(
            name="November 2026",
            profile=self.profile,
            owner=self.owner,
        )

        membership = add_workspace_member(
            workspace_id=workspace.id,
            user=self.member,
            role=WorkspaceMember.Role.VIEWER,
            actor=admin_user,
        )

        self.assertEqual(membership.role, WorkspaceMember.Role.VIEWER)

    def test_direct_add_requires_profile_manager_and_existing_member(self):
        workspace = Workspace.objects.create(
            name="October 2026",
            profile=self.profile,
            owner=self.owner,
        )

        with self.assertRaises(PermissionDenied):
            add_workspace_member(
                workspace_id=workspace.id,
                user=self.member,
                role=WorkspaceMember.Role.MEMBER,
                actor=self.member,
            )

        with self.assertRaises(ValidationError):
            add_workspace_member(
                workspace_id=workspace.id,
                user=self.outsider,
                role=WorkspaceMember.Role.MEMBER,
                actor=self.owner,
            )

    def test_other_profile_manager_cannot_add_workspace_member(self):
        workspace = Workspace.objects.create(
            name="Cross Profile Workspace",
            profile=self.profile,
            owner=self.owner,
        )
        other_owner = self.create_user("cross-profile-owner")
        create_profile_with_owner(
            name="Cross Profile Company",
            owner=other_owner,
        )

        with self.assertRaises(PermissionDenied):
            add_workspace_member(
                workspace_id=workspace.id,
                user=self.member,
                role=WorkspaceMember.Role.MEMBER,
                actor=other_owner,
            )

        self.assertFalse(
            WorkspaceMember.objects.filter(
                workspace=workspace,
                user=self.member,
            ).exists()
        )

    def test_workspace_owner_delete_is_protected(self):
        Workspace.objects.create(
            name="Protected Workspace",
            profile=self.profile,
            owner=self.owner,
        )

        with self.assertRaises(ProtectedError):
            self.owner.delete()

        self.assertIs(
            Workspace._meta.get_field("owner").remote_field.on_delete,
            models.PROTECT,
        )


class ProfileOwnerConcurrencyTests(
    WorkspaceTestDataMixin,
    TransactionTestCase,
):

    reset_sequences = False

    def test_concurrent_owner_deactivation_keeps_one_active_owner(self):
        first_owner = self.create_user("concurrent-first")
        second_owner = self.create_user("concurrent-second")
        profile = create_profile_with_owner(
            name="Concurrent Company",
            owner=first_owner,
        )
        first_membership = ProfileMembership.objects.get(
            profile=profile,
            user=first_owner,
        )
        second_membership = ProfileMembership.objects.create(
            profile=profile,
            user=second_owner,
            role=ProfileMembership.Role.OWNER,
            is_active=True,
        )
        barrier = Barrier(2)

        def deactivate(membership_id, actor_id):
            close_old_connections()
            try:
                actor = User.objects.get(id=actor_id)
                barrier.wait(timeout=10)
                try:
                    update_profile_membership(
                        membership_id=membership_id,
                        actor=actor,
                        is_active=False,
                    )
                except LastActiveProfileOwnerError:
                    return "blocked"
                return "updated"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(
                    deactivate,
                    first_membership.id,
                    first_owner.id,
                ),
                executor.submit(
                    deactivate,
                    second_membership.id,
                    second_owner.id,
                ),
            )
            results = [future.result(timeout=20) for future in futures]

        self.assertCountEqual(results, ("updated", "blocked"))
        self.assertEqual(
            ProfileMembership.objects.filter(
                profile=profile,
                role=ProfileMembership.Role.OWNER,
                is_active=True,
            ).count(),
            1,
        )

    def test_workspace_create_and_manager_demotion_cannot_commit_invalid_state(self):
        retained_owner = self.create_user("race-retained-owner")
        workspace_owner = self.create_user("race-workspace-owner")
        profile = create_profile_with_owner(
            name="Workspace Manager Race",
            owner=retained_owner,
        )
        workspace_owner_membership = ProfileMembership.objects.create(
            profile=profile,
            user=workspace_owner,
            role=ProfileMembership.Role.OWNER,
            is_active=True,
        )
        barrier = Barrier(2)

        def create_workspace():
            close_old_connections()
            try:
                thread_profile = Profile.objects.get(id=profile.id)
                thread_owner = User.objects.get(id=workspace_owner.id)
                barrier.wait(timeout=10)
                try:
                    Workspace.objects.create(
                        name="Concurrent Workspace",
                        profile=thread_profile,
                        owner=thread_owner,
                    )
                except ValidationError:
                    return "blocked"
                return "updated"
            finally:
                close_old_connections()

        def demote_workspace_owner():
            close_old_connections()
            try:
                actor = User.objects.get(id=retained_owner.id)
                barrier.wait(timeout=10)
                try:
                    update_profile_membership(
                        membership_id=workspace_owner_membership.id,
                        actor=actor,
                        role=ProfileMembership.Role.MEMBER,
                    )
                except ValidationError:
                    return "blocked"
                return "updated"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(create_workspace),
                executor.submit(demote_workspace_owner),
            )
            results = [future.result(timeout=20) for future in futures]

        self.assertCountEqual(results, ("updated", "blocked"))
        workspace_owner_membership.refresh_from_db()
        workspace_exists = Workspace.objects.filter(
            profile=profile,
            owner=workspace_owner,
        ).exists()
        if workspace_exists:
            self.assertTrue(workspace_owner_membership.is_active)
            self.assertIn(
                workspace_owner_membership.role,
                (
                    ProfileMembership.Role.OWNER,
                    ProfileMembership.Role.ADMIN,
                ),
            )

    def test_concurrent_legacy_mapping_cannot_reparent_workspace(self):
        owner = self.create_user("legacy-map-owner")
        first_profile = create_profile_with_owner(
            name="First Mapping Profile",
            owner=owner,
        )
        second_profile = create_profile_with_owner(
            name="Second Mapping Profile",
            owner=owner,
        )
        legacy_workspace = Workspace(
            name="Unmapped Legacy Workspace",
            owner=owner,
        )
        Workspace.objects.bulk_create((legacy_workspace,))
        barrier = Barrier(2)

        def map_workspace(profile_id):
            close_old_connections()
            try:
                workspace = Workspace.objects.get(id=legacy_workspace.id)
                profile = Profile.objects.get(id=profile_id)
                workspace.profile = profile
                barrier.wait(timeout=10)
                try:
                    workspace.save(update_fields=("profile",))
                except ValidationError:
                    return "blocked"
                return "updated"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(map_workspace, first_profile.id),
                executor.submit(map_workspace, second_profile.id),
            )
            results = [future.result(timeout=20) for future in futures]

        self.assertCountEqual(results, ("updated", "blocked"))
        legacy_workspace.refresh_from_db()
        self.assertIn(
            legacy_workspace.profile_id,
            (first_profile.id, second_profile.id),
        )

    def test_stale_legacy_save_cannot_undo_profile_mapping(self):
        owner = self.create_user("stale-legacy-owner")
        profile = create_profile_with_owner(
            name="Stale Legacy Mapping Profile",
            owner=owner,
        )
        legacy_workspace = Workspace(
            name="Stale Legacy Workspace",
            owner=owner,
        )
        Workspace.objects.bulk_create((legacy_workspace,))

        stale_validated = Event()
        original_full_clean = Workspace.full_clean

        def observe_stale_validation(instance, *args, **kwargs):
            result = original_full_clean(instance, *args, **kwargs)
            if (
                instance.id == legacy_workspace.id
                and instance.profile_id is None
            ):
                stale_validated.set()
            return result

        def save_stale_workspace():
            close_old_connections()
            try:
                workspace = Workspace.objects.get(id=legacy_workspace.id)
                workspace.name = "Stale Writer"
                try:
                    with transaction.atomic():
                        with connection.cursor() as cursor:
                            cursor.execute("SET LOCAL lock_timeout = '1s'")
                        workspace.save()
                except OperationalError:
                    return "locked"
                return "unexpectedly-updated"
            finally:
                close_old_connections()

        with patch.object(Workspace, "full_clean", observe_stale_validation):
            with transaction.atomic():
                locked_profile = Profile.objects.select_for_update().get(
                    id=profile.id
                )
                mapped_workspace = Workspace.objects.select_for_update().get(
                    id=legacy_workspace.id
                )
                mapped_workspace.profile = locked_profile
                mapped_workspace.save(update_fields=("profile",))

                with ThreadPoolExecutor(max_workers=1) as executor:
                    stale_result = executor.submit(
                        save_stale_workspace
                    ).result(timeout=10)

                self.assertEqual(stale_result, "locked")
                self.assertFalse(stale_validated.is_set())

        legacy_workspace.refresh_from_db()
        self.assertEqual(legacy_workspace.profile_id, profile.id)
        self.assertEqual(legacy_workspace.name, "Stale Legacy Workspace")
