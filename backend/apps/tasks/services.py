from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.reviews.models import Deliverable, Review
from apps.workspace.access import (
    TenantAccessNotFound,
    can_execute_workspace_tasks,
    can_manage_workspace_tasks,
    can_review_workspace_deliverables,
)
from apps.workspace.models import ProfileMembership, WorkspaceMember
from apps.workspace.services import lock_workspace_mutation_context

from .models import Task, TaskAssignment


_UNSET = object()


class TaskWorkflowConflict(ValidationError):
    """A requested transition conflicts with the current workflow state."""

    default_message = "The requested operation conflicts with the Task state."

    def __init__(self, message=None, *, field="detail"):
        super().__init__({field: message or self.default_message})


class TaskAssignmentConflict(TaskWorkflowConflict):
    """An assignment cannot be applied to the current Task state."""


class DeliverableReviewConflict(TaskWorkflowConflict):
    """A Deliverable can no longer receive the requested review decision."""


class InvalidTaskAssignmentReference(ValidationError):
    """Keep invalid, inactive, and cross-tenant assignees indistinguishable."""

    default_message = "Invalid eligible Editor membership reference."

    def __init__(self):
        super().__init__({
            "target_profile_membership_id": self.default_message,
        })


def _lock_task(*, workspace, task_id):
    try:
        task = Task.objects.select_for_update().filter(
            id=task_id,
            workspace_id=workspace.id,
        ).first()
    except (TypeError, ValueError, ValidationError, AttributeError):
        raise TenantAccessNotFound() from None

    if task is None:
        raise TenantAccessNotFound()

    return task


def _lock_deliverable(*, task, deliverable_id):
    try:
        deliverable = Deliverable.objects.select_for_update().filter(
            id=deliverable_id,
            task_id=task.id,
        ).first()
    except (TypeError, ValueError, ValidationError, AttributeError):
        raise TenantAccessNotFound() from None

    if deliverable is None:
        raise TenantAccessNotFound()

    return deliverable


def _write_audit(*, actor, action, entity, profile_id, workspace_id, metadata):
    AuditLog.objects.create(
        user=actor,
        action=action,
        entity_name=entity.__class__.__name__,
        entity_id=entity.id,
        metadata={
            "profile_id": str(profile_id),
            "workspace_id": str(workspace_id),
            **metadata,
        },
    )


def _save_task_status(*, task, next_status):
    previous_status = task.status
    task.status = next_status
    task.full_clean()
    task.save(update_fields=("status", "updated_at"))
    return previous_status


def _require_manager(context):
    if not can_manage_workspace_tasks(context):
        raise PermissionDenied("Task management is not allowed.")


def _require_executor(context):
    if not can_execute_workspace_tasks(context):
        raise PermissionDenied("Task execution is not allowed.")


def _require_reviewer(context):
    if not can_review_workspace_deliverables(context):
        raise PermissionDenied("Internal Deliverable review is not allowed.")


def _lock_current_editor_assignment(*, task, actor):
    assignment = TaskAssignment.objects.select_for_update().filter(
        task_id=task.id,
        user_id=actor.id,
        is_active=True,
    ).first()
    if assignment is None:
        raise PermissionDenied("Only the currently assigned Editor may act.")
    return assignment


@transaction.atomic
def create_task(
    *,
    actor,
    profile_id,
    workspace_id,
    title,
    description=None,
    priority=Task.Priority.MEDIUM,
    deadline=None,
):
    context, workspace, _ = lock_workspace_mutation_context(
        actor=actor,
        profile_id=profile_id,
        workspace_id=workspace_id,
    )
    _require_manager(context)

    task = Task(
        workspace=workspace,
        title=(title or "").strip(),
        description=description,
        status=Task.Status.PENDING,
        priority=priority,
        deadline=deadline,
        created_by=actor,
    )
    task.full_clean()
    task.save()

    _write_audit(
        actor=actor,
        action="task.created",
        entity=task,
        profile_id=workspace.profile_id,
        workspace_id=workspace.id,
        metadata={
            "status": task.status,
            "priority": task.priority,
        },
    )
    return task


