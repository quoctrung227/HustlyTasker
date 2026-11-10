from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef, Q

from apps.workspace.access import (
    TenantAccessNotFound,
    can_read_workspace,
    resolve_profile_access_context,
    resolve_workspace_access_context,
    workspaces_visible_to,
)
from apps.workspace.models import ProfileMembership, WorkspaceMember

from .models import Task, TaskAssignment


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


def task_compensation_visible_to(user, context):
    """Return the readable Tasks whose whole-Task compensation may be disclosed.

    This is a field projection, not a new Task read/write grant. Reuse the
    existing tenant scope, then repeat current role/assignment eligibility in
    the SQL statement. In particular, prefetched or historical assignments and
    stale role snapshots cannot grant financial visibility. Archived scopes
    retain their existing read-only behavior; no lifecycle write is enabled.
    """

    if (
        not getattr(user, "is_authenticated", False)
        or not getattr(user, "is_active", False)
        or getattr(context, "user_id", None) != getattr(user, "pk", None)
    ):
        return Task.objects.none()
    try:
        queryset = tasks_visible_to(context)
    except (TenantAccessNotFound, AttributeError, TypeError, ValueError, ValidationError):
        return Task.objects.none()

    current_membership = ProfileMembership.objects.filter(
        id=context.profile_context.membership_id,
        profile_id=context.profile_id,
        user_id=context.user_id,
        user__is_active=True,
        is_active=True,
    )
    profile_managers = current_membership.filter(
        role__in=(ProfileMembership.Role.OWNER, ProfileMembership.Role.ADMIN),
    )
    workspace_members = WorkspaceMember.objects.filter(
        workspace_id=OuterRef("workspace_id"),
        user_id=context.user_id,
        is_active=True,
        workspace__profile_id=context.profile_id,
        workspace__profile__memberships__id=context.profile_context.membership_id,
        workspace__profile__memberships__user_id=context.user_id,
        workspace__profile__memberships__user__is_active=True,
        workspace__profile__memberships__is_active=True,
        workspace__profile__memberships__role=ProfileMembership.Role.MEMBER,
    )
    # A retained assignment does not stay effective after a downgrade to
    # VIEWER. Domain assignment services only accept an active Workspace MEMBER.
    assignments = TaskAssignment.objects.filter(
        task_id=OuterRef("pk"),
        user_id=context.user_id,
        is_active=True,
    )
    return queryset.alias(
        _compensation_profile_manager=Exists(profile_managers),
        _compensation_workspace_manager=Exists(workspace_members.filter(role=WorkspaceMember.Role.ADMIN)),
        _compensation_workspace_editor=Exists(workspace_members.filter(role=WorkspaceMember.Role.MEMBER)),
        _compensation_assigned=Exists(assignments),
    ).filter(
        Q(_compensation_profile_manager=True)
        | Q(_compensation_workspace_manager=True)
        | Q(_compensation_workspace_editor=True, _compensation_assigned=True)
    )


def can_view_task_compensation(user, task, *, context=None):
    """Fail-closed single-Task helper using the same live projection policy."""

    if not isinstance(task, Task) or not getattr(user, "is_authenticated", False):
        return False
    if context is None:
        try:
            profile_context = resolve_profile_access_context(user, task.workspace.profile_id)
            context = resolve_workspace_access_context(profile_context, task.workspace_id)
        except (TenantAccessNotFound, AttributeError, TypeError, ValueError, ValidationError):
            return False
    return task_compensation_visible_to(user, context).filter(pk=task.pk).exists()


def task_assignee_display_values(user, context, task_ids):
    """Batch current same-tenant readable assignment identities for one page.

    Display does not confer execution or compensation authority. An assignee
    whose account or effective tenant access was revoked is not named, even
    when an old ACTIVE assignment or a prefetched User remains in memory.
    """

    if (
        not getattr(user, "is_authenticated", False)
        or not getattr(user, "is_active", False)
        or getattr(context, "user_id", None) != getattr(user, "pk", None)
    ):
        return TaskAssignment.objects.none().values("id")
    try:
        visible_tasks = tasks_visible_to(context).filter(pk__in=task_ids).values("pk")
    except (TenantAccessNotFound, AttributeError, TypeError, ValueError, ValidationError):
        return TaskAssignment.objects.none().values("id")
    memberships = ProfileMembership.objects.filter(
        profile_id=context.profile_id, user_id=OuterRef("user_id"),
        is_active=True, user__is_active=True,
    )
    workspace_access = WorkspaceMember.objects.filter(
        workspace_id=OuterRef("task__workspace_id"), user_id=OuterRef("user_id"),
        is_active=True,
        role__in=(WorkspaceMember.Role.ADMIN, WorkspaceMember.Role.MEMBER, WorkspaceMember.Role.VIEWER),
    )
    return TaskAssignment.objects.filter(
        task_id__in=visible_tasks, is_active=True, user__is_active=True,
    ).alias(
        _display_profile_manager=Exists(memberships.filter(role__in=(ProfileMembership.Role.OWNER, ProfileMembership.Role.ADMIN))),
        _display_profile_member=Exists(memberships.filter(role=ProfileMembership.Role.MEMBER)),
        _display_workspace_access=Exists(workspace_access),
    ).filter(
        Q(_display_profile_manager=True)
        | Q(_display_profile_member=True, _display_workspace_access=True)
    ).values("id", "user__first_name", "user__last_name", "user__username")
