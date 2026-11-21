"""Handover history, locked expectations, notification atomicity and RBAC."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections, connections
from django.test import TransactionTestCase
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.notifications.services import emit_task_notifications
from apps.reviews.models import Deliverable, Review
from apps.workspace.models import ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .models import Task, TaskAssignment
from .services import (
    TaskAssignmentConflict, approve_deliverable, assign_task, create_task,
    request_deliverable_changes, start_task, submit_deliverable, unassign_task, update_task,
)

User = get_user_model()


class _ReassignmentFixture:
    @classmethod
    def build_fixture(cls):
        for label in ('owner', 'admin', 'manager', 'editor', 'second', 'third', 'viewer', 'outsider'):
            setattr(cls, label, User.objects.create_user(
                username=f'handover-{label}', email=f'handover-{label}@example.test', password=None,
            ))
        cls.profile = create_profile_with_owner(name='Isolated handover', owner=cls.owner)
        cls.memberships = {}
        for label in ('admin', 'manager', 'editor', 'second', 'third', 'viewer'):
            cls.memberships[label] = ProfileMembership.objects.create(
                profile=cls.profile, user=getattr(cls, label),
                role=ProfileMembership.Role.ADMIN if label == 'admin' else ProfileMembership.Role.MEMBER,
            )
        cls.workspace = Workspace.objects.create(profile=cls.profile, owner=cls.owner, name='Handover workspace', period=date(2026, 11, 1))
        for label in ('manager', 'editor', 'second', 'third', 'viewer'):
            WorkspaceMember.objects.create(
                workspace=cls.workspace, user=getattr(cls, label),
                role={'manager': WorkspaceMember.Role.ADMIN, 'viewer': WorkspaceMember.Role.VIEWER}.get(label, WorkspaceMember.Role.MEMBER),
            )
        cls.foreign_profile = create_profile_with_owner(name='Other handover', owner=cls.outsider)
        cls.foreign_workspace = Workspace.objects.create(profile=cls.foreign_profile, owner=cls.outsider, name='Other workspace', period=date(2026, 11, 1))

    def scope(self):
        return {'profile_id': self.profile.pk, 'workspace_id': self.workspace.pk}

    def new_task(self, *, assigned=True):
        task = create_task(actor=self.owner, title='Preserved handover task', estimated_compensation_vnd='500000', **self.scope())
        if assigned:
            assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['editor'].pk, **self.scope())
            task.refresh_from_db()
        return task

    def current(self, task):
        return TaskAssignment.objects.get(task=task, is_active=True)

    def expectation(self, task):
        current = self.current(task)
        return {'expected_assignment_id': current.pk, 'expected_assigned_at': current.assigned_at}

    def api_expectation(self, task):
        current = self.current(task)
        return {'expected_assignment_id': str(current.pk), 'expected_assigned_at': current.assigned_at.isoformat()}

    def url(self, task, action=''):
        return f'/api/v1/profiles/{self.profile.pk}/workspaces/{self.workspace.pk}/tasks/{task.pk}/' + (action + '/' if action else '')


class ReassignmentApiTests(_ReassignmentFixture, APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_fixture()

    def test_unassign_returns_each_open_status_to_pending_and_retains_assignment_history(self):
        for state in (Task.Status.PENDING, Task.Status.ASSIGNED, Task.Status.WORKING):
            task = self.new_task()
            Task.objects.filter(pk=task.pk).update(status=state)
            old = self.current(task)
            original_identity = (old.task_id, old.user_id, old.assigned_at, old.created_at)
            self.client.force_authenticate(self.manager)
            response = self.client.post(self.url(task, 'unassign'), {**self.api_expectation(task), 'reason': ' Editor unavailable '}, format='json')
            self.assertEqual(response.status_code, 200)
            self.assertIsNone(response.data['active_assignment'])
            self.assertEqual(response.data['status'], Task.Status.PENDING)
            self.assertEqual(response.data['estimated_compensation_vnd'], '500000')
            self.assertFalse(response.data['can_unassign'])
            self.assertTrue(response.data['can_assign'])
            task.refresh_from_db()
            self.assertEqual(task.status, Task.Status.PENDING)
            old.refresh_from_db()
            self.assertFalse(old.is_active)
            self.assertEqual((old.task_id, old.user_id, old.assigned_at, old.created_at), original_identity)
            self.assertEqual(TaskAssignment.objects.filter(task=task).count(), 1)
            event = AuditLog.objects.get(action='task.unassigned', metadata__task_id=str(task.pk))
            self.assertEqual(event.metadata['previous_user_id'], str(self.editor.pk))
            self.assertEqual(event.metadata['reason'], 'Editor unavailable')
            self.assertEqual(event.metadata['task_status_before'], state)
            self.assertEqual(event.metadata['task_status_after'], Task.Status.PENDING)
            self.assertNotIn('estimated_compensation_vnd', event.metadata)
            self.assertTrue(Notification.objects.filter(event=event, user=self.editor, event_type='TASK_UNASSIGNED').exists())

    def test_unassign_after_request_changes_preserves_revisions_reviews_and_past_assignments(self):
        task = self.new_task()
        start_task(actor=self.editor, task_id=task.pk, **self.scope())
        product = submit_deliverable(actor=self.editor, task_id=task.pk, file_url='https://example.test/preserved-product', **self.scope())
        # A pending review must be decided through the existing review workflow.
        with self.assertRaises(TaskAssignmentConflict):
            unassign_task(actor=self.owner, task_id=task.pk, **self.expectation(task), **self.scope())
        request_deliverable_changes(actor=self.owner, task_id=task.pk, deliverable_id=product.pk, comment='Retain this feedback', **self.scope())
        assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['second'].pk, **self.expectation(task), **self.scope())
        start_task(actor=self.second, task_id=task.pk, **self.scope())
        current = self.current(task)
        assignments = list(TaskAssignment.objects.filter(task=task).order_by('pk').values('id', 'task_id', 'user_id', 'assigned_at', 'created_at'))
        products = list(Deliverable.objects.filter(task=task).order_by('pk').values())
        reviews = list(Review.objects.filter(deliverable__task=task).order_by('pk').values())
        history = list(AuditLog.objects.filter(metadata__task_id=str(task.pk)).order_by('pk').values())

        result = unassign_task(actor=self.owner, task_id=task.pk, **self.expectation(task), **self.scope())

        self.assertEqual(result.status, Task.Status.PENDING)
        self.assertEqual(TaskAssignment.objects.filter(task=task, is_active=True).count(), 0)
        self.assertEqual(list(TaskAssignment.objects.filter(task=task).order_by('pk').values('id', 'task_id', 'user_id', 'assigned_at', 'created_at')), assignments)
        self.assertEqual(list(Deliverable.objects.filter(task=task).order_by('pk').values()), products)
        self.assertEqual(list(Review.objects.filter(deliverable__task=task).order_by('pk').values()), reviews)
        self.assertEqual(list(AuditLog.objects.filter(pk__in=[row['id'] for row in history]).order_by('pk').values()), history)
        event = AuditLog.objects.get(action='task.unassigned', metadata__task_id=str(task.pk))
        self.assertEqual(event.metadata['previous_assignment_id'], str(current.pk))
        self.assertEqual(event.metadata['task_status_before'], Task.Status.WORKING)
        self.assertEqual(event.metadata['task_status_after'], Task.Status.PENDING)

    def test_transfer_preserves_submissions_authors_reviews_and_reason(self):
        task = self.new_task()
        start_task(actor=self.editor, task_id=task.pk, **self.scope())
        first = submit_deliverable(actor=self.editor, task_id=task.pk, file_url='https://example.test/first', **self.scope())
        decision = request_deliverable_changes(actor=self.owner, task_id=task.pk, deliverable_id=first.pk, comment='Preserved revision', **self.scope())
        self.assertEqual(Task.objects.get(pk=task.pk).status, Task.Status.WORKING)
        previous = self.current(task)
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.url(task, 'assign'), {**self.api_expectation(task), 'target_profile_membership_id': str(self.memberships['second'].pk), 'reason': 'Team handover'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'ASSIGNED')
        self.assertEqual(response.data['active_assignment']['display_name'], self.second.username)
        first.refresh_from_db(); decision.refresh_from_db(); previous.refresh_from_db()
        self.assertEqual(first.uploaded_by_id, self.editor.pk)
        self.assertEqual(first.file_url, 'https://example.test/first')
        self.assertEqual(decision.status, Review.Status.REQUEST_CHANGE)
        self.assertFalse(previous.is_active)
        event = AuditLog.objects.get(action='task.reassigned', metadata__task_id=str(task.pk))
        self.assertEqual(event.metadata['previous_user_id'], str(self.editor.pk))
        self.assertEqual(event.metadata['target_user_id'], str(self.second.pk))
        self.assertEqual(event.metadata['reason'], 'Team handover')
        self.assertEqual(event.metadata['task_status_before'], Task.Status.WORKING)
        self.assertEqual(event.metadata['task_status_after'], Task.Status.ASSIGNED)
        self.assertEqual(set(Notification.objects.filter(event=event).values_list('user_id', 'event_type')), {
            (self.editor.pk, 'TASK_UNASSIGNED'), (self.second.pk, 'TASK_ASSIGNED'),
        })
        start_task(actor=self.second, task_id=task.pk, **self.scope())
        second = submit_deliverable(actor=self.second, task_id=task.pk, file_url='https://example.test/second', **self.scope())
        accepted = approve_deliverable(actor=self.owner, task_id=task.pk, deliverable_id=second.pk, **self.scope())
        self.assertEqual(accepted.deliverable.uploaded_by_id, self.second.pk)
        self.assertTrue(accepted.compensation_snapshot_recorded)
        self.assertEqual(accepted.compensation_snapshot_vnd, 500000)
        update_task(actor=self.owner, task_id=task.pk, estimated_compensation_vnd='900000', **self.scope())
        accepted.refresh_from_db()
        self.assertEqual(accepted.compensation_snapshot_vnd, 500000)
        self.assertEqual(task.deliverables.count(), 2)

    def test_completed_review_and_cancelled_tasks_reject_both_actions(self):
        for state in (Task.Status.REVIEW, Task.Status.COMPLETED, Task.Status.CANCELLED):
            task = self.new_task()
            Task.objects.filter(pk=task.pk).update(status=state)
            self.client.force_authenticate(self.owner)
            for action in ('assign', 'unassign'):
                payload = self.api_expectation(task)
                if action == 'assign':
                    payload['target_profile_membership_id'] = str(self.memberships['second'].pk)
                response = self.client.post(self.url(task, action), payload, format='json')
                self.assertEqual(response.status_code, 409)
            self.assertEqual(self.current(task).user_id, self.editor.pk)
            self.assertEqual(TaskAssignment.objects.filter(task=task).count(), 1)
            task.refresh_from_db()
            self.assertEqual(task.status, state)

    def test_stale_confirmation_and_replay_do_not_mutate_second_assignment(self):
        task = self.new_task()
        stale = self.api_expectation(task)
        assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['second'].pk, **self.scope())
        self.client.force_authenticate(self.owner)
        for action in ('assign', 'unassign'):
            payload = {**stale, 'target_profile_membership_id': str(self.memberships['third'].pk)} if action == 'assign' else stale
            self.assertEqual(self.client.post(self.url(task, action), payload, format='json').status_code, 409)
        self.assertEqual(self.current(task).user_id, self.second.pk)

    def test_aba_reused_assignment_requires_current_timestamp(self):
        task = self.new_task()
        stale = self.expectation(task)
        assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['second'].pk, **self.scope())
        active = assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['editor'].pk, **self.scope())
        self.assertEqual(active.pk, stale['expected_assignment_id'])
        self.assertNotEqual(active.assigned_at, stale['expected_assigned_at'])
        with self.assertRaises(TaskAssignmentConflict):
            unassign_task(actor=self.owner, task_id=task.pk, **stale, **self.scope())

    def test_initial_null_pair_and_legacy_omitted_pair_are_compatible(self):
        task = self.new_task(assigned=False)
        self.client.force_authenticate(self.owner)
        payload = {'target_profile_membership_id': str(self.memberships['editor'].pk), 'expected_assignment_id': None, 'expected_assigned_at': None}
        self.assertEqual(self.client.post(self.url(task, 'assign'), payload, format='json').status_code, 200)
        self.assertEqual(self.client.post(self.url(task, 'assign'), {**payload, 'target_profile_membership_id': str(self.memberships['second'].pk)}, format='json').status_code, 409)
        self.assertEqual(self.client.post(self.url(task, 'assign'), {'target_profile_membership_id': str(self.memberships['second'].pk)}, format='json').status_code, 200)

    def test_unassign_requires_both_nonnull_expectations_and_strict_fields(self):
        task = self.new_task()
        self.client.force_authenticate(self.owner)
        for payload in ({}, {'expected_assignment_id': str(self.current(task).pk)}, {'expected_assignment_id': None, 'expected_assigned_at': None}, {**self.api_expectation(task), 'user_id': str(self.second.pk)}):
            self.assertEqual(self.client.post(self.url(task, 'unassign'), payload, format='json').status_code, 400)
        self.assertEqual(self.client.post(self.url(task, 'assign'), {'target_profile_membership_id': str(self.memberships['second'].pk), 'expected_assignment_id': None}, format='json').status_code, 400)

    def test_reason_limits_and_raw_input_are_validated_before_mutation(self):
        task = self.new_task()
        self.client.force_authenticate(self.owner)
        for value in (True, 12, {}, 'x' * 4001, '\x00', '\ud800'):
            # Escaped invalid Unicode reaches request validation rather than
            # failing in the test client's own UTF-8 encoder.
            payload = json.dumps({**self.api_expectation(task), 'reason': value}, ensure_ascii=True)
            response = self.client.post(self.url(task, 'unassign'), payload, content_type='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertEqual(self.current(task).user_id, self.editor.pk)
        self.assertFalse(AuditLog.objects.filter(action='task.unassigned', metadata__task_id=str(task.pk)).exists())

    def test_member_viewer_and_outsider_cannot_manage_assignment(self):
        task = self.new_task()
        for actor, expected in ((self.editor, 403), (self.viewer, 403), (self.outsider, 404)):
            self.client.force_authenticate(actor)
            self.assertEqual(self.client.post(self.url(task, 'unassign'), self.api_expectation(task), format='json').status_code, expected)
            payload = {**self.api_expectation(task), 'target_profile_membership_id': str(self.memberships['second'].pk)}
            self.assertEqual(self.client.post(self.url(task, 'assign'), payload, format='json').status_code, expected)

    def test_revoked_actor_and_cross_workspace_task_reference_are_hidden(self):
        task = self.new_task()
        self.client.force_authenticate(self.manager)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.manager).update(is_active=False)
        self.assertEqual(self.client.post(self.url(task, 'unassign'), self.api_expectation(task), format='json').status_code, 404)
        self.client.force_authenticate(self.owner)
        wrong_url = self.url(task, 'unassign').replace(str(self.workspace.pk), str(self.foreign_workspace.pk))
        self.assertEqual(self.client.post(wrong_url, self.api_expectation(task), format='json').status_code, 404)

    def test_target_membership_must_still_be_active_eligible_in_same_workspace(self):
        task = self.new_task()
        self.client.force_authenticate(self.owner)
        target = self.memberships['second']
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.second).update(is_active=False)
        self.assertEqual(self.client.post(self.url(task, 'assign'), {**self.api_expectation(task), 'target_profile_membership_id': str(target.pk)}, format='json').status_code, 400)
        foreign = ProfileMembership.objects.get(profile=self.foreign_profile, user=self.outsider)
        self.assertEqual(self.client.post(self.url(task, 'assign'), {**self.api_expectation(task), 'target_profile_membership_id': str(foreign.pk)}, format='json').status_code, 400)
        self.assertEqual(self.current(task).user_id, self.editor.pk)

    def test_same_assignee_rejected_without_notification_or_audit(self):
        task = self.new_task()
        before = (AuditLog.objects.count(), Notification.objects.count())
        with self.assertRaises(TaskAssignmentConflict):
            assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['editor'].pk, **self.expectation(task), **self.scope())
        self.assertEqual(before, (AuditLog.objects.count(), Notification.objects.count()))

    def test_archived_scope_is_readonly_and_capability_hints_fail_closed(self):
        task = self.new_task()
        self.client.force_authenticate(self.owner)
        for model, row in ((Workspace, self.workspace), (self.profile.__class__, self.profile)):
            model.objects.filter(pk=row.pk).update(status='ARCHIVED')
            detail = self.client.get(self.url(task))
            self.assertEqual(detail.status_code, 200)
            self.assertFalse(detail.data['can_assign']); self.assertFalse(detail.data['can_unassign'])
            self.assertEqual(self.client.post(self.url(task, 'unassign'), self.api_expectation(task), format='json').status_code, 403)
            model.objects.filter(pk=row.pk).update(status='ACTIVE')

    def test_capabilities_and_compensation_update_after_unassignment(self):
        task = self.new_task()
        self.client.force_authenticate(self.editor)
        detail = self.client.get(self.url(task))
        self.assertFalse(detail.data['can_assign']); self.assertFalse(detail.data['can_unassign'])
        self.assertEqual(detail.data['estimated_compensation_vnd'], '500000')
        unassign_task(actor=self.owner, task_id=task.pk, **self.expectation(task), **self.scope())
        detail = self.client.get(self.url(task))
        self.assertIsNone(detail.data['active_assignment']); self.assertIsNone(detail.data['estimated_compensation_vnd'])
        self.assertFalse(detail.data['can_start']); self.assertFalse(detail.data['can_submit'])
        self.assertEqual(self.client.patch(self.url(task), {'estimated_compensation_vnd': '1'}, format='json').status_code, 403)

    def test_csrf_anonymous_and_method_boundaries(self):
        task = self.new_task()
        self.assertEqual(self.client.post(self.url(task, 'unassign'), self.api_expectation(task), format='json').status_code, 403)
        csrf = APIClient(enforce_csrf_checks=True); csrf.force_login(self.owner)
        self.assertEqual(csrf.post(self.url(task, 'unassign'), self.api_expectation(task), format='json').status_code, 403)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(self.url(task, 'unassign')).status_code, 405)

    def test_revoked_previous_assignee_receives_no_new_notification(self):
        task = self.new_task()
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(is_active=False)
        assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['second'].pk, **self.expectation(task), **self.scope())
        event = AuditLog.objects.get(action='task.reassigned', metadata__task_id=str(task.pk))
        self.assertEqual(set(Notification.objects.filter(event=event).values_list('user_id', flat=True)), {self.second.pk})

    def test_actor_is_not_notified_of_their_own_assignment_removal(self):
        task = self.new_task()
        ProfileMembership.objects.filter(pk=self.memberships['editor'].pk).update(role=ProfileMembership.Role.ADMIN)
        unassign_task(actor=self.editor, task_id=task.pk, **self.expectation(task), **self.scope())
        event = AuditLog.objects.get(action='task.unassigned', metadata__task_id=str(task.pk))
        self.assertFalse(Notification.objects.filter(event=event).exists())

    def test_event_retry_deduplicates_both_recipients_and_retains_read_state(self):
        task = self.new_task()
        assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['second'].pk, **self.expectation(task), **self.scope())
        event = AuditLog.objects.get(action='task.reassigned', metadata__task_id=str(task.pk))
        Notification.objects.filter(event=event).update(is_read=True)
        for kind in (Notification.EventType.TASK_ASSIGNED, Notification.EventType.TASK_UNASSIGNED):
            emit_task_notifications(event=event, actor=self.owner, task=task, event_type=kind)
        self.assertEqual(Notification.objects.filter(event=event).count(), 2)
        self.assertFalse(Notification.objects.filter(event=event, is_read=False).exists())

    def test_older_assignment_event_cannot_reappear_after_row_reactivation(self):
        task = self.new_task()
        event = AuditLog.objects.get(action='task.assigned', metadata__task_id=str(task.pk))
        assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['second'].pk, **self.scope())
        assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['editor'].pk, **self.scope())
        Notification.objects.filter(event=event).delete()  # Isolated replay fixture only.
        self.assertEqual(emit_task_notifications(event=event, actor=self.owner, task=task, event_type=Notification.EventType.TASK_ASSIGNED), [])
        self.assertFalse(Notification.objects.filter(event=event).exists())

    def test_notification_failure_rolls_back_handover_and_both_notifications(self):
        task = self.new_task()
        old = self.current(task)
        before = (AuditLog.objects.count(), Notification.objects.count())
        with patch('apps.tasks.services.emit_task_notifications', side_effect=RuntimeError('synthetic rollback')):
            with self.assertRaises(RuntimeError):
                assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['second'].pk, **self.expectation(task), **self.scope())
        self.assertEqual(self.current(task).pk, old.pk)
        self.assertEqual(TaskAssignment.objects.filter(task=task).count(), 1)
        self.assertEqual(before, (AuditLog.objects.count(), Notification.objects.count()))

    def test_audit_failure_rolls_back_unassignment_and_pending_transition(self):
        task = self.new_task()
        start_task(actor=self.editor, task_id=task.pk, **self.scope())
        old = self.current(task)
        before = (AuditLog.objects.count(), Notification.objects.count())
        with patch('apps.tasks.services.AuditLog.objects.create', side_effect=RuntimeError('synthetic rollback')):
            with self.assertRaises(RuntimeError):
                unassign_task(actor=self.owner, task_id=task.pk, **self.expectation(task), **self.scope())
        self.assertEqual(self.current(task).pk, old.pk)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.WORKING)
        self.assertEqual(before, (AuditLog.objects.count(), Notification.objects.count()))

    def test_notification_failure_rolls_back_unassignment_status_and_audit(self):
        task = self.new_task()
        start_task(actor=self.editor, task_id=task.pk, **self.scope())
        old = self.current(task)
        before = (AuditLog.objects.count(), Notification.objects.count())
        with patch('apps.tasks.services.emit_task_notifications', side_effect=RuntimeError('synthetic notification rollback')):
            with self.assertRaises(RuntimeError):
                unassign_task(actor=self.owner, task_id=task.pk, **self.expectation(task), **self.scope())
        self.assertEqual(self.current(task).pk, old.pk)
        self.assertEqual(TaskAssignment.objects.filter(task=task).count(), 1)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.WORKING)
        self.assertEqual(before, (AuditLog.objects.count(), Notification.objects.count()))

    def test_old_recipient_notification_failure_also_rewinds_new_recipient_notification(self):
        task = self.new_task()
        old = self.current(task)
        before = (AuditLog.objects.count(), Notification.objects.count())

        def emit_then_fail(**kwargs):
            if kwargs['event_type'] == Notification.EventType.TASK_UNASSIGNED:
                raise RuntimeError('synthetic second-recipient failure')
            return emit_task_notifications(**kwargs)

        with patch('apps.tasks.services.emit_task_notifications', side_effect=emit_then_fail):
            with self.assertRaises(RuntimeError):
                assign_task(actor=self.owner, task_id=task.pk, target_profile_membership_id=self.memberships['second'].pk, **self.expectation(task), **self.scope())
        self.assertEqual(self.current(task).pk, old.pk)
        self.assertEqual(TaskAssignment.objects.filter(task=task).count(), 1)
        self.assertEqual(before, (AuditLog.objects.count(), Notification.objects.count()))


class ConcurrentReassignmentTests(_ReassignmentFixture, TransactionTestCase):
    def setUp(self):
        self.build_fixture()

    def test_two_managers_with_same_confirmation_allow_one_transfer(self):
        task = self.new_task()
        expectation = self.expectation(task)
        barrier = Barrier(2)

        def transfer(actor_id, membership_id):
            close_old_connections()
            try:
                actor = User.objects.get(pk=actor_id)
                barrier.wait(timeout=15)
                try:
                    assignment = assign_task(actor=actor, task_id=task.pk, target_profile_membership_id=membership_id, **expectation, **self.scope())
                    return ('ok', assignment.pk)
                except TaskAssignmentConflict:
                    return ('stale', None)
            finally:
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(transfer, self.owner.pk, self.memberships['second'].pk), executor.submit(transfer, self.admin.pk, self.memberships['third'].pk)]
            outcomes = [future.result(timeout=30)[0] for future in futures]
        self.assertCountEqual(outcomes, ['ok', 'stale'])
        self.assertEqual(TaskAssignment.objects.filter(task=task, is_active=True).count(), 1)
        self.assertEqual(AuditLog.objects.filter(action='task.reassigned', metadata__task_id=str(task.pk)).count(), 1)

    def test_unassign_and_transfer_with_same_confirmation_cannot_both_commit(self):
        task = self.new_task()
        expectation = self.expectation(task)
        barrier = Barrier(2)

        def mutate(remove):
            close_old_connections()
            try:
                actor = User.objects.get(pk=self.owner.pk if remove else self.admin.pk)
                barrier.wait(timeout=15)
                try:
                    if remove:
                        unassign_task(actor=actor, task_id=task.pk, **expectation, **self.scope())
                    else:
                        assign_task(actor=actor, task_id=task.pk, target_profile_membership_id=self.memberships['second'].pk, **expectation, **self.scope())
                    return ('ok', remove)
                except TaskAssignmentConflict:
                    return ('stale', None)
            finally:
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(mutate, True), executor.submit(mutate, False)]
            outcomes = [future.result(timeout=30) for future in futures]
        self.assertCountEqual([outcome for outcome, _ in outcomes], ['ok', 'stale'])
        removed = next(remove for outcome, remove in outcomes if outcome == 'ok')
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.PENDING if removed else Task.Status.ASSIGNED)
        self.assertEqual(TaskAssignment.objects.filter(task=task, is_active=True).count(), 0 if removed else 1)