@transaction.atomic
def update_task(
    *,
    actor,
    profile_id,
    workspace_id,
    task_id,
    title=_UNSET,
    description=_UNSET,
    priority=_UNSET,
    deadline=_UNSET,
):
    context, workspace, _ = lock_workspace_mutation_context(
        actor=actor,
        profile_id=profile_id,
        workspace_id=workspace_id,
    )
    _require_manager(context)
    task = _lock_task(workspace=workspace, task_id=task_id)

    changed_fields = []
    if title is not _UNSET:
        normalized_title = (title or "").strip()
        if task.title != normalized_title:
            task.title = normalized_title
            changed_fields.append("title")
    if description is not _UNSET and task.description != description:
        task.description = description
        changed_fields.append("description")
    if priority is not _UNSET and task.priority != priority:
        task.priority = priority
        changed_fields.append("priority")
    if deadline is not _UNSET and task.deadline != deadline:
        task.deadline = deadline
        changed_fields.append("deadline")

    if not changed_fields:
        return task

    task.full_clean()
    task.save(update_fields=(*changed_fields, "updated_at"))
    _write_audit(
        actor=actor,
        action="task.updated",
        entity=task,
        profile_id=workspace.profile_id,
        workspace_id=workspace.id,
        metadata={"changed_fields": changed_fields},
    )
    return task


@transaction.atomic
def assign_task(
    *,
    actor,
    profile_id,
    workspace_id,
    task_id,
    target_profile_membership_id,
):
    context, workspace, _ = lock_workspace_mutation_context(
        actor=actor,
        profile_id=profile_id,
        workspace_id=workspace_id,
    )
    _require_manager(context)
    task = _lock_task(workspace=workspace, task_id=task_id)

    if task.status not in (
        Task.Status.PENDING,
        Task.Status.ASSIGNED,
        Task.Status.WORKING,
    ):
        raise TaskAssignmentConflict(
            "This Task cannot be assigned in its current state."
        )

    try:
        target_membership = (
            ProfileMembership.objects.select_for_update().filter(
                id=target_profile_membership_id,
                profile_id=workspace.profile_id,
                user__is_active=True,
                is_active=True,
                role=ProfileMembership.Role.MEMBER,
            ).first()
        )
    except (TypeError, ValueError, ValidationError, AttributeError):
        raise InvalidTaskAssignmentReference() from None

    if target_membership is None:
        raise InvalidTaskAssignmentReference()

    target_workspace_membership_id = (
        WorkspaceMember.objects.select_for_update().filter(
            workspace_id=workspace.id,
            user_id=target_membership.user_id,
            is_active=True,
            role=WorkspaceMember.Role.MEMBER,
        ).values_list("id", flat=True).first()
    )
    if target_workspace_membership_id is None:
        raise InvalidTaskAssignmentReference()

    active_assignment = TaskAssignment.objects.select_for_update().filter(
        task_id=task.id,
        is_active=True,
    ).first()
    if (
        active_assignment is not None
        and active_assignment.user_id == target_membership.user_id
    ):
        raise TaskAssignmentConflict(
            "This Editor is already the active Task assignee."
        )

    previous_assignment_id = None
    if active_assignment is not None:
        previous_assignment_id = active_assignment.id
        active_assignment.is_active = False
        active_assignment.save(update_fields=("is_active", "updated_at"))

    assignment = TaskAssignment.objects.select_for_update().filter(
        task_id=task.id,
        user_id=target_membership.user_id,
    ).first()
    assigned_at = timezone.now()
    if assignment is None:
        assignment = TaskAssignment(
            task=task,
            user_id=target_membership.user_id,
            is_active=True,
            assigned_at=assigned_at,
        )
        try:
            with transaction.atomic():
                assignment.full_clean()
                assignment.save()
        except IntegrityError:
            raise TaskAssignmentConflict(
                "The Task assignment changed concurrently; retry the request."
            ) from None
    else:
        assignment.is_active = True
        assignment.assigned_at = assigned_at
        try:
            with transaction.atomic():
                assignment.full_clean()
                assignment.save(
                    update_fields=(
                        "is_active",
                        "assigned_at",
                        "updated_at",
                    )
                )
        except IntegrityError:
            raise TaskAssignmentConflict(
                "The Task assignment changed concurrently; retry the request."
            ) from None

    previous_status = _save_task_status(
        task=task,
        next_status=Task.Status.ASSIGNED,
    )
    action = (
        "task.assigned"
        if previous_assignment_id is None
        else "task.reassigned"
    )
    _write_audit(
        actor=actor,
        action=action,
        entity=assignment,
        profile_id=workspace.profile_id,
        workspace_id=workspace.id,
        metadata={
            "task_id": str(task.id),
            "target_profile_membership_id": str(target_membership.id),
            "previous_assignment_id": (
                str(previous_assignment_id)
                if previous_assignment_id is not None
                else None
            ),
            "task_status_before": previous_status,
            "task_status_after": task.status,
        },
    )
    return assignment


