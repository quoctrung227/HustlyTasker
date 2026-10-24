import hashlib
import hmac
import secrets
from datetime import timedelta

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from apps.audit.models import AuditLog

from .email_delivery import (
    AccountSecurityDeliveryUnavailable,
    ensure_account_security_delivery_available,
    schedule_account_security_delivery,
)
from .identity import AmbiguousAccountIdentity, resolve_unique_user_for_email
from .models import AccountSecurityToken, User, normalize_account_email


EMAIL_VERIFICATION_TTL = timedelta(hours=24)
PASSWORD_RESET_TTL = timedelta(hours=1)


class AccountSecurityConflict(Exception):
    """A token, account, or identity state is unsafe for this operation."""


def digest_account_security_token(*, raw_token, purpose):
    if not isinstance(raw_token, str) or not raw_token:
        raise AccountSecurityConflict()
    try:
        material = f"hustlytasker:{purpose}:{raw_token}".encode("utf-8")
    except UnicodeEncodeError as exc:
        raise AccountSecurityConflict() from exc
    return hashlib.sha256(material).hexdigest()


def _password_fingerprint(user):
    """Bind a reset credential to the exact encoded password state."""

    return hashlib.sha256(user.password.encode("utf-8")).hexdigest()


def _write_security_audit(*, user, token, action, before, after):
    AuditLog.objects.create(
        user=user,
        action=action,
        entity_name="AccountSecurityToken",
        entity_id=token.id,
        metadata={
            "purpose": token.purpose,
            "before": before,
            "after": after,
        },
    )


def _materialize_expiration(*, token, now):
    if (
        token.status == AccountSecurityToken.Status.PENDING
        and token.expires_at <= now
    ):
        before = {"status": token.status}
        token.status = AccountSecurityToken.Status.EXPIRED
        token.expired_at = now
        token.save(update_fields=("status", "expired_at", "updated_at"))
        _write_security_audit(
            user=token.user,
            token=token,
            action="account.security_token.expired",
            before=before,
            after={"status": token.status},
        )
        return True
    return False


@sensitive_variables("raw_token")
def _issue_token_locked(*, user, purpose, ttl, now, raise_on_delivery_failure):
    previous = (
        AccountSecurityToken.objects.select_for_update()
        .filter(
            user=user,
            purpose=purpose,
            status=AccountSecurityToken.Status.PENDING,
        )
        .first()
    )
    if previous is not None:
        if not _materialize_expiration(token=previous, now=now):
            before = {"status": previous.status}
            previous.status = AccountSecurityToken.Status.REVOKED
            previous.revoked_at = now
            previous.save(
                update_fields=("status", "revoked_at", "updated_at"),
            )
            _write_security_audit(
                user=user,
                token=previous,
                action="account.security_token.rotated",
                before=before,
                after={"status": previous.status},
            )

    raw_token = secrets.token_urlsafe(32)
    token = AccountSecurityToken(
        user=user,
        purpose=purpose,
        email_normalized=normalize_account_email(user.email),
        token_digest=digest_account_security_token(
            raw_token=raw_token,
            purpose=purpose,
        ),
        password_fingerprint=(
            _password_fingerprint(user)
            if purpose == AccountSecurityToken.Purpose.PASSWORD_RESET
            else None
        ),
        status=AccountSecurityToken.Status.PENDING,
        expires_at=now + ttl,
        delivery_status=AccountSecurityToken.DeliveryStatus.QUEUED,
        replaces=previous,
    )
    token.created_at = now
    try:
        token.full_clean()
        token.save()
    except (IntegrityError, ValidationError) as exc:
        raise AccountSecurityConflict() from exc

    _write_security_audit(
        user=user,
        token=token,
        action=(
            "account.email_verification.requested"
            if purpose == AccountSecurityToken.Purpose.EMAIL_VERIFICATION
            else "account.password_reset.requested"
        ),
        before=None,
        after={
            "status": token.status,
            "delivery_status": token.delivery_status,
        },
    )
    schedule_account_security_delivery(
        token=token,
        raw_token=raw_token,
        raise_on_failure=raise_on_delivery_failure,
    )
    return token


def _resolve_current_unique_user(normalized_email):
    try:
        return resolve_unique_user_for_email(normalized_email)
    except AmbiguousAccountIdentity as exc:
        raise AccountSecurityConflict() from exc


def request_email_verification(*, user):
    ensure_account_security_delivery_available()
    with transaction.atomic():
        locked_user = User.objects.select_for_update().filter(
            id=user.id,
            is_active=True,
        ).first()
        if locked_user is None:
            raise AccountSecurityConflict()

        normalized_email = normalize_account_email(locked_user.email)
        resolved = _resolve_current_unique_user(normalized_email)
        if resolved is None or resolved.id != locked_user.id:
            raise AccountSecurityConflict()
        if locked_user.is_email_verified:
            return None

        return _issue_token_locked(
            user=locked_user,
            purpose=AccountSecurityToken.Purpose.EMAIL_VERIFICATION,
            ttl=EMAIL_VERIFICATION_TTL,
            now=timezone.now(),
            raise_on_delivery_failure=True,
        )


