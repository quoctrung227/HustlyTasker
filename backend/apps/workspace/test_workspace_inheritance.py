"""Snapshot membership creation and invitation current-month boundaries.

These tests use only Django's isolated PostgreSQL harness database. Mail is
never delivered: recipient tests construct a synthetic already-sent credential.
"""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone as dt_timezone
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import close_old_connections
from django.test import TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.tasks.models import Task

from .access import TenantAccessNotFound, resolve_profile_access_context, resolve_workspace_access_context
from .invitation_services import InvitationConflict, accept_profile_invitation
from .models import Profile, ProfileInvitation, ProfileMembership, Workspace, WorkspaceMember
from .services import WorkspacePeriodConflict, create_profile_with_owner, create_workspace, revoke_workspace_member


User = get_user_model()


class InheritanceData:
    @staticmethod
    def user(label, **kwargs):
        return User.objects.create_user(
            username=f"inherit-{label}", email=f"inherit-{label}@example.test",
            password="isolated-inheritance-password", first_name=label, **kwargs,
        )

    def workspace(self, profile=None, owner=None, period=date(2026, 9, 1), **kwargs):
        return Workspace.objects.create(
            profile=profile or self.profile, owner=owner or self.owner,
            name="Source Workspace", period=period, **kwargs,
        )

    def profile_member(self, label, role=ProfileMembership.Role.MEMBER, **kwargs):
        user = self.user(label)
        return ProfileMembership.objects.create(
            profile=self.profile, user=user, role=role, **kwargs,
        )

    def sent_invitation(self, recipient, requested_role=ProfileInvitation.Role.MEMBER):
        token = f"isolated-synthetic-invitation-{recipient.id}-credential"
        now = timezone.now()
        invitation = ProfileInvitation.objects.create(
            profile=self.profile, recipient_email_normalized=recipient.email.strip().casefold(),
            recipient_user=recipient, requested_role=requested_role,
            invited_by_membership=ProfileMembership.objects.get(
                profile=self.profile, user=self.owner, is_active=True,
            ),
            token_digest=hashlib.sha256(token.encode()).hexdigest(),
            delivery_status=ProfileInvitation.DeliveryStatus.SENT,
            delivery_attempted_at=now, delivered_at=now,
            expires_at=now + timedelta(days=7),
        )
        return invitation, token


