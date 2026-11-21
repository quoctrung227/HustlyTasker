"""Read-only Task analytics. Querysets retain the actor's current tenant scope."""
from dataclasses import dataclass
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db.models import (
    BooleanField, Case, CharField, Count, DecimalField, Exists, F, IntegerField,
    OuterRef, Q, Subquery, Sum, Value, When,
)
from django.db.models.functions import Coalesce, Concat, Trim, TruncMonth
from django.utils import timezone
from apps.common.deletion import profile_live_q, task_live_q

from apps.reviews.models import Deliverable, Review
from apps.workspace.access import (
    TenantAccessNotFound, resolve_profile_access_context,
    resolve_workspace_access_context, workspaces_visible_to,
)
from apps.workspace.models import ProfileMembership, WorkspaceMember

from .analytics_serializers import ANALYTICS_TIMEZONE
from .models import Task, TaskAssignment
from .presentation import assignee_display_name


TERMINAL_STATUSES = (Task.Status.COMPLETED, Task.Status.CANCELLED)
MONEY_FIELD = DecimalField(max_digits=38, decimal_places=0)


@dataclass(frozen=True)
class AnalyticsScope:
    actor: object
    profile_context: object
    workspace_id: object
    mode: str
    workspace_ids: object
    tasks: object
    historical_workspace_ids: object
    historical_tasks: object
    start_at: datetime
    end_before: datetime
    from_date: object
    to_date: object
    snapshot_at: datetime


def _canonical_reviews():
    latest = Deliverable.objects.filter(
        task_id=OuterRef("deliverable__task_id"),
    ).order_by("-created_at", "-id").values("pk")[:1]
    return Review.objects.filter(
        status=Review.Status.APPROVED,
        deliverable__status=Deliverable.Status.APPROVED,
        deliverable__task__status=Task.Status.COMPLETED,
        deliverable_id=Subquery(latest),
    )


def resolve_analytics_scope(*, actor, profile_id, filters):
    context = resolve_profile_access_context(actor, profile_id)
    workspaces = workspaces_visible_to(context)
    historical_workspaces = workspaces_visible_to(context, include_deleted=True)
    workspace_id = filters.get("workspace_id")
    mode = "management" if context.profile_role in (
        ProfileMembership.Role.OWNER, ProfileMembership.Role.ADMIN,
    ) else "self"
    if mode == "management":
        current_manager = ProfileMembership.objects.filter(
            profile_live_q("profile"),
            pk=context.membership_id, profile_id=context.profile_id,
            user_id=context.user_id, user__is_active=True, is_active=True,
            role__in=(ProfileMembership.Role.OWNER, ProfileMembership.Role.ADMIN),
        )
        # workspaces_visible_to refreshes READ scope. A downgrade may still
        # permit ordinary Workspace reads, so management needs its own live
        # authority predicate rather than trusting the earlier role snapshot.
        workspaces = workspaces.alias(_analytics_profile_manager=Exists(current_manager)).filter(_analytics_profile_manager=True)
        historical_workspaces = historical_workspaces.alias(_analytics_profile_manager=Exists(current_manager)).filter(_analytics_profile_manager=True)
    if workspace_id is not None:
        workspace_context = resolve_workspace_access_context(context, workspace_id)
        workspaces = workspaces.filter(pk=workspace_id)
        historical_workspaces = historical_workspaces.filter(pk=workspace_id)
        if context.profile_role == ProfileMembership.Role.MEMBER and workspace_context.workspace_role == WorkspaceMember.Role.ADMIN:
            mode = "management"
            # A downgrade between resolution and queryset evaluation must not
            # turn a previously manager response into an ordinary read leak.
            still_manager = WorkspaceMember.objects.filter(
                workspace_id=OuterRef("pk"), user_id=context.user_id,
                is_active=True, role=WorkspaceMember.Role.ADMIN,
            )
            workspaces = workspaces.alias(_analytics_manager=Exists(still_manager)).filter(_analytics_manager=True)
            historical_workspaces = historical_workspaces.alias(_analytics_manager=Exists(still_manager)).filter(_analytics_manager=True)
    workspace_ids = workspaces.values("pk")
    historical_workspace_ids = historical_workspaces.values("pk")
    tasks = Task.objects.filter(task_live_q(), workspace_id__in=workspace_ids)
    historical_tasks = Task.objects.filter(workspace_id__in=historical_workspace_ids)
    if mode == "self":
        own_assignment = TaskAssignment.objects.filter(
            task_id=OuterRef("pk"), user_id=context.user_id, is_active=True,
        )
        own_credit = _canonical_reviews().filter(
            deliverable__task_id=OuterRef("pk"), deliverable__uploaded_by_id=context.user_id,
        )
        tasks = tasks.alias(
            _analytics_own_assignment=Exists(own_assignment),
            _analytics_own_credit=Exists(own_credit),
        ).filter(Q(_analytics_own_assignment=True) | Q(_analytics_own_credit=True))
        historical_tasks = historical_tasks.alias(
            _analytics_own_assignment=Exists(own_assignment),
            _analytics_own_credit=Exists(own_credit),
        ).filter(Q(_analytics_own_assignment=True) | Q(_analytics_own_credit=True))
    return AnalyticsScope(
        actor=actor, profile_context=context, workspace_id=workspace_id,
        mode=mode, workspace_ids=workspace_ids, tasks=tasks,
        historical_workspace_ids=historical_workspace_ids,
        historical_tasks=historical_tasks,
        start_at=filters["start_at"], end_before=filters["end_before"],
        from_date=filters["from"], to_date=filters["to"], snapshot_at=timezone.now(),
    )


