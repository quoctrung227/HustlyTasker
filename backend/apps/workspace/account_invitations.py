"""Account-bound invitations. Legacy email credentials remain a separate path."""
from datetime import timedelta
import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Case, CharField, Exists, F, Func, OuterRef, Q, Value, When
from django.db.models.functions import Coalesce, Concat, Lower, Substr, Trim
from django.utils import timezone
from apps.common.deletion import profile_live_q

from .access import TenantAccessNotFound
from .models import (
    InvitationDirectoryAccess, InvitationEmailAttempt, Profile, ProfileInvitation,
    ProfileMembership,
)
from .invitation_services import (
    INVITATION_TTL, InvitationConflict, InvitationRateLimitExceeded, _can_issue_role,
    _join_current_workspace_after_acceptance, _lock_manager_context,
    _materialize_expiration, _revoke_stale_workspace_access,
    _validate_original_inviter_locked, _write_invitation_audit,
    _write_profile_membership_audit,
)

User = get_user_model()
_UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
_PRIVATE = r"[@\x00-\x1f\x7f-\x9f]|" + _UUID + r"|([0-9][^0-9]*){7}"


def _safe_text(value):
    if not isinstance(value, str) or re.search(_PRIVATE, value) or any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        return ""
    return " ".join(value.split())


def safe_account_username(user):
    value = _safe_text(user.username)
    return value if re.fullmatch(r"[\w.+-]+", value) else None


def safe_account_display_label(user):
    return _safe_text(user.get_full_name()) or safe_account_username(user) or "Tài khoản HustlyTasker"


def masked_account_email(user):
    value = (user.email or "").strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value) or any(ord(c) < 32 for c in value):
        return None
    local, domain = value.split("@", 1)
    return f"{local[0]}***@{domain[0]}***"


def _identity_queryset():
    """Project only searchable, approved display fields inside PostgreSQL."""
    full_name = Trim(Func(Concat("first_name", Value(" "), "last_name"), Value(r"\s+"), Value(" "), Value("g"), function="regexp_replace", output_field=CharField()))
    private = r"[@[:cntrl:]]|" + _UUID + r"|([0-9][^0-9]*){7}"
    query = User.objects.filter(is_active=True).only("id", "first_name", "last_name", "username", "email").annotate(
        _dir_raw_name=Concat("first_name", Value(" "), "last_name"), _dir_full_name=full_name,
        _dir_email=Lower(Trim("email")),
    )
    query = query.annotate(_dir_username=Case(
        When(Q(username__regex=r"^[[:alnum:]_.+-]+$") & ~Q(username__regex=private), then=F("username")),
        default=Value(None), output_field=CharField(),
    ))
    query = query.annotate(_dir_name=Case(
        When(~Q(_dir_full_name="") & ~Q(_dir_raw_name__regex=private), then=F("_dir_full_name")),
        default=Coalesce("_dir_username", Value("Tài khoản HustlyTasker")), output_field=CharField(),
    ))
    domain = Func(Lower(Trim("email")), Value("@"), Value(2), function="split_part", output_field=CharField())
    query = query.annotate(_dir_masked=Case(
        When(Q(_dir_username__isnull=True) & Q(email__regex=r"^[^@\s]+@[^@\s]+\.[^@\s]+$"), then=Concat(Lower(Substr(Trim("email"), 1, 1)), Value("***@"), Substr(domain, 1, 1), Value("***"))),
        default=Value(None), output_field=CharField(),
    ))
    return query


