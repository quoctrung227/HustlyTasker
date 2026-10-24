import uuid

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.common.models import BaseModel


def normalize_account_email(value):
    """Return the canonical account identity used by existing auth flows."""

    return (value or "").strip().casefold()


class User(AbstractUser):

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    email = models.EmailField(
        unique=True,
        blank=False,
        null=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    email_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
    )

    verified_email_normalized = models.EmailField(
        max_length=254,
        null=True,
        blank=True,
        editable=False,
    )


    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [
        "username"
    ]

    class Meta(AbstractUser.Meta):
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        email_verified_at__isnull=True,
                        verified_email_normalized__isnull=True,
                    )
                    | models.Q(
                        email_verified_at__isnull=False,
                        verified_email_normalized__isnull=False,
                    )
                ),
                name="acct_verified_email_pair",
            ),
            models.UniqueConstraint(
                fields=("verified_email_normalized",),
                condition=models.Q(verified_email_normalized__isnull=False),
                name="uniq_verified_email_identity",
            ),
        ]

    @property
    def is_email_verified(self):
        return (
            self.email_verified_at is not None
            and self.verified_email_normalized
            == normalize_account_email(self.email)
        )

    def save(self, *args, **kwargs):
        """Invalidate pending proofs when their bound identity state changes."""

        if self._state.adding or not self.pk:
            return super().save(*args, **kwargs)

        with transaction.atomic():
            previous = type(self).objects.select_for_update().filter(
                pk=self.pk,
            ).values("email", "password").first()
            update_fields = kwargs.get("update_fields")
            updates_all_fields = update_fields is None
            email_changed = (
                previous is not None
                and (updates_all_fields or "email" in update_fields)
                and normalize_account_email(previous["email"])
                != normalize_account_email(self.email)
            )
            password_changed = (
                previous is not None
                and (updates_all_fields or "password" in update_fields)
                and previous["password"] != self.password
            )
            if email_changed:
                self.email_verified_at = None
                self.verified_email_normalized = None
                if update_fields is not None:
                    kwargs["update_fields"] = tuple(
                        set(update_fields)
                        | {"email_verified_at", "verified_email_normalized"}
                    )

            result = super().save(*args, **kwargs)
            if email_changed:
                now = timezone.now()
                AccountSecurityToken.objects.filter(
                    user_id=self.pk,
                    purpose__in=(
                        AccountSecurityToken.Purpose.EMAIL_VERIFICATION,
                        AccountSecurityToken.Purpose.PASSWORD_RESET,
                    ),
                    status=AccountSecurityToken.Status.PENDING,
                ).update(
                    status=AccountSecurityToken.Status.REVOKED,
                    revoked_at=now,
                    updated_at=now,
                )
            if password_changed:
                now = timezone.now()
                AccountSecurityToken.objects.filter(
                    user_id=self.pk,
                    purpose=AccountSecurityToken.Purpose.PASSWORD_RESET,
                    status=AccountSecurityToken.Status.PENDING,
                ).update(
                    status=AccountSecurityToken.Status.REVOKED,
                    revoked_at=now,
                    updated_at=now,
                )
            return result


