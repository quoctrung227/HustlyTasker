"""Scoped soft deletion and conservative, explicitly gated physical purge."""
import calendar
from datetime import timedelta
from math import ceil
from uuid import UUID

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, IntegrityError, connection, models, transaction
from django.db.models import Q, Value
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.reviews.models import Deliverable, Review
from apps.tasks.models import Task, TaskAssignment, TaskComment
from apps.tasks.presentation import assignee_display_name
from apps.workspace.access import TenantAccessNotFound
from apps.workspace.models import (
    InvitationEmailAttempt, Profile, ProfileInvitation, ProfileMembership,
    Workspace, WorkspaceMember,
)

from .permissions import can_manage, managed_profiles, membership_for, profile_id_for, task_management_q

RETENTION = timedelta(days=30)
MODELS = {"TASK": Task, "WORKSPACE": Workspace, "PROFILE": Profile}


class TrashConflict(Exception):
    def __init__(self, code, message, *, blockers=None):
        self.code = code
        self.message = message
        self.blockers = blockers or [{"code": code, "message": message}]
        super().__init__(message)


def _block(code, message):
    return {"code": code, "message": message}


def resolve_entry(kind, object_id):
    model = MODELS.get(kind)
    if model is None:
        raise TenantAccessNotFound()
    query = model.objects.select_related("deleted_by")
    if model is Task:
        query = query.select_related("workspace__profile", "parent", "parent__parent", "parent__parent__parent")
    elif model is Workspace:
        query = query.select_related("profile")
    try:
        obj = query.filter(pk=object_id).first()
    except (ValidationError, ValueError, TypeError):
        obj = None
    if obj is None or (model is Workspace and obj.profile_id is None):
        raise TenantAccessNotFound()
    return obj


def _parent_deleted(obj):
    if isinstance(obj, Profile):
        return False
    workspace = obj if isinstance(obj, Workspace) else obj.workspace
    if workspace.profile is None or workspace.profile.deleted_at is not None:
        return True
    if isinstance(obj, Workspace):
        return False
    if workspace.deleted_at is not None:
        return True
    parent = obj.parent
    seen = {obj.pk}
    for _ in range(Task.MAX_HIERARCHY_DEPTH):
        if parent is None:
            return False
        if parent.pk in seen or parent.workspace_id != obj.workspace_id or parent.deleted_at is not None:
            return True
        seen.add(parent.pk)
        parent = parent.parent
    return parent is not None


def _parent_archived(obj):
    if isinstance(obj, Profile):
        return False
    workspace = obj if isinstance(obj, Workspace) else obj.workspace
    return workspace.profile.status != Profile.Status.ACTIVE or (
        isinstance(obj, Task) and workspace.status != Workspace.Status.ACTIVE
    )


def _restore_blocker(obj, now):
    if _parent_deleted(obj):
        return "PARENT_DELETED"
    if _parent_archived(obj):
        return "PARENT_ARCHIVED"
    if obj.purge_after is None or now >= obj.purge_after:
        return "EXPIRED"
    return None


def _subtree(task):
    seen = {task.pk}
    frontier = {task.pk}
    for _ in range(Task.MAX_HIERARCHY_DEPTH + 1):
        rows = list(Task.objects.filter(parent_id__in=frontier).values_list("id", "workspace_id"))
        if not rows:
            return seen
        if any(pk in seen or ws != task.workspace_id for pk, ws in rows):
            raise TrashConflict("UNKNOWN_REFERENCE", "Cây công việc có liên kết không hợp lệ; cần kiểm tra riêng.")
        frontier = {pk for pk, _ in rows}
        seen.update(frontier)
    raise TrashConflict("UNKNOWN_REFERENCE", "Cây công việc vượt giới hạn phân cấp; cần kiểm tra riêng.")


