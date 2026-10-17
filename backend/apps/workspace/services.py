from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.audit.models import AuditLog

from .models import Profile, ProfileMembership, Workspace, WorkspaceMember


class LastActiveProfileOwnerError(ValidationError):
    pass


def _write_membership_audit(*, actor, membership, action, before, after):
    if isinstance(membership, ProfileMembership):
        profile_id = membership.profile_id
    else:
        profile_id = membership.workspace.profile_id

    AuditLog.objects.create(
        user=actor,
        action=action,
        entity_name=membership.__class__.__name__,
        entity_id=membership.id,
        metadata={
            "profile_id": str(profile_id),
            "target_user_id": str(membership.user_id),
            "before": before,
            "after": after,
        },
    )


@transaction.atomic
def create_profile_with_owner(*, name, owner):
    if owner.pk is None:
        raise ValidationError("The Profile owner must be a saved User.")

    if not owner.is_active:
        raise ValidationError("The initial Profile owner must be active.")

    profile = Profile(name=(name or "").strip())
    profile.full_clean()
    profile.save()

    membership = ProfileMembership(
        profile=profile,
        user=owner,
        role=ProfileMembership.Role.OWNER,
        is_active=True,
    )
    membership.full_clean()
    membership.save()

    _write_membership_audit(
        actor=owner,
        membership=membership,
        action="profile.membership.created",
        before=None,
        after={
            "role": membership.role,
            "is_active": membership.is_active,
        },
    )

    return profile


@transaction.atomic
def update_profile_membership(
    *,
    membership_id,
    actor,
    role=None,
    is_active=None,
):
    membership_reference = ProfileMembership.objects.only(
        "profile_id"
    ).get(id=membership_id)

    Profile.objects.select_for_update().get(
        id=membership_reference.profile_id
    )

    membership = ProfileMembership.objects.select_for_update().select_related(
        "user"
    ).get(id=membership_id)

    actor_membership = ProfileMembership.objects.select_for_update().filter(
        profile_id=membership.profile_id,
        user_id=actor.id,
        user__is_active=True,
        is_active=True,
        role__in=(
            ProfileMembership.Role.OWNER,
            ProfileMembership.Role.ADMIN,
        ),
    ).first()

    if actor_membership is None:
        raise PermissionDenied(
            "An active Profile Owner or Admin is required."
        )

    next_role = membership.role if role is None else role
    next_is_active = membership.is_active if is_active is None else is_active

    if next_role not in ProfileMembership.Role.values:
        raise ValidationError({"role": "Unsupported Profile membership role."})

    if not isinstance(next_is_active, bool):
        raise ValidationError({"is_active": "Expected a boolean value."})

    if not membership.is_active and next_is_active:
        raise ValidationError({
            "is_active": (
                "Profile membership activation requires the invitation "
                "acceptance flow."
            )
        })

    if (
        next_role == ProfileMembership.Role.OWNER
        and next_is_active
        and not membership.user.is_active
    ):
        raise ValidationError({
            "user": "An active Profile Owner must have an active account."
        })

    if (
        actor_membership.role == ProfileMembership.Role.ADMIN
        and (
            membership.role == ProfileMembership.Role.OWNER
            or next_role == ProfileMembership.Role.OWNER
        )
    ):
        raise PermissionDenied(
            "Profile Admins cannot appoint, demote, or deactivate Owners."
        )

    removes_active_owner = (
        membership.role == ProfileMembership.Role.OWNER
        and membership.is_active
        and membership.user.is_active
        and (
            next_role != ProfileMembership.Role.OWNER
            or not next_is_active
        )
    )

    if removes_active_owner and not ProfileMembership.objects.filter(
        profile_id=membership.profile_id,
        role=ProfileMembership.Role.OWNER,
        is_active=True,
        user__is_active=True,
    ).exclude(id=membership.id).exists():
        raise LastActiveProfileOwnerError(
            "A Profile must always retain at least one active Owner."
        )

    removes_workspace_manager_status = (
        membership.is_active
        and membership.role in (
            ProfileMembership.Role.OWNER,
            ProfileMembership.Role.ADMIN,
        )
        and (
            not next_is_active
            or next_role not in (
                ProfileMembership.Role.OWNER,
                ProfileMembership.Role.ADMIN,
            )
        )
    )
    if removes_workspace_manager_status and Workspace.objects.filter(
        profile_id=membership.profile_id,
        owner_id=membership.user_id,
    ).exists():
        raise ValidationError({
            "role": (
                "Reassign every Workspace owned by this user before removing "
                "their Profile manager status."
            )
        })

    before = {
        "role": membership.role,
        "is_active": membership.is_active,
    }
    after = {
        "role": next_role,
        "is_active": next_is_active,
    }

    if before == after:
        return membership

    membership.role = next_role
    membership.is_active = next_is_active
    membership.full_clean()
    membership.save(
        update_fields=("role", "is_active", "updated_at")
    )

    _write_membership_audit(
        actor=actor,
        membership=membership,
        action="profile.membership.updated",
        before=before,
        after=after,
    )

    return membership


@transaction.atomic
def add_workspace_member(*, workspace_id, user, role, actor):
    workspace_reference = Workspace.objects.only(
        "profile_id"
    ).get(id=workspace_id)

    if workspace_reference.profile_id is None:
        raise ValidationError({
            "workspace": "The workspace must be mapped to a profile first."
        })

    Profile.objects.select_for_update().get(
        id=workspace_reference.profile_id
    )
    workspace = Workspace.objects.select_for_update().get(id=workspace_id)

    actor_membership = ProfileMembership.objects.select_for_update().filter(
        profile_id=workspace.profile_id,
        user_id=actor.id,
        user__is_active=True,
        is_active=True,
        role__in=(
            ProfileMembership.Role.OWNER,
            ProfileMembership.Role.ADMIN,
        ),
    ).first()
    if actor_membership is None:
        raise PermissionDenied(
            "An active Profile Owner or Admin is required."
        )

    target_membership = ProfileMembership.objects.select_for_update().filter(
        profile_id=workspace.profile_id,
        user_id=user.id,
        user__is_active=True,
        is_active=True,
    ).first()
    if target_membership is None:
        raise ValidationError({
            "user": (
                "The user must first have an active membership in the "
                "workspace profile."
            )
        })

    if role not in WorkspaceMember.Role.values:
        raise ValidationError({"role": "Unsupported Workspace membership role."})

    membership = WorkspaceMember(
        workspace=workspace,
        user=user,
        role=role,
    )
    membership.save()

    _write_membership_audit(
        actor=actor,
        membership=membership,
        action="workspace.membership.created",
        before=None,
        after={"role": membership.role},
    )

    return membership