def _directory_queryset(*, profile_id, manager, now):
    query = _identity_queryset()
    duplicates = _identity_queryset().exclude(pk=OuterRef("pk")).filter(
        Q(_dir_username__iexact=OuterRef("_dir_username"))
        | Q(_dir_username__isnull=True, _dir_name__iexact=OuterRef("_dir_name"), _dir_masked=OuterRef("_dir_masked"))
    )
    pending = ProfileInvitation.objects.filter(profile_id=profile_id, status="PENDING", expires_at__gt=now).filter(
        Q(recipient_user_id=OuterRef("pk"))
        | Q(acceptance_kind="EMAIL_TOKEN", recipient_user__isnull=True, recipient_email_normalized=OuterRef("_dir_email"))
    )
    visible_pending = pending
    if manager.role == ProfileMembership.Role.ADMIN:
        visible_pending = pending.filter(requested_role="MEMBER")
    authority = ProfileMembership.objects.filter(
        profile_live_q("profile"),
        pk=manager.pk, profile_id=profile_id, user_id=manager.user_id,
        is_active=True, user__is_active=True, role=manager.role,
        profile__status=Profile.Status.ACTIVE,
    )
    return query.annotate(
        _dir_ambiguous=Exists(duplicates),
        _dir_member=Exists(ProfileMembership.objects.filter(profile_id=profile_id, user_id=OuterRef("pk"), is_active=True)),
        _dir_pending=Exists(pending), _dir_visible_pending=Exists(visible_pending),
        _dir_authorized=Exists(authority),
    ).filter(_dir_authorized=True)


def candidate_data(user):
    identifiable = bool(user._dir_username or user._dir_masked) and not user._dir_ambiguous
    relation = "AVAILABLE"
    if user._dir_member:
        relation = "ACTIVE_MEMBER"
    elif user._dir_pending:
        relation = "PENDING_INVITATION" if user._dir_visible_pending else "UNAVAILABLE"
    elif not identifiable:
        relation = "UNAVAILABLE"
    return {"id": str(user.pk), "display_label": user._dir_name,
            "username": user._dir_username, "masked_email": user._dir_masked,
            "relation": relation, "can_invite": identifiable and relation == "AVAILABLE"}


def invitation_candidates(*, actor, profile_id, search=""):
    with transaction.atomic():
        profile, manager = _lock_manager_context(actor=actor, profile_id=profile_id, lock_user=False)
        # User lock makes the rolling window shared across Profiles/processes.
        locked_actor = User.objects.select_for_update().get(pk=actor.pk)
        if not locked_actor.is_active:
            raise TenantAccessNotFound()
        now = timezone.now()
        if InvitationDirectoryAccess.objects.filter(user_id=actor.pk, created_at__gte=now-timedelta(minutes=1)).count() >= 30:
            raise InvitationRateLimitExceeded()
        InvitationDirectoryAccess.objects.create(user_id=actor.pk)
    query = _directory_queryset(profile_id=profile.pk, manager=manager, now=now)
    if search:
        query = query.filter(Q(_dir_name__icontains=search) | Q(_dir_username__icontains=search) | Q(_dir_masked__icontains=search))
    return query.order_by(Lower("_dir_name"), "id")


def recipient_invitations_visible_to(actor):
    if not getattr(actor, "is_authenticated", False) or not getattr(actor, "is_active", False):
        return ProfileInvitation.objects.none()
    return ProfileInvitation.objects.filter(
        profile_live_q("profile"),
        acceptance_kind=ProfileInvitation.AcceptanceKind.ACCOUNT,
        recipient_user_id=actor.pk, recipient_user__is_active=True,
        invited_by_membership__profile_id=F("profile_id"),
    ).select_related("profile", "recipient_user", "invited_by_membership__user")


def recipient_invitation_capabilities(invitation, actor, membership_rows=None):
    own = (invitation.acceptance_kind == ProfileInvitation.AcceptanceKind.ACCOUNT
           and invitation.recipient_user_id == getattr(actor, "pk", None)
           and bool(getattr(actor, "is_active", False)))
    live_profile = invitation.profile.deleted_at is None
    pending = own and live_profile and invitation.effective_status == "PENDING" and invitation.profile.status == "ACTIVE"
    inviter = invitation.invited_by_membership
    eligible_inviter = inviter.profile_id == invitation.profile_id and inviter.is_active and inviter.user.is_active and _can_issue_role(inviter, invitation.requested_role)
    if not own:
        rows = []
    elif membership_rows is not None:
        rows = membership_rows.get(str(invitation.profile_id), [])
    else:
        rows = list(ProfileMembership.objects.filter(profile_id=invitation.profile_id, user_id=getattr(actor, "pk", None)).values("role", "is_active"))
    active = any(row["is_active"] for row in rows)
    inactive = [row for row in rows if not row["is_active"]]
    safe_rejoin = not inactive or (len(inactive) == 1 and inactive[0]["role"] == invitation.requested_role and inactive[0]["role"] != "OWNER")
    return {"can_accept": bool(pending and eligible_inviter and not active and safe_rejoin),
            "can_decline": bool(pending), "can_open_profile": bool(own and live_profile and active and invitation.profile.status == "ACTIVE")}


