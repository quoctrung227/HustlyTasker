from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.common.models import BaseModel
from apps.accounts.models import User


class Profile(BaseModel):

    name = models.CharField(
        max_length=255
    )


    def __str__(self):
        return self.name


class ProfileMembership(BaseModel):

    class Role(models.TextChoices):
        OWNER = "OWNER"
        ADMIN = "ADMIN"
        MEMBER = "MEMBER"


    profile = models.ForeignKey(
        Profile,
        on_delete=models.PROTECT,
        related_name="memberships"
    )


    user = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="profile_memberships"
    )


    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER
    )


    is_active = models.BooleanField(
        default=True
    )


    joined_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("profile", "user"),
                condition=models.Q(is_active=True),
                name="uniq_active_profile_user"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    role__in=("OWNER", "ADMIN", "MEMBER")
                ),
                name="profmem_valid_role"
            ),
        ]
        indexes = [
            models.Index(
                fields=("user", "is_active"),
                name="profmem_user_active_idx"
            ),
            models.Index(
                fields=("profile", "is_active", "role"),
                name="profmem_prof_active_role_idx"
            ),
        ]


    def __str__(self):
        return f"{self.user.email} - {self.profile.name}"

    def clean(self):
        super().clean()

        if (
            self.user_id
            and self.is_active
            and self.role == self.Role.OWNER
            and not User.objects.filter(
                id=self.user_id,
                is_active=True,
            ).exists()
        ):
            raise ValidationError({
                "user": "An active Profile Owner must have an active account."
            })


class Workspace(BaseModel):

    name = models.CharField(
        max_length=255
    )

    description = models.TextField(
        blank=True,
        null=True
    )


    profile = models.ForeignKey(
        Profile,
        on_delete=models.PROTECT,
        related_name="workspaces",
        null=True,
        help_text=(
            "Transitional nullable tenant link for existing rows. "
            "New workspaces must provide a profile."
        )
    )


    owner = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="owned_workspaces"
    )


    def clean(self):
        super().clean()

        persisted_profile_id = None
        persisted = False
        if self.pk:
            persisted_profile_id = Workspace.objects.filter(
                id=self.pk
            ).values_list(
                "profile_id",
                flat=True,
            ).first()
            persisted = Workspace.objects.filter(id=self.pk).exists()

        if self.profile_id is None:
            if persisted and persisted_profile_id is None:
                # Existing rows from before the tenant migration remain usable
                # until an explicit, verified mapping is available.
                return
            raise ValidationError({
                "profile": "A workspace must belong to a profile."
            })

        if (
            persisted
            and persisted_profile_id is not None
            and persisted_profile_id != self.profile_id
        ):
            raise ValidationError({
                "profile": "A workspace cannot be moved to another profile."
            })

        if self.owner_id and not ProfileMembership.objects.filter(
            profile_id=self.profile_id,
            user_id=self.owner_id,
            user__is_active=True,
            is_active=True,
            role__in=(
                ProfileMembership.Role.OWNER,
                ProfileMembership.Role.ADMIN,
            ),
        ).exists():
            raise ValidationError({
                "owner": (
                    "The transitional workspace owner must be an active "
                    "Profile Owner or Admin."
                )
            })

        if persisted and persisted_profile_id is None:
            workspace_user_ids = set(
                WorkspaceMember.objects.filter(
                    workspace_id=self.pk
                ).values_list("user_id", flat=True)
            )
            mapped_user_ids = set(
                ProfileMembership.objects.filter(
                    profile_id=self.profile_id,
                    user_id__in=workspace_user_ids,
                    user__is_active=True,
                    is_active=True,
                ).values_list("user_id", flat=True)
            )
            if workspace_user_ids - mapped_user_ids:
                raise ValidationError({
                    "profile": (
                        "Every existing workspace member must have an active "
                        "membership in the selected profile before mapping."
                    )
                })

    def save(self, *args, **kwargs):
        if self.profile_id is None:
            if self._state.adding:
                self.full_clean()
                return super().save(*args, **kwargs)

            with transaction.atomic():
                Workspace.objects.select_for_update().filter(id=self.pk).exists()
                self.full_clean()
                return super().save(*args, **kwargs)

        with transaction.atomic():
            Profile.objects.select_for_update().get(id=self.profile_id)
            if not self._state.adding:
                Workspace.objects.select_for_update().filter(id=self.pk).exists()
            self.full_clean()
            return super().save(*args, **kwargs)


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


    def clean(self):
        super().clean()

        if not self.workspace_id or not self.user_id:
            return

        profile_id = Workspace.objects.filter(
            id=self.workspace_id
        ).values_list(
            "profile_id",
            flat=True
        ).first()

        if profile_id is None:
            if self.pk:
                persisted = WorkspaceMember.objects.filter(
                    id=self.pk,
                    workspace_id=self.workspace_id,
                    user_id=self.user_id,
                ).exists()
                if persisted:
                    # Preserve an unchanged legacy relation until its
                    # Workspace receives an explicit Profile mapping.
                    return
            raise ValidationError({
                "workspace": (
                    "The workspace must be mapped to a profile before "
                    "members can be assigned."
                )
            })

        if not ProfileMembership.objects.filter(
            profile_id=profile_id,
            user_id=self.user_id,
            user__is_active=True,
            is_active=True,
        ).exists():
            raise ValidationError({
                "user": (
                    "A workspace member must first have an active membership "
                    "in the workspace profile."
                )
            })

    def save(self, *args, **kwargs):
        profile_id = Workspace.objects.filter(
            id=self.workspace_id
        ).values_list(
            "profile_id",
            flat=True,
        ).first()

        if profile_id is None:
            self.full_clean()
            return super().save(*args, **kwargs)

        with transaction.atomic():
            Profile.objects.select_for_update().get(id=profile_id)
            self.full_clean()
            return super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.user.email} - {self.workspace.name}"
