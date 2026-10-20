from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase

from apps.audit.models import AuditLog
from apps.reviews.models import Deliverable, Review
from apps.workspace.access import TenantAccessNotFound
from apps.workspace.models import ProfileMembership, Workspace, WorkspaceMember
from apps.workspace.services import create_profile_with_owner

from .models import Task, TaskAssignment
from .services import (
    approve_deliverable,
    assign_task,
    create_task,
    request_deliverable_changes,
    start_task,
    submit_deliverable,
    update_task,
)


User = get_user_model()


class TaskWorkflowServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = cls._create_user("owner")
        cls.profile_admin = cls._create_user("profile-admin")
        cls.workspace_admin = cls._create_user("workspace-admin")
        cls.editor = cls._create_user("editor")
        cls.second_editor = cls._create_user("second-editor")
        cls.viewer = cls._create_user("viewer")
        cls.revoked_editor = cls._create_user("revoked-editor")
        cls.other_owner = cls._create_user("other-owner")
        cls.other_editor = cls._create_user("other-editor")

        cls.profile = create_profile_with_owner(
            name="Task Services Profile",
            owner=cls.owner,
        )
        cls.owner_membership = ProfileMembership.objects.get(
            profile=cls.profile,
            user=cls.owner,
        )
        cls.profile_admin_membership = cls._profile_membership(
            cls.profile_admin,
            role=ProfileMembership.Role.ADMIN,
        )
        cls.workspace_admin_membership = cls._profile_membership(
            cls.workspace_admin
        )
        cls.editor_membership = cls._profile_membership(cls.editor)
        cls.second_editor_membership = cls._profile_membership(
            cls.second_editor
        )
        cls.viewer_membership = cls._profile_membership(cls.viewer)
        cls.revoked_editor_membership = cls._profile_membership(
            cls.revoked_editor
        )

        cls.workspace = Workspace.objects.create(
            profile=cls.profile,
            owner=cls.owner,
            name="Task Services Workspace",
            period=date(2026, 10, 1),
        )
        cls.sibling_workspace = Workspace.objects.create(
            profile=cls.profile,
            owner=cls.owner,
            name="Sibling Workspace",
            period=date(2026, 11, 1),
        )
        WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.workspace_admin,
            role=WorkspaceMember.Role.ADMIN,
        )
        WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.editor,
            role=WorkspaceMember.Role.MEMBER,
        )
        WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.second_editor,
            role=WorkspaceMember.Role.MEMBER,
        )
        WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.viewer,
            role=WorkspaceMember.Role.VIEWER,
        )
        WorkspaceMember.objects.create(
            workspace=cls.workspace,
            user=cls.revoked_editor,
            role=WorkspaceMember.Role.MEMBER,
            is_active=False,
        )

        cls.other_profile = create_profile_with_owner(
            name="Other Task Services Profile",
            owner=cls.other_owner,
        )
        cls.other_editor_membership = ProfileMembership.objects.create(
            profile=cls.other_profile,
            user=cls.other_editor,
            role=ProfileMembership.Role.MEMBER,
        )
        cls.other_workspace = Workspace.objects.create(
            profile=cls.other_profile,
            owner=cls.other_owner,
            name="Other Task Services Workspace",
            period=date(2026, 10, 1),
        )
        WorkspaceMember.objects.create(
            workspace=cls.other_workspace,
            user=cls.other_editor,
            role=WorkspaceMember.Role.MEMBER,
        )

    @classmethod
    def _create_user(cls, suffix):
        return User.objects.create_user(
            email=f"task-services-{suffix}@example.test",
            username=f"task-services-{suffix}",
            password=None,
        )

    @classmethod
    def _profile_membership(
        cls,
        user,
        *,
        role=ProfileMembership.Role.MEMBER,
    ):
        return ProfileMembership.objects.create(
            profile=cls.profile,
            user=user,
            role=role,
        )

    def scope(self, **extra):
        values = {
            "profile_id": self.profile.id,
            "workspace_id": self.workspace.id,
        }
        values.update(extra)
        return values

    def create_pending_task(self, *, title="Service Task"):
        return create_task(
            actor=self.owner,
            title=title,
            **self.scope(),
        )

    def prepare_working_task(self):
        task = self.create_pending_task()
        assign_task(
            actor=self.owner,
            task_id=task.id,
            target_profile_membership_id=self.editor_membership.id,
            **self.scope(),
        )
        return start_task(
            actor=self.editor,
            task_id=task.id,
            **self.scope(),
        )

    def test_create_and_update_are_manager_scoped_and_audited(self):
        task = create_task(
            actor=self.owner,
            title="  Managed Task  ",
            description="Initial description",
            priority=Task.Priority.HIGH,
            **self.scope(),
        )

        self.assertEqual(task.workspace, self.workspace)
        self.assertEqual(task.created_by, self.owner)
        self.assertEqual(task.title, "Managed Task")
        self.assertEqual(task.status, Task.Status.PENDING)
        self.assertTrue(
            AuditLog.objects.filter(
                action="task.created",
                entity_id=task.id,
                user=self.owner,
            ).exists()
        )

        updated = update_task(
            actor=self.workspace_admin,
            task_id=task.id,
            description="Updated by Workspace Admin",
            priority=Task.Priority.URGENT,
            **self.scope(),
        )

        self.assertEqual(updated.description, "Updated by Workspace Admin")
        self.assertEqual(updated.priority, Task.Priority.URGENT)
        self.assertEqual(updated.status, Task.Status.PENDING)
        self.assertTrue(
            AuditLog.objects.filter(
                action="task.updated",
                entity_id=task.id,
                user=self.workspace_admin,
            ).exists()
        )

        for actor in (self.editor, self.viewer):
            with self.subTest(actor=actor.username):
                with self.assertRaises(PermissionDenied):
                    update_task(
                        actor=actor,
                        task_id=task.id,
                        title="Forbidden",
                        **self.scope(),
                    )

    def test_assign_and_reassign_keep_exactly_one_active_editor(self):
        task = self.create_pending_task()

        first = assign_task(
            actor=self.profile_admin,
            task_id=task.id,
            target_profile_membership_id=self.editor_membership.id,
            **self.scope(),
        )
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.ASSIGNED)
        self.assertTrue(first.is_active)
        self.assertEqual(first.user, self.editor)

        second = assign_task(
            actor=self.workspace_admin,
            task_id=task.id,
            target_profile_membership_id=self.second_editor_membership.id,
            **self.scope(),
        )
        first.refresh_from_db()
        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)
        self.assertEqual(second.user, self.second_editor)
        self.assertEqual(
            TaskAssignment.objects.filter(task=task, is_active=True).count(),
            1,
        )
        self.assertEqual(
            AuditLog.objects.filter(
                action__in=("task.assigned", "task.reassigned"),
                metadata__task_id=str(task.id),
            ).count(),
            2,
        )

    def test_assignment_rejects_viewer_revoked_and_cross_profile_targets(self):
        task = self.create_pending_task()

        invalid_memberships = (
            self.viewer_membership,
            self.revoked_editor_membership,
            self.other_editor_membership,
        )
        for membership in invalid_memberships:
            with self.subTest(membership=membership.id):
                with self.assertRaises(ValidationError):
                    assign_task(
                        actor=self.owner,
                        task_id=task.id,
                        target_profile_membership_id=membership.id,
                        **self.scope(),
                    )

        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.PENDING)
        self.assertFalse(TaskAssignment.objects.filter(task=task).exists())

    def test_only_current_assigned_editor_can_start(self):
        task = self.create_pending_task()
        assign_task(
            actor=self.owner,
            task_id=task.id,
            target_profile_membership_id=self.editor_membership.id,
            **self.scope(),
        )

        with self.assertRaises(PermissionDenied):
            start_task(
                actor=self.second_editor,
                task_id=task.id,
                **self.scope(),
            )

        started = start_task(
            actor=self.editor,
            task_id=task.id,
            **self.scope(),
        )
        self.assertEqual(started.status, Task.Status.WORKING)
        self.assertTrue(
            AuditLog.objects.filter(
                action="task.started",
                entity_id=task.id,
                user=self.editor,
            ).exists()
        )

        with self.assertRaises(ValidationError):
            start_task(
                actor=self.editor,
                task_id=task.id,
                **self.scope(),
            )

    def test_request_changes_resubmit_and_approve_complete_internal_flow(self):
        task = self.prepare_working_task()
        first = submit_deliverable(
            actor=self.editor,
            task_id=task.id,
            file_url="https://files.example.test/task/revision-1",
            **self.scope(),
        )
        task.refresh_from_db()
        self.assertEqual(first.revision, 1)
        self.assertEqual(first.status, Deliverable.Status.SUBMITTED)
        self.assertEqual(task.status, Task.Status.REVIEW)

        first_review = request_deliverable_changes(
            actor=self.workspace_admin,
            task_id=task.id,
            deliverable_id=first.id,
            comment="Please revise the opening section.",
            **self.scope(),
        )
        first.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(first.status, Deliverable.Status.REJECTED)
        self.assertEqual(first_review.status, Review.Status.REQUEST_CHANGE)
        self.assertEqual(task.status, Task.Status.WORKING)

        second = submit_deliverable(
            actor=self.editor,
            task_id=task.id,
            file_url="https://files.example.test/task/revision-2",
            **self.scope(),
        )
        self.assertEqual(second.revision, 2)

        second_review = approve_deliverable(
            actor=self.profile_admin,
            task_id=task.id,
            deliverable_id=second.id,
            comment="Internal approval complete.",
            **self.scope(),
        )
        second.refresh_from_db()
        task.refresh_from_db()
        self.assertEqual(second.status, Deliverable.Status.APPROVED)
        self.assertEqual(second_review.status, Review.Status.APPROVED)
        self.assertEqual(task.status, Task.Status.COMPLETED)
        self.assertEqual(task.deliverables.count(), 2)
        self.assertEqual(
            AuditLog.objects.filter(
                action__in=(
                    "task.deliverable.submitted",
                    "task.deliverable.changes_requested",
                    "task.deliverable.approved",
                ),
                metadata__task_id=str(task.id),
            ).count(),
            4,
        )

    def test_self_review_stale_review_and_repeated_review_are_denied(self):
        task = self.prepare_working_task()
        first = submit_deliverable(
            actor=self.editor,
            task_id=task.id,
            file_url="https://files.example.test/task/self-review",
            **self.scope(),
        )

        ProfileMembership.objects.filter(
            id=self.editor_membership.id
        ).update(role=ProfileMembership.Role.ADMIN)
        with self.assertRaises(PermissionDenied):
            approve_deliverable(
                actor=self.editor,
                task_id=task.id,
                deliverable_id=first.id,
                **self.scope(),
            )
        ProfileMembership.objects.filter(
            id=self.editor_membership.id
        ).update(role=ProfileMembership.Role.MEMBER)

        request_deliverable_changes(
            actor=self.owner,
            task_id=task.id,
            deliverable_id=first.id,
            comment="A revision is required.",
            **self.scope(),
        )
        second = submit_deliverable(
            actor=self.editor,
            task_id=task.id,
            file_url="https://files.example.test/task/current-revision",
            **self.scope(),
        )

        with self.assertRaises(ValidationError):
            approve_deliverable(
                actor=self.owner,
                task_id=task.id,
                deliverable_id=first.id,
                **self.scope(),
            )

        approve_deliverable(
            actor=self.owner,
            task_id=task.id,
            deliverable_id=second.id,
            **self.scope(),
        )
        with self.assertRaises(ValidationError):
            approve_deliverable(
                actor=self.owner,
                task_id=task.id,
                deliverable_id=second.id,
                **self.scope(),
            )

    def test_revoked_editor_and_archived_tenant_fail_closed(self):
        task = self.create_pending_task()
        assign_task(
            actor=self.owner,
            task_id=task.id,
            target_profile_membership_id=self.editor_membership.id,
            **self.scope(),
        )
        WorkspaceMember.objects.filter(
            workspace=self.workspace,
            user=self.editor,
        ).update(is_active=False)

        with self.assertRaises(TenantAccessNotFound):
            start_task(
                actor=self.editor,
                task_id=task.id,
                **self.scope(),
            )

        Workspace.objects.filter(id=self.workspace.id).update(
            status=Workspace.Status.ARCHIVED
        )
        with self.assertRaises(PermissionDenied):
            create_task(
                actor=self.owner,
                title="Blocked by archived Workspace",
                **self.scope(),
            )

        Workspace.objects.filter(id=self.workspace.id).update(
            status=Workspace.Status.ACTIVE
        )
        self.profile.__class__.objects.filter(id=self.profile.id).update(
            status=self.profile.Status.ARCHIVED
        )
        with self.assertRaises(PermissionDenied):
            create_task(
                actor=self.owner,
                title="Blocked by archived Profile",
                **self.scope(),
            )

    def test_wrong_workspace_scope_does_not_resolve_task(self):
        task = self.create_pending_task()

        with self.assertRaises(TenantAccessNotFound):
            update_task(
                actor=self.owner,
                profile_id=self.profile.id,
                workspace_id=self.sibling_workspace.id,
                task_id=task.id,
                title="Wrong parent",
            )

    def test_audit_failure_rolls_back_assignment_and_state(self):
        task = self.create_pending_task()

        with patch(
            "apps.tasks.services.AuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                assign_task(
                    actor=self.owner,
                    task_id=task.id,
                    target_profile_membership_id=self.editor_membership.id,
                    **self.scope(),
                )

        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.PENDING)
        self.assertFalse(TaskAssignment.objects.filter(task=task).exists())

    def test_audit_failure_rolls_back_internal_approval_and_completion(self):
        task = self.prepare_working_task()
        deliverable = submit_deliverable(
            actor=self.editor,
            task_id=task.id,
            file_url="https://files.example.test/task/approval-rollback",
            **self.scope(),
        )

        with patch(
            "apps.tasks.services.AuditLog.objects.create",
            side_effect=RuntimeError("audit unavailable"),
        ):
            with self.assertRaises(RuntimeError):
                approve_deliverable(
                    actor=self.owner,
                    task_id=task.id,
                    deliverable_id=deliverable.id,
                    **self.scope(),
                )

        task.refresh_from_db()
        deliverable.refresh_from_db()
        self.assertEqual(task.status, Task.Status.REVIEW)
        self.assertEqual(deliverable.status, Deliverable.Status.SUBMITTED)
        self.assertFalse(
            Review.objects.filter(deliverable=deliverable).exists()
        )


