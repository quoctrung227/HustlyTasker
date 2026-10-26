"""Live SQL projection of the existing Profile/Workspace Task-read policy."""
from django.db.models import Exists, F, OuterRef, Q

from apps.workspace.models import ProfileMembership, Workspace, WorkspaceMember

from .models import Notification


def readable_memberships(*, profile_id, workspace_id):
    """Recipients must be active members with effective Task read access.

    The roles mirror can_read_workspace; staff/superuser status grants nothing.
    Archived content retains its existing read policy, unlike business writes.
    """
    effective_workspace_membership = WorkspaceMember.objects.filter(
        workspace_id=workspace_id, user_id=OuterRef("user_id"), is_active=True,
        role__in=(WorkspaceMember.Role.ADMIN, WorkspaceMember.Role.MEMBER, WorkspaceMember.Role.VIEWER),
    )
    return ProfileMembership.objects.filter(
        profile_id=profile_id, user__is_active=True, is_active=True,
    ).annotate(_workspace_reader=Exists(effective_workspace_membership)).filter(
        Q(role__in=(ProfileMembership.Role.OWNER, ProfileMembership.Role.ADMIN))
        | Q(role=ProfileMembership.Role.MEMBER, _workspace_reader=True)
    )


def notifications_visible_to(user):
    """Own feed, count and mutations use exactly the same fail-closed scope."""
    user_id = getattr(user, "pk", None)
    if user_id is None:
        return Notification.objects.none()
    active_profile_membership = ProfileMembership.objects.filter(
        profile_id=OuterRef("profile_id"), user_id=user_id,
        user__is_active=True, is_active=True,
    )
    manager = active_profile_membership.filter(
        role__in=(ProfileMembership.Role.OWNER, ProfileMembership.Role.ADMIN),
    )
    ordinary_member = active_profile_membership.filter(role=ProfileMembership.Role.MEMBER)
    effective_workspace_member = WorkspaceMember.objects.filter(
        workspace_id=OuterRef("workspace_id"), user_id=user_id, is_active=True,
        role__in=(WorkspaceMember.Role.ADMIN, WorkspaceMember.Role.MEMBER, WorkspaceMember.Role.VIEWER),
    )
    return Notification.objects.filter(
        user_id=user_id, event_type__in=Notification.EventType.values,
        event__isnull=False, task__isnull=False, workspace__isnull=False,
        profile__isnull=False, task__workspace_id=F("workspace_id"),
        workspace__profile_id=F("profile_id"),
    ).annotate(
        _profile_manager=Exists(manager), _profile_member=Exists(ordinary_member),
        _workspace_member=Exists(effective_workspace_member),
    ).filter(Q(_profile_manager=True) | Q(_profile_member=True, _workspace_member=True))