def _cohort(scope):
    return scope.tasks.filter(created_at__gte=scope.start_at, created_at__lt=scope.end_before)


def _approval_events(scope):
    events = _canonical_reviews().filter(
        deliverable__task_id__in=scope.historical_tasks.values("pk"),
        created_at__gte=scope.start_at, created_at__lt=scope.end_before,
    )
    if scope.mode == "self":
        events = events.filter(deliverable__uploaded_by_id=scope.profile_context.user_id)
    return events


def _financial_tasks(scope, *, include_deleted=False):
    # Management scope is already narrowed by the live Profile/Workspace role.
    tasks = scope.historical_tasks if include_deleted else scope.tasks
    if scope.mode == "management":
        return tasks
    membership = WorkspaceMember.objects.filter(
        workspace_id=OuterRef("workspace_id"), user_id=scope.profile_context.user_id,
        is_active=True,
    )
    current_assignment = TaskAssignment.objects.filter(
        task_id=OuterRef("pk"), user_id=scope.profile_context.user_id, is_active=True,
    )
    return tasks.alias(
        _analytics_pay_admin=Exists(membership.filter(role=WorkspaceMember.Role.ADMIN)),
        _analytics_pay_editor=Exists(membership.filter(role=WorkspaceMember.Role.MEMBER)),
        _analytics_pay_assigned=Exists(current_assignment),
    ).filter(Q(_analytics_pay_admin=True) | Q(_analytics_pay_editor=True, _analytics_pay_assigned=True))


def _can_read_money(scope):
    if scope.mode == "management":
        return True
    return WorkspaceMember.objects.filter(
        workspace_id__in=scope.historical_workspace_ids, user_id=scope.profile_context.user_id,
        is_active=True, role__in=(WorkspaceMember.Role.ADMIN, WorkspaceMember.Role.MEMBER),
    ).exists()


def _money(value):
    return str(int(value)) if value is not None else None