def _scope(obj):
    profile_ids = {obj.pk} if isinstance(obj, Profile) else set()
    workspace_ids = set(Workspace.objects.filter(profile_id=obj.pk).values_list("pk", flat=True)) if profile_ids else ({obj.pk} if isinstance(obj, Workspace) else set())
    task_ids = _subtree(obj) if isinstance(obj, Task) else set(Task.objects.filter(workspace_id__in=workspace_ids).values_list("pk", flat=True))
    delivered = set(Deliverable.objects.filter(task_id__in=task_ids).values_list("pk", flat=True))
    invitations = set(ProfileInvitation.objects.filter(profile_id__in=profile_ids).values_list("pk", flat=True))
    notification_q = Q(task_id__in=task_ids) | Q(workspace_id__in=workspace_ids) | Q(profile_id__in=profile_ids)
    plans = {
        Task: task_ids,
        Workspace: workspace_ids,
        Profile: profile_ids,
        Deliverable: delivered,
        Review: set(Review.objects.filter(deliverable_id__in=delivered).values_list("pk", flat=True)),
        TaskAssignment: set(TaskAssignment.objects.filter(task_id__in=task_ids).values_list("pk", flat=True)),
        TaskComment: set(TaskComment.objects.filter(task_id__in=task_ids).values_list("pk", flat=True)),
        Notification: set(Notification.objects.filter(notification_q).values_list("pk", flat=True)),
        WorkspaceMember: set(WorkspaceMember.objects.filter(workspace_id__in=workspace_ids).values_list("pk", flat=True)),
        ProfileMembership: set(ProfileMembership.objects.filter(profile_id__in=profile_ids).values_list("pk", flat=True)),
        ProfileInvitation: invitations,
        InvitationEmailAttempt: set(InvitationEmailAttempt.objects.filter(invitation_id__in=invitations).values_list("pk", flat=True)),
    }
    profile_id = profile_id_for(obj)
    canonical_tasks = dict(Task.objects.filter(pk__in=task_ids).values_list("pk", "workspace_id"))
    for notice in Notification.objects.filter(pk__in=plans[Notification]).values("profile_id", "workspace_id", "task_id", "invitation_id"):
        valid = notice["profile_id"] == profile_id
        if notice["task_id"] is not None:
            valid = valid and notice["task_id"] in canonical_tasks and notice["workspace_id"] == canonical_tasks[notice["task_id"]]
        elif notice["invitation_id"] is not None:
            valid = valid and notice["invitation_id"] in invitations and notice["workspace_id"] is None
        else:
            valid = False
        if not valid:
            raise TrashConflict("UNKNOWN_REFERENCE", "Có tham chiếu thông báo không khớp tổ chức; cần kiểm tra riêng.")
    return {"plans": plans, "profile_id": profile_id, "workspace_id": obj.workspace_id if isinstance(obj, Task) else (obj.pk if isinstance(obj, Workspace) else None)}


def _counts(scope):
    plans = scope["plans"]
    return {
        "tasks": len(plans[Task]), "workspaces": len(plans[Workspace]),
        "assignments": len(plans[TaskAssignment]), "deliverables": len(plans[Deliverable]),
        "reviews": len(plans[Review]), "comments": len(plans[TaskComment]),
        "notifications": len(plans[Notification]), "invitations": len(plans[ProfileInvitation]),
        "memberships": len(plans[ProfileMembership]) + len(plans[WorkspaceMember]),
    }


def _calendar_year(at):
    return at.replace(year=at.year + 1, day=min(at.day, calendar.monthrange(at.year + 1, at.month)[1]))


def _ai_references(scope):
    from apps.ai.models import AiBudgetBucket, AiDispatch, AiOperation, AiProposal
    plans = scope["plans"]
    with connection.cursor() as cursor:
        tables = set(connection.introspection.table_names(cursor))
    for model in (AiProposal, AiOperation, AiDispatch, AiBudgetBucket):
        if model._meta.db_table not in tables:
            continue
        query = Q(profile_id__in=plans[Profile])
        if any(field.name == "workspace" for field in model._meta.fields):
            query |= Q(workspace_id__in=plans[Workspace])
        if model.objects.filter(query).exists():
            return True
    if plans[Task] and scope["workspace_id"] is not None and AiProposal._meta.db_table in tables:
        target_ids = {str(pk) for pk in plans[Task]}
        def references(value):
            if isinstance(value, str):
                try:
                    return str(UUID(value)) in target_ids
                except (ValueError, AttributeError):
                    return False
            if isinstance(value, dict):
                return any(references(child) for child in value.values())
            return isinstance(value, list) and any(references(child) for child in value)
        return any(references(value) for value in AiProposal.objects.filter(workspace_id=scope["workspace_id"]).values_list("created_tasks", flat=True))
    return False


