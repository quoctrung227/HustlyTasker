from django.urls import path

from .views import (
    ProfileArchiveView,
    ProfileDetailView,
    ProfileListView,
    ProfileRestoreView,
    WorkspaceArchiveView,
    WorkspaceDetailView,
    WorkspaceListView,
    WorkspaceMemberDetailView,
    WorkspaceMemberListView,
    WorkspaceRestoreView,
)


app_name = "workspace"

urlpatterns = [
    path(
        "profiles/",
        ProfileListView.as_view(),
        name="profile-list",
    ),
    path(
        "profiles/<str:profile_id>/",
        ProfileDetailView.as_view(),
        name="profile-detail",
    ),
    path(
        "profiles/<str:profile_id>/archive/",
        ProfileArchiveView.as_view(),
        name="profile-archive",
    ),
    path(
        "profiles/<str:profile_id>/restore/",
        ProfileRestoreView.as_view(),
        name="profile-restore",
    ),
    path(
        "profiles/<str:profile_id>/workspaces/",
        WorkspaceListView.as_view(),
        name="workspace-list",
    ),
    path(
        "profiles/<str:profile_id>/workspaces/<str:workspace_id>/",
        WorkspaceDetailView.as_view(),
        name="workspace-detail",
    ),
    path(
        (
            "profiles/<str:profile_id>/workspaces/"
            "<str:workspace_id>/archive/"
        ),
        WorkspaceArchiveView.as_view(),
        name="workspace-archive",
    ),
    path(
        (
            "profiles/<str:profile_id>/workspaces/"
            "<str:workspace_id>/restore/"
        ),
        WorkspaceRestoreView.as_view(),
        name="workspace-restore",
    ),
    path(
        (
            "profiles/<str:profile_id>/workspaces/"
            "<str:workspace_id>/members/"
        ),
        WorkspaceMemberListView.as_view(),
        name="workspace-member-list",
    ),
    path(
        (
            "profiles/<str:profile_id>/workspaces/"
            "<str:workspace_id>/members/<str:membership_id>/"
        ),
        WorkspaceMemberDetailView.as_view(),
        name="workspace-member-detail",
    ),
]
