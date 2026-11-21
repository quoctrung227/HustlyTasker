"""Exact Task duration values accepted at the creation boundary."""

import re
from decimal import Decimal

from django.core.exceptions import ValidationError


MIN_ESTIMATED_HOURS = Decimal("0.01")
MAX_ESTIMATED_HOURS = Decimal("1000.00")
_DECIMAL_TEXT = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?")


def normalize_task_estimated_hours(value):
    if value is None:
        return None
    if type(value) is int or (
        type(value) is str and len(value) <= 32 and _DECIMAL_TEXT.fullmatch(value)
    ):
        value = Decimal(value)
    if (type(value) is not Decimal or not value.is_finite()
            or value.as_tuple().exponent < -2
            or not MIN_ESTIMATED_HOURS <= value <= MAX_ESTIMATED_HOURS):
        raise ValidationError({"estimated_hours": "Enter 0.01 to 1000 hours, with at most two decimal places."})
    return value.quantize(MIN_ESTIMATED_HOURS)
