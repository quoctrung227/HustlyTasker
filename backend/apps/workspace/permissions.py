from django.contrib.auth import get_user_model
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated

from .access import (
    TenantAccessNotFound,
    can_create_workspace,
    can_edit_workspace,
    can_manage_workspace_members,
    can_read_workspace,
    resolve_profile_access_context,
    resolve_workspace_access_context,
)


User = get_user_model()


class HasActiveTenantIdentity(IsAuthenticated):
    """Require the authenticated identity to remain active in the database."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return User.objects.filter(
            pk=request.user.pk,
            is_active=True,
        ).exists()


class HasProfileAccess(HasActiveTenantIdentity):
    """Resolve a current Profile context without disclosing tenant existence."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        try:
            view.profile_access_context = resolve_profile_access_context(
                request.user,
                view.kwargs["profile_id"],
            )
        except (KeyError, TenantAccessNotFound):
            raise NotFound() from None

        return True


class HasWorkspaceReadAccess(HasProfileAccess):
    """Resolve and revalidate read access to one nested Workspace."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        try:
            workspace_context = resolve_workspace_access_context(
                view.profile_access_context,
                view.kwargs["workspace_id"],
            )
        except (KeyError, TenantAccessNotFound):
            raise NotFound() from None

        if not can_read_workspace(workspace_context):
            raise NotFound()

        view.workspace_access_context = workspace_context
        return True


class CanCreateWorkspace(HasProfileAccess):
    """Allow Workspace creation only to same-Profile managers."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return can_create_workspace(view.profile_access_context)


class CanEditWorkspaceMetadata(HasWorkspaceReadAccess):
    """Resolve an assigned Workspace, then enforce its metadata capability."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return can_edit_workspace(view.workspace_access_context)


class CanManageWorkspaceMembers(HasWorkspaceReadAccess):
    """Resolve an assigned Workspace, then enforce membership management."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return can_manage_workspace_members(view.workspace_access_context)
