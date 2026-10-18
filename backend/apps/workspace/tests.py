from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from threading import Barrier, Event
from unittest.mock import patch
from uuid import uuid4

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

from .access import (
    ProfileAccessContext,
    TenantAccessNotFound,
    WorkspaceAccessContext,
    can_edit_workspace,
    can_manage_workspace_members,
    can_read_workspace,
    profiles_visible_to,
    resolve_profile_access_context,
    resolve_workspace_access_context,
    workspaces_visible_to,
)
from .models import Profile, ProfileMembership, Workspace, WorkspaceMember
from .services import (
    LastActiveProfileOwnerError,
    WorkspaceMembershipConflict,
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


class TenantAccessContextTests(WorkspaceTestDataMixin, TestCase):

    def setUp(self):
        self.owner = self.create_user("access-owner")
        self.admin = self.create_user("access-admin")
        self.member = self.create_user("access-member")
        self.other_owner = self.create_user("access-other-owner")

        self.profile = create_profile_with_owner(
            name="Access Profile",
            owner=self.owner,
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
        self.other_profile = create_profile_with_owner(
            name="Other Access Profile",
            owner=self.other_owner,
        )
        self.other_member_membership = ProfileMembership.objects.create(
            profile=self.other_profile,
            user=self.member,
            role=ProfileMembership.Role.MEMBER,
        )

        self.admin_workspace = self._create_workspace("Workspace Admin")
        self.editor_workspace = self._create_workspace("Workspace Editor")
        self.viewer_workspace = self._create_workspace("Workspace Viewer")
        self.legacy_owner_workspace = self._create_workspace(
            "Legacy Workspace Owner"
        )
        self.unassigned_workspace = self._create_workspace(
            "Unassigned Workspace"
        )
        self.other_workspace = Workspace.objects.create(
            name="Other Profile Workspace",
            profile=self.other_profile,
            owner=self.other_owner,
        )
        self.unmapped_workspace = Workspace(
            name="Unmapped Legacy Workspace",
            owner=self.owner,
        )
        Workspace.objects.bulk_create((self.unmapped_workspace,))

        for workspace, role in (
            (self.admin_workspace, WorkspaceMember.Role.ADMIN),
            (self.editor_workspace, WorkspaceMember.Role.MEMBER),
            (self.viewer_workspace, WorkspaceMember.Role.VIEWER),
            (self.legacy_owner_workspace, WorkspaceMember.Role.OWNER),
        ):
            WorkspaceMember.objects.create(
                workspace=workspace,
                user=self.member,
                role=role,
            )

    def _create_workspace(self, name):
        return Workspace.objects.create(
            name=name,
            profile=self.profile,
            owner=self.owner,
        )

    def test_profile_visibility_uses_current_active_account_and_memberships(self):
        self.assertSetEqual(
            set(profiles_visible_to(self.member).values_list("id", flat=True)),
            {self.profile.id, self.other_profile.id},
        )

        self.other_member_membership.is_active = False
        self.other_member_membership.save(
            update_fields=("is_active", "updated_at")
        )
        self.assertSetEqual(
            set(profiles_visible_to(self.member).values_list("id", flat=True)),
            {self.profile.id},
        )

        User.objects.filter(id=self.member.id).update(is_active=False)
        self.assertFalse(profiles_visible_to(self.member).exists())

    def test_profile_context_is_id_based_immutable_and_tenant_scoped(self):
        context = resolve_profile_access_context(
            self.member,
            self.profile.id,
        )

        self.assertIsInstance(context, ProfileAccessContext)
        self.assertEqual(context.user_id, self.member.id)
        self.assertEqual(context.profile_id, self.profile.id)
        self.assertEqual(context.membership_id, self.member_membership.id)
        self.assertEqual(context.profile_role, ProfileMembership.Role.MEMBER)
        with self.assertRaises(FrozenInstanceError):
            context.profile_role = ProfileMembership.Role.OWNER

    def test_profile_context_hides_unknown_and_out_of_scope_profiles(self):
        failures = []
        for profile_id in (self.profile.id, uuid4()):
            with self.assertRaises(TenantAccessNotFound) as raised:
                resolve_profile_access_context(self.other_owner, profile_id)
            failures.append(str(raised.exception))

        self.assertEqual(failures[0], failures[1])

    def test_profile_managers_see_every_mapped_workspace_in_profile(self):
        expected_ids = {
            self.admin_workspace.id,
            self.editor_workspace.id,
            self.viewer_workspace.id,
            self.legacy_owner_workspace.id,
            self.unassigned_workspace.id,
        }

        for actor in (self.owner, self.admin):
            with self.subTest(actor=actor.username):
                profile_context = resolve_profile_access_context(
                    actor,
                    self.profile.id,
                )
                self.assertSetEqual(
                    set(
                        workspaces_visible_to(profile_context).values_list(
                            "id",
                            flat=True,
                        )
                    ),
                    expected_ids,
                )

    def test_profile_member_sees_only_explicit_effective_workspace_roles(self):
        profile_context = resolve_profile_access_context(
            self.member,
            self.profile.id,
        )

        self.assertSetEqual(
            set(
                workspaces_visible_to(profile_context).values_list(
                    "id",
                    flat=True,
                )
            ),
            {
                self.admin_workspace.id,
                self.editor_workspace.id,
                self.viewer_workspace.id,
            },
        )

        with self.assertRaises(TenantAccessNotFound):
            resolve_workspace_access_context(
                profile_context,
                self.legacy_owner_workspace.id,
            )
        with self.assertRaises(TenantAccessNotFound):
            resolve_workspace_access_context(
                profile_context,
                self.unassigned_workspace.id,
            )

    def test_workspace_capabilities_match_effective_role_mapping(self):
        owner_context = resolve_profile_access_context(
            self.owner,
            self.profile.id,
        )
        inherited_context = resolve_workspace_access_context(
            owner_context,
            self.unassigned_workspace.id,
        )
        self.assertIsNone(inherited_context.workspace_role)
        self.assertTrue(can_read_workspace(inherited_context))
        self.assertTrue(can_edit_workspace(inherited_context))
        self.assertTrue(can_manage_workspace_members(inherited_context))

        profile_context = resolve_profile_access_context(
            self.member,
            self.profile.id,
        )
        role_expectations = (
            (self.admin_workspace, True, True, True),
            (self.editor_workspace, True, True, False),
            (self.viewer_workspace, True, False, False),
        )
        for workspace, can_read, can_edit, can_manage in role_expectations:
            with self.subTest(workspace=workspace.name):
                context = resolve_workspace_access_context(
                    profile_context,
                    workspace.id,
                )
                self.assertIsInstance(context, WorkspaceAccessContext)
                self.assertEqual(can_read_workspace(context), can_read)
                self.assertEqual(can_edit_workspace(context), can_edit)
                self.assertEqual(
                    can_manage_workspace_members(context),
                    can_manage,
                )

        legacy_context = WorkspaceAccessContext(
            profile_context=profile_context,
            workspace_id=self.legacy_owner_workspace.id,
            workspace_role=WorkspaceMember.Role.OWNER,
        )
        self.assertFalse(can_read_workspace(legacy_context))
        self.assertFalse(can_edit_workspace(legacy_context))
        self.assertFalse(can_manage_workspace_members(legacy_context))

    def test_replaced_workspace_context_cannot_forge_capabilities(self):
        profile_context = resolve_profile_access_context(
            self.member,
            self.profile.id,
        )
        viewer_context = resolve_workspace_access_context(
            profile_context,
            self.viewer_workspace.id,
        )

        forged_context = replace(
            viewer_context,
            workspace_role=WorkspaceMember.Role.ADMIN,
        )

        self.assertFalse(can_read_workspace(forged_context))
        self.assertFalse(can_edit_workspace(forged_context))
        self.assertFalse(can_manage_workspace_members(forged_context))

    def test_workspace_capabilities_fail_closed_after_role_or_user_revocation(self):
        profile_context = resolve_profile_access_context(
            self.member,
            self.profile.id,
        )
        admin_context = resolve_workspace_access_context(
            profile_context,
            self.admin_workspace.id,
        )

        WorkspaceMember.objects.filter(
            workspace=self.admin_workspace,
            user=self.member,
        ).update(role=WorkspaceMember.Role.VIEWER)

        self.assertFalse(can_read_workspace(admin_context))
        self.assertFalse(can_edit_workspace(admin_context))
        self.assertFalse(can_manage_workspace_members(admin_context))

        viewer_context = resolve_workspace_access_context(
            profile_context,
            self.admin_workspace.id,
        )
        self.assertTrue(can_read_workspace(viewer_context))
        self.assertFalse(can_edit_workspace(viewer_context))
        self.assertFalse(can_manage_workspace_members(viewer_context))

        User.objects.filter(id=self.member.id).update(is_active=False)
        self.assertFalse(can_read_workspace(viewer_context))

        forged_profile_context = ProfileAccessContext(
            user_id=self.member.id,
            profile_id=self.profile.id,
            membership_id=self.member_membership.id,
            profile_role=ProfileMembership.Role.OWNER,
        )
        forged_workspace_context = WorkspaceAccessContext(
            profile_context=forged_profile_context,
            workspace_id=self.unassigned_workspace.id,
            workspace_role=None,
        )
        self.assertFalse(can_read_workspace(forged_workspace_context))
        self.assertFalse(can_edit_workspace(forged_workspace_context))
        self.assertFalse(
            can_manage_workspace_members(forged_workspace_context)
        )
        with self.assertRaises(TenantAccessNotFound):
            workspaces_visible_to(forged_profile_context)

    def test_workspace_context_hides_unknown_and_out_of_scope_workspaces(self):
        other_context = resolve_profile_access_context(
            self.other_owner,
            self.other_profile.id,
        )
        failures = []
        for workspace_id in (self.unassigned_workspace.id, uuid4()):
            with self.assertRaises(TenantAccessNotFound) as raised:
                resolve_workspace_access_context(other_context, workspace_id)
            failures.append(str(raised.exception))

        self.assertEqual(failures[0], failures[1])

    def test_stale_profile_context_fails_closed(self):
        member_context = resolve_profile_access_context(
            self.member,
            self.profile.id,
        )
        unevaluated_scope = workspaces_visible_to(member_context)
        self.member_membership.is_active = False
        self.member_membership.save(
            update_fields=("is_active", "updated_at")
        )

        self.assertFalse(unevaluated_scope.exists())
        with self.assertRaises(TenantAccessNotFound):
            workspaces_visible_to(member_context)
        with self.assertRaises(TenantAccessNotFound):
            resolve_workspace_access_context(
                member_context,
                self.editor_workspace.id,
            )

        admin_context = resolve_profile_access_context(
            self.admin,
            self.profile.id,
        )
        User.objects.filter(id=self.admin.id).update(is_active=False)
        with self.assertRaises(TenantAccessNotFound):
            workspaces_visible_to(admin_context)


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
                profile_id=self.profile.id,
                membership_id=self.owner_membership.id,
                actor=self.owner,
                is_active=False,
            )

        with self.assertRaises(LastActiveProfileOwnerError):
            update_profile_membership(
                profile_id=self.profile.id,
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
            profile_id=self.profile.id,
            membership_id=self.member_membership.id,
            actor=self.owner,
            role=ProfileMembership.Role.OWNER,
        )
        update_profile_membership(
            profile_id=self.profile.id,
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
                profile_id=self.profile.id,
                membership_id=self.member_membership.id,
                actor=self.admin,
                role=ProfileMembership.Role.OWNER,
            )

        with self.assertRaises(PermissionDenied):
            update_profile_membership(
                profile_id=self.profile.id,
                membership_id=self.owner_membership.id,
                actor=self.admin,
                is_active=False,
            )

    def test_admin_can_deactivate_current_profile_member(self):
        updated_membership = update_profile_membership(
            profile_id=self.profile.id,
            membership_id=self.member_membership.id,
            actor=self.admin,
            is_active=False,
        )

        self.assertFalse(updated_membership.is_active)
        audit = AuditLog.objects.get(
            action="profile.membership.updated",
            entity_id=self.member_membership.id,
        )
        self.assertEqual(audit.user, self.admin)

    def test_admin_cannot_manage_admin_or_promote_member(self):
        attempts = (
            {
                "membership_id": self.admin_membership.id,
                "role": ProfileMembership.Role.MEMBER,
            },
            {
                "membership_id": self.member_membership.id,
                "role": ProfileMembership.Role.ADMIN,
            },
        )

        for attempt in attempts:
            with self.subTest(attempt=attempt):
                with self.assertRaises(PermissionDenied):
                    update_profile_membership(
                        profile_id=self.profile.id,
                        actor=self.admin,
                        **attempt,
                    )

        self.assertFalse(
            AuditLog.objects.filter(
                action="profile.membership.updated"
            ).exists()
        )

    def test_target_lookup_hides_cross_profile_and_unknown_memberships(self):
        other_owner = self.create_user("scoped-target-other-owner")
        other_profile = create_profile_with_owner(
            name="Scoped Target Other Profile",
            owner=other_owner,
        )
        failures = []

        for membership_id in (
            ProfileMembership.objects.get(
                profile=other_profile,
                user=other_owner,
            ).id,
            uuid4(),
        ):
            with self.assertRaises(TenantAccessNotFound) as raised:
                update_profile_membership(
                    profile_id=self.profile.id,
                    membership_id=membership_id,
                    actor=self.owner,
                    is_active=False,
                )
            failures.append(str(raised.exception))

        self.assertEqual(failures[0], failures[1])
        self.assertFalse(
            AuditLog.objects.filter(
                action="profile.membership.updated"
            ).exists()
        )

    def test_non_manager_cannot_change_profile_membership(self):
        with self.assertRaises(PermissionDenied):
            update_profile_membership(
                profile_id=self.profile.id,
                membership_id=self.admin_membership.id,
                actor=self.member,
                is_active=False,
            )

    def test_manager_role_does_not_apply_to_another_profile(self):
        other_owner = self.create_user("other-profile-owner")
        other_profile = create_profile_with_owner(
            name="Other Profile",
            owner=other_owner,
        )

        with self.assertRaises(TenantAccessNotFound):
            update_profile_membership(
                profile_id=other_profile.id,
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

        with self.assertRaises(TenantAccessNotFound):
            update_profile_membership(
                profile_id=self.profile.id,
                membership_id=self.member_membership.id,
                actor=self.admin,
                role=ProfileMembership.Role.ADMIN,
            )

        self.member.is_active = False
        self.member.save(update_fields=("is_active",))
        with self.assertRaises(ValidationError):
            update_profile_membership(
                profile_id=self.profile.id,
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
                profile_id=self.profile.id,
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
                profile_id=self.profile.id,
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
                profile_id=self.profile.id,
                membership_id=second_membership.id,
                actor=self.owner,
                is_active=False,
            )

        workspace.owner = self.owner
        workspace.save(update_fields=("owner",))
        updated_membership = update_profile_membership(
            profile_id=self.profile.id,
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
        self.member_profile_membership = ProfileMembership.objects.create(
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
            profile_id=self.profile.id,
            workspace_id=workspace.id,
            target_profile_membership_id=self.member_profile_membership.id,
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
            profile_id=self.profile.id,
            workspace_id=workspace.id,
            target_profile_membership_id=self.member_profile_membership.id,
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

        with self.assertRaises(TenantAccessNotFound):
            add_workspace_member(
                profile_id=self.profile.id,
                workspace_id=workspace.id,
                target_profile_membership_id=(
                    self.member_profile_membership.id
                ),
                role=WorkspaceMember.Role.MEMBER,
                actor=self.member,
            )

        with self.assertRaises(TenantAccessNotFound):
            add_workspace_member(
                profile_id=self.profile.id,
                workspace_id=workspace.id,
                target_profile_membership_id=uuid4(),
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
        other_profile = create_profile_with_owner(
            name="Cross Profile Company",
            owner=other_owner,
        )

        with self.assertRaises(TenantAccessNotFound):
            add_workspace_member(
                profile_id=other_profile.id,
                workspace_id=workspace.id,
                target_profile_membership_id=(
                    self.member_profile_membership.id
                ),
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


class WorkspaceMembershipServiceTests(WorkspaceTestDataMixin, TestCase):

    def setUp(self):
        self.owner = self.create_user("membership-service-owner")
        self.profile_admin = self.create_user(
            "membership-service-profile-admin"
        )
        self.workspace_admin = self.create_user(
            "membership-service-workspace-admin"
        )
        self.editor = self.create_user("membership-service-editor")
        self.viewer = self.create_user("membership-service-viewer")
        self.target = self.create_user("membership-service-target")

        self.profile = create_profile_with_owner(
            name="Membership Service Profile",
            owner=self.owner,
        )
        ProfileMembership.objects.create(
            profile=self.profile,
            user=self.profile_admin,
            role=ProfileMembership.Role.ADMIN,
        )
        for user in (
            self.workspace_admin,
            self.editor,
            self.viewer,
        ):
            ProfileMembership.objects.create(
                profile=self.profile,
                user=user,
                role=ProfileMembership.Role.MEMBER,
            )
        self.target_membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=self.target,
            role=ProfileMembership.Role.MEMBER,
        )

        self.workspace = Workspace.objects.create(
            name="Membership Service Workspace",
            profile=self.profile,
            owner=self.owner,
        )
        self.other_workspace = Workspace.objects.create(
            name="Other Membership Service Workspace",
            profile=self.profile,
            owner=self.owner,
        )
        for user, role in (
            (self.workspace_admin, WorkspaceMember.Role.ADMIN),
            (self.editor, WorkspaceMember.Role.MEMBER),
            (self.viewer, WorkspaceMember.Role.VIEWER),
        ):
            WorkspaceMember.objects.create(
                workspace=self.workspace,
                user=user,
                role=role,
            )

    def _create_target_membership(self, suffix):
        user = self.create_user(f"membership-target-{suffix}")
        return ProfileMembership.objects.create(
            profile=self.profile,
            user=user,
            role=ProfileMembership.Role.MEMBER,
        )

    def test_profile_managers_assign_supported_roles_but_never_legacy_owner(self):
        for actor_label, actor in (
            ("owner", self.owner),
            ("profile-admin", self.profile_admin),
        ):
            for role in (
                WorkspaceMember.Role.ADMIN,
                WorkspaceMember.Role.MEMBER,
                WorkspaceMember.Role.VIEWER,
            ):
                with self.subTest(actor=actor_label, role=role):
                    target = self._create_target_membership(
                        f"{actor_label}-{role.lower()}"
                    )
                    membership = add_workspace_member(
                        actor=actor,
                        profile_id=self.profile.id,
                        workspace_id=self.workspace.id,
                        target_profile_membership_id=target.id,
                        role=role,
                    )
                    self.assertEqual(membership.role, role)

            denied_target = self._create_target_membership(
                f"{actor_label}-legacy-owner"
            )
            with self.subTest(actor=actor_label, role="legacy-owner"):
                with self.assertRaises(PermissionDenied):
                    add_workspace_member(
                        actor=actor,
                        profile_id=self.profile.id,
                        workspace_id=self.workspace.id,
                        target_profile_membership_id=denied_target.id,
                        role=WorkspaceMember.Role.OWNER,
                    )

    def test_workspace_admin_assigns_editor_or_viewer_only_in_own_workspace(self):
        for role in (
            WorkspaceMember.Role.MEMBER,
            WorkspaceMember.Role.VIEWER,
        ):
            with self.subTest(role=role):
                target = self._create_target_membership(
                    f"workspace-admin-{role.lower()}"
                )
                membership = add_workspace_member(
                    actor=self.workspace_admin,
                    profile_id=self.profile.id,
                    workspace_id=self.workspace.id,
                    target_profile_membership_id=target.id,
                    role=role,
                )
                self.assertEqual(membership.role, role)

        denied_target = self._create_target_membership(
            "workspace-admin-denied"
        )
        audit_count = AuditLog.objects.filter(
            action="workspace.membership.created"
        ).count()
        for role in (
            WorkspaceMember.Role.ADMIN,
            WorkspaceMember.Role.OWNER,
        ):
            with self.subTest(role=role):
                with self.assertRaises(PermissionDenied):
                    add_workspace_member(
                        actor=self.workspace_admin,
                        profile_id=self.profile.id,
                        workspace_id=self.workspace.id,
                        target_profile_membership_id=denied_target.id,
                        role=role,
                    )

        with self.assertRaises(TenantAccessNotFound):
            add_workspace_member(
                actor=self.workspace_admin,
                profile_id=self.profile.id,
                workspace_id=self.other_workspace.id,
                target_profile_membership_id=denied_target.id,
                role=WorkspaceMember.Role.MEMBER,
            )
        self.assertEqual(
            AuditLog.objects.filter(
                action="workspace.membership.created"
            ).count(),
            audit_count,
        )

    def test_editor_and_viewer_cannot_manage_workspace_members(self):
        for actor in (self.editor, self.viewer):
            with self.subTest(actor=actor.username):
                with self.assertRaises(PermissionDenied):
                    add_workspace_member(
                        actor=actor,
                        profile_id=self.profile.id,
                        workspace_id=self.workspace.id,
                        target_profile_membership_id=(
                            self.target_membership.id
                        ),
                        role=WorkspaceMember.Role.MEMBER,
                    )

        self.assertFalse(
            AuditLog.objects.filter(
                action="workspace.membership.created"
            ).exists()
        )

    def test_target_lookup_requires_active_same_profile_membership_and_user(self):
        inactive_membership_user = self.create_user(
            "inactive-target-membership"
        )
        inactive_membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=inactive_membership_user,
            role=ProfileMembership.Role.MEMBER,
            is_active=False,
        )
        inactive_user = self.create_user(
            "inactive-target-user",
            is_active=False,
        )
        inactive_user_membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=inactive_user,
            role=ProfileMembership.Role.MEMBER,
        )
        other_owner = self.create_user("target-other-profile-owner")
        other_profile = create_profile_with_owner(
            name="Target Other Profile",
            owner=other_owner,
        )
        other_membership = ProfileMembership.objects.get(
            profile=other_profile,
            user=other_owner,
        )

        failures = []
        for target_id in (
            inactive_membership.id,
            inactive_user_membership.id,
            other_membership.id,
            uuid4(),
        ):
            with self.subTest(target_id=target_id):
                with self.assertRaises(TenantAccessNotFound) as raised:
                    add_workspace_member(
                        actor=self.owner,
                        profile_id=self.profile.id,
                        workspace_id=self.workspace.id,
                        target_profile_membership_id=target_id,
                        role=WorkspaceMember.Role.MEMBER,
                    )
                failures.append(str(raised.exception))

        self.assertEqual(len(set(failures)), 1)
        self.assertFalse(
            AuditLog.objects.filter(
                action="workspace.membership.created"
            ).exists()
        )

    def test_duplicate_workspace_membership_has_stable_domain_conflict(self):
        first = add_workspace_member(
            actor=self.owner,
            profile_id=self.profile.id,
            workspace_id=self.workspace.id,
            target_profile_membership_id=self.target_membership.id,
            role=WorkspaceMember.Role.MEMBER,
        )

        with self.assertRaises(WorkspaceMembershipConflict) as raised:
            add_workspace_member(
                actor=self.owner,
                profile_id=self.profile.id,
                workspace_id=self.workspace.id,
                target_profile_membership_id=self.target_membership.id,
                role=WorkspaceMember.Role.VIEWER,
            )

        self.assertEqual(
            raised.exception.message_dict,
            {
                "target_profile_membership_id": [
                    WorkspaceMembershipConflict.default_message
                ]
            },
        )
        self.assertEqual(
            WorkspaceMember.objects.filter(
                workspace=self.workspace,
                user=self.target,
            ).count(),
            1,
        )
        self.assertEqual(
            AuditLog.objects.filter(
                action="workspace.membership.created",
                entity_id=first.id,
            ).count(),
            1,
        )


class WorkspaceMembershipConcurrencyTests(
    WorkspaceTestDataMixin,
    TransactionTestCase,
):

    reset_sequences = False

    def test_concurrent_direct_add_creates_one_membership_and_one_audit(self):
        owner = self.create_user("concurrent-member-owner")
        target = self.create_user("concurrent-member-target")
        profile = create_profile_with_owner(
            name="Concurrent Membership Profile",
            owner=owner,
        )
        target_membership = ProfileMembership.objects.create(
            profile=profile,
            user=target,
            role=ProfileMembership.Role.MEMBER,
        )
        workspace = Workspace.objects.create(
            name="Concurrent Membership Workspace",
            profile=profile,
            owner=owner,
        )
        barrier = Barrier(2)

        def direct_add():
            close_old_connections()
            try:
                thread_actor = User.objects.get(id=owner.id)
                barrier.wait(timeout=10)
                try:
                    add_workspace_member(
                        actor=thread_actor,
                        profile_id=profile.id,
                        workspace_id=workspace.id,
                        target_profile_membership_id=target_membership.id,
                        role=WorkspaceMember.Role.MEMBER,
                    )
                except WorkspaceMembershipConflict:
                    return "conflict"
                return "created"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(direct_add),
                executor.submit(direct_add),
            )
            results = [future.result(timeout=20) for future in futures]

        self.assertCountEqual(results, ("created", "conflict"))
        self.assertEqual(
            WorkspaceMember.objects.filter(
                workspace=workspace,
                user=target,
            ).count(),
            1,
        )
        self.assertEqual(
            AuditLog.objects.filter(
                action="workspace.membership.created",
            ).count(),
            1,
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
                        profile_id=profile.id,
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
                        profile_id=profile.id,
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
