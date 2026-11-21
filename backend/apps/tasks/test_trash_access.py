"""Effective deletion/security and retained approval history on isolated PostgreSQL."""
from datetime import date, datetime, timedelta, timezone as dt_timezone
import hashlib
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.notifications.access import notifications_visible_to
from apps.notifications.models import Notification
from apps.notifications.services import mark_notification_read
from apps.reviews.models import Deliverable, Review
from apps.workspace.access import (
    TenantAccessNotFound, profiles_visible_to, resolve_profile_access_context,
    resolve_workspace_access_context, workspaces_visible_to,
)
from apps.workspace.account_invitations import (
    create_account_invitation, invitation_candidates, recipient_invitations_visible_to,
    respond_account_invitation,
)
from apps.workspace.invitation_services import InvitationConflict, accept_profile_invitation
from apps.workspace.models import Profile, ProfileInvitation, ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner, create_workspace, update_workspace
from .access import tasks_visible_to
from .analytics import analytics_summary, resolve_analytics_scope
from .analytics_serializers import AnalyticsQuerySerializer
from .models import Task, TaskAssignment
from .services import assign_task, create_task, update_task


class TrashAccessFixture:
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        for label in ('owner', 'editor', 'viewer', 'recipient', 'foreign'):
            setattr(cls, label, User.objects.create_user(username='trash-access-' + label,
                email='trash-access-' + label + '@example.test', password=None))
        cls.profile = create_profile_with_owner(name='Trash access tenant', owner=cls.owner)
        cls.owner_membership = ProfileMembership.objects.get(profile=cls.profile, user=cls.owner)
        cls.editor_membership = ProfileMembership.objects.create(profile=cls.profile, user=cls.editor, role='MEMBER')
        ProfileMembership.objects.create(profile=cls.profile, user=cls.viewer, role='MEMBER')
        cls.workspace = Workspace.objects.create(profile=cls.profile, owner=cls.owner,
            name='Trash access month', period=date(2026, 11, 1))
        WorkspaceMember.objects.create(workspace=cls.workspace, user=cls.editor, role='MEMBER')
        WorkspaceMember.objects.create(workspace=cls.workspace, user=cls.viewer, role='VIEWER')
        cls.task = Task.objects.create(workspace=cls.workspace, created_by=cls.owner, title='Private retained work')
        cls.foreign_profile = create_profile_with_owner(name='Foreign trash tenant', owner=cls.foreign)

    def setUp(self):
        self.client.force_authenticate(self.owner)

    def mark(self, obj, deleted=True):
        at = timezone.now() if deleted else None
        type(obj).objects.filter(pk=obj.pk).update(deleted_at=at,
            deleted_by_id=self.owner.pk if deleted else None,
            purge_after=at + timedelta(days=30) if deleted else None)

    def context(self, actor=None):
        pc = resolve_profile_access_context(actor or self.owner, self.profile.pk)
        return resolve_workspace_access_context(pc, self.workspace.pk)

    def task_url(self, task=None):
        return f'/api/v1/profiles/{self.profile.pk}/workspaces/{self.workspace.pk}/tasks/{(task or self.task).pk}/'


