"""Mask recognizable private values in free text before model transport."""

import re

from django.views.decorators.debug import sensitive_variables


REDACTED = "[redacted]"
_PRIVATE_PATTERNS = (
    # Named credentials and internal headers can contain multiple values.
    # Mask the rest of that line to avoid returning a partial secret.
    re.compile(r"(?im)\b(?:authorization|cookie|set-cookie|api[_ -]?key|access[_ -]?token|refresh[_ -]?token|"
               r"token|password|passwd|secret|mật khẩu|khóa api)\s*[:=][^\r\n]*"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"),
    re.compile(r"(?i)\b(?:sk-(?:proj-)?[a-z0-9_-]{12,}|gh[pousr]_[a-z0-9]{12,}|eyJ[a-z0-9_-]+\.[a-z0-9_-]+\.[a-z0-9_-]+)\b"),
    re.compile(r"(?i)(?:\b[a-z][a-z0-9+.-]{1,20}://|\bwww\.)[^\s<>\"']+"),
    re.compile(r"(?i)[^\s<>\"'@]{1,254}@(?:[\w-]+\.)+[\w-]+"),
    re.compile(r"(?i)\b(?:[a-z0-9-]+\.)+[a-z]{2,}(?:[/?#][^\s<>\"']*)?"),
    re.compile(r"(?<!\w)(?:\+?\d[ .()-]?){9,15}(?!\w)"),
    re.compile(r"(?im)\b(?:e-mail|email|phone|address|full name|địa chỉ|số điện thoại|họ tên)\s*[:=][^\r\n]*"),
    re.compile(r"(?i)(?<!\w)[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}(?!\w)"),
    re.compile(r"(?i)(?<!\w)[a-f0-9]{32,}(?!\w)"),
)


@sensitive_variables()
def redact_provider_text(text):
    """Redact explicit contact and credential patterns. Free text can still identify someone."""
    for pattern in _PRIVATE_PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text
