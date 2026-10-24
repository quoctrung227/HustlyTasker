import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from apps.audit.models import AuditLog

from .access import TenantAccessNotFound, resolve_profile_access_context
from .invitation_delivery import (
    ensure_invitation_delivery_available,
    schedule_invitation_delivery,
)
from .invitation_identity import (
    AmbiguousInvitationIdentity,
    normalize_invitation_email,
    resolve_unique_user_for_invitation_email,
)
from .models import (
    Profile,
    ProfileInvitation,
    ProfileMembership,
    WorkspaceMember,
)


User = get_user_model()
INVITATION_TTL = timedelta(days=7)
INVITATION_RATE_WINDOW = timedelta(hours=24)
MAX_INVITATIONS_PER_RECIPIENT = 5
MAX_INVITATIONS_PER_INVITER = 30


class InvitationConflict(Exception):
    """Invitation state or identity is unsafe for the requested operation."""


class InvitationRateLimitExceeded(Exception):
    """A durable invitation issuance limit has been reached."""


def _write_invitation_audit(*, actor, invitation, action, before, after):
    AuditLog.objects.create(
        user=actor,
        action=action,
        entity_name="ProfileInvitation",
        entity_id=invitation.id,
        metadata={
            "profile_id": str(invitation.profile_id),
            "requested_role": invitation.requested_role,
            "before": before,
            "after": after,
        },
    )


def _write_profile_membership_audit(*, actor, membership, action, before, after):
    AuditLog.objects.create(
        user=actor,
        action=action,
        entity_name="ProfileMembership",
        entity_id=membership.id,
        metadata={
            "profile_id": str(membership.profile_id),
            "target_user_id": str(membership.user_id),
            "before": before,
            "after": after,
        },
    )


def _write_workspace_rejoin_revoke_audit(*, actor, membership):
    AuditLog.objects.create(
        user=actor,
        action="workspace.membership.revoked_on_profile_rejoin",
        entity_name="WorkspaceMember",
        entity_id=membership.id,
        metadata={
            "profile_id": str(membership.workspace.profile_id),
            "workspace_id": str(membership.workspace_id),
            "target_user_id": str(membership.user_id),
            "before": {
                "role": membership.role,
                "is_active": True,
            },
            "after": {
                "role": membership.role,
                "is_active": False,
            },
        },
    )


def _can_issue_role(membership, requested_role):
    if membership.role == ProfileMembership.Role.OWNER:
        return requested_role in (
            ProfileInvitation.Role.ADMIN,
            ProfileInvitation.Role.MEMBER,
        )
    return (
        membership.role == ProfileMembership.Role.ADMIN
        and requested_role == ProfileInvitation.Role.MEMBER
    )


def _lock_manager_context(*, actor, profile_id, requested_role=None):
    context = resolve_profile_access_context(actor, profile_id)
    profile = Profile.objects.select_for_update().filter(
        id=context.profile_id,
    ).first()
    if profile is None:
        raise TenantAccessNotFound()
    if profile.status != Profile.Status.ACTIVE:
        raise PermissionDenied(
            "Invitation changes are not allowed while the Profile is archived."
        )

    membership = ProfileMembership.objects.select_for_update().filter(
        id=context.membership_id,
        profile_id=context.profile_id,
        user_id=context.user_id,
        user__is_active=True,
        is_active=True,
        role__in=(
            ProfileMembership.Role.OWNER,
            ProfileMembership.Role.ADMIN,
        ),
    ).first()
    if membership is None:
        if context.profile_role == ProfileMembership.Role.MEMBER:
            raise PermissionDenied("Profile invitation management is not allowed.")
        raise TenantAccessNotFound()

    if requested_role is not None and not _can_issue_role(
        membership,
        requested_role,
    ):
        raise PermissionDenied("The requested invitation role is not allowed.")
    return profile, membership


