from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction

from apps.audit.models import AuditLog

from .access import (
    TenantAccessNotFound,
    can_edit_workspace,
    can_manage_workspace_members,
    resolve_profile_access_context,
    resolve_workspace_access_context,
)
from .models import Profile, ProfileMembership, Workspace, WorkspaceMember


_UNSET = object()


class LastActiveProfileOwnerError(ValidationError):
    pass


class WorkspaceMembershipConflict(ValidationError):
    default_message = (
        "A Workspace membership already exists for this Profile member."
    )

    def __init__(self):
        super().__init__({"target_profile_membership_id": self.default_message})


class InvalidWorkspaceMembershipReference(ValidationError):
    default_message = "Invalid Profile membership reference."

    def __init__(self, field="target_profile_membership_id"):
        super().__init__({field: self.default_message})


def _write_membership_audit(*, actor, membership, action, before, after):
    if isinstance(membership, ProfileMembership):
        profile_id = membership.profile_id
        workspace_id = None
    else:
        profile_id = membership.workspace.profile_id
        workspace_id = membership.workspace_id

    metadata = {
        "profile_id": str(profile_id),
        "target_user_id": str(membership.user_id),
        "before": before,
        "after": after,
    }
    if workspace_id is not None:
        metadata["workspace_id"] = str(workspace_id)

    AuditLog.objects.create(
        user=actor,
        action=action,
        entity_name=membership.__class__.__name__,
        entity_id=membership.id,
        metadata=metadata,
    )


def _write_workspace_audit(*, actor, workspace, action, before, after):
    AuditLog.objects.create(
        user=actor,
        action=action,
        entity_name="Workspace",
        entity_id=workspace.id,
        metadata={
            "profile_id": str(workspace.profile_id),
            "before": before,
            "after": after,
        },
    )