def _reserve_email_attempt(invitation, now):
    if InvitationEmailAttempt.objects.filter(invitation=invitation, created_at__gte=now-timedelta(hours=24)).count() >= 3:
        raise InvitationRateLimitExceeded()
    attempt = InvitationEmailAttempt.objects.create(invitation=invitation)
    invitation.delivery_status = ProfileInvitation.DeliveryStatus.QUEUED
    invitation.delivered_at = None
    invitation.save(update_fields=("delivery_status", "delivered_at", "updated_at"))
    from .account_invitation_delivery import schedule_account_invitation_delivery
    schedule_account_invitation_delivery(invitation=invitation, attempt=attempt)


def create_account_invitation(*, actor, profile_id, recipient_user_id, requested_role="MEMBER"):
    if requested_role not in ProfileInvitation.Role.values:
        raise ValidationError({"requested_role": "Unsupported invitation role."})
    with transaction.atomic():
        profile, manager = _lock_manager_context(actor=actor, profile_id=profile_id, requested_role=requested_role, lock_user=False)
        # Consistent User order prevents actor/recipient counter deadlocks across Profiles.
        users = {user.pk: user for user in User.objects.select_for_update().filter(pk__in=(actor.pk, recipient_user_id)).order_by("pk")}
        if actor.pk not in users or not users[actor.pk].is_active:
            raise TenantAccessNotFound()
        target = users.get(recipient_user_id)
        if target is None or not target.is_active:
            raise TenantAccessNotFound()
        now = timezone.now()
        if ProfileInvitation.objects.filter(invited_by_membership__user_id=actor.pk, created_at__gte=now-timedelta(hours=24)).count() >= 30 or ProfileInvitation.objects.filter(recipient_user_id=target.pk, created_at__gte=now-timedelta(hours=24)).count() >= 5:
            raise InvitationRateLimitExceeded()
        pending = list(ProfileInvitation.objects.select_for_update().filter(profile=profile, status="PENDING").filter(
            Q(recipient_user=target)
            | Q(acceptance_kind="EMAIL_TOKEN", recipient_user__isnull=True, recipient_email_normalized=target.email.strip().casefold())
        ).order_by("pk"))
        for old in pending:
            if not _materialize_expiration(invitation=old, actor=actor, now=now):
                raise InvitationConflict()
        candidate = _directory_queryset(profile_id=profile.pk, manager=manager, now=now).filter(pk=target.pk).first()
        if candidate is None or not candidate_data(candidate)["can_invite"]:
            raise InvitationConflict()
        invitation = ProfileInvitation(
            profile=profile, recipient_user=target, recipient_email_normalized=target.email.strip().casefold(),
            invited_by_membership=manager, requested_role=requested_role,
            acceptance_kind="ACCOUNT", token_digest=None, expires_at=now+INVITATION_TTL,
        )
        invitation.created_at = now
        invitation.full_clean()
        invitation.save()
        event = _write_invitation_audit(actor=actor, invitation=invitation, action="profile.invitation.created", before=None, after={"status": "PENDING", "delivery_status": "QUEUED"})
        from apps.notifications.services import emit_invitation_notification
        emitted = emit_invitation_notification(event=event, actor=actor, invitation=invitation)
        if len(emitted) != 1:
            raise InvitationConflict()
        _reserve_email_attempt(invitation, now)
    return invitation


