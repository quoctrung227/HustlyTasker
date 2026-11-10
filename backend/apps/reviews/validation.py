"""Validation for new linked submissions; legacy references are read unchanged."""

from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


DELIVERABLE_URL_MAX_LENGTH = 500
_http_url = URLValidator(schemes=("http", "https"))


def normalize_deliverable_url(value):
    """Validate a reference only: never fetch, preview or inspect its resource."""

    error = {"file_url": "Use a valid HTTP or HTTPS product link of at most 500 characters, without embedded credentials."}
    if not isinstance(value, str) or any(
        ord(char) < 32 or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF
        for char in value
    ):
        raise ValidationError(error)
    value = value.strip()
    if (
        not value or len(value) > DELIVERABLE_URL_MAX_LENGTH
        or "\\" in value or any(char.isspace() for char in value)
    ):
        raise ValidationError(error)
    try:
        _http_url(value)
        parts = urlsplit(value)
        if not parts.hostname or parts.username is not None or parts.password is not None:
            raise ValueError()
        # Accessing port validates numeric syntax/range without making a request.
        parts.port
    except (ValidationError, ValueError):
        raise ValidationError(error) from None
    return value