def _event_finance(events):
    result = events.aggregate(
        amount=Sum("compensation_snapshot_vnd", filter=Q(compensation_snapshot_recorded=True), output_field=MONEY_FIELD),
        priced=Count("pk", filter=Q(compensation_snapshot_recorded=True, compensation_snapshot_vnd__isnull=False)),
        unpriced=Count("pk", filter=Q(compensation_snapshot_recorded=True, compensation_snapshot_vnd__isnull=True)),
        unknown=Count("pk", filter=Q(compensation_snapshot_recorded=False)),
    )
    return {
        "approved_total_vnd": _money(result["amount"]),
        "approved_priced_tasks": result["priced"],
        "approved_unpriced_tasks": result["unpriced"],
        "approved_unknown_tasks": result["unknown"],
    }


def analytics_summary(scope):
    cohort = _cohort(scope)
    canonical = _canonical_reviews().filter(deliverable__task_id=OuterRef("pk"))
    credited = canonical if scope.mode == "management" else canonical.filter(deliverable__uploaded_by_id=scope.profile_context.user_id)
    active = TaskAssignment.objects.filter(task_id=OuterRef("pk"), is_active=True)
    result = cohort.alias(_approved=Exists(credited), _verified=Exists(canonical), _assigned=Exists(active)).aggregate(
        total_tasks=Count("pk"),
        approved_tasks=Count("pk", filter=Q(_approved=True)),
        working_tasks=Count("pk", filter=Q(status=Task.Status.WORKING)),
        review_tasks=Count("pk", filter=Q(status=Task.Status.REVIEW)),
        overdue_tasks=Count("pk", filter=Q(deadline__lt=scope.snapshot_at) & ~Q(status__in=TERMINAL_STATUSES)),
        unassigned_tasks=Count("pk", filter=Q(_assigned=False) & ~Q(status__in=TERMINAL_STATUSES)),
        unverified_completed_tasks=Count("pk", filter=Q(status=Task.Status.COMPLETED, _verified=False)),
    )
    distribution = dict(cohort.values_list("status").annotate(count=Count("pk")))
    events = _approval_events(scope)
    attributed = ProfileMembership.objects.filter(
        profile_id=scope.profile_context.profile_id,
        user_id=OuterRef("deliverable__uploaded_by_id"),
    )
    result["unattributed_approved_tasks"] = events.alias(_has_tenant_identity=Exists(attributed)).filter(_has_tenant_identity=False).count()
    months = {
        row["month"].strftime("%Y-%m"): row["count"]
        for row in events.annotate(month=TruncMonth("created_at", tzinfo=ANALYTICS_TIMEZONE))
        .values("month").annotate(count=Count("pk")).order_by("month")
    }
    trend = []
    year, month = scope.from_date.year, scope.from_date.month
    while (year, month) <= (scope.to_date.year, scope.to_date.month):
        label = f"{year:04d}-{month:02d}"
        trend.append({"month": label, "count": months.get(label, 0)})
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    can_money = _can_read_money(scope)
    finance = None
    if can_money:
        financial = _financial_tasks(scope)
        estimates = financial.filter(created_at__gte=scope.start_at, created_at__lt=scope.end_before).aggregate(
            amount=Sum("estimated_compensation_vnd", output_field=MONEY_FIELD),
            known=Count("pk", filter=Q(estimated_compensation_vnd__isnull=False)),
            unpriced=Count("pk", filter=Q(estimated_compensation_vnd__isnull=True)),
        )
        finance = {
            "estimated_total_vnd": _money(estimates["amount"]),
            "estimated_known_tasks": estimates["known"],
            "estimated_unpriced_tasks": estimates["unpriced"],
            **_event_finance(events.filter(deliverable__task_id__in=_financial_tasks(scope, include_deleted=True).values("pk"))),
        }
    return {
        "scope": {
            "mode": scope.mode, "profile_id": str(scope.profile_context.profile_id),
            "workspace_id": str(scope.workspace_id) if scope.workspace_id else None,
            "timezone": "Asia/Ho_Chi_Minh", "from": scope.from_date.isoformat(),
            "to": scope.to_date.isoformat(), "start_at": scope.start_at.isoformat(),
            "end_before": scope.end_before.isoformat(), "snapshot_at": scope.snapshot_at.isoformat(),
            "cohort_basis": "task_created_at", "approvals_basis": "review_created_at",
            "include_subtasks": True,
            "operational_tasks_exclude_deleted": True,
            "historical_approvals_include_deleted": True,
            "deleted_task_details_omitted": True,
        },
        "capabilities": {"can_view_employee_breakdown": scope.mode == "management", "can_view_financial_totals": can_money},
        "kpis": result, "finance": finance,
        "distribution": [{"status": status, "count": distribution.get(status, 0)} for status in Task.Status.values],
        "approval_trend": trend,
    }