class TrashAccessTests(TrashAccessFixture, APITestCase):
    def test_deleted_tasks_are_hidden_in_each_workflow_state_without_status_change(self):
        for status in Task.Status.values:
            with self.subTest(status=status):
                task = Task.objects.create(workspace=self.workspace, created_by=self.owner, title=status, status=status)
                self.mark(task)
                self.assertEqual(self.client.get(self.task_url(task)).status_code, 404)
                self.assertFalse(tasks_visible_to(self.context()).filter(pk=task.pk).exists())
                self.assertEqual(Task.objects.get(pk=task.pk).status, status)

    def test_parent_deletion_hides_descendants_and_restore_keeps_separate_child_deleted(self):
        child = Task.objects.create(workspace=self.workspace, created_by=self.owner, parent=self.task, title='Separate child')
        sibling = Task.objects.create(workspace=self.workspace, created_by=self.owner, parent=self.task, title='Inherited child')
        self.mark(child)
        self.mark(self.task)
        self.assertFalse(tasks_visible_to(self.context()).filter(pk__in=[self.task.pk, child.pk, sibling.pk]).exists())
        self.assertIsNone(Task.objects.get(pk=sibling.pk).deleted_at)
        self.mark(self.task, False)
        self.assertEqual(set(tasks_visible_to(self.context()).values_list('pk', flat=True)), {self.task.pk, sibling.pk})

    def test_deleted_parent_rejects_create_reparent_and_stale_mutation(self):
        child = Task.objects.create(workspace=self.workspace, created_by=self.owner, parent=self.task, title='Inherited child')
        self.mark(self.task)
        for values in ({'task_id': self.task.pk}, {'task_id': child.pk}):
            with self.assertRaises(TenantAccessNotFound):
                update_task(actor=self.owner, profile_id=self.profile.pk, workspace_id=self.workspace.pk,
                    title='Cannot update', **values)
        with self.assertRaises(TenantAccessNotFound):
            create_task(actor=self.owner, profile_id=self.profile.pk, workspace_id=self.workspace.pk,
                title='Cannot attach', parent_id=self.task.pk)
        other = Task.objects.create(workspace=self.workspace, created_by=self.owner, title='Other')
        with self.assertRaises(TenantAccessNotFound):
            update_task(actor=self.owner, profile_id=self.profile.pk, workspace_id=self.workspace.pk,
                task_id=other.pk, parent_id=self.task.pk)

    def test_workspace_delete_hides_all_children_and_denies_metadata_mutation(self):
        stale = self.context()
        self.mark(self.workspace)
        with self.assertRaises(TenantAccessNotFound):
            tasks_visible_to(stale)
        with self.assertRaises(TenantAccessNotFound):
            update_workspace(actor=self.owner, profile_id=self.profile.pk, workspace_id=self.workspace.pk, name='Denied')
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)
        self.assertIsNone(Task.objects.get(pk=self.task.pk).deleted_at)

    def test_profile_delete_closes_existing_contexts_lists_and_workspace_create(self):
        pc = resolve_profile_access_context(self.owner, self.profile.pk)
        self.mark(self.profile)
        self.assertFalse(profiles_visible_to(self.owner).filter(pk=self.profile.pk).exists())
        with self.assertRaises(TenantAccessNotFound):
            workspaces_visible_to(pc)
        with self.assertRaises(TenantAccessNotFound):
            create_workspace(actor=self.owner, profile_id=self.profile.pk, name='Denied', period=date(2027, 1, 1))
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)

    def test_archive_is_still_readable_and_mutations_still_denied(self):
        Profile.objects.filter(pk=self.profile.pk).update(status='ARCHIVED')
        Workspace.objects.filter(pk=self.workspace.pk).update(status='ARCHIVED')
        self.assertEqual(self.client.get(self.task_url()).status_code, 200)
        with self.assertRaises(PermissionDenied):
            update_task(actor=self.owner, profile_id=self.profile.pk, workspace_id=self.workspace.pk,
                task_id=self.task.pk, title='Archived')

    def test_task_notice_hides_in_trash_and_returns_without_read_state_reset(self):
        assign_task(actor=self.owner, profile_id=self.profile.pk, workspace_id=self.workspace.pk,
            task_id=self.task.pk, target_profile_membership_id=self.editor_membership.pk)
        notice = Notification.objects.get(user=self.editor, task=self.task)
        mark_notification_read(actor=self.editor, notification_id=notice.pk)
        self.mark(self.task)
        self.assertFalse(notifications_visible_to(self.editor).filter(pk=notice.pk).exists())
        with self.assertRaises(TenantAccessNotFound):
            mark_notification_read(actor=self.editor, notification_id=notice.pk)
        self.mark(self.task, False)
        self.assertTrue(notifications_visible_to(self.editor).get(pk=notice.pk).is_read)

    def test_restoring_metadata_does_not_reactivate_revoked_membership(self):
        self.mark(self.workspace)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(is_active=False)
        self.mark(self.workspace, False)
        with self.assertRaises(TenantAccessNotFound):
            self.context(self.editor)
        self.assertFalse(WorkspaceMember.objects.get(workspace=self.workspace, user=self.editor).is_active)

    def test_deleted_profile_hides_recipient_inbox_and_notice_and_blocks_decision(self):
        invitation = create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=self.recipient.pk)
        notice = Notification.objects.get(invitation=invitation)
        self.assertTrue(recipient_invitations_visible_to(self.recipient).filter(pk=invitation.pk).exists())
        self.mark(self.profile)
        self.assertFalse(recipient_invitations_visible_to(self.recipient).exists())
        self.assertFalse(notifications_visible_to(self.recipient).filter(pk=notice.pk).exists())
        with self.assertRaises(TenantAccessNotFound):
            respond_account_invitation(actor=self.recipient, invitation_id=invitation.pk, accept=True)
        self.assertFalse(ProfileMembership.objects.filter(profile=self.profile, user=self.recipient).exists())

    def test_directory_and_reserved_account_mail_do_not_mutate_deleted_profile(self):
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            invitation = create_account_invitation(actor=self.owner, profile_id=self.profile.pk, recipient_user_id=self.recipient.pk)
        self.mark(self.profile)
        with self.assertRaises(TenantAccessNotFound):
            invitation_candidates(actor=self.owner, profile_id=self.profile.pk)
        with patch('apps.workspace.account_invitation_delivery.send_default_email') as sender:
            for callback in callbacks:
                callback()
        sender.assert_not_called()
        invitation.refresh_from_db()
        self.assertEqual(invitation.delivery_status, 'QUEUED')
        self.assertEqual(invitation.email_attempts.get().status, 'PENDING')

    def test_legacy_token_cannot_accept_deleted_profile(self):
        token = 'synthetic-trash-legacy-proof'
        now = timezone.now()
        ProfileInvitation.objects.create(profile=self.profile, invited_by_membership=self.owner_membership,
            recipient_email_normalized=self.recipient.email, recipient_user=self.recipient,
            token_digest=hashlib.sha256(token.encode()).hexdigest(), expires_at=now + timedelta(days=7),
            delivery_status='SENT', delivered_at=now, delivery_attempted_at=now)
        self.mark(self.profile)
        with self.assertRaises(InvitationConflict):
            accept_profile_invitation(actor=self.recipient, token=token)

    def test_foreign_tenant_cannot_read_trash_scoped_task(self):
        self.client.force_authenticate(self.foreign)
        self.assertEqual(self.client.get(self.task_url()).status_code, 404)


