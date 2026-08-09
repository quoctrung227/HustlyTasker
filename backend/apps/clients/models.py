from django.db import models

from apps.common.models import BaseModel


class Client(BaseModel):

    name = models.CharField(
        max_length=255
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    company = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )


    def __str__(self):
        return self.name



class ShareLink(BaseModel):

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="share_links"
    )


    token = models.CharField(
        max_length=255,
        unique=True
    )


    expired_at = models.DateTimeField(
        null=True,
        blank=True
    )


    def __str__(self):
        return self.token