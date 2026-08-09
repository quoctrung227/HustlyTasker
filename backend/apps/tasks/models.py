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
        on_delete=models.CASCADE,
        related_name="created_tasks"
    )


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
        on_delete=models.CASCADE,
        related_name="assigned_tasks"
    )


    assigned_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:
        unique_together = (
            "task",
            "user"
        )



class TaskComment(BaseModel):

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments"
    )


    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="task_comments"
    )


    content = models.TextField()


    def __str__(self):
        return f"Comment by {self.user.email}"