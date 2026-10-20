from django.db import models

from apps.common.models import BaseModel
from apps.accounts.models import User
from apps.workspace.models import Workspace


class Task(BaseModel):

    class Status(models.TextChoices):
        PENDING = "PENDING"
        ASSIGNED = "ASSIGNED"
        WORKING = "WORKING"
        REVIEW = "REVIEW"
        COMPLETED = "COMPLETED"
        CANCELLED = "CANCELLED"


    class Priority(models.TextChoices):
        LOW = "LOW"
        MEDIUM = "MEDIUM"
        HIGH = "HIGH"
        URGENT = "URGENT"


    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="tasks"
    )


    title = models.CharField(
        max_length=255
    )


    description = models.TextField(
        blank=True,
        null=True
    )


    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )


    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM
    )


    deadline = models.DateTimeField(
        blank=True,
        null=True
    )


    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_tasks"
    )


    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "PENDING",
                        "ASSIGNED",
                        "WORKING",
                        "REVIEW",
                        "COMPLETED",
                        "CANCELLED",
                    )
                ),
                name="task_valid_status",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    priority__in=(
                        "LOW",
                        "MEDIUM",
                        "HIGH",
                        "URGENT",
                    )
                ),
                name="task_valid_priority",
            ),
        ]
        indexes = [
            models.Index(
                fields=("workspace", "status", "-created_at"),
                name="task_ws_status_created_idx",
            ),
        ]


    def __str__(self):
        return self.title



class TaskAssignment(BaseModel):

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="assignments"
    )


    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="assigned_tasks"
    )


    is_active = models.BooleanField(
        default=True,
        help_text="Only the current Task assignment may be active.",
    )


    assigned_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:
        unique_together = (
            "task",
            "user"
        )
        constraints = [
            models.UniqueConstraint(
                fields=("task",),
                condition=models.Q(is_active=True),
                name="uniq_active_task_assignment",
            ),
        ]
        indexes = [
            models.Index(
                fields=("task", "is_active", "-assigned_at"),
                name="task_active_assigned_idx",
            ),
        ]



class TaskComment(BaseModel):

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments"
    )


    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="task_comments"
    )


    content = models.TextField()


    def __str__(self):
        return f"Comment by {self.user.email}"