def _inspect_foreign_reference(scope):
    """Inspect actual PostgreSQL FKs, including unknown/unapplied-model boundaries.

    No Django Collector and no introspection of a table that does not exist.
    Every dependent row must itself occur in the exact deletion plan.
    """
    plans = {model._meta.db_table: ids for model, ids in scope["plans"].items()}
    quote = connection.ops.quote_name
    with connection.cursor() as cursor:
        for target, ids in plans.items():
            if not ids:
                continue
            cursor.execute("""SELECT n.nspname,c.relname,
                ARRAY(SELECT a.attname FROM unnest(k.conkey) WITH ORDINALITY u(num,pos) JOIN pg_attribute a ON a.attrelid=k.conrelid AND a.attnum=u.num ORDER BY u.pos),
                ARRAY(SELECT a.attname FROM unnest(k.confkey) WITH ORDINALITY u(num,pos) JOIN pg_attribute a ON a.attrelid=k.confrelid AND a.attnum=u.num ORDER BY u.pos)
                FROM pg_constraint k JOIN pg_class c ON c.oid=k.conrelid JOIN pg_namespace n ON n.oid=c.relnamespace
                WHERE k.contype='f' AND k.confrelid=to_regclass(%s)""", [target])
            references = cursor.fetchall()
            for schema, table, fields, target_fields in references:
                if schema != "public" or len(fields) != 1 or target_fields != ["id"]:
                    return True
                query = f"SELECT 1 FROM {quote(schema)}.{quote(table)} WHERE {quote(fields[0])} = ANY(%s)"
                params = [list(ids)]
                if table in plans and plans[table]:
                    query += f" AND NOT ({quote('id')} = ANY(%s))"
                    params.append(list(plans[table]))
                cursor.execute(query + " LIMIT 1", params)
                if cursor.fetchone() is not None:
                    return True
    return False


def _safe_dependency_check(function, scope):
    try:
        with transaction.atomic():
            return function(scope)
    except DatabaseError:
        raise TrashConflict("UNKNOWN_REFERENCE", "Không thể kiểm chứng đầy đủ ràng buộc dữ liệu; thao tác bị chặn an toàn.") from None


def _foreign_reference(scope):
    return _safe_dependency_check(_inspect_foreign_reference, scope)


def purge_blockers(obj, *, scope=None, now=None, check_references=True, evaluate_disabled=False):
    now = now or timezone.now()
    scope = scope or _scope(obj)
    plans = scope["plans"]
    blockers = []
    if getattr(settings, "TRASH_PURGE_ENABLED", False) is not True:
        blockers.append(_block("PURGE_DISABLED", "Xóa vĩnh viễn chưa được bật; cần Owner phê duyệt riêng."))
    if obj.deleted_at is None or obj.purge_after is None or now < obj.purge_after:
        blockers.append(_block("RETENTION_NOT_ELAPSED", "Chưa đủ 30 ngày kể từ thời điểm xóa ban đầu."))
    elif any(model.objects.filter(pk__in=plans[model], deleted_at__isnull=False, purge_after__gt=now).exists() for model in (Task, Workspace, Profile)):
        blockers.append(_block("RETENTION_NOT_ELAPSED", "Còn đối tượng con có thời hạn lưu trữ chưa kết thúc."))
    # Any Review is protected in V1, including pending decisions and revision
    # feedback. The absence of a recorded amount is not permission to erase it.
    if plans[Review] or Task.objects.filter(pk__in=plans[Task], status=Task.Status.COMPLETED).exists():
        blockers.append(_block("PROTECTED_HISTORY", "Đang bảo toàn lịch sử Review, hoàn thành hoặc tiền công; cần chính sách lưu trữ riêng."))
    for invitation in ProfileInvitation.objects.filter(pk__in=plans[ProfileInvitation]):
        terminal_at = {"ACCEPTED": invitation.accepted_at, "DECLINED": invitation.declined_at,
                       "REVOKED": invitation.revoked_at, "EXPIRED": invitation.expired_at}.get(invitation.status)
        if terminal_at is None or terminal_at > now or now < _calendar_year(terminal_at):
            blockers.append(_block("INVITATION_RETENTION", "Lời mời chưa kết thúc hoặc chưa đủ thời gian lưu tối thiểu 12 tháng."))
            break
    if InvitationEmailAttempt.objects.filter(pk__in=plans[InvitationEmailAttempt], status="PENDING").exists():
        blockers.append(_block("INVITATION_RETENTION", "Còn lần gửi email chưa có kết quả; cần xử lý riêng."))
    if _safe_dependency_check(_ai_references, scope):
        blockers.append(_block("AI_DEPENDENCY", "Còn dữ liệu hoặc tham chiếu phục hồi AI cần được bảo toàn."))
    # Execution checks every reverse FK. Preview does the same only when due and
    # enabled; a disabled preview is never represented as an executable plan.
    can_check = not any(row["code"] == "RETENTION_NOT_ELAPSED" for row in blockers) and (evaluate_disabled or not any(row["code"] == "PURGE_DISABLED" for row in blockers))
    if check_references and can_check and _foreign_reference(scope):
        blockers.append(_block("UNKNOWN_REFERENCE", "Còn tham chiếu ngoài phạm vi xóa hoặc ràng buộc chưa xử lý an toàn."))
    return blockers


