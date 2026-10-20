from django.contrib import admin

from .models import Workspace, WorkspaceMember


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "profile",
        "period",
        "status",
        "owner",
        "created_at",
    )

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = ["status"]
        if obj is not None and obj.profile_id is not None:
            readonly_fields.append("profile")
        if obj is not None and obj.period is not None:
            readonly_fields.append("period")
        return tuple(readonly_fields)

    def has_delete_permission(self, request, obj=None):
        # Workspace deletion would cascade into Task workflow history. Keep
        # hard deletion behind a future controlled retention operation.
        return False


@admin.register(WorkspaceMember)
class WorkspaceMemberAdmin(admin.ModelAdmin):

    list_display = (
        "workspace",
        "user",
        "role",
        "is_active",
    )

    readonly_fields = (
        "workspace",
        "user",
        "role",
        "is_active",
        "joined_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