class AccountSecurityToken(BaseModel):
    """Hashed, purpose-bound credential for account security operations."""

    class Purpose(models.TextChoices):
        EMAIL_VERIFICATION = "EMAIL_VERIFICATION"
        PASSWORD_RESET = "PASSWORD_RESET"

    class Status(models.TextChoices):
        PENDING = "PENDING"
        CONSUMED = "CONSUMED"
        REVOKED = "REVOKED"
        EXPIRED = "EXPIRED"

    class DeliveryStatus(models.TextChoices):
        QUEUED = "QUEUED"
        SENT = "SENT"
        FAILED = "FAILED"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="account_security_tokens",
    )
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    email_normalized = models.EmailField(max_length=254, editable=False)
    token_digest = models.CharField(max_length=64, unique=True, editable=False)
    password_fingerprint = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        editable=False,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    expires_at = models.DateTimeField()
    delivery_status = models.CharField(
        max_length=10,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.QUEUED,
    )
    delivery_attempted_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)
    replaces = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        related_name="replacement",
        null=True,
        blank=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    purpose__in=("EMAIL_VERIFICATION", "PASSWORD_RESET")
                ),
                name="acctok_valid_purpose",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    status__in=("PENDING", "CONSUMED", "REVOKED", "EXPIRED")
                ),
                name="acctok_valid_status",
            ),
            models.CheckConstraint(
                condition=models.Q(
                    delivery_status__in=("QUEUED", "SENT", "FAILED")
                ),
                name="acctok_valid_delivery",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        purpose="EMAIL_VERIFICATION",
                        password_fingerprint__isnull=True,
                    )
                    | models.Q(
                        purpose="PASSWORD_RESET",
                        password_fingerprint__isnull=False,
                    )
                ),
                name="acctok_fingerprint_by_purpose",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        status="PENDING",
                        consumed_at__isnull=True,
                        revoked_at__isnull=True,
                        expired_at__isnull=True,
                    )
                    | models.Q(
                        status="CONSUMED",
                        consumed_at__isnull=False,
                        revoked_at__isnull=True,
                        expired_at__isnull=True,
                    )
                    | models.Q(
                        status="REVOKED",
                        consumed_at__isnull=True,
                        revoked_at__isnull=False,
                        expired_at__isnull=True,
                    )
                    | models.Q(
                        status="EXPIRED",
                        consumed_at__isnull=True,
                        revoked_at__isnull=True,
                        expired_at__isnull=False,
                    )
                ),
                name="acctok_terminal_state_valid",
            ),
            models.CheckConstraint(
                condition=(
                    ~models.Q(status="CONSUMED")
                    | models.Q(delivery_status="SENT")
                ),
                name="acctok_consume_requires_sent",
            ),
            models.CheckConstraint(
                condition=models.Q(expires_at__gt=models.F("created_at")),
                name="acctok_expiry_after_created",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(
                        delivery_status="QUEUED",
                        delivered_at__isnull=True,
                    )
                    | models.Q(
                        delivery_status="FAILED",
                        delivery_attempted_at__isnull=False,
                        delivered_at__isnull=True,
                    )
                    | models.Q(
                        delivery_status="SENT",
                        delivery_attempted_at__isnull=False,
                        delivered_at__isnull=False,
                    )
                ),
                name="acctok_delivery_state_valid",
            ),
            models.CheckConstraint(
                condition=~models.Q(replaces=models.F("id")),
                name="acctok_not_self_replacement",
            ),
            models.UniqueConstraint(
                fields=("user", "purpose"),
                condition=models.Q(status="PENDING"),
                name="uniq_pending_user_acctok_purpose",
            ),
        ]
        indexes = [
            models.Index(
                fields=("user", "purpose", "status", "created_at"),
                name="acctok_user_purpose_status_idx",
            ),
            models.Index(
                fields=("email_normalized", "purpose", "status"),
                name="acctok_email_purpose_idx",
            ),
            models.Index(
                fields=("expires_at", "status"),
                name="acctok_expiry_status_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.email_normalized != normalize_account_email(
            self.email_normalized
        ):
            raise ValidationError({
                "email_normalized": "Account email must be normalized."
            })

        digest = self.token_digest or ""
        if len(digest) != 64 or any(
            character not in "0123456789abcdef" for character in digest
        ):
            raise ValidationError({
                "token_digest": "Invalid account security credential."
            })

        fingerprint = self.password_fingerprint or ""
        if self.purpose == self.Purpose.PASSWORD_RESET and (
            len(fingerprint) != 64
            or any(
                character not in "0123456789abcdef"
                for character in fingerprint
            )
        ):
            raise ValidationError({
                "password_fingerprint": "Invalid password state fingerprint."
            })
        if (
            self.purpose == self.Purpose.EMAIL_VERIFICATION
            and self.password_fingerprint is not None
        ):
            raise ValidationError({
                "password_fingerprint": (
                    "Email verification tokens cannot bind password state."
                )
            })

        if self.replaces_id:
            replaced = AccountSecurityToken.objects.filter(
                id=self.replaces_id,
            ).values("user_id", "purpose").first()
            if replaced and (
                replaced["user_id"] != self.user_id
                or replaced["purpose"] != self.purpose
            ):
                raise ValidationError({
                    "replaces": "Replacement tokens must keep user and purpose."
                })

        if (
            self.expires_at
            and self.created_at
            and self.expires_at <= self.created_at
        ):
            raise ValidationError({
                "expires_at": "Token expiry must be after creation."
            })

    def __str__(self):
        return f"Account security token {self.id} ({self.purpose}/{self.status})"