class ConcurrentTaskReviewServiceTests(TransactionTestCase):
    reset_sequences = False

    def setUp(self):
        self.owner = self.create_user("owner")
        self.profile_admin = self.create_user("profile-admin")
        self.editor = self.create_user("editor")
        self.second_editor = self.create_user("second-editor")
        self.profile = create_profile_with_owner(
            name="Concurrent Review Profile",
            owner=self.owner,
        )
        ProfileMembership.objects.create(
            profile=self.profile,
            user=self.profile_admin,
            role=ProfileMembership.Role.ADMIN,
        )
        self.editor_membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=self.editor,
            role=ProfileMembership.Role.MEMBER,
        )
        self.second_editor_membership = ProfileMembership.objects.create(
            profile=self.profile,
            user=self.second_editor,
            role=ProfileMembership.Role.MEMBER,
        )
        self.workspace = Workspace.objects.create(
            profile=self.profile,
            owner=self.owner,
            name="Concurrent Review Workspace",
            period=date(2026, 12, 1),
        )
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.editor,
            role=WorkspaceMember.Role.MEMBER,
        )
        WorkspaceMember.objects.create(
            workspace=self.workspace,
            user=self.second_editor,
            role=WorkspaceMember.Role.MEMBER,
        )

        self.task = create_task(
            actor=self.owner,
            profile_id=self.profile.id,
            workspace_id=self.workspace.id,
            title="Concurrent approval",
        )
        assign_task(
            actor=self.owner,
            profile_id=self.profile.id,
            workspace_id=self.workspace.id,
            task_id=self.task.id,
            target_profile_membership_id=self.editor_membership.id,
        )
        start_task(
            actor=self.editor,
            profile_id=self.profile.id,
            workspace_id=self.workspace.id,
            task_id=self.task.id,
        )
        self.deliverable = submit_deliverable(
            actor=self.editor,
            profile_id=self.profile.id,
            workspace_id=self.workspace.id,
            task_id=self.task.id,
            file_url="https://files.example.test/task/concurrent",
        )

    @staticmethod
    def create_user(suffix):
        return User.objects.create_user(
            email=f"task-concurrent-{suffix}@example.test",
            username=f"task-concurrent-{suffix}",
            password=None,
        )

    def test_concurrent_review_creates_one_decision_and_one_completion(self):
        barrier = Barrier(2)

        def approve(actor_id):
            close_old_connections()
            try:
                actor = User.objects.get(id=actor_id)
                barrier.wait(timeout=10)
                review = approve_deliverable(
                    actor=actor,
                    profile_id=self.profile.id,
                    workspace_id=self.workspace.id,
                    task_id=self.task.id,
                    deliverable_id=self.deliverable.id,
                )
                return ("approved", review.id)
            except Exception as exc:  # Returned for an assertion in main thread.
                return ("error", exc)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    approve,
                    (self.owner.id, self.profile_admin.id),
                )
            )

        approved = [value for kind, value in results if kind == "approved"]
        errors = [value for kind, value in results if kind == "error"]
        self.assertEqual(len(approved), 1)
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], ValidationError)

        self.task.refresh_from_db()
        self.deliverable.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.COMPLETED)
        self.assertEqual(self.deliverable.status, Deliverable.Status.APPROVED)
        self.assertEqual(
            Review.objects.filter(deliverable=self.deliverable).count(),
            1,
        )
        self.assertEqual(
            AuditLog.objects.filter(
                action="task.deliverable.approved",
                metadata__task_id=str(self.task.id),
            ).count(),
            1,
        )

    def test_concurrent_assignment_preserves_one_active_editor(self):
        task = create_task(
            actor=self.owner,
            profile_id=self.profile.id,
            workspace_id=self.workspace.id,
            title="Concurrent assignment",
        )
        barrier = Barrier(2)

        def assign(actor_id, target_membership_id):
            close_old_connections()
            try:
                actor = User.objects.get(id=actor_id)
                barrier.wait(timeout=10)
                assignment = assign_task(
                    actor=actor,
                    profile_id=self.profile.id,
                    workspace_id=self.workspace.id,
                    task_id=task.id,
                    target_profile_membership_id=target_membership_id,
                )
                return ("assigned", assignment.id)
            except Exception as exc:  # Returned for an assertion in main thread.
                return ("error", exc)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = (
                executor.submit(
                    assign,
                    self.owner.id,
                    self.editor_membership.id,
                ),
                executor.submit(
                    assign,
                    self.profile_admin.id,
                    self.second_editor_membership.id,
                ),
            )
            results = [future.result(timeout=20) for future in futures]

        self.assertEqual(
            [kind for kind, _ in results],
            ["assigned", "assigned"],
        )
        self.assertEqual(TaskAssignment.objects.filter(task=task).count(), 2)
        self.assertEqual(
            TaskAssignment.objects.filter(task=task, is_active=True).count(),
            1,
        )
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.ASSIGNED)
        self.assertEqual(
            AuditLog.objects.filter(
                action__in=("task.assigned", "task.reassigned"),
                metadata__task_id=str(task.id),
            ).count(),
            2,
        )