def item_data(obj, actor):
    now = timezone.now()
    scope = _scope(obj)
    member = membership_for(actor, scope["profile_id"])
    allowed = can_manage(actor, obj, membership=member)
    restore_blocker = _restore_blocker(obj, now)
    blockers = purge_blockers(obj, scope=scope, now=now)
    owner = bool(member and member.role == ProfileMembership.Role.OWNER)
    if not owner:
        blockers.insert(0, _block("OWNER_REQUIRED", "Chỉ Owner tổ chức được xóa vĩnh viễn."))
    deleter = obj.deleted_by
    name = assignee_display_name(first_name=deleter.first_name, last_name=deleter.last_name, username=deleter.username) if deleter else "Tài khoản không còn khả dụng"
    if name == "Thành viên được giao":
        name = "Thành viên"
    return {
        "id": str(obj.pk), "object_type": obj.__class__.__name__.upper(),
        "title": obj.title if isinstance(obj, Task) else obj.name,
        "profile_id": str(scope["profile_id"]),
        "workspace_id": str(scope["workspace_id"]) if scope["workspace_id"] else None,
        "parent_id": str(obj.parent_id) if isinstance(obj, Task) and obj.parent_id else None,
        "deleted_by": {"display_name": name}, "deleted_at": obj.deleted_at,
        "purge_after": obj.purge_after, "days_remaining": max(0, ceil((obj.purge_after-now).total_seconds()/86400)) if obj.purge_after else 0,
        "parent_deleted": _parent_deleted(obj), "affected_counts": _counts(scope),
        "can_restore": bool(allowed and obj.deleted_at and restore_blocker is None),
        "can_purge": bool(allowed and owner and not blockers),
        "restore_blocker": restore_blocker, "purge_blockers": blockers,
    }


def read_page_entries(actor, filters):
    if filters.get("profile_id") and membership_for(actor, filters["profile_id"]) is None:
        raise TenantAccessNotFound()
    owners = ProfileMembership.objects.filter(user_id=actor.pk, user__is_active=True, is_active=True, role=ProfileMembership.Role.OWNER).values("profile_id")
    queries = {
        "PROFILE": Profile.objects.filter(pk__in=owners),
        "WORKSPACE": Workspace.objects.filter(profile_id__in=managed_profiles(actor)),
        "TASK": Task.objects.filter(task_management_q(actor)),
    }
    union = None
    for kind, query in queries.items():
        if filters.get("object_type") and filters["object_type"] != kind:
            continue
        if filters.get("profile_id"):
            key = "pk" if kind == "PROFILE" else ("profile_id" if kind == "WORKSPACE" else "workspace__profile_id")
            query = query.filter(**{key: filters["profile_id"]})
        if filters.get("search"):
            query = query.filter(**{("title__icontains" if kind == "TASK" else "name__icontains"): filters["search"]})
        query = query.filter(deleted_at__isnull=False).annotate(object_type=Value(kind, output_field=models.CharField())).values("id", "object_type", "deleted_at")
        union = query if union is None else union.union(query)
    return union.order_by("-deleted_at", "object_type", "id")


def _audit(actor, obj, action, scope, *, automatic=False):
    return AuditLog.objects.create(user=actor, action=f"{obj.__class__.__name__.lower()}.{action}",
        entity_name=obj.__class__.__name__, entity_id=obj.pk,
        metadata={"profile_id": str(scope["profile_id"]), "workspace_id": str(scope["workspace_id"]) if scope["workspace_id"] else None,
                  "deleted_at": obj.deleted_at.isoformat() if obj.deleted_at else None,
                  "purge_after": obj.purge_after.isoformat() if obj.purge_after else None,
                  "affected_counts": _counts(scope), "automatic": automatic})