@transaction.atomic
def start_task(*, actor, profile_id, workspace_id, task_id):
    context, workspace, _ = lock_workspace_mutation_context(
        actor=actor,
        profile_id=profile_id,
        workspace_id=workspace_id,
    )
    _require_executor(context)
    task = _lock_task(workspace=workspace, task_id=task_id)
    assignment = _lock_current_editor_assignment(task=task, actor=actor)

    if task.status != Task.Status.ASSIGNED:
        raise TaskWorkflowConflict(
            "Only an assigned Task can be started."
        )

    previous_status = _save_task_status(
        task=task,
        next_status=Task.Status.WORKING,
    )
    _write_audit(
        actor=actor,
        action="task.started",
        entity=task,
        profile_id=workspace.profile_id,
        workspace_id=workspace.id,
        metadata={
            "assignment_id": str(assignment.id),
            "status_before": previous_status,
            "status_after": task.status,
        },
    )
    return task


@transaction.atomic
def submit_deliverable(
    *,
    actor,
    profile_id,
    workspace_id,
    task_id,
    file_url,
):
    context, workspace, _ = lock_workspace_mutation_context(
        actor=actor,
        profile_id=profile_id,
        workspace_id=workspace_id,
    )
    _require_executor(context)
    task = _lock_task(workspace=workspace, task_id=task_id)
    assignment = _lock_current_editor_assignment(task=task, actor=actor)

    if task.status != Task.Status.WORKING:
        raise TaskWorkflowConflict(
            "A Deliverable can be submitted only while the Task is in progress."
        )

    if Deliverable.objects.select_for_update().filter(
        task_id=task.id,
        status__in=(Deliverable.Status.PENDING, Deliverable.Status.SUBMITTED),
    ).exists():
        raise TaskWorkflowConflict(
            "This Task already has an unresolved Deliverable."
        )

    latest_revision = Deliverable.objects.select_for_update().filter(
        task_id=task.id,
        revision__isnull=False,
    ).order_by("-revision").values_list("revision", flat=True).first()
    revision = (latest_revision or 0) + 1

    deliverable = Deliverable(
        task=task,
        file_url=(file_url or "").strip(),
        uploaded_by=actor,
        revision=revision,
        status=Deliverable.Status.SUBMITTED,
    )
    try:
        with transaction.atomic():
            deliverable.full_clean()
            deliverable.save()
    except IntegrityError:
        raise TaskWorkflowConflict(
            "The Deliverable history changed concurrently; retry the request."
        ) from None

    previous_status = _save_task_status(
        task=task,
        next_status=Task.Status.REVIEW,
    )
    _write_audit(
        actor=actor,
        action="task.deliverable.submitted",
        entity=deliverable,
        profile_id=workspace.profile_id,
        workspace_id=workspace.id,
        metadata={
            "task_id": str(task.id),
            "assignment_id": str(assignment.id),
            "revision": deliverable.revision,
            "deliverable_status": deliverable.status,
            "task_status_before": previous_status,
            "task_status_after": task.status,
        },
    )
    return deliverable


