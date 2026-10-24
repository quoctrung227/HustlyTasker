from django.conf import settings
from django.core.mail import EmailMessage
from django.views.decorators.debug import sensitive_variables


_UNSAFE_DEFAULT_EMAIL_BACKENDS = {
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
    "django.core.mail.backends.filebased.EmailBackend",
}


class EmailDeliveryUnavailable(RuntimeError):
    """Credential email delivery is unavailable without exposing its cause."""

    default_message = "Email delivery is currently unavailable."

    def __init__(self):
        super().__init__(self.default_message)


def ensure_default_email_delivery_available():
    backend = settings.MAILERS.get("default", {}).get("BACKEND")
    if not backend or backend in _UNSAFE_DEFAULT_EMAIL_BACKENDS:
        raise EmailDeliveryUnavailable()


@sensitive_variables()
def send_default_email(*, subject, body, recipient):
    """Send one message through the configured default mailer alias."""

    ensure_default_email_delivery_available()
    try:
        message = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
        )
        sent_count = message.send(fail_silently=False, using="default")
    except Exception:
        raise EmailDeliveryUnavailable() from None

    if sent_count != 1:
        raise EmailDeliveryUnavailable()

