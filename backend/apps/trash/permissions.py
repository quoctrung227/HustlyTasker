"""Trash authority is current tenant governance, never staff status."""
from django.db.models import Q

from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember


def membership_for(actor, profile_id, *, lock=False):
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "is_active", False):
        return None
    query = ProfileMembership.objects.filter(
        profile_id=profile_id, user_id=actor.pk, is_active=True, user__is_active=True,
    )
    if lock:
        query = query.select_for_update(of=("self",))
    return query.order_by("id").first()


def profile_id_for(obj):
    if isinstance(obj, Profile):
        return obj.pk
    if isinstance(obj, Workspace):
        return obj.profile_id
    return obj.workspace.profile_id


def can_manage(actor, obj, *, membership=None):
    member = membership or membership_for(actor, profile_id_for(obj))
    if member is None:
        return False
    if isinstance(obj, Profile):
        return member.role == ProfileMembership.Role.OWNER
    if member.role in (ProfileMembership.Role.OWNER, ProfileMembership.Role.ADMIN):
        return True
    if isinstance(obj, Workspace):
        return False
    return bool(member.role == ProfileMembership.Role.MEMBER and WorkspaceMember.objects.filter(
        workspace_id=obj.workspace_id, user_id=actor.pk, is_active=True,
        role=WorkspaceMember.Role.ADMIN,
    ).exists())


def managed_profiles(actor):
    return ProfileMembership.objects.filter(
        user_id=actor.pk, user__is_active=True, is_active=True,
        role__in=(ProfileMembership.Role.OWNER, ProfileMembership.Role.ADMIN),
    ).values("profile_id")


def task_management_q(actor):
    managers = managed_profiles(actor)
    local = WorkspaceMember.objects.filter(
        user_id=actor.pk, user__is_active=True, is_active=True, role=WorkspaceMember.Role.ADMIN,
        workspace__profile__memberships__user_id=actor.pk,
        workspace__profile__memberships__is_active=True,
        workspace__profile__memberships__role=ProfileMembership.Role.MEMBER,
    ).values("workspace_id")
    return Q(workspace__profile_id__in=managers) | Q(workspace_id__in=local)