class WorkspaceInheritanceApiTests(InheritanceData, APITestCase):
    def setUp(self):
        self.owner = self.user("owner")
        self.profile = create_profile_with_owner(name="Inheritance Profile", owner=self.owner)
        self.source = self.workspace()
        self.assignments = {}
        for label, role in (("admin", "ADMIN"), ("editor", "MEMBER"), ("viewer", "VIEWER")):
            membership = self.profile_member(label)
            row = WorkspaceMember.objects.create(workspace=self.source, user=membership.user, role=role)
            self.assignments[role] = (membership, row)
        self.revoked = self.profile_member("revoked")
        WorkspaceMember.objects.create(workspace=self.source, user=self.revoked.user, is_active=False)
        self.inactive = self.profile_member("inactive-profile")
        WorkspaceMember.objects.create(workspace=self.source, user=self.inactive.user)
        self.inactive.is_active = False
        self.inactive.save(update_fields=("is_active",))
        self.inactive_account = self.profile_member("inactive-account")
        WorkspaceMember.objects.create(workspace=self.source, user=self.inactive_account.user)
        User.objects.filter(pk=self.inactive_account.user_id).update(is_active=False)
        self.profile_admin = self.profile_member("profile-admin", role=ProfileMembership.Role.ADMIN)
        WorkspaceMember.objects.create(workspace=self.source, user=self.profile_admin.user, role="ADMIN")
        WorkspaceMember.objects.create(workspace=self.source, user=self.owner, role="ADMIN")
        self.legacy = self.profile_member("legacy-owner")
        WorkspaceMember.objects.create(workspace=self.source, user=self.legacy.user, role="OWNER")
        self.list_url = reverse("workspace:workspace-list", kwargs={"profile_id": self.profile.id})
        self.preview_url = reverse("workspace:workspace-inheritance-preview", kwargs={"profile_id": self.profile.id})
        self.client.force_authenticate(self.owner)

    def create(self, **extra):
        return self.client.post(self.list_url, {
            "name": "New month", "period": "2026-12-01", **extra,
        }, format="json")

    def preview(self, **extra):
        return self.client.get(self.preview_url, {"source_workspace_id": str(self.source.id), **extra})

    def test_inherits_exact_supported_roles_and_skips_revoked_inactive_and_inherited_managers(self):
        response = self.create(source_workspace_id=str(self.source.id))
        self.assertEqual(response.status_code, 201)
        rows = WorkspaceMember.objects.filter(workspace_id=response.data["id"])
        self.assertCountEqual(list(rows.values_list("user_id", "role")), [
            (membership.user_id, role) for role, (membership, _) in self.assignments.items()
        ])
        self.assertEqual(rows.count(), 3)
        self.assertEqual(AuditLog.objects.filter(
            action="workspace.membership.created", entity_id__in=rows.values("id"),
        ).count(), 3)
        audit = AuditLog.objects.get(entity_id=response.data["id"], action="workspace.created")
        self.assertEqual(audit.metadata["after"]["source_workspace_id"], str(self.source.id))
        self.assertEqual(audit.metadata["after"]["inherited_membership_count"], 3)

    def test_preview_is_paginated_privacy_minimal_and_reports_exclusions(self):
        response = self.preview(page_size=2)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["mode"], "inheritance")
        self.assertEqual(response.data["count"], 3)
        self.assertIsNotNone(response.data["next"])
        self.assertEqual(response.data["excluded_count"], 6)
        self.assertEqual(response.data["source_workspace"]["id"], str(self.source.id))
        for row in response.data["results"]:
            self.assertEqual(set(row), {"profile_membership_id", "display_name", "role"})
        self.assertNotIn("@example.test", str(response.data))
        self.assertNotIn(str(self.owner.id), str(response.data))

    def test_no_source_preserves_legacy_manual_create(self):
        preview = self.client.get(self.preview_url)
        self.assertEqual(preview.data["mode"], "manual")
        self.assertEqual(preview.data["count"], 0)
        response = self.create()
        self.assertEqual(response.status_code, 201)
        self.assertFalse(WorkspaceMember.objects.filter(workspace_id=response.data["id"]).exists())

    def test_archived_source_is_readable_snapshot_without_source_mutation(self):
        Workspace.objects.filter(pk=self.source.id).update(status=Workspace.Status.ARCHIVED)
        self.assertEqual(self.preview().status_code, 200)
        self.assertEqual(self.create(source_workspace_id=str(self.source.id)).status_code, 201)
        self.source.refresh_from_db()
        self.assertEqual(self.source.status, Workspace.Status.ARCHIVED)

    def test_source_business_rows_and_roles_are_not_copied_or_mutated(self):
        task = Task.objects.create(workspace=self.source, title="Original task", created_by=self.owner)
        before_source = Workspace.objects.values().get(id=self.source.id)
        before_rows = list(WorkspaceMember.objects.filter(workspace=self.source).order_by("id").values())
        response = self.create(source_workspace_id=str(self.source.id))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Workspace.objects.values().get(id=self.source.id), before_source)
        self.assertEqual(list(WorkspaceMember.objects.filter(workspace=self.source).order_by("id").values()), before_rows)
        self.assertEqual(Task.objects.count(), 1)
        self.assertEqual(Task.objects.get().id, task.id)

    def test_snapshot_roles_do_not_follow_later_source_changes(self):
        response = self.create(source_workspace_id=str(self.source.id))
        membership, row = self.assignments["MEMBER"]
        row.role = "VIEWER"
        row.save(update_fields=("role",))
        self.assertEqual(WorkspaceMember.objects.get(
            workspace_id=response.data["id"], user=membership.user,
        ).role, "MEMBER")

    def test_preview_is_recomputed_after_source_revocation(self):
        self.assertEqual(self.preview().data["count"], 3)
        _, row = self.assignments["MEMBER"]
        revoke_workspace_member(actor=self.owner, profile_id=self.profile.id,
                                workspace_id=self.source.id, membership_id=row.id)
        response = self.create(source_workspace_id=str(self.source.id))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(WorkspaceMember.objects.filter(workspace_id=response.data["id"]).count(), 2)

    def test_source_cross_profile_and_missing_ids_are_tenant_safe(self):
        other_owner = self.user("other-owner")
        other_profile = create_profile_with_owner(name="Other", owner=other_owner)
        other_source = self.workspace(profile=other_profile, owner=other_owner)
        for source_id in (other_source.id, uuid4()):
            with self.subTest(source=source_id):
                self.assertEqual(self.create(source_workspace_id=str(source_id)).status_code, 404)
                self.assertEqual(self.preview(source_workspace_id=str(source_id)).status_code, 404)
        self.assertEqual(Workspace.objects.count(), 2)

    def test_workspace_admin_cannot_create_or_preview_inheritance(self):
        self.client.force_authenticate(self.assignments["ADMIN"][0].user)
        self.assertEqual(self.create(source_workspace_id=str(self.source.id)).status_code, 403)
        self.assertEqual(self.preview().status_code, 403)

    def test_profile_admin_can_inherit_roles_without_owner_elevation(self):
        self.client.force_authenticate(self.profile_admin.user)
        self.assertEqual(self.create(source_workspace_id=str(self.source.id)).status_code, 201)

    def test_invalid_source_and_role_injection_rejected(self):
        for payload in (
            {"source_workspace_id": "not-a-uuid"},
            {"source_workspace_id": str(self.source.id), "role": "OWNER"},
            {"source_workspace_id": str(self.source.id), "initial_profile_membership_ids": []},
            {"source_workspace_id": str(self.source.id), "members": []},
        ):
            with self.subTest(payload=payload):
                self.assertEqual(self.create(**payload).status_code, 400)
        self.assertEqual(self.preview(source_workspace_id="invalid").status_code, 400)

    def test_archived_profile_and_revoked_actor_cannot_create(self):
        Profile.objects.filter(pk=self.profile.id).update(status=Profile.Status.ARCHIVED)
        self.assertEqual(self.create(source_workspace_id=str(self.source.id)).status_code, 403)
        self.assertEqual(self.preview().status_code, 403)
        Profile.objects.filter(pk=self.profile.id).update(status=Profile.Status.ACTIVE)
        ProfileMembership.objects.filter(profile=self.profile, user=self.owner).update(is_active=False)
        self.assertEqual(self.create(source_workspace_id=str(self.source.id)).status_code, 404)
        self.assertEqual(self.preview().status_code, 404)

    def test_failed_membership_creation_rolls_back_workspace_all_grants_and_audits(self):
        before = (Workspace.objects.count(), WorkspaceMember.objects.count(), AuditLog.objects.count())
        real_save = WorkspaceMember.save
        attempts = []

        def fail_second(membership, *args, **kwargs):
            attempts.append(membership.pk)
            if len(attempts) == 2:
                raise RuntimeError("synthetic grant failure")
            return real_save(membership, *args, **kwargs)

        with patch.object(WorkspaceMember, "save", new=fail_second):
            with self.assertRaises(RuntimeError):
                create_workspace(actor=self.owner, profile_id=self.profile.id, name="Rollback",
                                 period=date(2026, 12, 1), source_workspace_id=self.source.id)
        self.assertEqual(len(attempts), 2)
        self.assertEqual((Workspace.objects.count(), WorkspaceMember.objects.count(), AuditLog.objects.count()), before)

    def test_duplicate_period_does_not_duplicate_memberships_or_audits(self):
        self.assertEqual(self.create(source_workspace_id=str(self.source.id)).status_code, 201)
        before = (WorkspaceMember.objects.count(), AuditLog.objects.count())
        self.assertEqual(self.create(source_workspace_id=str(self.source.id)).status_code, 409)
        self.assertEqual((WorkspaceMember.objects.count(), AuditLog.objects.count()), before)

    def test_missing_month_does_not_guess_latest_source(self):
        self.workspace(period=date(2026, 11, 1))
        response = self.create()
        self.assertEqual(response.status_code, 201)
        self.assertFalse(WorkspaceMember.objects.filter(workspace_id=response.data["id"]).exists())

    def test_authentication_and_session_csrf_are_enforced(self):
        anonymous = APIClient(enforce_csrf_checks=True)
        self.assertEqual(anonymous.post(self.list_url, {}, format="json").status_code, 403)
        self.assertEqual(anonymous.get(self.preview_url).status_code, 403)
        anonymous.force_login(self.owner)
        self.assertEqual(anonymous.post(self.list_url, {"name": "No CSRF", "period": "2026-12-01"}, format="json").status_code, 403)


