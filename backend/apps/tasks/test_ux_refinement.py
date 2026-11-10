"""URL submissions and safe current assignee presentation, isolated PostgreSQL."""

from datetime import date
import json
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import SimpleTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.reviews.models import Deliverable, Review
from apps.reviews.validation import normalize_deliverable_url
from apps.workspace.access import resolve_profile_access_context, resolve_workspace_access_context
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .models import Task, TaskAssignment
from .presentation import assignee_display_name
from .serializers import DeliverableSubmitSerializer, TaskReadSerializer
from .services import submit_deliverable
from .views import _task_read_queryset


User = get_user_model()


class ProductLinkValidationTests(SimpleTestCase):
    def test_supported_http_links_include_private_provider_resources_without_fetching(self):
        urls = (
            'https://drive.google.com/file/d/synthetic/view?usp=sharing',
            'https://1drv.ms/v/s!synthetic', 'https://www.dropbox.com/scl/fi/synthetic/video.mp4?dl=0',
            'https://www.youtube.com/watch?v=synthetic', 'http://files.example.test/private/video',
        )
        with patch('socket.getaddrinfo', side_effect=AssertionError('No DNS request is allowed')):
            for url in urls:
                self.assertEqual(normalize_deliverable_url(f'  {url}  '), url)

    def test_storage_bound_is_exactly_500_characters(self):
        prefix = 'https://example.test/'
        value = prefix + 'x' * (500 - len(prefix))
        self.assertEqual(normalize_deliverable_url(value), value)
        with self.assertRaises(ValidationError):
            normalize_deliverable_url(value + 'x')

    def test_unsafe_schemes_invalid_unicode_controls_userinfo_and_non_string_values_rejected(self):
        for value in (
            'javascript:alert(1)', 'data:text/html,text', 'file:///tmp/clip', 'ftp://example.test/file',
            '//example.test/file', '/media/old.mp4', 'A plain text submission', '', ' ',
            'https://example.test/\x00', 'https://example.test/\n', 'https://example.test/\x85',
            'https://example.test/\ud800', 'https://example.test/a b', 'https://example.test\\evil',
            'https://user:password@example.test/private', 'https://user@example.test/private',
            'https://example.test:99999/file', None, 123, True, {}, [],
        ):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(ValidationError):
                    normalize_deliverable_url(value)

    def test_serializer_does_not_coerce_or_trim_away_invalid_raw_input(self):
        for value in (123, True, 'https://example.test/file\n', 'https://example.test/\ud800'):
            serializer = DeliverableSubmitSerializer(data={'file_url': value})
            self.assertFalse(serializer.is_valid())
            self.assertIn('file_url', serializer.errors)

    def test_display_name_uses_full_name_then_safe_username_and_never_email_or_uuid(self):
        self.assertEqual(assignee_display_name(first_name='An', last_name='Nguyễn', username='editor'), 'An Nguyễn')
        self.assertEqual(assignee_display_name(first_name='', last_name='', username='editor_safe'), 'editor_safe')
        for username in ('editor@example.test', '00000000-0000-4000-8000-000000000001', 'https://example.test/private', ''):
            self.assertEqual(assignee_display_name(first_name='', last_name='', username=username), 'Thành viên được giao')
        self.assertEqual(assignee_display_name(first_name='00000000-0000-4000-8000-000000000001', last_name='', username='editor'), 'editor')


class TaskUxRefinementApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        for label in ('owner', 'manager', 'editor', 'next_editor', 'viewer', 'outsider', 'foreign'):
            setattr(cls, label, User.objects.create_user(username=f'ux-{label}', email=f'ux-{label}@example.test', password=None))
        cls.profile = create_profile_with_owner(name='UX tenant', owner=cls.owner)
        cls.workspace = Workspace.objects.create(profile=cls.profile, owner=cls.owner, name='UX month', period=date(2026, 11, 1))
        cls.sibling = Workspace.objects.create(profile=cls.profile, owner=cls.owner, name='Other month', period=date(2026, 12, 1))
        cls.memberships = {}
        for label, role in (('manager', 'ADMIN'), ('editor', 'MEMBER'), ('next_editor', 'MEMBER'), ('viewer', 'VIEWER')):
            actor = getattr(cls, label)
            cls.memberships[label] = ProfileMembership.objects.create(profile=cls.profile, user=actor)
            WorkspaceMember.objects.create(workspace=cls.workspace, user=actor, role=role)
        User.objects.filter(pk=cls.editor.pk).update(first_name='An', last_name='Nguyễn')
        User.objects.filter(pk=cls.next_editor.pk).update(first_name='Bình', last_name='Trần')
        cls.foreign_profile = create_profile_with_owner(name='Other UX tenant', owner=cls.foreign)
        cls.foreign_workspace = Workspace.objects.create(profile=cls.foreign_profile, owner=cls.foreign, name='Other UX month', period=date(2026, 11, 1))
        cls.task = Task.objects.create(workspace=cls.workspace, created_by=cls.owner, title='UX work', status='WORKING', estimated_compensation_vnd='500000')
        cls.assignment = TaskAssignment.objects.create(task=cls.task, user=cls.editor)

    def url(self, route='task-detail', *, task=None, deliverable=None, **scope):
        kwargs = {'profile_id': self.profile.pk, 'workspace_id': self.workspace.pk, **scope}
        if route != 'task-list': kwargs['task_id'] = getattr(task or self.task, 'pk', task or self.task)
        if deliverable is not None: kwargs['deliverable_id'] = getattr(deliverable, 'pk', deliverable)
        return reverse('tasks:' + route, kwargs=kwargs)

    def login(self, actor):
        self.client.force_login(actor)

    def context(self, actor):
        return resolve_workspace_access_context(resolve_profile_access_context(actor, self.profile.pk), self.workspace.pk)

    def submit(self, url='https://drive.google.com/file/d/synthetic/view'):
        return self.client.post(self.url('task-deliverable-list'), {'file_url': url}, format='json')

    def test_current_assignee_full_name_in_list_detail_and_pay_policy_unchanged(self):
        for actor, amount in ((self.owner, '500000'), (self.manager, '500000'), (self.editor, '500000'), (self.viewer, None)):
            self.login(actor)
            detail = self.client.get(self.url())
            self.assertEqual(detail.status_code, 200)
            self.assertEqual(detail.data['active_assignment']['display_name'], 'An Nguyễn')
            self.assertEqual(detail.data['estimated_compensation_vnd'], amount)
            listed = self.client.get(self.url('task-list'))
            self.assertEqual(listed.data['results'][0]['active_assignment'], detail.data['active_assignment'])
            self.assertNotIn(self.editor.email, json.dumps(detail.data, default=str))

    def test_blank_name_has_safe_username_fallback(self):
        User.objects.filter(pk=self.editor.pk).update(first_name='', last_name='')
        self.login(self.viewer)
        self.assertEqual(self.client.get(self.url()).data['active_assignment']['display_name'], 'ux-editor')

    def test_email_or_uuid_fallback_never_leaks_identifiers(self):
        self.login(self.viewer)
        for username in ('private@example.test', str(self.editor.pk)):
            User.objects.filter(pk=self.editor.pk).update(first_name='', last_name='', username=username)
            self.assertEqual(self.client.get(self.url()).data['active_assignment']['display_name'], 'Thành viên được giao')

    def test_unassigned_task_returns_null_assignment(self):
        TaskAssignment.objects.filter(pk=self.assignment.pk).update(is_active=False)
        self.login(self.viewer)
        self.assertIsNone(self.client.get(self.url()).data['active_assignment'])

    def test_inactive_assignee_does_not_disclose_a_cached_name(self):
        self.login(self.viewer)
        User.objects.filter(pk=self.editor.pk).update(is_active=False)
        self.assertIsNone(self.client.get(self.url()).data['active_assignment']['display_name'])

    def test_revoked_profile_membership_does_not_disclose_name(self):
        self.login(self.viewer)
        ProfileMembership.objects.filter(pk=self.memberships['editor'].pk).update(is_active=False)
        self.assertIsNone(self.client.get(self.url()).data['active_assignment']['display_name'])

    def test_revoked_workspace_membership_does_not_disclose_name(self):
        self.login(self.viewer)
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(is_active=False)
        self.assertIsNone(self.client.get(self.url()).data['active_assignment']['display_name'])

    def test_read_access_is_not_execution_or_compensation_authority(self):
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(role='VIEWER')
        self.login(self.viewer)
        self.assertEqual(self.client.get(self.url()).data['active_assignment']['display_name'], 'An Nguyễn')
        self.login(self.editor)
        row = self.client.get(self.url()).data
        self.assertFalse(row['can_submit'])
        self.assertIsNone(row['estimated_compensation_vnd'])
        self.assertEqual(self.submit().status_code, 403)

    def test_profile_manager_assignee_retains_inherited_read_access_without_execution(self):
        ProfileMembership.objects.filter(pk=self.memberships['editor'].pk).update(role='ADMIN')
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(is_active=False)
        self.login(self.viewer)
        self.assertEqual(self.client.get(self.url()).data['active_assignment']['display_name'], 'An Nguyễn')
        self.login(self.editor)
        self.assertFalse(self.client.get(self.url()).data['can_submit'])

    def test_assignment_change_returns_new_name_and_keeps_single_active_history(self):
        self.login(self.owner)
        response = self.client.post(self.url('task-assign'), {'target_profile_membership_id': str(self.memberships['next_editor'].pk)}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['active_assignment']['display_name'], 'Bình Trần')
        self.assertEqual(TaskAssignment.objects.filter(task=self.task, is_active=True).count(), 1)
        self.assertEqual(TaskAssignment.objects.filter(task=self.task).count(), 2)
        self.login(self.editor)
        row = self.client.get(self.url()).data
        self.assertEqual(row['active_assignment']['display_name'], 'Bình Trần')
        self.assertIsNone(row['estimated_compensation_vnd'])

    def test_cached_user_or_assignment_cannot_restore_revoked_name(self):
        context = self.context(self.viewer)
        loaded = list(_task_read_queryset(context).filter(pk=self.task.pk))[0]
        WorkspaceMember.objects.filter(workspace=self.workspace, user=self.editor).update(is_active=False)
        row = TaskReadSerializer(loaded, context={'request': SimpleNamespace(user=self.viewer), 'workspace_access_context': context}).data
        self.assertIsNone(row['active_assignment']['display_name'])

    def test_missing_or_mismatched_actor_context_fails_closed_for_display(self):
        for context in ({}, {'request': SimpleNamespace(user=self.viewer), 'workspace_access_context': self.context(self.owner)}):
            self.assertIsNone(TaskReadSerializer(self.task, context=context).data['active_assignment']['display_name'])

    def test_mixed_task_scope_cannot_disclose_foreign_assignee_name(self):
        task = Task.objects.create(workspace=self.foreign_workspace, created_by=self.foreign, title='Other tenant')
        TaskAssignment.objects.create(task=task, user=self.foreign)
        rows = TaskReadSerializer([self.task, task], many=True, context={'request': SimpleNamespace(user=self.viewer), 'workspace_access_context': self.context(self.viewer)}).data
        self.assertEqual(rows[0]['active_assignment']['display_name'], 'An Nguyễn')
        self.assertIsNone(rows[1]['active_assignment']['display_name'])

    def test_archived_read_scope_keeps_name_and_existing_mutation_denial(self):
        Workspace.objects.filter(pk=self.workspace.pk).update(status='ARCHIVED')
        Profile.objects.filter(pk=self.profile.pk).update(status='ARCHIVED')
        self.login(self.viewer)
        self.assertEqual(self.client.get(self.url()).data['active_assignment']['display_name'], 'An Nguyễn')
        self.login(self.editor)
        self.assertEqual(self.submit().status_code, 403)

    def test_list_name_projection_has_no_per_task_query_growth(self):
        self.login(self.viewer)
        with CaptureQueriesContext(connection) as first:
            small = self.client.get(self.url('task-list'), {'page_size': 50})
        self.assertEqual(small.status_code, 200)
        for index in range(12):
            task = Task.objects.create(workspace=self.workspace, created_by=self.owner, title=f'Name page {index}')
            TaskAssignment.objects.create(task=task, user=self.editor if index % 2 else self.next_editor)
        with CaptureQueriesContext(connection) as second:
            large = self.client.get(self.url('task-list'), {'page_size': 50})
        self.assertEqual(large.status_code, 200)
        self.assertEqual(len(large.data['results']), 13)
        self.assertEqual(len(first), len(second))
        self.assertEqual({row['active_assignment']['display_name'] for row in large.data['results']}, {'An Nguyễn', 'Bình Trần'})

    def test_valid_url_submission_is_trimmed_and_revisioned(self):
        self.login(self.editor)
        response = self.submit('  https://drive.google.com/file/d/synthetic/view  ')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['file_url'], 'https://drive.google.com/file/d/synthetic/view')
        self.assertEqual(response.data['revision'], 1)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'REVIEW')

    def test_invalid_url_rejected_without_task_revision_audit_or_notification_mutation(self):
        self.login(self.editor)
        before_audits = AuditLog.objects.count()
        before_notifications = Notification.objects.count()
        for value in ('javascript:alert(1)', 'data:text/html,evil', '/media/legacy.mp4', 'https://example.test/\x85', 'https://example.test/' + 'x' * 500):
            response = self.submit(value)
            self.assertEqual(response.status_code, 400)
            self.assertIn('file_url', response.data)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'WORKING')
        self.assertFalse(Deliverable.objects.filter(task=self.task).exists())
        self.assertEqual(AuditLog.objects.count(), before_audits)
        self.assertEqual(Notification.objects.count(), before_notifications)

    def test_domain_service_also_rejects_invalid_url_without_state_change(self):
        with self.assertRaises(ValidationError):
            submit_deliverable(actor=self.editor, profile_id=self.profile.pk, workspace_id=self.workspace.pk, task_id=self.task.pk, file_url='javascript:alert(1)')
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'WORKING')
        self.assertFalse(Deliverable.objects.filter(task=self.task).exists())

    def test_revision_link_history_and_review_workflow_are_independent(self):
        self.login(self.editor)
        first = self.submit('https://example.test/revision-1')
        self.assertEqual(first.status_code, 201)
        self.login(self.manager)
        changes = self.client.post(self.url('task-deliverable-request-changes', deliverable=first.data['id']), {'comment': 'Chỉnh màu'}, format='json')
        self.assertEqual(changes.status_code, 200)
        self.login(self.editor)
        second = self.submit('https://example.test/revision-2')
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.data['revision'], 2)
        self.login(self.manager)
        approved = self.client.post(self.url('task-deliverable-approve', deliverable=second.data['id']), {}, format='json')
        self.assertEqual(approved.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'COMPLETED')
        self.assertEqual(list(Deliverable.objects.filter(task=self.task).order_by('revision').values_list('file_url', flat=True)), ['https://example.test/revision-1', 'https://example.test/revision-2'])
        self.assertEqual(Review.objects.filter(deliverable__task=self.task).count(), 2)

    def test_existing_non_url_reference_remains_readable_and_unmodified(self):
        old = Deliverable.objects.create(task=self.task, file_url='/media/legacy video.mp4', uploaded_by=self.editor, revision=None, status='REJECTED')
        self.login(self.viewer)
        read = self.client.get(self.url('task-deliverable-list'))
        self.assertEqual(read.status_code, 200)
        self.assertEqual(next(row for row in read.data['results'] if str(row['id']) == str(old.pk))['file_url'], '/media/legacy video.mp4')
        self.login(self.editor)
        submitted = self.submit()
        self.assertEqual(submitted.status_code, 201)
        self.assertEqual(submitted.data['revision'], 1)
        old.refresh_from_db()
        self.assertEqual(old.file_url, '/media/legacy video.mp4')
        self.assertIsNone(old.revision)

    def test_unauthorized_submission_review_and_foreign_reference_remain_denied(self):
        self.login(self.editor)
        submitted = self.submit()
        self.assertEqual(submitted.status_code, 201)
        self.assertEqual(self.client.post(self.url('task-deliverable-approve', deliverable=submitted.data['id']), {}, format='json').status_code, 403)
        for actor in (self.viewer, self.next_editor, self.outsider):
            self.login(actor)
            self.assertIn(self.submit().status_code, (403, 404))
        for actor in (self.outsider, self.foreign):
            self.login(actor)
            response = self.client.get(self.url('task-deliverable-list'))
            self.assertEqual(response.status_code, 404)
            self.assertNotIn('drive.google.com', json.dumps(response.data, default=str))

    def test_submission_requires_csrf_and_replay_does_not_duplicate_revision(self):
        client = APIClient(enforce_csrf_checks=True)
        client.force_login(self.editor)
        self.assertEqual(client.post(self.url('task-deliverable-list'), {'file_url': 'https://example.test/revision'}, format='json').status_code, 403)
        self.login(self.editor)
        self.assertEqual(self.submit().status_code, 201)
        self.assertEqual(self.submit().status_code, 409)
        self.assertEqual(Deliverable.objects.filter(task=self.task).count(), 1)
