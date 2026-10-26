"""Hierarchy invariants and workflow isolation on the normal Task services."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase

from apps.audit.models import AuditLog
from apps.reviews.models import Deliverable, Review
from apps.workspace.access import TenantAccessNotFound
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
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


class TaskHierarchyServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        def user(suffix):
            return User.objects.create_user(
                email=f"hierarchy-{suffix}@example.test",
                username=f"hierarchy-{suffix}",
                password=None,
            )

        cls.owner = user("owner")
        cls.profile_admin = user("profile-admin")
        cls.workspace_admin = user("workspace-admin")
        cls.editor = user("editor")
        cls.viewer = user("viewer")
        cls.staff = user("staff")
        cls.other_owner = user("other-owner")
        cls.profile = create_profile_with_owner(name="Hierarchy Profile", owner=cls.owner)
        cls.workspace = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner, name="Hierarchy October",
            period=date(2026, 10, 1),
        )
        cls.other_workspace = Workspace.objects.create(
            profile=cls.profile, owner=cls.owner, name="Hierarchy November",
            period=date(2026, 11, 1),
        )
        for actor, profile_role, workspace_role in (
            (cls.profile_admin, ProfileMembership.Role.ADMIN, None),
            (cls.workspace_admin, ProfileMembership.Role.MEMBER, WorkspaceMember.Role.ADMIN),
            (cls.editor, ProfileMembership.Role.MEMBER, WorkspaceMember.Role.MEMBER),
            (cls.viewer, ProfileMembership.Role.MEMBER, WorkspaceMember.Role.VIEWER),
        ):
            membership = ProfileMembership.objects.create(
                profile=cls.profile, user=actor, role=profile_role,
            )
            if actor == cls.editor:
                cls.editor_membership = membership
            if workspace_role:
                WorkspaceMember.objects.create(
                    workspace=cls.workspace, user=actor, role=workspace_role,
                )
        cls.other_profile = create_profile_with_owner(
            name="Other Hierarchy Profile", owner=cls.other_owner,
        )
        cls.foreign_workspace = Workspace.objects.create(
            profile=cls.other_profile, owner=cls.other_owner,
            name="Foreign Hierarchy Workspace", period=date(2026, 10, 1),
        )

    def scope(self):
        return {"profile_id": self.profile.id, "workspace_id": self.workspace.id}

    def task(self, title="Hierarchy Task", **values):
        return create_task(actor=self.owner, title=title, **self.scope(), **values)

    def change(self, task, **values):
        return update_task(actor=self.owner, task_id=task.id, **self.scope(), **values)

    def working(self, task):
        assign_task(
            actor=self.owner, task_id=task.id,
            target_profile_membership_id=self.editor_membership.id, **self.scope(),
        )
        return start_task(actor=self.editor, task_id=task.id, **self.scope())

    def submit(self, task, revision="first"):
        return submit_deliverable(
            actor=self.editor, task_id=task.id, **self.scope(),
            file_url=f"https://files.example.test/hierarchy/{task.id}/{revision}",
        )

    def approve(self, task, deliverable, actor=None):
        return approve_deliverable(
            actor=actor or self.owner, task_id=task.id,
            deliverable_id=deliverable.id, **self.scope(),
        )

    def test_child_uses_own_defaults_without_inheriting_parent_fields(self):
        deadline = datetime(2026, 10, 25, 12, tzinfo=datetime_timezone.utc)
        parent = self.task(priority=Task.Priority.URGENT, deadline=deadline)
        child = self.task("Child", parent_id=parent.id)
        self.assertIsNone(parent.parent_id)
        self.assertEqual(child.parent_id, parent.id)
        self.assertEqual(child.workspace_id, parent.workspace_id)
        self.assertEqual(child.status, Task.Status.PENDING)
        self.assertEqual(child.priority, Task.Priority.MEDIUM)
        self.assertIsNone(child.deadline)
        self.assertFalse(TaskAssignment.objects.filter(task=child).exists())

    def test_creation_accepts_depth_three_and_rejects_depth_four(self):
        parent = self.task("Root")
        for depth in range(1, 4):
            parent = self.task(f"Depth {depth}", parent_id=parent.id)
        before = Task.objects.count()
        with self.assertRaises(ValidationError):
            self.task("Too deep", parent_id=parent.id)
        self.assertEqual(Task.objects.count(), before)

    def test_self_parent_is_rejected_by_service_and_model_validation(self):
        task = self.task()
        with self.assertRaises(ValidationError):
            self.change(task, parent_id=task.id)
        task.refresh_from_db()
        self.assertIsNone(task.parent_id)
        task.parent_id = task.id
        with self.assertRaises(ValidationError):
            task.full_clean()

    def test_ancestor_cannot_be_reparented_under_its_descendant(self):
        root = self.task("Root")
        child = self.task("Child", parent_id=root.id)
        leaf = self.task("Leaf", parent_id=child.id)
        with self.assertRaises(ValidationError):
            self.change(root, parent_id=leaf.id)
        root.refresh_from_db()
        self.assertIsNone(root.parent_id)
        self.assertEqual(Task.objects.filter(parent_id=root.id).count(), 1)

    def test_move_checks_depth_of_entire_existing_subtree(self):
        target = self.task("Target")
        target_child = self.task("Target child", parent_id=target.id)
        target_leaf = self.task("Target leaf", parent_id=target_child.id)
        moving = self.task("Moving root")
        descendant = self.task("Moving child", parent_id=moving.id)
        before = AuditLog.objects.filter(action="task.updated").count()
        with self.assertRaises(ValidationError):
            self.change(moving, parent_id=target_leaf.id)
        moving.refresh_from_db()
        descendant.refresh_from_db()
        self.assertIsNone(moving.parent_id)
        self.assertEqual(descendant.parent_id, moving.id)
        self.assertEqual(AuditLog.objects.filter(action="task.updated").count(), before)

    def test_detaching_child_preserves_its_subtree_and_metadata(self):
        root = self.task("Root")
        deadline = datetime(2026, 11, 12, tzinfo=datetime_timezone.utc)
        child = self.task("Child", parent_id=root.id, priority=Task.Priority.HIGH,
                          deadline=deadline)
        leaf = self.task("Leaf", parent_id=child.id)
        self.change(child, parent_id=None)
        child.refresh_from_db()
        leaf.refresh_from_db()
        self.assertIsNone(child.parent_id)
        self.assertEqual(leaf.parent_id, child.id)
        self.assertEqual(child.priority, Task.Priority.HIGH)
        self.assertEqual(child.deadline, deadline)
        self.assertEqual(child.status, Task.Status.PENDING)

    def test_missing_malformed_and_foreign_parents_use_same_not_found_boundary(self):
        sibling_parent = create_task(
            actor=self.owner, profile_id=self.profile.id,
            workspace_id=self.other_workspace.id, title="Other month",
        )
        foreign_parent = create_task(
            actor=self.other_owner, profile_id=self.other_profile.id,
            workspace_id=self.foreign_workspace.id, title="Other tenant",
        )
        child = self.task("Local child")
        before = Task.objects.count()
        for parent_id in (uuid4(), "not-a-uuid", sibling_parent.id, foreign_parent.id):
            with self.subTest(parent_id=parent_id):
                with self.assertRaises(TenantAccessNotFound):
                    self.task("Invalid child", parent_id=parent_id)
                with self.assertRaises(TenantAccessNotFound):
                    self.change(child, parent_id=parent_id)
        self.assertEqual(Task.objects.count(), before)
        child.refresh_from_db()
        self.assertIsNone(child.parent_id)

    def test_model_validation_rejects_cross_workspace_parent(self):
        parent = self.task()
        child = Task(
            workspace=self.other_workspace, parent=parent,
            title="Wrong Workspace", created_by=self.owner,
        )
        with self.assertRaises(ValidationError):
            child.full_clean()

    def test_foreign_task_id_cannot_be_updated_through_local_scope(self):
        foreign = create_task(
            actor=self.other_owner, profile_id=self.other_profile.id,
            workspace_id=self.foreign_workspace.id, title="Foreign Task",
        )
        with self.assertRaises(TenantAccessNotFound):
            self.change(foreign, priority=Task.Priority.URGENT)
        foreign.refresh_from_db()
        self.assertEqual(foreign.priority, Task.Priority.MEDIUM)

    def test_existing_manager_roles_can_manage_hierarchy(self):
        parent = self.task()
        for actor in (self.profile_admin, self.workspace_admin):
            with self.subTest(actor=actor.username):
                child = create_task(
                    actor=actor, title="Manager child", parent_id=parent.id,
                    **self.scope(),
                )
                updated = update_task(
                    actor=actor, task_id=child.id, parent_id=None,
                    priority=Task.Priority.HIGH, **self.scope(),
                )
                self.assertIsNone(updated.parent_id)
                self.assertEqual(updated.priority, Task.Priority.HIGH)

    def test_editor_and_viewer_cannot_create_or_reparent_or_raise_priority(self):
        parent = self.task("Parent")
        child = self.task("Child")
        for actor in (self.editor, self.viewer):
            with self.subTest(actor=actor.username):
                with self.assertRaises(PermissionDenied):
                    create_task(actor=actor, title="Denied", parent_id=parent.id,
                                **self.scope())
                with self.assertRaises(PermissionDenied):
                    update_task(actor=actor, task_id=child.id, parent_id=parent.id,
                                priority=Task.Priority.URGENT, **self.scope())
        child.refresh_from_db()
        self.assertIsNone(child.parent_id)
        self.assertEqual(child.priority, Task.Priority.MEDIUM)

    def test_staff_and_superuser_without_membership_do_not_bypass_tenant_boundary(self):
        parent = self.task()
        for superuser in (False, True):
            self.staff.is_staff = True
            self.staff.is_superuser = superuser
            self.staff.save(update_fields=("is_staff", "is_superuser"))
            with self.subTest(superuser=superuser):
                with self.assertRaises(TenantAccessNotFound):
                    create_task(actor=self.staff, title="Denied", parent_id=parent.id,
                                **self.scope())

    def test_archived_profile_and_workspace_block_hierarchy_writes(self):
        parent = self.task()
        for model, instance in ((Profile, self.profile), (Workspace, self.workspace)):
            model.objects.filter(pk=instance.pk).update(status=model.Status.ARCHIVED)
            with self.subTest(model=model.__name__):
                with self.assertRaises(PermissionDenied):
                    self.task("Denied child", parent_id=parent.id)
                with self.assertRaises(PermissionDenied):
                    self.change(parent, deadline=None, priority=Task.Priority.HIGH)
            model.objects.filter(pk=instance.pk).update(status=model.Status.ACTIVE)

    def test_inactive_account_profile_or_workspace_membership_fails_closed(self):
        task = self.task()
        predicates = (
            (User.objects.filter(pk=self.workspace_admin.pk), "is_active"),
            (ProfileMembership.objects.filter(profile=self.profile,
                                              user=self.workspace_admin), "is_active"),
            (WorkspaceMember.objects.filter(workspace=self.workspace,
                                            user=self.workspace_admin), "is_active"),
        )
        for queryset, field in predicates:
            queryset.update(**{field: False})
            self.workspace_admin.refresh_from_db()
            with self.subTest(model=queryset.model.__name__):
                with self.assertRaises(TenantAccessNotFound):
                    update_task(actor=self.workspace_admin, task_id=task.id,
                                parent_id=None, priority=Task.Priority.HIGH,
                                **self.scope())
            queryset.update(**{field: True})
            self.workspace_admin.refresh_from_db()

    def test_aware_deadline_roundtrips_and_can_be_cleared(self):
        deadline = datetime(2026, 10, 25, 20, 30,
                            tzinfo=datetime_timezone(timedelta(hours=7)))
        task = self.task(deadline=deadline)
        task.refresh_from_db()
        self.assertEqual(task.deadline, deadline.astimezone(datetime_timezone.utc))
        self.assertIsNotNone(task.deadline.utcoffset())
        self.change(task, deadline=None)
        task.refresh_from_db()
        self.assertIsNone(task.deadline)

    def test_naive_malformed_and_utc_overflow_deadlines_are_rejected(self):
        task = self.task()
        invalid_deadlines = (
            datetime(2026, 10, 25, 12),
            "invalid-datetime",
            datetime(1, 1, 1, tzinfo=datetime_timezone(timedelta(hours=14))),
        )
        for deadline in invalid_deadlines:
            with self.subTest(deadline=deadline):
                with self.assertRaises(ValidationError):
                    self.change(task, deadline=deadline)
        task.refresh_from_db()
        self.assertIsNone(task.deadline)

    def test_parent_and_child_deadlines_are_independent_and_overdue_does_not_change_state(self):
        parent_deadline = datetime(2020, 1, 1, tzinfo=datetime_timezone.utc)
        child_deadline = datetime(2030, 1, 1, tzinfo=datetime_timezone.utc)
        parent = self.task(deadline=parent_deadline)
        child = self.task("Child", parent_id=parent.id, deadline=child_deadline)
        self.change(parent, deadline=None, priority=Task.Priority.URGENT)
        child.refresh_from_db()
        parent.refresh_from_db()
        self.assertEqual(child.deadline, child_deadline)
        self.assertEqual(child.priority, Task.Priority.MEDIUM)
        self.assertEqual(parent.status, Task.Status.PENDING)
        self.assertEqual(child.status, Task.Status.PENDING)

    def test_invalid_priority_does_not_mutate_or_audit(self):
        task = self.task()
        before = AuditLog.objects.filter(action="task.updated").count()
        with self.assertRaises(ValidationError):
            self.change(task, priority="CRITICAL")
        with self.assertRaises(ValidationError):
            self.task(priority="CRITICAL")
        task.refresh_from_db()
        self.assertEqual(task.priority, Task.Priority.MEDIUM)
        self.assertEqual(AuditLog.objects.filter(action="task.updated").count(), before)

    def test_reparent_and_priority_changes_have_scoped_audit_metadata(self):
        parent = self.task("Parent")
        child = self.task("Child")
        self.change(child, parent_id=parent.id, priority=Task.Priority.HIGH)
        event = AuditLog.objects.get(action="task.updated", entity_id=child.id)
        self.assertEqual(set(event.metadata["changed_fields"]), {"parent", "priority"})
        self.assertIsNone(event.metadata["parent_id_before"])
        self.assertEqual(event.metadata["parent_id_after"], str(parent.id))
        self.assertEqual(event.metadata["profile_id"], str(self.profile.id))
        self.assertEqual(event.metadata["workspace_id"], str(self.workspace.id))

    def test_audit_failure_rolls_back_child_creation(self):
        parent = self.task()
        before = Task.objects.count()
        with patch("apps.tasks.services.AuditLog.objects.create",
                   side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.task("Rolled back child", parent_id=parent.id)
        self.assertEqual(Task.objects.count(), before)
        self.assertFalse(parent.subtasks.exists())

    def test_audit_failure_rolls_back_reparent_and_other_metadata(self):
        parent = self.task("Parent")
        child = self.task("Child")
        with patch("apps.tasks.services.AuditLog.objects.create",
                   side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.change(child, parent_id=parent.id, priority=Task.Priority.URGENT)
        child.refresh_from_db()
        self.assertIsNone(child.parent_id)
        self.assertEqual(child.priority, Task.Priority.MEDIUM)

    def test_parent_approval_does_not_complete_or_assign_unfinished_child(self):
        parent = self.task("Parent")
        child = self.task("Unfinished child", parent_id=parent.id)
        self.working(parent)
        deliverable = self.submit(parent)
        self.approve(parent, deliverable)
        parent.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual(parent.status, Task.Status.COMPLETED)
        self.assertEqual(child.status, Task.Status.PENDING)
        self.assertFalse(child.assignments.exists())
        self.assertFalse(child.deliverables.exists())

    def test_all_children_completed_do_not_implicitly_complete_parent(self):
        parent = self.task("Pending parent")
        child = self.task("Only child", parent_id=parent.id)
        self.working(child)
        self.approve(child, self.submit(child))
        parent.refresh_from_db()
        child.refresh_from_db()
        self.assertEqual(child.status, Task.Status.COMPLETED)
        self.assertEqual(parent.status, Task.Status.PENDING)
        self.assertFalse(parent.deliverables.exists())

    def test_child_revision_does_not_change_completed_parent_or_its_review(self):
        parent = self.task("Parent")
        child = self.task("Child", parent_id=parent.id)
        self.working(parent)
        parent_deliverable = self.submit(parent)
        parent_review = self.approve(parent, parent_deliverable)
        self.working(child)
        child_deliverable = self.submit(child)
        request_deliverable_changes(
            actor=self.owner, task_id=child.id, deliverable_id=child_deliverable.id,
            comment="Revise this child only.", **self.scope(),
        )
        child.refresh_from_db()
        parent.refresh_from_db()
        parent_deliverable.refresh_from_db()
        parent_review.refresh_from_db()
        self.assertEqual(child.status, Task.Status.WORKING)
        self.assertEqual(parent.status, Task.Status.COMPLETED)
        self.assertEqual(parent_deliverable.status, Deliverable.Status.APPROVED)
        self.assertEqual(parent_review.status, Review.Status.APPROVED)

    def test_reparent_in_review_preserves_deliverable_revision_and_approval_target(self):
        old_parent = self.task("Old parent")
        new_parent = self.task("New parent")
        child = self.task("Child", parent_id=old_parent.id, priority=Task.Priority.HIGH)
        self.working(child)
        deliverable = self.submit(child)
        self.change(child, parent_id=new_parent.id)
        deliverable.refresh_from_db()
        self.assertEqual(deliverable.task_id, child.id)
        self.assertEqual(deliverable.revision, 1)
        self.assertEqual(deliverable.status, Deliverable.Status.SUBMITTED)
        self.approve(child, deliverable)
        child.refresh_from_db()
        old_parent.refresh_from_db()
        new_parent.refresh_from_db()
        self.assertEqual(child.parent_id, new_parent.id)
        self.assertEqual(child.priority, Task.Priority.HIGH)
        self.assertEqual(child.status, Task.Status.COMPLETED)
        self.assertEqual(old_parent.status, Task.Status.PENDING)
        self.assertEqual(new_parent.status, Task.Status.PENDING)

    def test_child_keeps_self_review_and_reviewer_role_restrictions(self):
        parent = self.task()
        child = self.task("Child", parent_id=parent.id)
        self.working(child)
        deliverable = self.submit(child)
        with self.assertRaises(PermissionDenied):
            self.approve(child, deliverable, actor=self.viewer)
        ProfileMembership.objects.filter(pk=self.editor_membership.id).update(
            role=ProfileMembership.Role.ADMIN,
        )
        with self.assertRaises(PermissionDenied):
            self.approve(child, deliverable, actor=self.editor)
        child.refresh_from_db()
        self.assertEqual(child.status, Task.Status.REVIEW)
        self.assertFalse(Review.objects.filter(deliverable=deliverable).exists())

    def test_child_stale_approval_is_rejected_after_request_changes(self):
        parent = self.task()
        child = self.task("Child", parent_id=parent.id)
        self.working(child)
        first = self.submit(child)
        request_deliverable_changes(
            actor=self.owner, task_id=child.id, deliverable_id=first.id,
            comment="New revision required.", **self.scope(),
        )
        latest = self.submit(child, "second")
        with self.assertRaises(ValidationError):
            self.approve(child, first)
        self.approve(child, latest)
        child.refresh_from_db()
        parent.refresh_from_db()
        self.assertEqual(child.status, Task.Status.COMPLETED)
        self.assertEqual(parent.status, Task.Status.PENDING)
        self.assertEqual(latest.revision, 2)

    def test_database_check_rejects_self_parent_even_for_queryset_update(self):
        task = self.task()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Task.objects.filter(pk=task.id).update(parent_id=task.id)
        task.refresh_from_db()
        self.assertIsNone(task.parent_id)

    def test_parent_deletion_is_protected_without_deleting_descendants(self):
        parent = self.task()
        child = self.task("Child", parent_id=parent.id)
        with self.assertRaises(ProtectedError):
            parent.delete()
        self.assertTrue(Task.objects.filter(pk=parent.id).exists())
        self.assertTrue(Task.objects.filter(pk=child.id, parent_id=parent.id).exists())


class ConcurrentTaskHierarchyTests(TransactionTestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email="hierarchy-concurrent-owner@example.test",
            username="hierarchy-concurrent-owner", password=None,
        )
        self.profile = create_profile_with_owner(
            name="Concurrent Hierarchy Profile", owner=self.owner,
        )
        self.workspace = Workspace.objects.create(
            profile=self.profile, owner=self.owner,
            name="Concurrent Hierarchy Workspace", period=date(2026, 10, 1),
        )

    def task(self, title, parent_id=None):
        return create_task(
            actor=self.owner, profile_id=self.profile.id,
            workspace_id=self.workspace.id, title=title, parent_id=parent_id,
        )

    def race(self, changes):
        barrier = Barrier(2)

        def reparent(change):
            close_old_connections()
            try:
                # A lock-order regression must fail rather than hang the suite.
                with connection.cursor() as cursor:
                    cursor.execute("SET statement_timeout = '10s'")
                actor = User.objects.get(pk=self.owner.id)
                barrier.wait(timeout=10)
                task_id, parent_id = change
                task = update_task(
                    actor=actor, profile_id=self.profile.id,
                    workspace_id=self.workspace.id, task_id=task_id,
                    parent_id=parent_id,
                )
                return ("updated", task.id)
            except Exception as exc:
                return ("error", exc)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(reparent, change) for change in changes]
            results = [future.result(timeout=20) for future in futures]
        successes = [value for kind, value in results if kind == "updated"]
        errors = [value for kind, value in results if kind == "error"]
        self.assertEqual(len(successes), 1, results)
        self.assertEqual(len(errors), 1, results)
        self.assertIsInstance(errors[0], ValidationError)
        return successes

    def test_opposite_parent_changes_serialize_and_cannot_create_cycle(self):
        first = self.task("First root")
        second = self.task("Second root")
        self.race(((first.id, second.id), (second.id, first.id)))
        first.refresh_from_db()
        second.refresh_from_db()
        self.assertNotEqual(first.parent_id is None, second.parent_id is None)
        for task in (first, second):
            task.full_clean()
        self.assertEqual(AuditLog.objects.filter(
            action="task.updated", entity_id__in=(first.id, second.id),
        ).count(), 1)

    def test_concurrent_subtree_extension_and_move_cannot_exceed_depth_cap(self):
        root = self.task("Target root")
        level_one = self.task("Target one", parent_id=root.id)
        level_two = self.task("Target two", parent_id=level_one.id)
        moving = self.task("Moving root")
        extending = self.task("Extending root")
        # Each change is valid alone; together they would create depth four.
        self.race(((moving.id, level_two.id), (extending.id, moving.id)))
        for task in Task.objects.all():
            task.full_clean()
        self.assertEqual(AuditLog.objects.filter(
            action="task.updated", entity_id__in=(moving.id, extending.id),
        ).count(), 1)
