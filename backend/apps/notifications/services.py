"""Atomic database notifications, integrated explicitly with successful events."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Exists, OuterRef, Q

from apps.audit.models import AuditLog
from apps.reviews.models import Deliverable, Review
from apps.tasks.models import Task, TaskAssignment, TaskComment
from apps.workspace.access import (
    TenantAccessNotFound, resolve_profile_access_context, resolve_workspace_access_context,
)
from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember

from .access import notifications_visible_to, readable_memberships
from .content import EVENT_CONTENT
from .models import Notification


EVENT_ACTIONS = {
    "TASK_ASSIGNED": ("task.assigned", "task.reassigned"),
    "REVIEW_SUBMITTED": ("task.deliverable.submitted",),
    "REVIEW_APPROVED": ("task.deliverable.approved",),
    "REVIEW_CHANGES_REQUESTED": ("task.deliverable.changes_requested",),
    "TASK_COMMENTED": ("task.comment.created",),
}


@transaction.atomic
def emit_task_notifications(*, event, actor, task, event_type, deliverable=None):
    """Failures propagate to the enclosing business/audit transaction.

    No best-effort callback, email, signal or second event mechanism exists.
    Repeated delivery of an already-persisted event retains existing read state.
    """
    if event_type not in EVENT_ACTIONS or not isinstance(event, AuditLog):
        raise ValidationError("Invalid notification event.")
    if event._state.adding:
        raise ValidationError("Notification event must already be persisted.")
    event = AuditLog.objects.filter(pk=event.pk).first()
    canonical = Task.objects.filter(pk=task.pk).values(
        "workspace_id", "workspace__profile_id",
    ).first()
    if event is None or canonical is None or not canonical["workspace__profile_id"]:
        raise ValidationError("Invalid notification event target.")
    profile_id = canonical["workspace__profile_id"]
    profile = Profile.objects.select_for_update().filter(pk=profile_id).first()
    workspace = Workspace.objects.select_for_update().filter(
        pk=canonical["workspace_id"], profile_id=profile_id,
    ).first()
    task = Task.objects.filter(pk=task.pk, workspace_id=canonical["workspace_id"]).first()
    if profile is None or workspace is None or task is None:
        raise ValidationError("Invalid notification event target.")
    task.workspace = workspace
    if (event.action not in EVENT_ACTIONS[event_type]
        or event.user_id != actor.pk
        or event.metadata.get("profile_id") != str(profile_id)
        or event.metadata.get("workspace_id") != str(task.workspace_id)
        or event.metadata.get("task_id") != str(task.pk)):
        raise ValidationError("Notification event does not match its Task context.")
    recipients = readable_memberships(profile_id=profile_id, workspace_id=task.workspace_id)
    if (profile.status != Profile.Status.ACTIVE or workspace.status != Workspace.Status.ACTIVE
        or not recipients.filter(user_id=actor.pk).exists()):
        # Historical replay cannot create notifications after eligibility ends.
        return []
    if event_type == Notification.EventType.TASK_ASSIGNED:
        if event.entity_name != "TaskAssignment":
            raise ValidationError("Assignment event must identify its assignment.")
        assignment = TaskAssignment.objects.filter(
            pk=event.entity_id, task_id=task.pk, is_active=True,
        ).first()
        if assignment is None:
            return []
        recipients = recipients.filter(
            user_id=assignment.user_id, role=ProfileMembership.Role.MEMBER,
            pk=event.metadata.get("target_profile_membership_id"),
            user__workspace_memberships__workspace_id=task.workspace_id,
            user__workspace_memberships__is_active=True,
            user__workspace_memberships__role=WorkspaceMember.Role.MEMBER,
        )
    elif event_type == Notification.EventType.REVIEW_SUBMITTED:
        if (event.entity_name != "Deliverable" or not isinstance(deliverable, Deliverable)
            or event.entity_id != deliverable.pk
            or not Deliverable.objects.filter(
                pk=event.entity_id, task_id=task.pk, uploaded_by_id=actor.pk,
                revision=event.metadata.get("revision"),
            ).exists()):
            raise ValidationError("Submission event must identify its deliverable.")
        workspace_reviewers = WorkspaceMember.objects.filter(
            workspace_id=task.workspace_id, user_id=OuterRef("user_id"),
            is_active=True, role=WorkspaceMember.Role.ADMIN,
        )
        recipients = recipients.annotate(_workspace_reviewer=Exists(workspace_reviewers)).filter(
            Q(role__in=(ProfileMembership.Role.OWNER, ProfileMembership.Role.ADMIN))
            | Q(role=ProfileMembership.Role.MEMBER, _workspace_reviewer=True),
        )
    elif event_type in (Notification.EventType.REVIEW_APPROVED,
                        Notification.EventType.REVIEW_CHANGES_REQUESTED):
        review_status = (Review.Status.APPROVED if event_type == Notification.EventType.REVIEW_APPROVED
                         else Review.Status.REQUEST_CHANGE)
        if (event.entity_name != "Review" or not isinstance(deliverable, Deliverable)
            or event.metadata.get("deliverable_id") != str(deliverable.pk)):
            raise ValidationError("Review notification requires its Task deliverable.")
        proof = Review.objects.filter(
                pk=event.entity_id, reviewer_id=actor.pk, status=review_status,
                deliverable_id=deliverable.pk, deliverable__task_id=task.pk,
                deliverable__revision=event.metadata.get("revision"),
            ).values("deliverable__uploaded_by_id").first()
        if proof is None:
            raise ValidationError("Review notification requires its Task deliverable.")
        recipients = recipients.filter(user_id=proof["deliverable__uploaded_by_id"])
    else:
        if event.entity_name != "TaskComment":
            raise ValidationError("Comment event does not match its Task.")
        if not TaskComment.objects.filter(pk=event.entity_id, task_id=task.pk, user_id=actor.pk).exists():
            raise ValidationError("Comment event does not match its Task.")
        if TaskComment.objects.filter(pk=event.entity_id, deleted_at__isnull=False).exists():
            return []
        assignee_ids = TaskAssignment.objects.filter(task_id=task.pk, is_active=True).values("user_id")
        recipients = recipients.filter(Q(user_id=task.created_by_id) | Q(user_id__in=assignee_ids))

    title, message = EVENT_CONTENT[event_type]
    created = []
    for user_id in recipients.exclude(user_id=actor.pk).values_list("user_id", flat=True).distinct():
        notification, _ = Notification.objects.get_or_create(
            event_id=event.pk, user_id=user_id,
            defaults={"profile_id":profile_id, "workspace_id":task.workspace_id,
                      "task_id":task.pk, "event_type":event_type,
                      "title":title, "message":message},
        )
        created.append(notification)
    return created


@transaction.atomic
def mark_notification_read(*, actor, notification_id):
    """Mark personal metadata under tenant locks, including readable archives."""
    try:
        target = notifications_visible_to(actor).filter(pk=notification_id).values(
            "profile_id", "workspace_id",
        ).first()
    except (TypeError, ValueError, ValidationError, AttributeError):
        raise TenantAccessNotFound() from None
    if target is None:
        raise TenantAccessNotFound()
    # Keep the existing tenant aggregate lock order without the lifecycle write
    # gate: reading/marking an own notification never changes archived content.
    if Profile.objects.select_for_update().filter(pk=target["profile_id"]).first() is None:
        raise TenantAccessNotFound()
    if Workspace.objects.select_for_update().filter(
        pk=target["workspace_id"], profile_id=target["profile_id"],
    ).first() is None:
        raise TenantAccessNotFound()
    context = resolve_profile_access_context(actor, target["profile_id"])
    resolve_workspace_access_context(context, target["workspace_id"])
    notification = notifications_visible_to(actor).select_for_update(of=("self",)).filter(
        pk=notification_id,
    ).first()
    if notification is None:
        raise TenantAccessNotFound()
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=("is_read", "updated_at"))
    return notification