def _count_subquery(queryset, grouping, predicate=None):
    return Coalesce(Subquery(
        queryset.order_by().values(grouping).annotate(_count=Count("pk", filter=predicate)).values("_count")[:1],
        output_field=IntegerField(),
    ), Value(0))


def _sum_subquery(queryset, grouping, field, predicate=None):
    return Subquery(
        queryset.order_by().values(grouping).annotate(_sum=Sum(field, filter=predicate, output_field=MONEY_FIELD)).values("_sum")[:1],
        output_field=MONEY_FIELD,
    )


def analytics_employees(scope, *, search="", ordering="-active_tasks"):
    current = _cohort(scope).exclude(status__in=TERMINAL_STATUSES).filter(
        assignments__user_id=OuterRef("user_id"), assignments__is_active=True,
    )
    events = _approval_events(scope).filter(deliverable__uploaded_by_id=OuterRef("user_id"))
    canonical_membership = ProfileMembership.objects.filter(
        profile_id=scope.profile_context.profile_id, user_id=OuterRef("user_id"),
    ).order_by("-is_active", "-joined_at", "-id").values("pk")[:1]
    reader = WorkspaceMember.objects.filter(
        user_id=OuterRef("user_id"), workspace_id__in=scope.workspace_ids, is_active=True,
        role__in=(WorkspaceMember.Role.ADMIN, WorkspaceMember.Role.MEMBER, WorkspaceMember.Role.VIEWER),
    )
    queryset = ProfileMembership.objects.filter(profile_id=scope.profile_context.profile_id).annotate(
        _canonical_id=Subquery(canonical_membership),
        _current=Exists(current), _credited=Exists(events), _reader=Exists(reader),
    ).filter(pk=F("_canonical_id")).filter(
        Q(_current=True) | Q(_credited=True)
        | Q(is_active=True, user__is_active=True, role=ProfileMembership.Role.MEMBER, _reader=True)
    )
    if scope.mode == "self":
        queryset = queryset.filter(user_id=scope.profile_context.user_id)
    queryset = queryset.annotate(
        _available=Case(
            When(Q(is_active=True, user__is_active=True) & (Q(role__in=(ProfileMembership.Role.OWNER, ProfileMembership.Role.ADMIN)) | Q(role=ProfileMembership.Role.MEMBER, _reader=True)), then=Value(True)),
            default=Value(False), output_field=BooleanField(),
        ),
        active_tasks=_count_subquery(current, "assignments__user_id"),
        approved_tasks=_count_subquery(events, "deliverable__uploaded_by_id"),
        overdue_tasks=_count_subquery(current, "assignments__user_id", Q(deadline__lt=scope.snapshot_at)),
    ).select_related("user")
    financial = _financial_tasks(scope)
    priced_current = current.filter(pk__in=financial.values("pk"))
    priced_events = events.filter(deliverable__task_id__in=_financial_tasks(scope, include_deleted=True).values("pk"))
    queryset = queryset.annotate(
        _active_value=_sum_subquery(priced_current, "assignments__user_id", "estimated_compensation_vnd"),
        _active_known=_count_subquery(priced_current, "assignments__user_id", Q(estimated_compensation_vnd__isnull=False)),
        _active_unpriced=_count_subquery(priced_current, "assignments__user_id", Q(estimated_compensation_vnd__isnull=True)),
        _approved_value=_sum_subquery(priced_events, "deliverable__uploaded_by_id", "compensation_snapshot_vnd", Q(compensation_snapshot_recorded=True)),
        _approved_priced=_count_subquery(priced_events, "deliverable__uploaded_by_id", Q(compensation_snapshot_recorded=True, compensation_snapshot_vnd__isnull=False)),
        _approved_unpriced=_count_subquery(priced_events, "deliverable__uploaded_by_id", Q(compensation_snapshot_recorded=True, compensation_snapshot_vnd__isnull=True)),
        _approved_unknown=_count_subquery(priced_events, "deliverable__uploaded_by_id", Q(compensation_snapshot_recorded=False)),
    )
    if search:
        # Search only candidate names that may actually be disclosed; do not
        # turn an unavailable identity or email-valued username into a lookup.
        queryset = queryset.annotate(_raw_name=Trim(Concat("user__first_name", Value(" "), "user__last_name"))).annotate(
            _search_name=Case(
                When(Q(_available=True) & ~Q(_raw_name="") & ~Q(_raw_name__contains="@") & ~Q(_raw_name__regex=r"[\x01-\x1f\x7f-\x9f]") & ~Q(_raw_name__regex=r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"), then=F("_raw_name")),
                When(Q(_available=True, user__username__regex=r"^[[:alnum:]_.+-]+$") & ~Q(user__username__regex=r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"), then=F("user__username")),
                default=Value(""), output_field=CharField(),
            ),
        ).filter(_search_name__icontains=search)
    field = {"approved_value": "_approved_value"}.get(ordering.lstrip("-"), ordering.lstrip("-"))
    expression = F(field).desc(nulls_last=True) if ordering.startswith("-") else F(field).asc(nulls_last=True)
    return queryset.order_by(expression, "id")


def employee_row(scope, membership, *, can_money=None):
    if can_money is None:
        can_money = _can_read_money(scope)
    finance = None
    if can_money:
        finance = {
            "active_total_vnd": _money(membership._active_value),
            "active_known_tasks": membership._active_known,
            "active_unpriced_tasks": membership._active_unpriced,
            "approved_total_vnd": _money(membership._approved_value),
            "approved_priced_tasks": membership._approved_priced,
            "approved_unpriced_tasks": membership._approved_unpriced,
            "approved_unknown_tasks": membership._approved_unknown,
        }
    return {
        "id": str(membership.pk), "is_available": membership._available,
        "display_name": assignee_display_name(
            first_name=membership.user.first_name, last_name=membership.user.last_name,
            username=membership.user.username,
        ) if membership._available else None,
        "active_tasks": membership.active_tasks, "approved_tasks": membership.approved_tasks,
        "overdue_tasks": membership.overdue_tasks, "finance": finance,
    }


def employee_tasks(scope, membership):
    current = TaskAssignment.objects.filter(
        task_id=OuterRef("pk"), user_id=membership.user_id, is_active=True,
    )
    approved = _approval_events(scope).filter(
        deliverable__task_id=OuterRef("pk"), deliverable__uploaded_by_id=membership.user_id,
    )
    return scope.tasks.annotate(
        _employee_current=Case(
            When(Q(created_at__gte=scope.start_at, created_at__lt=scope.end_before) & ~Q(status__in=TERMINAL_STATUSES) & Exists(current), then=Value(True)),
            default=Value(False), output_field=BooleanField(),
        ),
        _employee_approved=Exists(approved),
    ).filter(Q(_employee_current=True) | Q(_employee_approved=True)).order_by("-created_at", "id")


def employee_task_row(task):
    return {
        "id": str(task.pk), "workspace_id": str(task.workspace_id), "title": task.title,
        "status": task.status, "deadline": task.deadline.isoformat() if task.deadline else None,
        "relation": "current_and_approved" if task._employee_current and task._employee_approved else "current" if task._employee_current else "approved",
    }
