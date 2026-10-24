from apps.accounts.identity import (
    AmbiguousAccountIdentity,
    resolve_unique_user_for_email,
)
from apps.accounts.models import normalize_account_email


def normalize_invitation_email(value):
    """Canonicalize invitation identity consistently and deterministically."""

    return normalize_account_email(value)


def resolve_unique_user_for_invitation_email(normalized_email):
    """Return the sole matching account, or fail closed on ambiguous identity."""

    try:
        return resolve_unique_user_for_email(normalized_email)
    except AmbiguousAccountIdentity as exc:
        raise AmbiguousInvitationIdentity() from exc


class AmbiguousInvitationIdentity(LookupError):
    """The current account schema cannot resolve this email uniquely."""

