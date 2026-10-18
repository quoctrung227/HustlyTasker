from django.urls import path

from .views import (
    ProfileDetailView,
    ProfileListView,
    WorkspaceDetailView,
    WorkspaceListView,
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
        "profiles/<str:profile_id>/workspaces/",
        WorkspaceListView.as_view(),
        name="workspace-list",
    ),
    path(
        "profiles/<str:profile_id>/workspaces/<str:workspace_id>/",
        WorkspaceDetailView.as_view(),
        name="workspace-detail",
    ),
]