class TrashAnalyticsTests(TrashAccessFixture, APITestCase):

    def approval(self):
        Task.objects.filter(pk=self.task.pk).update(status='COMPLETED',
            created_at=datetime(2026, 11, 5, tzinfo=dt_timezone.utc), estimated_compensation_vnd='900000')
        TaskAssignment.objects.create(task=self.task, user=self.editor)
        deliverable = Deliverable.objects.create(task=self.task, uploaded_by=self.editor,
            file_url='https://example.test/retained-proof', revision=1, status='APPROVED')
        review = Review.objects.create(deliverable=deliverable, reviewer=self.owner, status='APPROVED',
            compensation_snapshot_recorded=True, compensation_snapshot_vnd='250000')
        Review.objects.filter(pk=review.pk).update(created_at=datetime(2026, 11, 10, tzinfo=dt_timezone.utc))

    def summary(self, actor=None):
        self.client.force_authenticate(actor or self.owner)
        response = self.client.get(f'/api/v1/profiles/{self.profile.pk}/analytics/', {'from':'2026-11-01','to':'2026-11-30'})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_deleted_task_keeps_snapshot_finance_but_hides_operational_details(self):
        self.approval()
        self.mark(self.task)
        data = self.summary()
        self.assertEqual(data['kpis']['total_tasks'], 0)
        self.assertEqual(data['finance']['approved_total_vnd'], '250000')
        self.assertIsNone(data['finance']['estimated_total_vnd'])
        self.assertTrue(data['scope']['historical_approvals_include_deleted'])
        detail = self.client.get(f'/api/v1/profiles/{self.profile.pk}/analytics/employees/{self.editor_membership.pk}/', {'from':'2026-11-01','to':'2026-11-30'})
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data['results'], [])
        self.assertEqual(detail.data['employee']['finance']['approved_total_vnd'], '250000')

    def test_deleted_workspace_keeps_approved_finance_for_current_authorized_roles(self):
        self.approval()
        self.mark(self.workspace)
        self.assertEqual(self.summary()['finance']['approved_total_vnd'], '250000')
        self.assertEqual(self.summary(self.editor)['finance']['approved_total_vnd'], '250000')
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(role='VIEWER')
        self.assertIsNone(self.summary(self.editor)['finance'])

    def test_restore_reveals_operational_task_without_repricing_old_approval(self):
        self.approval()
        self.mark(self.task)
        self.mark(self.task, False)
        data = self.summary()
        self.assertEqual(data['kpis']['total_tasks'], 1)
        self.assertEqual(data['finance']['estimated_total_vnd'], '900000')
        self.assertEqual(data['finance']['approved_total_vnd'], '250000')

    def test_deleted_profile_and_revoked_actor_cannot_read_retained_finance(self):
        self.approval()
        self.mark(self.profile)
        self.assertEqual(self.client.get(f'/api/v1/profiles/{self.profile.pk}/analytics/').status_code, 404)
        self.mark(self.profile, False)
        ProfileMembership.objects.filter(pk=self.editor_membership.pk).update(is_active=False)
        self.client.force_authenticate(self.editor)
        self.assertEqual(self.client.get(f'/api/v1/profiles/{self.profile.pk}/analytics/').status_code, 404)

    def test_lazy_historical_scope_fails_closed_after_owner_revocation(self):
        self.approval()
        serializer = AnalyticsQuerySerializer(data={'from':'2026-11-01','to':'2026-11-30'})
        self.assertTrue(serializer.is_valid())
        scope = resolve_analytics_scope(actor=self.owner, profile_id=self.profile.pk, filters=serializer.validated_data)
        ProfileMembership.objects.filter(pk=self.owner_membership.pk).update(is_active=False)
        data = analytics_summary(scope)
        self.assertEqual(data['kpis']['total_tasks'], 0)
        self.assertIsNone(data['finance']['approved_total_vnd'])
