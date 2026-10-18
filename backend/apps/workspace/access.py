from dataclasses import dataclass, field
from uuid import UUID

from django.core.exceptions import ValidationError

from .models import Profile, ProfileMembership, Workspace, WorkspaceMember


_CONTEXT_VERIFICATION = object()


class TenantAccessNotFound(LookupError):
    """A resource is absent from, or not visible in, the actor's tenant scope."""

    default_message = "The requested resource is not available in this tenant scope."

    def __init__(self):
        super().__init__(self.default_message)


@dataclass(frozen=True, slots=True)
class ProfileAccessContext:
    user_id: UUID
    profile_id: UUID
    membership_id: UUID
    profile_role: str
    _verification: object | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )


@dataclass(frozen=True, slots=True)
class WorkspaceAccessContext:
    profile_context: ProfileAccessContext
    workspace_id: UUID
    workspace_role: str | None
    _verification: object | None = field(
        default=None,
        init=False,
        repr=False,
        compare=False,
    )

    @property
    def user_id(self):
        return self.profile_context.user_id

    @property
    def profile_id(self):
        return self.profile_context.profile_id

    @property
    def profile_role(self):
        return self.profile_context.profile_role


def _build_profile_access_context(membership):
    context = ProfileAccessContext(
        user_id=membership.user_id,
        profile_id=membership.profile_id,
        membership_id=membership.id,
        profile_role=membership.role,
    )
    object.__setattr__(context, "_verification", _CONTEXT_VERIFICATION)
    return context


def _build_workspace_access_context(
    *,
    profile_context,
    workspace_id,
    workspace_role,
):
    context = WorkspaceAccessContext(
        profile_context=profile_context,
        workspace_id=workspace_id,
        workspace_role=workspace_role,
    )
    object.__setattr__(context, "_verification", _CONTEXT_VERIFICATION)
    return context


def _is_verified_profile_context(context):
    return (
        isinstance(context, ProfileAccessContext)
        and context._verification is _CONTEXT_VERIFICATION
    )


def _is_verified_workspace_context(context):
    return (
        isinstance(context, WorkspaceAccessContext)
        and context._verification is _CONTEXT_VERIFICATION
        and _is_verified_profile_context(context.profile_context)
    )


def _is_current_workspace_context(context):
    """Revalidate a capability snapshot and fail closed on any drift."""

    if not _is_verified_workspace_context(context):
        return False

    profile_context = context.profile_context
    try:
        if profile_context.profile_role in (
            ProfileMembership.Role.OWNER,
            ProfileMembership.Role.ADMIN,
        ):
            if context.workspace_role is not None:
                return False

            return Workspace.objects.filter(
                id=context.workspace_id,
                profile_id=profile_context.profile_id,
                profile__memberships__id=profile_context.membership_id,
                profile__memberships__user_id=profile_context.user_id,
                profile__memberships__user__is_active=True,
                profile__memberships__is_active=True,
                profile__memberships__role=profile_context.profile_role,
            ).exists()

        if (
            profile_context.profile_role != ProfileMembership.Role.MEMBER
            or context.workspace_role not in (
                WorkspaceMember.Role.ADMIN,
                WorkspaceMember.Role.MEMBER,
                WorkspaceMember.Role.VIEWER,
            )
        ):
            return False

        return WorkspaceMember.objects.filter(
            workspace_id=context.workspace_id,
            user_id=profile_context.user_id,
            role=context.workspace_role,
            workspace__profile_id=profile_context.profile_id,
            workspace__profile__memberships__id=(
                profile_context.membership_id
            ),
            workspace__profile__memberships__user_id=profile_context.user_id,
            workspace__profile__memberships__user__is_active=True,
            workspace__profile__memberships__is_active=True,
            workspace__profile__memberships__role=(
                ProfileMembership.Role.MEMBER
            ),
        ).exists()
    except (TypeError, ValueError, ValidationError, AttributeError):
        return False


def profiles_visible_to(user):
    """Return only Profiles backed by a currently usable membership."""

    user_id = getattr(user, "pk", None)
    if user_id is None:
        return Profile.objects.none()

    return Profile.objects.filter(
        memberships__user_id=user_id,
        memberships__user__is_active=True,
        memberships__is_active=True,
    ).distinct()


def resolve_profile_access_context(user, profile_id):
    """Resolve an active Profile membership without globally reading Profile."""

    user_id = getattr(user, "pk", None)
    if user_id is None:
        raise TenantAccessNotFound()

    try:
        membership = ProfileMembership.objects.only(
            "id",
            "profile_id",
            "user_id",
            "role",
        ).filter(
            profile_id=profile_id,
            user_id=user_id,
            user__is_active=True,
            is_active=True,
        ).first()
    except (TypeError, ValueError, ValidationError):
        raise TenantAccessNotFound() from None

    if membership is None:
        raise TenantAccessNotFound()

    return _build_profile_access_context(membership)