class FirstWorkspaceInheritanceTests(InheritanceData, APITestCase):
    def setUp(self):
        self.owner = self.user("first-owner")
        self.profile = create_profile_with_owner(name="First", owner=self.owner)
        self.member = self.profile_member("first-member")
        self.unselected = self.profile_member("first-unselected")
        self.admin = self.profile_member("first-admin", role="ADMIN")
        self.inactive = self.profile_member("first-inactive", is_active=False)
        self.client.force_authenticate(self.owner)
        self.url = reverse("workspace:workspace-list", kwargs={"profile_id": self.profile.id})
        self.preview_url = reverse("workspace:workspace-inheritance-preview", kwargs={"profile_id": self.profile.id})

    def test_initial_preview_suggests_only_active_ordinary_members_at_member_role(self):
        response = self.client.get(self.preview_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["mode"], "initial")
        self.assertFalse(response.data["has_workspaces"])
        self.assertEqual(response.data["count"], 2)
        self.assertEqual({row["role"] for row in response.data["results"]}, {"MEMBER"})
        self.assertEqual({row["profile_membership_id"] for row in response.data["results"]}, {str(self.member.id), str(self.unselected.id)})

    def test_first_workspace_grants_only_explicitly_confirmed_members(self):
        response = self.client.post(self.url, {
            "name": "First", "period": "2026-11-01",
            "initial_profile_membership_ids": [str(self.member.id)],
        }, format="json")
        self.assertEqual(response.status_code, 201)
        rows = WorkspaceMember.objects.filter(workspace_id=response.data["id"])
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.get().user_id, self.member.user_id)
        self.assertEqual(rows.get().role, "MEMBER")

    def test_invalid_inactive_duplicate_or_manager_initial_references_rejected(self):
        for ids in ([str(uuid4())], [str(self.inactive.id)], [str(self.admin.id)],
                    [str(self.member.id), str(self.member.id)]):
            with self.subTest(ids=ids):
                response = self.client.post(self.url, {
                    "name": "Invalid", "period": "2026-11-01", "initial_profile_membership_ids": ids,
                }, format="json")
                self.assertEqual(response.status_code, 400)
        self.assertFalse(Workspace.objects.filter(profile=self.profile).exists())

    def test_initial_members_option_rejected_once_workspace_exists(self):
        self.workspace()
        response = self.client.post(self.url, {
            "name": "Second", "period": "2026-11-01", "initial_profile_membership_ids": [str(self.member.id)],
        }, format="json")
        self.assertEqual(response.status_code, 400)


