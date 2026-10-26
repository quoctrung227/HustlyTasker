from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import BaseModel
from apps.accounts.models import User


class Notification(BaseModel):

    class EventType(models.TextChoices):
        TASK_ASSIGNED = "TASK_ASSIGNED"
        REVIEW_SUBMITTED = "REVIEW_SUBMITTED"
        REVIEW_APPROVED = "REVIEW_APPROVED"
        REVIEW_CHANGES_REQUESTED = "REVIEW_CHANGES_REQUESTED"
        TASK_COMMENTED = "TASK_COMMENTED"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications"
    )

    title = models.CharField(
        max_length=255
    )

    message = models.TextField()


    is_read = models.BooleanField(
        default=False
    )

    # Nullable as a group: historical notifications have no safe tenant mapping.
    event_type = models.CharField(max_length=32, choices=EventType.choices, null=True, blank=True)
    profile = models.ForeignKey("workspace.Profile", on_delete=models.PROTECT,
                                related_name="notifications", null=True, blank=True)
    workspace = models.ForeignKey("workspace.Workspace", on_delete=models.PROTECT,
                                  related_name="notifications", null=True, blank=True)
    task = models.ForeignKey("tasks.Task", on_delete=models.PROTECT,
                             related_name="notifications", null=True, blank=True)
    event = models.ForeignKey("audit.AuditLog", on_delete=models.PROTECT,
                              related_name="notifications", null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(event_type__isnull=True, profile__isnull=True,
                             workspace__isnull=True, task__isnull=True, event__isnull=True)
                    | models.Q(event_type__isnull=False, profile__isnull=False,
                               workspace__isnull=False, task__isnull=False, event__isnull=False)
                ),
                name="notif_context_complete",
            ),
            models.CheckConstraint(
                condition=models.Q(event_type__isnull=True) | models.Q(event_type__in=(
                    "TASK_ASSIGNED", "REVIEW_SUBMITTED", "REVIEW_APPROVED",
                    "REVIEW_CHANGES_REQUESTED", "TASK_COMMENTED",
                )),
                name="notif_valid_event_type",
            ),
            models.UniqueConstraint(fields=("user", "event"),
                                    condition=models.Q(event__isnull=False),
                                    name="uniq_notif_event_user"),
        ]
        indexes = [
            models.Index(fields=("user", "is_read", "-created_at", "id"),
                         name="notif_user_read_created_idx"),
        ]

    def clean(self):
        super().clean()
        fields = (self.event_type, self.profile_id, self.workspace_id, self.task_id, self.event_id)
        if any(value is not None for value in fields) and not all(value is not None for value in fields):
            raise ValidationError("Notification context must be complete or entirely legacy.")
        if self.task_id:
            from apps.tasks.models import Task
            canonical = Task.objects.filter(pk=self.task_id).values(
                "workspace_id", "workspace__profile_id",
            ).first()
            if canonical is None or canonical != {
                "workspace_id": self.workspace_id, "workspace__profile_id": self.profile_id,
            }:
                raise ValidationError("Notification target must belong to its Workspace and Profile.")


    def __str__(self):
        return self.title
