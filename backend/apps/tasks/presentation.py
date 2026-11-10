"""Safe Task identity labels without contact or UUID fallback disclosure."""

import re


_uuid_label = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)


def assignee_display_name(*, first_name, last_name, username):
    def safe(value):
        if (
            not isinstance(value, str) or "@" in value or _uuid_label.search(value)
            or any(ord(char) < 32 or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF for char in value)
        ):
            return ""
        return " ".join(value.split())

    full_name = safe(f"{first_name} {last_name}")
    safe_username = safe(username)
    if not re.fullmatch(r"[\w.+-]+", safe_username):
        safe_username = ""
    return full_name or safe_username or "Thành viên được giao"
