from django.core.exceptions import ValidationError

from apps.workspace.access import (
    TenantAccessNotFound,
    can_read_workspace,
    workspaces_visible_to,
)

from .models import Task


def tasks_visible_to(context):
    """Return Tasks inside a resolver-produced, currently readable Workspace.

    The Workspace subquery repeats the actor's live Profile/Workspace
    membership predicates at queryset evaluation time. A membership or role
    change after the request context was resolved therefore narrows the lazy
    queryset instead of leaking Task rows.
    """

    if not can_read_workspace(context):
        raise TenantAccessNotFound()

    visible_workspace_ids = workspaces_visible_to(
        context.profile_context
    ).filter(
        id=context.workspace_id,
    ).values("id")

    return Task.objects.filter(
        workspace_id__in=visible_workspace_ids,
    )


def resolve_task_in_scope(context, task_id):
    """Resolve one Task through its verified nested Workspace scope."""

    try:
        task = tasks_visible_to(context).filter(id=task_id).first()
    except (TypeError, ValueError, ValidationError, AttributeError):
        raise TenantAccessNotFound() from None

    if task is None:
        raise TenantAccessNotFound()

    return task
