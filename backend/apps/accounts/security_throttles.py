import hashlib
from collections.abc import Mapping

from rest_framework.throttling import SimpleRateThrottle, UserRateThrottle

from .models import normalize_account_email


def _fingerprint(value):
    safe_value = value if isinstance(value, str) else ""
    return hashlib.sha256(
        safe_value.encode("utf-8", errors="surrogatepass")
    ).hexdigest()


class EmailVerificationRequestThrottle(UserRateThrottle):
    scope = "auth_email_verification_request"


class EmailVerificationConfirmThrottle(UserRateThrottle):
    scope = "auth_email_verification_confirm"


class PasswordResetRequestEmailThrottle(SimpleRateThrottle):
    scope = "auth_password_reset_request_email"

    def get_cache_key(self, request, view):
        email = request.data.get("email") if isinstance(request.data, Mapping) else ""
        normalized = normalize_account_email(email) if isinstance(email, str) else ""
        identity = normalized or f"invalid:{self.get_ident(request)}"
        return self.cache_format % {
            "scope": self.scope,
            "ident": _fingerprint(identity),
        }


class PasswordResetRequestIpThrottle(SimpleRateThrottle):
    scope = "auth_password_reset_request_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": _fingerprint(self.get_ident(request)),
        }


class PasswordResetConfirmThrottle(SimpleRateThrottle):
    """Bound attempts against one submitted credential across client IPs."""

    scope = "auth_password_reset_confirm"

    def get_cache_key(self, request, view):
        token = request.data.get("token") if isinstance(request.data, Mapping) else ""
        safe_token = token if isinstance(token, str) else ""
        identity = safe_token or f"invalid:{self.get_ident(request)}"
        return self.cache_format % {
            "scope": self.scope,
            "ident": _fingerprint(identity),
        }


class PasswordResetConfirmIpThrottle(SimpleRateThrottle):
    """Bound rotating invalid-token attempts from one trusted client address."""

    scope = "auth_password_reset_confirm_ip"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": _fingerprint(self.get_ident(request)),
        }
