from django.contrib.auth import get_user_model

from .models import normalize_account_email


User = get_user_model()


class AmbiguousAccountIdentity(LookupError):
    """A case-insensitive email lookup did not resolve to one safe account."""


def resolve_unique_user_for_email(normalized_email):
    """Return one exact normalized-email account, or fail closed on ambiguity."""

    matches = list(
        User.objects.filter(email__iexact=normalized_email).order_by("id")[:2]
    )
    if not matches:
        return None
    if len(matches) != 1:
        raise AmbiguousAccountIdentity()
    if normalize_account_email(matches[0].email) != normalized_email:
        return None
    return matches[0]
