from rest_framework.exceptions import NotFound

from apps.workspace.access import (
    TenantAccessNotFound,
    can_execute_workspace_tasks,
    can_manage_workspace_tasks,
    can_review_workspace_deliverables,
)
from apps.workspace.permissions import HasWorkspaceReadAccess

from .access import resolve_task_in_scope


class HasTaskReadAccess(HasWorkspaceReadAccess):
    """Resolve a Task only through the already-authorized nested Workspace."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        try:
            view.task = resolve_task_in_scope(
                view.workspace_access_context,
                view.kwargs["task_id"],
            )
        except (KeyError, TenantAccessNotFound):
            raise NotFound() from None

        return True


class CanManageWorkspaceTasks(HasWorkspaceReadAccess):
    """Allow manager Task writes, with optional nested Task pre-resolution."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        task_id = view.kwargs.get("task_id")
        if task_id is not None:
            try:
                view.task = resolve_task_in_scope(
                    view.workspace_access_context,
                    task_id,
                )
            except TenantAccessNotFound:
                raise NotFound() from None

        return can_manage_workspace_tasks(view.workspace_access_context)


class CanExecuteWorkspaceTasks(HasTaskReadAccess):
    """Require the role-level Editor capability for Task workflow actions."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return can_execute_workspace_tasks(view.workspace_access_context)


class CanReviewWorkspaceDeliverables(HasTaskReadAccess):
    """Require current internal-review authority for a scoped Task."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        return can_review_workspace_deliverables(
            view.workspace_access_context
        )