class InvitationCurrentWorkspaceTests(InheritanceData, APITestCase):
    def setUp(self):
        self.owner = self.user("accept-owner")
        self.profile = create_profile_with_owner(name="Current", owner=self.owner)
        self.current_period = timezone.localdate(timezone=timezone.get_default_timezone()).replace(day=1)
        self.current = self.workspace(period=self.current_period)
        self.old = self.workspace(period=date(2020, 1, 1))
        self.future = self.workspace(period=date(2040, 1, 1))
        self.recipient = self.user("accept-recipient")

    def accept(self, recipient=None, role="MEMBER"):
        invitation, token = self.sent_invitation(recipient or self.recipient, requested_role=role)
        membership = accept_profile_invitation(actor=recipient or self.recipient, token=token)
        return invitation, token, membership

    def test_only_successful_accept_grants_exact_current_month_member(self):
        invitation, token = self.sent_invitation(self.recipient)
        self.assertFalse(WorkspaceMember.objects.filter(user=self.recipient).exists())
        accept_profile_invitation(actor=self.recipient, token=token)
        rows = WorkspaceMember.objects.filter(user=self.recipient)
        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.get().workspace_id, self.current.id)
        self.assertEqual(rows.get().role, "MEMBER")
        self.assertEqual(AuditLog.objects.filter(action="workspace.membership.created_by_invitation", entity_id=rows.get().id).count(), 1)
        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(actor=self.recipient, token=token)
        self.assertEqual(WorkspaceMember.objects.filter(user=self.recipient).count(), 1)

    def test_wrong_recipient_and_expired_invitation_do_not_grant(self):
        invitation, token = self.sent_invitation(self.recipient)
        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(actor=self.owner, token=token)
        with patch("apps.workspace.invitation_services.timezone.now", return_value=invitation.expires_at + timedelta(seconds=1)):
            with self.assertRaises(InvitationConflict):
                accept_profile_invitation(actor=self.recipient, token=token)
        self.assertFalse(WorkspaceMember.objects.filter(user=self.recipient).exists())
        self.assertFalse(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient).exists())

    def test_no_current_workspace_accepts_without_picking_latest_future_or_legacy(self):
        Workspace.objects.filter(pk=self.current.id).update(period=None)
        self.accept()
        self.assertTrue(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient, is_active=True).exists())
        self.assertFalse(WorkspaceMember.objects.filter(user=self.recipient).exists())

    def test_archived_current_workspace_does_not_receive_auto_grant(self):
        Workspace.objects.filter(pk=self.current.id).update(status="ARCHIVED")
        self.accept()
        self.assertFalse(WorkspaceMember.objects.filter(user=self.recipient).exists())

    def test_profile_admin_keeps_inherited_governance_without_redundant_direct_row(self):
        _, _, membership = self.accept(role="ADMIN")
        self.assertEqual(membership.role, "ADMIN")
        self.assertFalse(WorkspaceMember.objects.filter(user=self.recipient).exists())
        resolve_workspace_access_context(resolve_profile_access_context(self.recipient, self.profile.id), self.current.id)

    def test_reactivated_profile_member_without_current_history_receives_new_current_grant(self):
        prior = ProfileMembership.objects.create(profile=self.profile, user=self.recipient, is_active=False)
        _, _, membership = self.accept()
        self.assertEqual(membership.id, prior.id)
        self.assertTrue(WorkspaceMember.objects.filter(workspace=self.current, user=self.recipient, is_active=True).exists())

    def test_reactivated_member_current_revoked_or_stale_active_rows_never_revive(self):
        for active in (False, True):
            with self.subTest(previous_active=active):
                recipient = self.user(f"current-historical-{active}")
                pm = ProfileMembership.objects.create(profile=self.profile, user=recipient)
                row = WorkspaceMember.objects.create(workspace=self.current, user=recipient, is_active=active, role="VIEWER")
                pm.is_active = False
                pm.save(update_fields=("is_active",))
                self.accept(recipient=recipient)
                row.refresh_from_db()
                self.assertFalse(row.is_active)
                self.assertEqual(row.role, "VIEWER")
                self.assertEqual(WorkspaceMember.objects.filter(workspace=self.current, user=recipient).count(), 1)
                with self.assertRaises(TenantAccessNotFound):
                    resolve_workspace_access_context(resolve_profile_access_context(recipient, self.profile.id), self.current.id)

    def test_auto_grant_failure_rolls_back_invitation_profile_membership_and_audit(self):
        invitation, token = self.sent_invitation(self.recipient)
        before_audits = AuditLog.objects.count()
        with patch("apps.workspace.invitation_services.WorkspaceMember.save", side_effect=RuntimeError("synthetic save failure")):
            with self.assertRaises(RuntimeError):
                accept_profile_invitation(actor=self.recipient, token=token)
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, "PENDING")
        self.assertFalse(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient).exists())
        self.assertFalse(WorkspaceMember.objects.filter(user=self.recipient).exists())
        self.assertEqual(AuditLog.objects.count(), before_audits)

    def test_configured_utc_month_is_used_at_boundary_not_client_timezone(self):
        at_boundary = datetime(2027, 1, 31, 23, 30, tzinfo=dt_timezone.utc)
        january = self.workspace(period=date(2027, 1, 1))
        self.workspace(period=date(2027, 2, 1))
        invitation, token = self.sent_invitation(self.recipient)
        ProfileInvitation.objects.filter(pk=invitation.id).update(expires_at=at_boundary + timedelta(days=1))
        with patch("apps.workspace.invitation_services.timezone.now", return_value=at_boundary):
            accept_profile_invitation(actor=self.recipient, token=token)
        self.assertEqual(WorkspaceMember.objects.get(user=self.recipient).workspace_id, january.id)