def _acquire_recipient_rate_lock(normalized_email):
    """Serialize a recipient counter across actors when PostgreSQL is active."""

    if connection.vendor != "postgresql":
        return
    digest = hashlib.sha256(normalized_email.encode("utf-8")).digest()
    advisory_key = int.from_bytes(digest[:8], byteorder="big", signed=True)
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", [advisory_key])


def _enforce_issuance_limits(*, actor, normalized_email, now):
    User.objects.select_for_update().filter(id=actor.id).get()
    _acquire_recipient_rate_lock(normalized_email)
    window_start = now - INVITATION_RATE_WINDOW

    inviter_count = ProfileInvitation.objects.filter(
        invited_by_membership__user_id=actor.id,
        created_at__gte=window_start,
    ).count()
    recipient_count = ProfileInvitation.objects.filter(
        recipient_email_normalized=normalized_email,
        created_at__gte=window_start,
    ).count()
    if (
        inviter_count >= MAX_INVITATIONS_PER_INVITER
        or recipient_count >= MAX_INVITATIONS_PER_RECIPIENT
    ):
        raise InvitationRateLimitExceeded()


def _materialize_expiration(*, invitation, actor, now):
    if (
        invitation.status == ProfileInvitation.Status.PENDING
        and invitation.expires_at <= now
    ):
        before = {"status": invitation.status}
        invitation.status = ProfileInvitation.Status.EXPIRED
        invitation.expired_at = now
        invitation.save(
            update_fields=("status", "expired_at", "updated_at"),
        )
        _write_invitation_audit(
            actor=actor,
            invitation=invitation,
            action="profile.invitation.expired",
            before=before,
            after={"status": invitation.status},
        )
        return True
    return False


def _resolve_recipient_account(normalized_email):
    try:
        return resolve_unique_user_for_invitation_email(normalized_email)
    except AmbiguousInvitationIdentity as exc:
        raise InvitationConflict() from exc


@sensitive_variables("raw_token")
def _issue_invitation_locked(
    *,
    profile,
    inviter_membership,
    normalized_email,
    requested_role,
    recipient_user,
    now,
    replaces=None,
):
    raw_token = secrets.token_urlsafe(32)
    token_digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    invitation = ProfileInvitation(
        profile=profile,
        recipient_email_normalized=normalized_email,
        recipient_user=recipient_user,
        requested_role=requested_role,
        invited_by_membership=inviter_membership,
        token_digest=token_digest,
        status=ProfileInvitation.Status.PENDING,
        expires_at=now + INVITATION_TTL,
        delivery_status=ProfileInvitation.DeliveryStatus.QUEUED,
        replaces=replaces,
    )
    # ``created_at`` is assigned again by ``auto_now_add`` on insert. Setting
    # it for validation lets the database-equivalent expiry constraint be
    # checked before the row is written.
    invitation.created_at = now
    try:
        invitation.full_clean()
    except ValidationError as exc:
        raise InvitationConflict() from exc
    try:
        invitation.save()
    except IntegrityError as exc:
        raise InvitationConflict() from exc

    _write_invitation_audit(
        actor=inviter_membership.user,
        invitation=invitation,
        action="profile.invitation.created",
        before=None,
        after={
            "status": invitation.status,
            "delivery_status": invitation.delivery_status,
        },
    )
    schedule_invitation_delivery(
        invitation=invitation,
        raw_token=raw_token,
    )
    return invitation


