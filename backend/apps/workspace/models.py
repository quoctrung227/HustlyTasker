from django.core.exceptions import ValidationError
from django.db import models, transaction

from apps.common.models import BaseModel
from apps.accounts.models import User


class Profile(BaseModel):

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        ARCHIVED = "ARCHIVED"

    name = models.CharField(
        max_length=255
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )


    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=("ACTIVE", "ARCHIVED")),
                name="profile_valid_status",
            ),
        ]
        indexes = [
            models.Index(
                fields=("status",),
                name="profile_status_idx",
            ),
        ]


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

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        ARCHIVED = "ARCHIVED"

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

    period = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Canonical monthly period represented by its first day. "
            "Null is reserved for legacy rows awaiting an explicit mapping."
        ),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )


    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=("ACTIVE", "ARCHIVED")),
                name="workspace_valid_status",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(period__isnull=True)
                    | models.Q(period__day=1)
                ),
                name="workspace_period_first_day",
            ),
            models.UniqueConstraint(
                fields=("profile", "period"),
                condition=(
                    models.Q(profile__isnull=False)
                    & models.Q(period__isnull=False)
                ),
                name="uniq_profile_workspace_period",
            ),
        ]
        indexes = [
            models.Index(
                fields=("profile", "status", "period"),
                name="ws_prof_status_period_idx",
            ),
        ]


    def clean(self):
        super().clean()

        if self.period is not None and self.period.day != 1:
            raise ValidationError({
                "period": "Workspace period must be the first day of a month."
            })

        persisted_profile_id = None
        persisted_period = None
        persisted = False
        if self.pk:
            persisted_values = Workspace.objects.filter(id=self.pk).values(
                "profile_id",
                "period",
            ).first()
            if persisted_values is not None:
                persisted = True
                persisted_profile_id = persisted_values["profile_id"]
                persisted_period = persisted_values["period"]

        if not persisted and self.period is None:
            raise ValidationError({
                "period": "A new workspace must have a monthly period."
            })

        if (
            persisted
            and persisted_period is not None
            and self.period != persisted_period
        ):
            raise ValidationError({
                "period": "A workspace monthly period cannot be changed."
            })

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

    is_active = models.BooleanField(
        default=True
    )


    joined_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:
        unique_together = (
            "workspace",
            "user"
        )
        indexes = [
            models.Index(
                fields=("workspace", "is_active", "role"),
                name="wsmem_ws_active_role_idx",
            ),
        ]


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

        if self.is_active and not ProfileMembership.objects.filter(
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
