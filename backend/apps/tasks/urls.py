from django.urls import path

from .comment_views import CommentDetailView, CommentListView
from .views import (
    DeliverableApproveView,
    DeliverableListView,
    DeliverableRequestChangesView,
    TaskAssignView,
    TaskDetailView,
    TaskListView,
    TaskStartView,
    TaskSubtaskListView,
)


app_name = "tasks"

_workspace_prefix = (
    "profiles/<str:profile_id>/workspaces/<str:workspace_id>/tasks/"
)

urlpatterns = [
    path(
        f"{_workspace_prefix}<str:task_id>/comments/",
        CommentListView.as_view(),
        name="task-comment-list",
    ),
    path(
        f"{_workspace_prefix}<str:task_id>/comments/<str:comment_id>/",
        CommentDetailView.as_view(),
        name="task-comment-detail",
    ),
    path(
        _workspace_prefix,
        TaskListView.as_view(),
        name="task-list",
    ),
    path(
        f"{_workspace_prefix}<str:task_id>/",
        TaskDetailView.as_view(),
        name="task-detail",
    ),
    path(
        f"{_workspace_prefix}<str:task_id>/assign/",
        TaskAssignView.as_view(),
        name="task-assign",
    ),
    path(
        f"{_workspace_prefix}<str:task_id>/subtasks/",
        TaskSubtaskListView.as_view(),
        name="task-subtask-list",
    ),
    path(
        f"{_workspace_prefix}<str:task_id>/start/",
        TaskStartView.as_view(),
        name="task-start",
    ),
    path(
        f"{_workspace_prefix}<str:task_id>/deliverables/",
        DeliverableListView.as_view(),
        name="task-deliverable-list",
    ),
    path(
        (
            f"{_workspace_prefix}<str:task_id>/deliverables/"
            "<str:deliverable_id>/approve/"
        ),
        DeliverableApproveView.as_view(),
        name="task-deliverable-approve",
    ),
    path(
        (
            f"{_workspace_prefix}<str:task_id>/deliverables/"
            "<str:deliverable_id>/request-changes/"
        ),
        DeliverableRequestChangesView.as_view(),
        name="task-deliverable-request-changes",
    ),
]
