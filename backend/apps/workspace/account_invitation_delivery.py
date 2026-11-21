"""Notification-only email for account invitations; never an acceptance proof."""
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from urllib.parse import urlsplit

from apps.common.email_delivery import EmailDeliveryUnavailable, send_default_email
from .models import InvitationEmailAttempt, Profile, ProfileInvitation


def _web_inbox_url():
    # Reuse configured trusted frontend origins; never trust a request header.
    for origin in settings.CSRF_TRUSTED_ORIGINS:
        parsed = urlsplit(origin)
        if parsed.scheme in ("http", "https") and parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and parsed.path in ("", "/"):
            return origin.rstrip("/") + "/invitations"
    if settings.ENVIRONMENT == "development":
        return "http://127.0.0.1:5173/invitations"
    raise EmailDeliveryUnavailable()


def schedule_account_invitation_delivery(*, invitation, attempt):
    invitation_id, profile_id, attempt_id = invitation.pk, invitation.profile_id, attempt.pk

    def deliver():
        # Same Profile-first order as acceptance/revocation. The bounded transport
        # call is serialized with retry so one process cannot race its own state.
        with transaction.atomic():
            profile = Profile.objects.select_for_update().filter(pk=profile_id).first()
            if profile is None or profile.deleted_at is not None:
                # A deleted tenant is unavailable. Preserve its reservation and
                # historical delivery state without dispatching or mutating it.
                return
            current = ProfileInvitation.objects.select_for_update(of=("self",)).select_related("profile", "invited_by_membership__user").get(pk=invitation_id)
            reservation = InvitationEmailAttempt.objects.select_for_update().get(pk=attempt_id, invitation=current)
            if reservation.status != "PENDING":
                return
            from django.contrib.auth import get_user_model
            recipient = get_user_model().objects.select_for_update().filter(pk=current.recipient_user_id, is_active=True).first()
            now = timezone.now()
            current.delivery_attempted_at = now
            success = False
            try:
                if recipient is None or current.acceptance_kind != "ACCOUNT" or current.status != "PENDING" or current.expires_at <= now or current.profile.status != "ACTIVE":
                    raise EmailDeliveryUnavailable()
                from .account_invitations import safe_account_display_label
                send_default_email(
                    subject="Your HustlyTasker Profile invitation",
                    body=(f"Bạn được mời tham gia tổ chức {current.profile.name}.\n"
                          f"Người mời: {safe_account_display_label(current.invited_by_membership.user)}.\n"
                          f"Vai trò: {current.requested_role}.\n"
                          "Đăng nhập đúng tài khoản HustlyTasker và mở trang Thông báo / Lời mời để chấp nhận hoặc từ chối.\n"
                          f"Trang lời mời: {_web_inbox_url()}\n"
                          "Email này chỉ thông báo; mở email không chấp nhận lời mời."),
                    recipient=recipient.email,
                )
                success = True
            except EmailDeliveryUnavailable:
                pass  # Web transaction already committed; never turn it into a false create failure.
            finished = timezone.now()
            reservation.status = "SENT" if success else "FAILED"
            reservation.finished_at = finished
            reservation.save(update_fields=("status", "finished_at", "updated_at"))
            current.delivery_status = "SENT" if success else "FAILED"
            current.delivered_at = finished if success else None
            current.save(update_fields=("delivery_status", "delivery_attempted_at", "delivered_at", "updated_at"))

    transaction.on_commit(deliver, robust=True)