def _refresh_profile_access_context(context):
    if not _is_verified_profile_context(context):
        raise TenantAccessNotFound()

    try:
        membership = ProfileMembership.objects.only(
            "id",
            "profile_id",
            "user_id",
            "role",
        ).filter(
            id=context.membership_id,
            profile_id=context.profile_id,
            user_id=context.user_id,
            user__is_active=True,
            is_active=True,
        ).first()
    except (TypeError, ValueError, ValidationError, AttributeError):
        raise TenantAccessNotFound() from None

    if membership is None:
        raise TenantAccessNotFound()

    return _build_profile_access_context(membership)


def _workspaces_visible_to_valid_context(context):
    # Repeat the Profile membership predicates in the returned lazy queryset.
    # A context that becomes stale before queryset evaluation therefore fails
    # closed instead of widening access.
    queryset = Workspace.objects.filter(
        profile_id=context.profile_id,
        profile__memberships__id=context.membership_id,
        profile__memberships__user_id=context.user_id,
        profile__memberships__user__is_active=True,
        profile__memberships__is_active=True,
        profile__memberships__role=context.profile_role,
    )

    if context.profile_role in (
        ProfileMembership.Role.OWNER,
        ProfileMembership.Role.ADMIN,
    ):
        return queryset.distinct()

    if context.profile_role != ProfileMembership.Role.MEMBER:
        return queryset.none()

    return queryset.filter(
        members__user_id=context.user_id,
        members__role__in=(
            WorkspaceMember.Role.ADMIN,
            WorkspaceMember.Role.MEMBER,
            WorkspaceMember.Role.VIEWER,
        ),
    ).distinct()


def workspaces_visible_to(context):
    """Return the current, fail-closed Workspace scope for a Profile context."""

    current_context = _refresh_profile_access_context(context)
    return _workspaces_visible_to_valid_context(current_context)


def resolve_workspace_access_context(profile_context, workspace_id):
    """Resolve Workspace only after applying the actor's current Profile scope."""

    current_profile_context = _refresh_profile_access_context(profile_context)

    try:
        workspace = _workspaces_visible_to_valid_context(
            current_profile_context
        ).only("id").filter(id=workspace_id).first()
    except (TypeError, ValueError, ValidationError):
        raise TenantAccessNotFound() from None

    if workspace is None:
        raise TenantAccessNotFound()

    workspace_role = None
    if current_profile_context.profile_role == ProfileMembership.Role.MEMBER:
        workspace_role = WorkspaceMember.objects.filter(
            workspace_id=workspace.id,
            user_id=current_profile_context.user_id,
            workspace__profile_id=current_profile_context.profile_id,
            workspace__profile__memberships__id=(
                current_profile_context.membership_id
            ),
            workspace__profile__memberships__user_id=(
                current_profile_context.user_id
            ),
            workspace__profile__memberships__user__is_active=True,
            workspace__profile__memberships__is_active=True,
            workspace__profile__memberships__role=(
                ProfileMembership.Role.MEMBER
            ),
            role__in=(
                WorkspaceMember.Role.ADMIN,
                WorkspaceMember.Role.MEMBER,
                WorkspaceMember.Role.VIEWER,
            ),
        ).values_list("role", flat=True).first()

        if workspace_role is None:
            # Defend against membership changes between the two reads.
            raise TenantAccessNotFound()

    return _build_workspace_access_context(
        profile_context=current_profile_context,
        workspace_id=workspace.id,
        workspace_role=workspace_role,
    )


def can_read_workspace(context):
    """Revalidate and evaluate a resolver-produced Workspace context."""

    if not _is_current_workspace_context(context):
        return False

    if context.profile_role in (
        ProfileMembership.Role.OWNER,
        ProfileMembership.Role.ADMIN,
    ):
        return True

    return context.workspace_role in (
        WorkspaceMember.Role.ADMIN,
        WorkspaceMember.Role.MEMBER,
        WorkspaceMember.Role.VIEWER,
    )


def can_edit_workspace(context):
    """Revalidate and evaluate a resolver-produced Workspace context."""

    if not _is_current_workspace_context(context):
        return False

    if context.profile_role in (
        ProfileMembership.Role.OWNER,
        ProfileMembership.Role.ADMIN,
    ):
        return True

    return context.workspace_role in (
        WorkspaceMember.Role.ADMIN,
        WorkspaceMember.Role.MEMBER,
    )


def can_manage_workspace_members(context):
    """Revalidate and evaluate a resolver-produced Workspace context."""

    if not _is_current_workspace_context(context):
        return False

    if context.profile_role in (
        ProfileMembership.Role.OWNER,
        ProfileMembership.Role.ADMIN,
    ):
        return True

    return context.workspace_role == WorkspaceMember.Role.ADMIN