def _lock_workspace_mutation_context(*, actor, profile_id, workspace_id):
    profile_context = resolve_profile_access_context(actor, profile_id)
    workspace_context = resolve_workspace_access_context(
        profile_context,
        workspace_id,
    )

    Profile.objects.select_for_update().filter(
        id=profile_context.profile_id
    ).get()

    workspace = Workspace.objects.select_for_update().filter(
        id=workspace_context.workspace_id,
        profile_id=profile_context.profile_id,
    ).first()
    if workspace is None:
        raise TenantAccessNotFound()

    actor_membership = ProfileMembership.objects.select_for_update().filter(
        id=profile_context.membership_id,
        profile_id=profile_context.profile_id,
        user_id=profile_context.user_id,
        user__is_active=True,
        is_active=True,
    ).first()
    if actor_membership is None:
        raise TenantAccessNotFound()

    locked_workspace_role = None
    if actor_membership.role == ProfileMembership.Role.MEMBER:
        locked_workspace_role = WorkspaceMember.objects.select_for_update().filter(
            workspace_id=workspace.id,
            user_id=actor_membership.user_id,
            role__in=(
                WorkspaceMember.Role.ADMIN,
                WorkspaceMember.Role.MEMBER,
                WorkspaceMember.Role.VIEWER,
            ),
        ).values_list("role", flat=True).first()

        if locked_workspace_role is None:
            raise TenantAccessNotFound()

    if (
        actor_membership.role != workspace_context.profile_role
        or locked_workspace_role != workspace_context.workspace_role
    ):
        # Role changes after initial resolution must be retried from a fresh
        # context; a stale snapshot never broadens mutation authority.
        raise TenantAccessNotFound()

    return workspace_context, workspace, actor_membership


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
    actor,
    profile_id,
    membership_id,
    role=None,
    is_active=None,
):
    profile_context = resolve_profile_access_context(actor, profile_id)

    Profile.objects.select_for_update().filter(
        id=profile_context.profile_id
    ).get()

    actor_membership = ProfileMembership.objects.select_for_update().filter(
        id=profile_context.membership_id,
        profile_id=profile_context.profile_id,
        user_id=profile_context.user_id,
        user__is_active=True,
        is_active=True,
    ).first()

    if actor_membership is None:
        raise TenantAccessNotFound()

    if actor_membership.role not in (
        ProfileMembership.Role.OWNER,
        ProfileMembership.Role.ADMIN,
    ):
        raise PermissionDenied("Profile membership management is not allowed.")

    try:
        membership = ProfileMembership.objects.select_for_update().select_related(
            "user"
        ).filter(
            id=membership_id,
            profile_id=profile_context.profile_id,
        ).first()
    except (TypeError, ValueError, ValidationError):
        raise TenantAccessNotFound() from None

    if membership is None:
        raise TenantAccessNotFound()

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

    if actor_membership.role == ProfileMembership.Role.ADMIN and (
        membership.role != ProfileMembership.Role.MEMBER
        or next_role != ProfileMembership.Role.MEMBER
    ):
        raise PermissionDenied(
            "Profile Admins may manage only existing Profile Members and "
            "cannot grant Profile Admin or Owner roles."
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
        profile_id=profile_context.profile_id,
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
        profile_id=profile_context.profile_id,
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
def create_workspace(*, actor, profile_id, name, description=None):
    profile_context = resolve_profile_access_context(actor, profile_id)

    profile = Profile.objects.select_for_update().filter(
        id=profile_context.profile_id
    ).first()
    if profile is None:
        raise TenantAccessNotFound()

    actor_membership = ProfileMembership.objects.select_for_update().filter(
        id=profile_context.membership_id,
        profile_id=profile_context.profile_id,
        user_id=profile_context.user_id,
        user__is_active=True,
        is_active=True,
    ).first()
    if actor_membership is None:
        raise TenantAccessNotFound()

    if actor_membership.role != profile_context.profile_role:
        raise TenantAccessNotFound()

    if actor_membership.role not in (
        ProfileMembership.Role.OWNER,
        ProfileMembership.Role.ADMIN,
    ):
        raise PermissionDenied("Workspace creation is not allowed.")

    workspace = Workspace(
        profile=profile,
        owner=actor,
        name=(name or "").strip(),
        description=description,
    )
    workspace.save()

    _write_workspace_audit(
        actor=actor,
        workspace=workspace,
        action="workspace.created",
        before=None,
        after={
            "name": workspace.name,
            "description": workspace.description,
        },
    )

    return workspace


@transaction.atomic
def update_workspace(
    *,
    actor,
    profile_id,
    workspace_id,
    name=_UNSET,
    description=_UNSET,
):
    workspace_context, workspace, _ = _lock_workspace_mutation_context(
        actor=actor,
        profile_id=profile_id,
        workspace_id=workspace_id,
    )

    if not can_edit_workspace(workspace_context):
        raise PermissionDenied("Workspace metadata changes are not allowed.")

    before = {
        "name": workspace.name,
        "description": workspace.description,
    }

    if name is not _UNSET:
        workspace.name = (name or "").strip()
    if description is not _UNSET:
        workspace.description = description

    after = {
        "name": workspace.name,
        "description": workspace.description,
    }
    if before == after:
        return workspace

    workspace.save(update_fields=("name", "description", "updated_at"))
    _write_workspace_audit(
        actor=actor,
        workspace=workspace,
        action="workspace.updated",
        before=before,
        after=after,
    )

    return workspace


@transaction.atomic
def add_workspace_member(
    *,
    actor,
    profile_id,
    workspace_id,
    target_profile_membership_id,
    role,
):
    workspace_context, workspace, actor_membership = (
        _lock_workspace_mutation_context(
            actor=actor,
            profile_id=profile_id,
            workspace_id=workspace_id,
        )
    )

    if not can_manage_workspace_members(workspace_context):
        raise PermissionDenied("Workspace membership management is not allowed.")

    if role not in WorkspaceMember.Role.values:
        raise ValidationError({"role": "Unsupported Workspace membership role."})

    if actor_membership.role in (
        ProfileMembership.Role.OWNER,
        ProfileMembership.Role.ADMIN,
    ):
        assignable_roles = (
            WorkspaceMember.Role.ADMIN,
            WorkspaceMember.Role.MEMBER,
            WorkspaceMember.Role.VIEWER,
        )
    else:
        assignable_roles = (
            WorkspaceMember.Role.MEMBER,
            WorkspaceMember.Role.VIEWER,
        )

    if role not in assignable_roles:
        raise PermissionDenied(
            "The requested Workspace role exceeds the actor's assignment "
            "ceiling."
        )

    try:
        target_membership = ProfileMembership.objects.select_for_update().filter(
            id=target_profile_membership_id,
            profile_id=workspace.profile_id,
            user__is_active=True,
            is_active=True,
        ).first()
    except (TypeError, ValueError, ValidationError):
        raise InvalidWorkspaceMembershipReference() from None

    if target_membership is None:
        raise InvalidWorkspaceMembershipReference()

    existing_membership = WorkspaceMember.objects.select_for_update().filter(
        workspace_id=workspace.id,
        user_id=target_membership.user_id,
    ).first()
    if existing_membership is not None:
        raise WorkspaceMembershipConflict()

    membership = WorkspaceMember(
        workspace=workspace,
        user_id=target_membership.user_id,
        role=role,
    )
    try:
        # The nested savepoint lets the outer transaction safely translate a
        # concurrent unique-constraint race into the stable domain conflict.
        with transaction.atomic():
            membership.save()
    except IntegrityError:
        if WorkspaceMember.objects.filter(
            workspace_id=workspace.id,
            user_id=target_membership.user_id,
        ).exists():
            raise WorkspaceMembershipConflict() from None
        raise

    _write_membership_audit(
        actor=actor,
        membership=membership,
        action="workspace.membership.created",
        before=None,
        after={"role": membership.role},
    )

    return membership


@transaction.atomic
def update_workspace_member(
    *,
    actor,
    profile_id,
    workspace_id,
    membership_id,
    role,
):
    workspace_context, workspace, actor_membership = (
        _lock_workspace_mutation_context(
            actor=actor,
            profile_id=profile_id,
            workspace_id=workspace_id,
        )
    )

    if not can_manage_workspace_members(workspace_context):
        raise PermissionDenied("Workspace membership management is not allowed.")

    if role not in WorkspaceMember.Role.values:
        raise ValidationError({"role": "Unsupported Workspace membership role."})

    try:
        target_user_id = WorkspaceMember.objects.filter(
            id=membership_id,
            workspace_id=workspace.id,
        ).values_list("user_id", flat=True).first()
    except (TypeError, ValueError, ValidationError):
        raise TenantAccessNotFound() from None

    if target_user_id is None:
        raise TenantAccessNotFound()

    target_profile_membership = (
        ProfileMembership.objects.select_for_update().filter(
            profile_id=workspace.profile_id,
            user_id=target_user_id,
            user__is_active=True,
            is_active=True,
        ).first()
    )
    if target_profile_membership is None:
        raise InvalidWorkspaceMembershipReference(field="membership_id")

    membership = WorkspaceMember.objects.select_for_update().select_related(
        "workspace"
    ).filter(
        id=membership_id,
        workspace_id=workspace.id,
        user_id=target_profile_membership.user_id,
    ).first()
    if membership is None:
        raise TenantAccessNotFound()

    if actor_membership.role in (
        ProfileMembership.Role.OWNER,
        ProfileMembership.Role.ADMIN,
    ):
        manageable_roles = (
            WorkspaceMember.Role.ADMIN,
            WorkspaceMember.Role.MEMBER,
            WorkspaceMember.Role.VIEWER,
        )
    else:
        manageable_roles = (
            WorkspaceMember.Role.MEMBER,
            WorkspaceMember.Role.VIEWER,
        )

    if membership.role not in manageable_roles or role not in manageable_roles:
        raise PermissionDenied(
            "The Workspace membership role exceeds the actor's management "
            "ceiling."
        )

    if membership.role == role:
        return membership

    before = {"role": membership.role}
    membership.role = role
    membership.save(update_fields=("role", "updated_at"))

    _write_membership_audit(
        actor=actor,
        membership=membership,
        action="workspace.membership.updated",
        before=before,
        after={"role": membership.role},
    )

    return membership