def resend_account_invitation(*, actor, profile_id, invitation_id):
    from .invitation_services import _get_locked_manager_invitation
    with transaction.atomic():
        _, _, invitation = _get_locked_manager_invitation(actor=actor, profile_id=profile_id, invitation_id=invitation_id, lock_user=False)
        if invitation.acceptance_kind != "ACCOUNT" or invitation.effective_status != "PENDING":
            raise InvitationConflict()
        identities = {user.pk: user for user in User.objects.select_for_update().filter(pk__in=(actor.pk, invitation.recipient_user_id)).order_by("pk")}
        if actor.pk not in identities or not identities[actor.pk].is_active or invitation.recipient_user_id not in identities or not identities[invitation.recipient_user_id].is_active:
            raise InvitationConflict()
        _reserve_email_attempt(invitation, timezone.now())
        _write_invitation_audit(actor=actor, invitation=invitation, action="profile.invitation.email_retry_requested", before=None, after={"delivery_status": "QUEUED"})
    return invitation


def _locked_account_invitation(actor, invitation_id):
    probe = recipient_invitations_visible_to(actor).filter(pk=invitation_id).values("profile_id").first()
    if probe is None:
        raise TenantAccessNotFound()
    profile = Profile.objects.select_for_update().filter(profile_live_q(), pk=probe["profile_id"]).first()
    if profile is None:
        raise TenantAccessNotFound()
    invitation = recipient_invitations_visible_to(actor).select_for_update(of=("self",)).filter(pk=invitation_id, profile=profile).first()
    if invitation is None:
        raise TenantAccessNotFound()
    identities = {user.pk: user for user in User.objects.select_for_update().filter(
        pk__in=(actor.pk, invitation.invited_by_membership.user_id),
    ).order_by("pk")}
    if actor.pk not in identities or not identities[actor.pk].is_active:
        raise TenantAccessNotFound()
    return profile, invitation


def respond_account_invitation(*, actor, invitation_id, accept):
    expired = False
    with transaction.atomic():
        profile, invitation = _locked_account_invitation(actor, invitation_id)
        expected = "ACCEPTED" if accept else "DECLINED"
        if invitation.status == expected:
            return invitation  # Historical response never recreates or reactivates access.
        if profile.status != "ACTIVE" or invitation.status != "PENDING":
            raise InvitationConflict()
        now = timezone.now()
        if _materialize_expiration(invitation=invitation, actor=actor, now=now):
            expired = True
        else:
            if accept:
                _validate_original_inviter_locked(invitation, lock_user=False)
                rows = list(ProfileMembership.objects.select_for_update().filter(profile=profile, user_id=actor.pk).order_by("created_at", "pk"))
                if any(row.is_active for row in rows) or len(rows) > 1:
                    raise InvitationConflict()
                if rows:
                    membership = rows[0]
                    if membership.role == "OWNER" or membership.role != invitation.requested_role:
                        raise InvitationConflict()
                    before = {"role": membership.role, "is_active": False}
                    membership.is_active = True
                    membership.full_clean()
                    membership.save(update_fields=("is_active", "updated_at"))
                    action = "profile.membership.reactivated_by_invitation"
                else:
                    membership = ProfileMembership(profile=profile, user=actor, role=invitation.requested_role)
                    membership.full_clean()
                    membership.save()
                    before = None
                    action = "profile.membership.created_by_invitation"
                _revoke_stale_workspace_access(actor=actor, profile=profile, user=actor, now=now)
                _write_profile_membership_audit(actor=actor, membership=membership, action=action, before=before, after={"role": membership.role, "is_active": True})
                invitation.status = "ACCEPTED"
                invitation.accepted_at = now
                invitation.accepted_by = actor
                invitation.save(update_fields=("status", "accepted_at", "accepted_by", "updated_at"))
                _join_current_workspace_after_acceptance(actor=actor, profile=profile, membership=membership, now=now)
            else:
                invitation.status = "DECLINED"
                invitation.declined_at = now
                invitation.declined_by = actor
                invitation.save(update_fields=("status", "declined_at", "declined_by", "updated_at"))
            _write_invitation_audit(actor=actor, invitation=invitation, action="profile.invitation.accepted" if accept else "profile.invitation.declined", before={"status": "PENDING"}, after={"status": invitation.status})
    if expired:
        raise InvitationConflict()
    return invitation
