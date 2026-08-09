from django.db import models
from apps.common.models import BaseModel
from apps.accounts.models import User


class Workspace(BaseModel):

    name = models.CharField(
        max_length=255
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="owned_workspaces"
    )


    def __str__(self):
        return self.name



class WorkspaceMember(BaseModel):

    class Role(models.TextChoices):
        OWNER = "OWNER"
        ADMIN = "ADMIN"
        MEMBER = "MEMBER"
        VIEWER = "VIEWER"


    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="members"
    )


    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="workspace_memberships"
    )


    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )


    joined_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:
        unique_together = (
            "workspace",
            "user"
        )


    def __str__(self):
        return f"{self.user.email} - {self.workspace.name}"