from django.contrib import admin

from .models import Task, TaskAssignment, TaskComment


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "workspace",
        "status",
        "priority",
        "deadline",
    )


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "task",
        "user",
        "assigned_at",
    )


@admin.register(TaskComment)
class TaskCommentAdmin(admin.ModelAdmin):

    list_display = (
        "task",
        "user",
        "created_at",
    )