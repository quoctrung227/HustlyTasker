"""Bounded Task brief values shared by HTTP and domain-service validation.

No document is fetched here. Monetary values are whole VND, with an exact
18-digit storage boundary rather than a product-level compensation budget.
"""

import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator


TASK_REFERENCE_MAX_LENGTH = 2048
TASK_BRIEF_URL_FIELDS = (
    "raw_video_url", "reference_video_url", "template_project_url", "script_url",
)
TASK_COMPENSATION_MAX = 999999999999999999
_http_url = URLValidator(schemes=("http", "https"))
_whole_vnd = re.compile(r"[0-9]{1,18}\Z", flags=re.ASCII)


def normalize_task_reference(value, *, field):
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError({field: "Use an HTTP or HTTPS URL."})
    value = value.strip()
    if not value:
        return None
    if (
        len(value) > TASK_REFERENCE_MAX_LENGTH
        or any(ord(char) < 32 or ord(char) == 127 or 0xD800 <= ord(char) <= 0xDFFF for char in value)
    ):
        raise ValidationError({field: "Use a valid HTTP or HTTPS URL of at most 2048 characters."})
    try:
        _http_url(value)
    except ValidationError:
        raise ValidationError({field: "Use a valid HTTP or HTTPS URL."}) from None
    return value


def normalize_task_compensation(value, *, allow_decimal=False):
    """Return integer/None without ever coercing an untrusted float.

    Decimal is accepted only for model/read validation, because Django loads
    numeric(18,0) as Decimal. HTTP and service inputs accept int or digit string.
    """

    field = "estimated_compensation_vnd"
    error = {field: "Use a nonnegative whole VND amount of at most 18 digits."}
    if value is None or isinstance(value, str) and value == "":
        return None
    if isinstance(value, bool):
        raise ValidationError(error)
    if isinstance(value, int):
        amount = value
    elif isinstance(value, str) and _whole_vnd.fullmatch(value):
        amount = int(value)
    elif allow_decimal and isinstance(value, Decimal):
        if (
            not value.is_finite() or value != value.to_integral_value()
            or value < 0 or value > TASK_COMPENSATION_MAX
        ):
            raise ValidationError(error)
        amount = int(value)
    else:
        raise ValidationError(error)
    if amount < 0 or amount > TASK_COMPENSATION_MAX:
        raise ValidationError(error)
    return amount
