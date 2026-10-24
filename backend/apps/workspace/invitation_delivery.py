from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from apps.common.email_delivery import (
    EmailDeliveryUnavailable,
    ensure_default_email_delivery_available,
    send_default_email,
)

from .models import ProfileInvitation


class InvitationDeliveryUnavailable(RuntimeError):
    """Invitation delivery is unavailable or failed without exposing secrets."""

    default_message = "Invitation delivery is currently unavailable."

    def __init__(self):
        super().__init__(self.default_message)


def ensure_invitation_delivery_available():
    try:
        ensure_default_email_delivery_available()
    except EmailDeliveryUnavailable:
        raise InvitationDeliveryUnavailable() from None


@sensitive_variables("raw_token")
def schedule_invitation_delivery(*, invitation, raw_token):
    """Send only after commit, then persist an honest delivery outcome.

    The callback deliberately raises a generic exception after recording a
    failure.  In the normal request/autocommit path this lets the API return
    503 even though the invitation audit transaction remains durably stored.
    """

    invitation_id = invitation.id
    token_digest = invitation.token_digest
    recipient = invitation.recipient_email_normalized
    profile_name = invitation.profile.name

    @sensitive_variables()
    def deliver():
        attempted_at = timezone.now()
        claimed = ProfileInvitation.objects.filter(
            id=invitation_id,
            status=ProfileInvitation.Status.PENDING,
            token_digest=token_digest,
            expires_at__gt=attempted_at,
        ).update(
            delivery_status=ProfileInvitation.DeliveryStatus.QUEUED,
            delivery_attempted_at=attempted_at,
            updated_at=attempted_at,
        )
        if claimed != 1:
            raise InvitationDeliveryUnavailable()

        try:
            send_default_email(
                subject="Your HustlyTasker Profile invitation",
                body=(
                    f"You were invited to join the HustlyTasker Profile "
                    f"'{profile_name}'.\n\n"
                    "Sign in with this recipient email, then submit the following "
                    "single-use token to the authenticated invitation acceptance "
                    f"endpoint:\n\n{raw_token}\n\n"
                    "This token expires in seven days. If you did not expect this "
                    "invitation, you may ignore this message."
                ),
                recipient=recipient,
            )
        except EmailDeliveryUnavailable:
            failed_at = timezone.now()
            ProfileInvitation.objects.filter(
                id=invitation_id,
                status=ProfileInvitation.Status.PENDING,
                token_digest=token_digest,
            ).update(
                delivery_status=ProfileInvitation.DeliveryStatus.FAILED,
                delivery_attempted_at=attempted_at,
                delivered_at=None,
                updated_at=failed_at,
            )
            raise InvitationDeliveryUnavailable() from None

        delivered_at = timezone.now()
        updated = ProfileInvitation.objects.filter(
            id=invitation_id,
            status=ProfileInvitation.Status.PENDING,
            token_digest=token_digest,
        ).update(
            delivery_status=ProfileInvitation.DeliveryStatus.SENT,
            delivery_attempted_at=attempted_at,
            delivered_at=delivered_at,
            updated_at=delivered_at,
        )
        if updated != 1:
            raise InvitationDeliveryUnavailable()

    transaction.on_commit(deliver)