class WorkspaceInheritanceConcurrencyTests(InheritanceData, TransactionTestCase):
    def setUp(self):
        self.owner = self.user("race-owner")
        self.profile = create_profile_with_owner(name="Race", owner=self.owner)
        self.member = self.profile_member("race-member")
        self.source = self.workspace()
        self.source_member = WorkspaceMember.objects.create(workspace=self.source, user=self.member.user, role="MEMBER")

    def parallel(self, operation):
        barrier = Barrier(2)

        def run(label):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return operation(label)
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(run, label) for label in range(2)]
            return [future.result(timeout=30) for future in futures]

    def test_concurrent_same_month_inheritance_has_one_workspace_roster_and_audit(self):
        def create(label):
            try:
                create_workspace(actor=User.objects.get(id=self.owner.id), profile_id=self.profile.id,
                                 name=f"Race {label}", period=date(2026, 12, 1), source_workspace_id=self.source.id)
            except WorkspacePeriodConflict:
                return "conflict"
            return "created"
        self.assertCountEqual(self.parallel(create), ["created", "conflict"])
        target = Workspace.objects.get(profile=self.profile, period=date(2026, 12, 1))
        self.assertEqual(WorkspaceMember.objects.filter(workspace=target).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="workspace.created", entity_id=target.id).count(), 1)

    def test_concurrent_accept_has_one_current_membership_and_one_audit(self):
        self.workspace(period=timezone.localdate().replace(day=1))
        recipient = self.user("race-recipient")
        _, token = self.sent_invitation(recipient)

        def accept(label):
            try:
                accept_profile_invitation(actor=User.objects.get(id=recipient.id), token=token)
            except InvitationConflict:
                return "conflict"
            return "accepted"
        self.assertCountEqual(self.parallel(accept), ["accepted", "conflict"])
        self.assertEqual(WorkspaceMember.objects.filter(user=recipient).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action="workspace.membership.created_by_invitation").count(), 1)

    def test_concurrent_revoke_and_snapshot_are_serialized_without_source_resurrection(self):
        def mutate(label):
            actor = User.objects.get(id=self.owner.id)
            if label:
                revoke_workspace_member(actor=actor, profile_id=self.profile.id,
                                        workspace_id=self.source.id, membership_id=self.source_member.id)
                return "revoked"
            create_workspace(actor=actor, profile_id=self.profile.id, name="Snapshot",
                             period=date(2026, 12, 1), source_workspace_id=self.source.id)
            return "created"
        self.assertCountEqual(self.parallel(mutate), ["created", "revoked"])
        self.source_member.refresh_from_db()
        self.assertFalse(self.source_member.is_active)
        target = Workspace.objects.get(profile=self.profile, period=date(2026, 12, 1))
        target_rows = WorkspaceMember.objects.filter(workspace=target)
        # Whichever transaction acquired the Profile lock first defines the
        # immutable snapshot. A later revoke never mutates that new snapshot.
        self.assertIn(target_rows.count(), (0, 1))
        if target_rows.exists():
            self.assertEqual(target_rows.get().role, "MEMBER")
