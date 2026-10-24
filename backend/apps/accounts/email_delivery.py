from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables

from apps.common.email_delivery import (
    EmailDeliveryUnavailable,
    ensure_default_email_delivery_available,
    send_default_email,
)

from .models import AccountSecurityToken


class AccountSecurityDeliveryUnavailable(RuntimeError):
    """Account security email delivery failed without exposing its cause."""

    default_message = "Account security email delivery is currently unavailable."

    def __init__(self):
        super().__init__(self.default_message)


def ensure_account_security_delivery_available():
    try:
        ensure_default_email_delivery_available()
    except EmailDeliveryUnavailable:
        raise AccountSecurityDeliveryUnavailable() from None


def _message_content(*, purpose, raw_token):
    if purpose == AccountSecurityToken.Purpose.EMAIL_VERIFICATION:
        return (
            "Verify your HustlyTasker email",
            (
                "Submit the following single-use token to the authenticated "
                "email verification endpoint:\n\n"
                f"{raw_token}\n\n"
                "This token expires in 24 hours. If you did not request it, "
                "you may ignore this message."
            ),
        )
    if purpose == AccountSecurityToken.Purpose.PASSWORD_RESET:
        return (
            "Reset your HustlyTasker password",
            (
                "Submit the following single-use token with your new password "
                "to the password reset confirmation endpoint:\n\n"
                f"{raw_token}\n\n"
                "This token expires in one hour. If you did not request it, "
                "you may ignore this message. Your password has not changed."
            ),
        )
    raise AccountSecurityDeliveryUnavailable()


@sensitive_variables("raw_token")
def schedule_account_security_delivery(
    *,
    token,
    raw_token,
    raise_on_failure,
):
    """Deliver after commit and keep delivery state truthful.

    Password-reset requests deliberately suppress runtime delivery failures so
    an attacker cannot distinguish an eligible address from an unknown one.
    """

    token_id = token.id
    token_digest = token.token_digest
    purpose = token.purpose
    recipient = token.email_normalized

    @sensitive_variables()
    def deliver():
        attempted_at = timezone.now()
        claimed = AccountSecurityToken.objects.filter(
            id=token_id,
            purpose=purpose,
            status=AccountSecurityToken.Status.PENDING,
            token_digest=token_digest,
            expires_at__gt=attempted_at,
        ).update(
            delivery_status=AccountSecurityToken.DeliveryStatus.QUEUED,
            delivery_attempted_at=attempted_at,
            updated_at=attempted_at,
        )
        if claimed != 1:
            if raise_on_failure:
                raise AccountSecurityDeliveryUnavailable()
            return

        try:
            subject, body = _message_content(
                purpose=purpose,
                raw_token=raw_token,
            )
            send_default_email(
                subject=subject,
                body=body,
                recipient=recipient,
            )
        except (EmailDeliveryUnavailable, AccountSecurityDeliveryUnavailable):
            failed_at = timezone.now()
            AccountSecurityToken.objects.filter(
                id=token_id,
                purpose=purpose,
                status=AccountSecurityToken.Status.PENDING,
                token_digest=token_digest,
            ).update(
                delivery_status=AccountSecurityToken.DeliveryStatus.FAILED,
                delivery_attempted_at=attempted_at,
                delivered_at=None,
                updated_at=failed_at,
            )
            if raise_on_failure:
                raise AccountSecurityDeliveryUnavailable() from None
            return

        delivered_at = timezone.now()
        updated = AccountSecurityToken.objects.filter(
            id=token_id,
            purpose=purpose,
            status=AccountSecurityToken.Status.PENDING,
            token_digest=token_digest,
        ).update(
            delivery_status=AccountSecurityToken.DeliveryStatus.SENT,
            delivery_attempted_at=attempted_at,
            delivered_at=delivered_at,
            updated_at=delivered_at,
        )
        if updated != 1 and raise_on_failure:
            raise AccountSecurityDeliveryUnavailable()

    transaction.on_commit(deliver)
