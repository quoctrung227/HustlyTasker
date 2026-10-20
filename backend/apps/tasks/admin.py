from django.contrib import admin

from .models import Task, TaskAssignment, TaskComment


class InspectionOnlyAdminMixin:

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Task)
class TaskAdmin(InspectionOnlyAdminMixin, admin.ModelAdmin):

    list_display = (
        "title",
        "workspace",
        "status",
        "priority",
        "deadline",
    )


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(InspectionOnlyAdminMixin, admin.ModelAdmin):

    list_display = (
        "task",
        "user",
        "is_active",
        "assigned_at",
    )


@admin.register(TaskComment)
class TaskCommentAdmin(InspectionOnlyAdminMixin, admin.ModelAdmin):

    list_display = (
        "task",
        "user",
        "created_at",
    )