def _review_deliverable(
    *,
    actor,
    profile_id,
    workspace_id,
    task_id,
    deliverable_id,
    review_status,
    comment,
):
    context, workspace, _ = lock_workspace_mutation_context(
        actor=actor,
        profile_id=profile_id,
        workspace_id=workspace_id,
    )
    _require_reviewer(context)
    task = _lock_task(workspace=workspace, task_id=task_id)
    deliverable = _lock_deliverable(
        task=task,
        deliverable_id=deliverable_id,
    )

    if task.status != Task.Status.REVIEW:
        raise DeliverableReviewConflict(
            "This Task is not awaiting an internal review."
        )

    latest_deliverable = Deliverable.objects.select_for_update().filter(
        task_id=task.id,
    ).order_by("-created_at", "-id").first()
    if latest_deliverable is None or latest_deliverable.id != deliverable.id:
        raise DeliverableReviewConflict(
            "Only the latest Deliverable revision may be reviewed."
        )

    if deliverable.status != Deliverable.Status.SUBMITTED:
        raise DeliverableReviewConflict(
            "This Deliverable is not awaiting an internal review."
        )

    if deliverable.uploaded_by_id == actor.id:
        raise PermissionDenied(
            "A reviewer cannot review their own Deliverable."
        )

    if Review.objects.select_for_update().filter(
        deliverable_id=deliverable.id,
    ).exists():
        raise DeliverableReviewConflict(
            "This Deliverable already has an internal review decision."
        )

    review = Review(
        deliverable=deliverable,
        reviewer=actor,
        status=review_status,
        comment=comment,
    )
    try:
        with transaction.atomic():
            review.full_clean()
            review.save()
    except IntegrityError:
        raise DeliverableReviewConflict(
            "This Deliverable already has an internal review decision."
        ) from None

    task_status_before = task.status
    deliverable_status_before = deliverable.status
    if review_status == Review.Status.APPROVED:
        deliverable.status = Deliverable.Status.APPROVED
        next_task_status = Task.Status.COMPLETED
        action = "task.deliverable.approved"
    else:
        deliverable.status = Deliverable.Status.REJECTED
        next_task_status = Task.Status.WORKING
        action = "task.deliverable.changes_requested"

    deliverable.full_clean()
    deliverable.save(update_fields=("status", "updated_at"))
    _save_task_status(task=task, next_status=next_task_status)

    _write_audit(
        actor=actor,
        action=action,
        entity=review,
        profile_id=workspace.profile_id,
        workspace_id=workspace.id,
        metadata={
            "task_id": str(task.id),
            "deliverable_id": str(deliverable.id),
            "revision": deliverable.revision,
            "review_scope": "INTERNAL",
            "review_status": review.status,
            "deliverable_status_before": deliverable_status_before,
            "deliverable_status_after": deliverable.status,
            "task_status_before": task_status_before,
            "task_status_after": task.status,
        },
    )
    return review


@transaction.atomic
def approve_deliverable(
    *,
    actor,
    profile_id,
    workspace_id,
    task_id,
    deliverable_id,
    comment=None,
):
    normalized_comment = None
    if comment is not None:
        normalized_comment = str(comment).strip() or None

    return _review_deliverable(
        actor=actor,
        profile_id=profile_id,
        workspace_id=workspace_id,
        task_id=task_id,
        deliverable_id=deliverable_id,
        review_status=Review.Status.APPROVED,
        comment=normalized_comment,
    )


@transaction.atomic
def request_deliverable_changes(
    *,
    actor,
    profile_id,
    workspace_id,
    task_id,
    deliverable_id,
    comment,
):
    normalized_comment = str(comment or "").strip()
    if not normalized_comment:
        raise ValidationError({
            "comment": "A reason is required when requesting changes."
        })

    return _review_deliverable(
        actor=actor,
        profile_id=profile_id,
        workspace_id=workspace_id,
        task_id=task_id,
        deliverable_id=deliverable_id,
        review_status=Review.Status.REQUEST_CHANGE,
        comment=normalized_comment,
    )
