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

    # The inspection-only admin has global Django model permissions, not the
    # tenant/assignment context required for this field. Pay is available only
    # through the scoped Task API; never auto-include it in the model form.
    exclude = ("estimated_compensation_vnd",)

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
