from datetime import datetime, timezone as datetime_timezone

from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.utils import timezone

from apps.common.models import BaseModel
from apps.accounts.models import User
from apps.workspace.models import Workspace


class Task(BaseModel):

    # Root depth is zero: at most three parent edges (four visible levels).
    MAX_HIERARCHY_DEPTH = 3

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

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        related_name="subtasks",
        blank=True,
        null=True,
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
                condition=~models.Q(id=models.F("parent_id")),
                name="task_not_own_parent",
            ),
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
                fields=("workspace", "parent", "created_at"),
                name="task_ws_parent_created_idx",
            ),
            models.Index(
                fields=("workspace", "status", "-created_at"),
                name="task_ws_status_created_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.deadline is not None:
            if not isinstance(self.deadline, datetime) or not timezone.is_aware(self.deadline):
                raise ValidationError({"deadline": "Use a timezone-aware datetime."})
            try:
                self.deadline.astimezone(datetime_timezone.utc)
            except (OverflowError, ValueError):
                raise ValidationError({"deadline": "Datetime is outside the supported range."}) from None

        seen = {self.pk}
        parent_id = self.parent_id
        depth = 0
        while parent_id is not None:
            if parent_id in seen:
                raise ValidationError({"parent": "A Task hierarchy cannot contain a cycle."})
            seen.add(parent_id)
            parent = Task.objects.filter(pk=parent_id).values(
                "workspace_id", "parent_id",
            ).first()
            if parent is None or parent["workspace_id"] != self.workspace_id:
                raise ValidationError({"parent": "Parent must be in the same Workspace."})
            depth += 1
            if depth > self.MAX_HIERARCHY_DEPTH:
                raise ValidationError({"parent": "Task hierarchy exceeds the maximum depth of 3."})
            parent_id = parent["parent_id"]

        # A move must also leave the deepest descendant within the depth cap.
        # At most four batched descendant queries; never recursively serialize.
        if not self._state.adding:
            previous = Task.objects.filter(pk=self.pk).values(
                "parent_id", "workspace_id",
            ).first()
            if previous and (
                previous["parent_id"] != self.parent_id
                or previous["workspace_id"] != self.workspace_id
            ):
                frontier = [self.pk]
                descendants_seen = {self.pk}
                for distance in range(1, self.MAX_HIERARCHY_DEPTH + 2):
                    descendants = list(Task.objects.filter(
                        parent_id__in=frontier,
                    ).values_list("id", "workspace_id"))
                    if not descendants:
                        break
                    if depth + distance > self.MAX_HIERARCHY_DEPTH:
                        raise ValidationError({"parent": "The moved subtree exceeds the maximum depth of 3."})
                    if any(ws_id != self.workspace_id or pk in descendants_seen
                           for pk, ws_id in descendants):
                        raise ValidationError({"parent": "Invalid Task subtree."})
                    frontier = [pk for pk, _ in descendants]
                    descendants_seen.update(frontier)


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

    CONTENT_MAX_LENGTH = 4000

    task = models.ForeignKey(
        Task,
        on_delete=models.PROTECT,
        related_name="comments"
    )


    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="task_comments"
    )


    content = models.TextField(validators=[MaxLengthValidator(CONTENT_MAX_LENGTH)])

    edited_at = models.DateTimeField(blank=True, null=True)
    deleted_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(edited_at__isnull=True) | models.Q(edited_at__gte=models.F("created_at")),
                name="comment_edit_after_create",
            ),
            models.CheckConstraint(
                condition=models.Q(deleted_at__isnull=True) | models.Q(deleted_at__gte=models.F("created_at")),
                name="comment_delete_after_create",
            ),
        ]
        indexes = [
            models.Index(fields=("task", "created_at", "id"), name="comment_task_created_id_idx"),
        ]


    def __str__(self):
        return f"Task comment {self.pk}"
