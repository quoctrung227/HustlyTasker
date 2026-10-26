"""Tenant-scoped discussion writes, independent of Task review decisions."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.workspace.access import (
    TenantAccessNotFound, can_execute_workspace_tasks, can_manage_workspace_tasks,
)
from apps.workspace.models import ProfileMembership
from apps.workspace.services import lock_workspace_mutation_context

from .access import tasks_visible_to
from .models import TaskComment
from .services import TaskWorkflowConflict, _lock_task


def can_comment_on_task(context):
    return can_manage_workspace_tasks(context) or can_execute_workspace_tasks(context)


def comments_visible_to(context, task_id):
    scoped_task_ids = tasks_visible_to(context).filter(id=task_id).values("id")
    current_author_membership = ProfileMembership.objects.filter(
        profile_id=context.profile_id, user_id=OuterRef("user_id"),
        user__is_active=True, is_active=True,
    ).order_by("joined_at", "id").values("id")[:1]
    return TaskComment.objects.filter(task_id__in=scoped_task_ids).select_related(
        "task__workspace",
    ).annotate(_author_profile_membership_id=Subquery(current_author_membership))


def _content(value):
    if not isinstance(value, str) or not value.strip():
        raise ValidationError({"content": "A non-blank text comment is required."})
    try:
        value.encode("utf-8", errors="strict")
    except UnicodeEncodeError:
        raise ValidationError({"content": "Comment must contain valid Unicode text."}) from None
    if "\x00" in value:
        raise ValidationError({"content": "Comment cannot contain null characters."})
    value = value.strip()
    if len(value) > TaskComment.CONTENT_MAX_LENGTH:
        raise ValidationError({"content": "Comments may contain at most 4000 characters."})
    return value


def _lock_comment(*, task, comment_id):
    try:
        comment = TaskComment.objects.select_for_update().filter(pk=comment_id, task_id=task.id).first()
    except (TypeError, ValueError, ValidationError, AttributeError):
        raise TenantAccessNotFound() from None
    if comment is None:
        raise TenantAccessNotFound()
    comment.task = task
    return comment


def _mutation_scope(*, actor, profile_id, workspace_id, task_id):
    context, workspace, _ = lock_workspace_mutation_context(
        actor=actor, profile_id=profile_id, workspace_id=workspace_id,
    )
    task = _lock_task(workspace=workspace, task_id=task_id)
    if not can_comment_on_task(context):
        raise PermissionDenied("Task discussion changes are not allowed.")
    task.workspace = workspace
    return context, task


def _audit(*, actor, comment, action):
    return AuditLog.objects.create(
        user=actor, action=action, entity_name="TaskComment", entity_id=comment.id,
        metadata={"profile_id": str(comment.task.workspace.profile_id),
                  "workspace_id": str(comment.task.workspace_id),
                  "task_id": str(comment.task_id), "comment_id": str(comment.id)},
    )


@transaction.atomic
def create_comment(*, actor, profile_id, workspace_id, task_id, content):
    _, task = _mutation_scope(actor=actor, profile_id=profile_id, workspace_id=workspace_id, task_id=task_id)
    comment = TaskComment(task=task, user=actor, content=_content(content))
    comment.full_clean()
    comment.save()
    event = _audit(actor=actor, comment=comment, action="task.comment.created")
    from apps.notifications.models import Notification
    from apps.notifications.services import emit_task_notifications
    emit_task_notifications(event=event, actor=actor, task=task,
                            event_type=Notification.EventType.TASK_COMMENTED)
    return comment


@transaction.atomic
def update_comment(*, actor, profile_id, workspace_id, task_id, comment_id, content):
    _, task = _mutation_scope(actor=actor, profile_id=profile_id, workspace_id=workspace_id, task_id=task_id)
    comment = _lock_comment(task=task, comment_id=comment_id)
    if comment.user_id != actor.id:
        raise PermissionDenied("Only the current author may edit a comment.")
    if comment.deleted_at is not None:
        raise TaskWorkflowConflict("A deleted comment cannot be edited.")
    normalized = _content(content)
    if comment.content == normalized:
        return comment
    comment.content = normalized
    comment.edited_at = timezone.now()
    comment.full_clean()
    comment.save(update_fields=("content", "edited_at", "updated_at"))
    _audit(actor=actor, comment=comment, action="task.comment.updated")
    return comment


@transaction.atomic
def delete_comment(*, actor, profile_id, workspace_id, task_id, comment_id):
    context, task = _mutation_scope(actor=actor, profile_id=profile_id, workspace_id=workspace_id, task_id=task_id)
    comment = _lock_comment(task=task, comment_id=comment_id)
    if comment.user_id != actor.id and not can_manage_workspace_tasks(context):
        raise PermissionDenied("Comment moderation is not allowed.")
    if comment.deleted_at is not None:
        return comment
    comment.deleted_at = timezone.now()
    # Historical oversized text is retained; deletion validates lifecycle only.
    comment.full_clean(exclude=("content",))
    comment.save(update_fields=("deleted_at", "updated_at"))
    _audit(actor=actor, comment=comment, action="task.comment.deleted")
    return comment
