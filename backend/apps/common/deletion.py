"""Explicit effective-deletion SQL scopes; archive and default managers stay intact."""
from django.db.models import Q


def _path(prefix, field):
    return f"{prefix.rstrip('_')}__{field}" if prefix else field


def profile_live_q(prefix=""):
    return Q(**{_path(prefix, "deleted_at__isnull"): True})


def workspace_live_q(prefix=""):
    return profile_live_q(prefix) & profile_live_q(_path(prefix, "profile"))


def task_live_q(prefix=""):
    predicate = profile_live_q(prefix) & workspace_live_q(_path(prefix, "workspace"))
    ancestor = prefix
    # Task.MAX_HIERARCHY_DEPTH is three parent edges. Missing ancestors are
    # NULL and pass; any independently deleted ancestor hides its descendants.
    for _ in range(3):
        ancestor = _path(ancestor, "parent")
        predicate &= profile_live_q(ancestor)
    # Fail closed for malformed legacy trees deeper than the supported cap.
    return predicate & Q(**{_path(ancestor, "parent_id__isnull"): True})