@transaction.atomic
def mutate(*, actor, object_type, object_id, action, confirm=False, confirmation_name=None, automatic=False):
    if action not in ("delete", "restore", "purge") or (automatic and (actor is not None or action != "purge")):
        raise TenantAccessNotFound()
    probe = resolve_entry(object_type, object_id)
    profile_id = profile_id_for(probe)
    if not automatic and not can_manage(actor, probe):
        raise TenantAccessNotFound()
    profile = Profile.objects.select_for_update().filter(pk=profile_id).first()
    if profile is None:
        raise TenantAccessNotFound()
    workspace = None
    if not isinstance(probe, Profile):
        ws_id = probe.pk if isinstance(probe, Workspace) else probe.workspace_id
        workspace = Workspace.objects.select_for_update().filter(pk=ws_id, profile_id=profile.pk).first()
        if workspace is None:
            raise TenantAccessNotFound()
        workspace.profile = profile
    member = None if automatic else membership_for(actor, profile.pk, lock=True)
    if not automatic and (member is None or not can_manage(actor, probe, membership=member)):
        raise TenantAccessNotFound()
    if isinstance(probe, Profile):
        obj = profile
    else:
        obj = workspace if isinstance(probe, Workspace) else Task.objects.select_for_update().filter(pk=probe.pk, workspace_id=workspace.pk).first()
        if obj is None:
            raise TenantAccessNotFound()
        if isinstance(obj, Task):
            obj.workspace = workspace
    now = timezone.now()
    if action == "delete":
        if obj.deleted_at is not None:
            return obj
        if _parent_deleted(obj):
            raise TrashConflict("PARENT_DELETED", "Cần khôi phục đối tượng cha trước.")
        if _parent_archived(obj):
            raise TrashConflict("PARENT_ARCHIVED", "Đối tượng cha đang được lưu trữ và chỉ cho phép đọc.")
        obj.deleted_at, obj.deleted_by, obj.purge_after = now, actor, now + RETENTION
        obj.save(update_fields=("deleted_at", "deleted_by", "purge_after", "updated_at"))
        _audit(actor, obj, "deleted", _scope(obj))
        return obj
    if action == "restore":
        if obj.deleted_at is None:
            return obj
        blocker = _restore_blocker(obj, now)
        if blocker is not None:
            raise TrashConflict(blocker, "Không thể khôi phục: đối tượng cha chưa khả dụng hoặc đã hết thời hạn.")
        scope = _scope(obj)
        _audit(actor, obj, "restored", scope)
        obj.deleted_at = obj.deleted_by = obj.purge_after = None
        obj.save(update_fields=("deleted_at", "deleted_by", "purge_after", "updated_at"))
        return obj
    if not automatic and member.role != ProfileMembership.Role.OWNER:
        raise PermissionDenied("Chỉ Owner tổ chức được xóa vĩnh viễn.")
    if not automatic and (confirm is not True or (not isinstance(obj, Task) and confirmation_name != obj.name)):
        raise ValidationError({"confirmation_name": ["Nhập đúng tên đối tượng và xác nhận xóa vĩnh viễn."]})
    scope = _scope(obj)
    blockers = purge_blockers(obj, scope=scope, now=now)
    if blockers:
        raise TrashConflict(blockers[0]["code"], "Chưa thể xóa vĩnh viễn; dữ liệu vẫn được bảo toàn.", blockers=blockers)
    _audit(actor, obj, "purged", scope, automatic=automatic)
    # Explicit children first; _raw_delete bypasses only Django Collector, never
    # database FKs. Unknown/foreign references were rejected above. Global Users,
    # directory quotas, finance/client rows and AuditLog are never in this plan.
    order = (Notification, InvitationEmailAttempt, ProfileInvitation, TaskComment,
             Review, Deliverable, TaskAssignment, Task, WorkspaceMember,
             Workspace, ProfileMembership, Profile)
    try:
        with transaction.atomic():
            for model in order:
                ids = scope["plans"][model]
                if ids:
                    model.objects.filter(pk__in=ids)._raw_delete("default")
            # Deferred PostgreSQL FK checks must fail inside this savepoint,
            # not after a successful response/audit commit.
            with connection.cursor() as cursor:
                cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
                cursor.execute("SET CONSTRAINTS ALL DEFERRED")
    except IntegrityError:
        raise TrashConflict("UNKNOWN_REFERENCE", "Ràng buộc dữ liệu ngăn xóa; toàn bộ thao tác đã được hoàn tác.") from None
    return None
