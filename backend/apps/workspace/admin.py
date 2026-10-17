from django.contrib import admin

from .models import Workspace, WorkspaceMember


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "profile",
        "owner",
        "created_at",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and obj.profile_id is not None:
            return ("profile",)
        return ()


@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):

    list_display = (
        "workspace",
        "user",
        "role",
    )

    readonly_fields = (
        "workspace",
        "user",
        "role",
        "joined_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