@sensitive_variables("raw_token")
def create_profile_invitation(
    *,
    actor,
    profile_id,
    recipient_email,
    requested_role=ProfileInvitation.Role.MEMBER,
):
    normalized_email = normalize_invitation_email(recipient_email)
    if not normalized_email:
        raise ValidationError({"recipient_email": "This field may not be blank."})
    if requested_role not in ProfileInvitation.Role.values:
        raise ValidationError({"requested_role": "Unsupported invitation role."})

    with transaction.atomic():
        profile, inviter_membership = _lock_manager_context(
            actor=actor,
            profile_id=profile_id,
            requested_role=requested_role,
        )
        ensure_invitation_delivery_available()
        now = timezone.now()
        _enforce_issuance_limits(
            actor=actor,
            normalized_email=normalized_email,
            now=now,
        )

        pending = ProfileInvitation.objects.select_for_update().filter(
            profile=profile,
            recipient_email_normalized=normalized_email,
            status=ProfileInvitation.Status.PENDING,
        ).first()
        if pending is not None:
            if not _materialize_expiration(
                invitation=pending,
                actor=actor,
                now=now,
            ):
                raise InvitationConflict()

        recipient_user = _resolve_recipient_account(normalized_email)
        if recipient_user is not None and ProfileMembership.objects.filter(
            profile=profile,
            user=recipient_user,
            is_active=True,
        ).exists():
            raise InvitationConflict()
        if recipient_user is not None:
            pending_for_user = (
                ProfileInvitation.objects.select_for_update()
                .filter(
                    profile=profile,
                    recipient_user=recipient_user,
                    status=ProfileInvitation.Status.PENDING,
                )
                .first()
            )
            if pending_for_user is not None and not _materialize_expiration(
                invitation=pending_for_user,
                actor=actor,
                now=now,
            ):
                raise InvitationConflict()

        return _issue_invitation_locked(
            profile=profile,
            inviter_membership=inviter_membership,
            normalized_email=normalized_email,
            requested_role=requested_role,
            recipient_user=recipient_user,
            now=now,
        )


def _get_locked_manager_invitation(
    *,
    actor,
    profile_id,
    invitation_id,
):
    profile, manager_membership = _lock_manager_context(
        actor=actor,
        profile_id=profile_id,
    )
    invitation = ProfileInvitation.objects.select_for_update().filter(
        id=invitation_id,
        profile=profile,
    ).first()
    if invitation is None:
        raise TenantAccessNotFound()
    if not _can_issue_role(manager_membership, invitation.requested_role):
        raise TenantAccessNotFound()
    return profile, manager_membership, invitation


def revoke_profile_invitation(*, actor, profile_id, invitation_id):
    expired = False
    result = None
    with transaction.atomic():
        _, _, invitation = _get_locked_manager_invitation(
            actor=actor,
            profile_id=profile_id,
            invitation_id=invitation_id,
        )
        now = timezone.now()
        if _materialize_expiration(
            invitation=invitation,
            actor=actor,
            now=now,
        ):
            expired = True
        else:
            if invitation.status != ProfileInvitation.Status.PENDING:
                raise InvitationConflict()

            before = {"status": invitation.status}
            invitation.status = ProfileInvitation.Status.REVOKED
            invitation.revoked_at = now
            invitation.revoked_by = actor
            invitation.save(
                update_fields=(
                    "status",
                    "revoked_at",
                    "revoked_by",
                    "updated_at",
                )
            )
            _write_invitation_audit(
                actor=actor,
                invitation=invitation,
                action="profile.invitation.revoked",
                before=before,
                after={"status": invitation.status},
            )
            result = invitation

    if expired:
        raise InvitationConflict()
    return result


