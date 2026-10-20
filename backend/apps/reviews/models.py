from django.db import models

from apps.common.models import BaseModel
from apps.accounts.models import User
from apps.tasks.models import Task



class Deliverable(BaseModel):

    class Status(models.TextChoices):
        PENDING = "PENDING"
        SUBMITTED = "SUBMITTED"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"


    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="deliverables"
    )


    file_url = models.CharField(
        max_length=500
    )


    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="uploaded_deliverables"
    )


    revision = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=(
            "Service-created revisions start at 1. Null is reserved for "
            "legacy rows that have not been mapped."
        ),
    )


    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )


    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "PENDING",
                        "SUBMITTED",
                        "APPROVED",
                        "REJECTED",
                    )
                ),
                name="deliverable_valid_status",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(revision__isnull=True)
                    | models.Q(revision__gte=1)
                ),
                name="deliverable_revision_positive",
            ),
            models.UniqueConstraint(
                fields=("task", "revision"),
                condition=models.Q(revision__isnull=False),
                name="uniq_task_deliv_revision",
            ),
        ]
        indexes = [
            models.Index(
                fields=("task", "status", "-created_at"),
                name="deliv_task_status_created_idx",
            ),
        ]


    def __str__(self):
        return f"Deliverable - {self.task.title}"



class Review(BaseModel):

    class Status(models.TextChoices):
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REQUEST_CHANGE = "REQUEST_CHANGE"


    deliverable = models.ForeignKey(
        Deliverable,
        on_delete=models.CASCADE,
        related_name="reviews"
    )


    reviewer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="reviews_given"
    )


    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )


    comment = models.TextField(
        blank=True,
        null=True
    )


    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    status__in=(
                        "PENDING",
                        "APPROVED",
                        "REQUEST_CHANGE",
                    )
                ),
                name="review_valid_status",
            ),
            models.UniqueConstraint(
                fields=("deliverable",),
                name="uniq_deliverable_review",
            ),
        ]


    def __str__(self):
        return f"Review - {self.deliverable.task.title}"
