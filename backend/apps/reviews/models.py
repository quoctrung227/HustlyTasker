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
        on_delete=models.CASCADE,
        related_name="uploaded_deliverables"
    )


    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )


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
        on_delete=models.CASCADE,
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


    def __str__(self):
        return f"Review - {self.deliverable.task.title}"