def request_password_reset(*, email):
    # Check before identity resolution so backend misconfiguration has the same
    # externally visible result for every submitted address.
    ensure_account_security_delivery_available()
    normalized_email = normalize_account_email(email)
    try:
        user = resolve_unique_user_for_email(normalized_email)
    except AmbiguousAccountIdentity:
        return None
    if user is None or not user.is_active or not user.has_usable_password():
        return None

    with transaction.atomic():
        locked_user = User.objects.select_for_update().filter(
            id=user.id,
            is_active=True,
        ).first()
        if (
            locked_user is None
            or not locked_user.has_usable_password()
            or normalize_account_email(locked_user.email) != normalized_email
        ):
            return None
        try:
            resolved = resolve_unique_user_for_email(normalized_email)
        except AmbiguousAccountIdentity:
            return None
        if resolved is None or resolved.id != locked_user.id:
            return None

        return _issue_token_locked(
            user=locked_user,
            purpose=AccountSecurityToken.Purpose.PASSWORD_RESET,
            ttl=PASSWORD_RESET_TTL,
            now=timezone.now(),
            raise_on_delivery_failure=False,
        )


@sensitive_variables("raw_token")
def _lookup_candidate(*, raw_token, purpose):
    digest = digest_account_security_token(
        raw_token=raw_token,
        purpose=purpose,
    )
    candidate = AccountSecurityToken.objects.only("id", "user_id").filter(
        token_digest=digest,
        purpose=purpose,
    ).first()
    if candidate is None:
        raise AccountSecurityConflict()
    return candidate, digest


def _lock_candidate(*, candidate, digest, purpose):
    user = User.objects.select_for_update().filter(
        id=candidate.user_id,
        is_active=True,
    ).first()
    if user is None:
        raise AccountSecurityConflict()
    token = AccountSecurityToken.objects.select_for_update().filter(
        id=candidate.id,
        user=user,
        purpose=purpose,
        token_digest=digest,
    ).first()
    if (
        token is None
        or token.status != AccountSecurityToken.Status.PENDING
        or token.delivery_status != AccountSecurityToken.DeliveryStatus.SENT
    ):
        raise AccountSecurityConflict()
    return user, token


def _validate_locked_identity(*, user, token):
    normalized_email = normalize_account_email(user.email)
    if normalized_email != token.email_normalized:
        raise AccountSecurityConflict()
    resolved = _resolve_current_unique_user(normalized_email)
    if resolved is None or resolved.id != user.id:
        raise AccountSecurityConflict()
    return normalized_email


@sensitive_variables("raw_token")
def confirm_email_verification(*, actor, raw_token):
    purpose = AccountSecurityToken.Purpose.EMAIL_VERIFICATION
    candidate, digest = _lookup_candidate(raw_token=raw_token, purpose=purpose)
    expired = False
    with transaction.atomic():
        user, token = _lock_candidate(
            candidate=candidate,
            digest=digest,
            purpose=purpose,
        )
        if user.id != actor.id:
            raise AccountSecurityConflict()

        now = timezone.now()
        if _materialize_expiration(token=token, now=now):
            expired = True
        else:
            normalized_email = _validate_locked_identity(user=user, token=token)
            user.email_verified_at = now
            user.verified_email_normalized = normalized_email
            try:
                user.save(
                    update_fields=(
                        "email_verified_at",
                        "verified_email_normalized",
                        "updated_at",
                    )
                )
            except IntegrityError as exc:
                raise AccountSecurityConflict() from exc

            token.status = AccountSecurityToken.Status.CONSUMED
            token.consumed_at = now
            token.save(
                update_fields=("status", "consumed_at", "updated_at"),
            )
            _write_security_audit(
                user=user,
                token=token,
                action="account.email_verification.confirmed",
                before={"status": AccountSecurityToken.Status.PENDING},
                after={"status": token.status},
            )

    if expired:
        raise AccountSecurityConflict()
    return user


@sensitive_variables("raw_token", "new_password")
def confirm_password_reset(*, raw_token, new_password):
    purpose = AccountSecurityToken.Purpose.PASSWORD_RESET
    candidate, digest = _lookup_candidate(raw_token=raw_token, purpose=purpose)
    expired = False
    with transaction.atomic():
        user, token = _lock_candidate(
            candidate=candidate,
            digest=digest,
            purpose=purpose,
        )
        now = timezone.now()
        if _materialize_expiration(token=token, now=now):
            expired = True
        else:
            _validate_locked_identity(user=user, token=token)
            if (
                not user.has_usable_password()
                or not hmac.compare_digest(
                    token.password_fingerprint or "",
                    _password_fingerprint(user),
                )
            ):
                raise AccountSecurityConflict()
            password_validation.validate_password(new_password, user=user)
            token.status = AccountSecurityToken.Status.CONSUMED
            token.consumed_at = now
            token.save(
                update_fields=("status", "consumed_at", "updated_at"),
            )

            # Consume before saving the new password so User.save() can revoke
            # every *other* pending reset credential without revoking this one.
            user.set_password(new_password)
            user.save(update_fields=("password", "updated_at"))
            _write_security_audit(
                user=user,
                token=token,
                action="account.password_reset.completed",
                before={"status": AccountSecurityToken.Status.PENDING},
                after={"status": token.status},
            )

    if expired:
        raise AccountSecurityConflict()
    return user
