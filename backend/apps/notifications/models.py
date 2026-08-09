from django.db import models

from apps.common.models import BaseModel
from apps.accounts.models import User


class Notification(BaseModel):

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


    def __str__(self):
        return self.title