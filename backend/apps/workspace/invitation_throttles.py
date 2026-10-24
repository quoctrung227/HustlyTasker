import hashlib
from collections.abc import Mapping

from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle

from .invitation_identity import normalize_invitation_email


class InvitationSendThrottle(UserRateThrottle):
    """Share the approved per-inviter budget across create and resend."""

    scope = "invitation_send"


class InvitationRecipientThrottle(SimpleRateThrottle):
    """Bound create attempts by normalized recipient across authenticated actors."""

    scope = "invitation_recipient"

    def get_cache_key(self, request, view):
        if not isinstance(request.data, Mapping):
            return None
        email = request.data.get("recipient_email")
        if not isinstance(email, str):
            return None
        normalized = normalize_invitation_email(email)
        if not normalized:
            return None
        fingerprint = hashlib.sha256(
            normalized.encode("utf-8", errors="surrogatepass")
        ).hexdigest()
        return self.cache_format % {
            "scope": self.scope,
            "ident": fingerprint,
        }


class InvitationTokenActionThrottle(UserRateThrottle):
    """Share a brute-force budget across accept and decline token attempts."""

    scope = "invitation_token_action"
