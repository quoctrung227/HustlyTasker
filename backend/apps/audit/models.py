from django.db import models

from apps.common.models import BaseModel


class AuditLog(BaseModel):

    user = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    action = models.CharField(
        max_length=255
    )

    entity_name = models.CharField(
        max_length=100
    )

    entity_id = models.UUIDField(
        null=True,
        blank=True
    )

    metadata = models.JSONField(
        default=dict,
        blank=True
    )


    def __str__(self):
        return self.action