def resend_profile_invitation(*, actor, profile_id, invitation_id):
    with transaction.atomic():
        profile, manager_membership, invitation = _get_locked_manager_invitation(
            actor=actor,
            profile_id=profile_id,
            invitation_id=invitation_id,
        )
        ensure_invitation_delivery_available()
        now = timezone.now()
        _materialize_expiration(
            invitation=invitation,
            actor=actor,
            now=now,
        )
        if invitation.status not in (
            ProfileInvitation.Status.PENDING,
            ProfileInvitation.Status.EXPIRED,
        ):
            raise InvitationConflict()
        if ProfileInvitation.objects.filter(replaces=invitation).exists():
            raise InvitationConflict()

        _enforce_issuance_limits(
            actor=actor,
            normalized_email=invitation.recipient_email_normalized,
            now=now,
        )

        if invitation.status == ProfileInvitation.Status.PENDING:
            before = {"status": invitation.status}
            invitation.status = ProfileInvitation.Status.REVOKED
            invitation.revoked_at = now
            invitation.revoked_by = actor
            invitation.save(
                update_fields=(
                    "status",
                    "revoked_at",
                    "revoked_by",
                    "updated_at",
                )
            )
            _write_invitation_audit(
                actor=actor,
                invitation=invitation,
                action="profile.invitation.rotated",
                before=before,
                after={"status": invitation.status},
            )

        recipient_user = _resolve_recipient_account(
            invitation.recipient_email_normalized
        )
        if recipient_user is not None and ProfileMembership.objects.filter(
            profile=profile,
            user=recipient_user,
            is_active=True,
        ).exists():
            raise InvitationConflict()

        replacement = _issue_invitation_locked(
            profile=profile,
            inviter_membership=manager_membership,
            normalized_email=invitation.recipient_email_normalized,
            requested_role=invitation.requested_role,
            recipient_user=recipient_user,
            now=now,
            replaces=invitation,
        )
        _write_invitation_audit(
            actor=actor,
            invitation=replacement,
            action="profile.invitation.resent",
            before={"replaces_invitation_id": str(invitation.id)},
            after={"status": replacement.status},
        )
        return replacement


@sensitive_variables("raw_token")
def _lookup_token_candidate(raw_token):
    if not isinstance(raw_token, str) or not raw_token:
        raise InvitationConflict()
    digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    candidate = ProfileInvitation.objects.only("id", "profile_id").filter(
        token_digest=digest,
    ).first()
    if candidate is None:
        raise InvitationConflict()
    return candidate, digest


def _validate_recipient_locked(*, actor, invitation):
    locked_actor = User.objects.select_for_update().filter(
        id=actor.id,
        is_active=True,
    ).first()
    if locked_actor is None:
        raise InvitationConflict()
    normalized_actor_email = normalize_invitation_email(locked_actor.email)
    if normalized_actor_email != invitation.recipient_email_normalized:
        raise InvitationConflict()
    recipient_user = _resolve_recipient_account(normalized_actor_email)
    if recipient_user is None or recipient_user.id != actor.id:
        raise InvitationConflict()
    if (
        invitation.recipient_user_id is not None
        and invitation.recipient_user_id != actor.id
    ):
        raise InvitationConflict()
    return locked_actor


def _validate_original_inviter_locked(invitation):
    inviter = ProfileMembership.objects.select_for_update().filter(
        id=invitation.invited_by_membership_id,
        profile_id=invitation.profile_id,
        user__is_active=True,
        is_active=True,
    ).first()
    if inviter is None or not _can_issue_role(inviter, invitation.requested_role):
        raise InvitationConflict()


def _lock_usable_token(*, actor, candidate, digest, now):
    profile = Profile.objects.select_for_update().filter(
        id=candidate.profile_id,
    ).first()
    if profile is None:
        raise InvitationConflict()
    invitation = ProfileInvitation.objects.select_for_update().filter(
        id=candidate.id,
        profile=profile,
        token_digest=digest,
    ).select_related("profile").first()
    if invitation is None:
        raise InvitationConflict()
    if (
        profile.status != Profile.Status.ACTIVE
        or invitation.status != ProfileInvitation.Status.PENDING
        or invitation.delivery_status != ProfileInvitation.DeliveryStatus.SENT
    ):
        raise InvitationConflict()
    _validate_recipient_locked(actor=actor, invitation=invitation)
    if _materialize_expiration(invitation=invitation, actor=actor, now=now):
        return profile, invitation, False
    return profile, invitation, True


def _revoke_stale_workspace_access(*, actor, profile, user, now):
    memberships = list(
        WorkspaceMember.objects.select_for_update()
        .select_related("workspace")
        .filter(
            workspace__profile=profile,
            user=user,
            is_active=True,
        )
        .order_by("id")
    )
    for membership in memberships:
        membership.is_active = False
        membership.updated_at = now
        WorkspaceMember.objects.filter(id=membership.id).update(
            is_active=False,
            updated_at=now,
        )
        _write_workspace_rejoin_revoke_audit(
            actor=actor,
            membership=membership,
        )


@sensitive_variables("token")
def accept_profile_invitation(*, actor, token):
    candidate, digest = _lookup_token_candidate(token)
    expired = False
    result = None
    with transaction.atomic():
        now = timezone.now()
        profile, invitation, usable = _lock_usable_token(
            actor=actor,
            candidate=candidate,
            digest=digest,
            now=now,
        )
        if not usable:
            expired = True
        else:
            _validate_original_inviter_locked(invitation)
            memberships = list(
                ProfileMembership.objects.select_for_update()
                .filter(profile=profile, user=actor)
                .order_by("created_at", "id")
            )
            if any(item.is_active for item in memberships):
                raise InvitationConflict()

            inactive_memberships = [item for item in memberships if not item.is_active]
            if len(inactive_memberships) > 1:
                raise InvitationConflict()
            if inactive_memberships:
                membership = inactive_memberships[0]
                if (
                    membership.role == ProfileMembership.Role.OWNER
                    or membership.role != invitation.requested_role
                ):
                    raise InvitationConflict()
                before_membership = {
                    "role": membership.role,
                    "is_active": membership.is_active,
                }
                membership.is_active = True
                membership.full_clean()
                membership.save(update_fields=("is_active", "updated_at"))
                membership_action = "profile.membership.reactivated_by_invitation"
            else:
                membership = ProfileMembership(
                    profile=profile,
                    user=actor,
                    role=invitation.requested_role,
                    is_active=True,
                )
                membership.full_clean()
                membership.save()
                before_membership = None
                membership_action = "profile.membership.created_by_invitation"

            _revoke_stale_workspace_access(
                actor=actor,
                profile=profile,
                user=actor,
                now=now,
            )
            _write_profile_membership_audit(
                actor=actor,
                membership=membership,
                action=membership_action,
                before=before_membership,
                after={
                    "role": membership.role,
                    "is_active": membership.is_active,
                },
            )

            before = {"status": invitation.status}
            invitation.status = ProfileInvitation.Status.ACCEPTED
            invitation.accepted_at = now
            invitation.accepted_by = actor
            if invitation.recipient_user_id is None:
                invitation.recipient_user = actor
            invitation.save(
                update_fields=(
                    "status",
                    "accepted_at",
                    "accepted_by",
                    "recipient_user",
                    "updated_at",
                )
            )
            _write_invitation_audit(
                actor=actor,
                invitation=invitation,
                action="profile.invitation.accepted",
                before=before,
                after={"status": invitation.status},
            )
            result = membership

    if expired:
        raise InvitationConflict()
    return result


@sensitive_variables("token")
def decline_profile_invitation(*, actor, token):
    candidate, digest = _lookup_token_candidate(token)
    expired = False
    result = None
    with transaction.atomic():
        now = timezone.now()
        _, invitation, usable = _lock_usable_token(
            actor=actor,
            candidate=candidate,
            digest=digest,
            now=now,
        )
        if not usable:
            expired = True
        else:
            before = {"status": invitation.status}
            invitation.status = ProfileInvitation.Status.DECLINED
            invitation.declined_at = now
            invitation.declined_by = actor
            if invitation.recipient_user_id is None:
                invitation.recipient_user = actor
            invitation.save(
                update_fields=(
                    "status",
                    "declined_at",
                    "declined_by",
                    "recipient_user",
                    "updated_at",
                )
            )
            _write_invitation_audit(
                actor=actor,
                invitation=invitation,
                action="profile.invitation.declined",
                before=before,
                after={"status": invitation.status},
            )
            result = invitation

    if expired:
        raise InvitationConflict()
    return result
