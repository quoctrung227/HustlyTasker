from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import generics
from rest_framework.exceptions import NotFound, ValidationError as ApiValidationError
from rest_framework.response import Response

from apps.workspace.permissions import HasProfileAccess
from apps.workspace.views import TenantApiViewMixin

from .analytics import (
    _can_read_money, analytics_employees, analytics_summary, employee_row,
    employee_task_row, employee_tasks, resolve_analytics_scope,
)
from .analytics_serializers import AnalyticsQuerySerializer


class AnalyticsViewMixin(TenantApiViewMixin):
    permission_classes = (HasProfileAccess,)
    http_method_names = ("get", "head", "options")
    serializer_class = AnalyticsQuerySerializer

    def analytics_context(self):
        if hasattr(self, "_analytics_context"):
            return self._analytics_context
        params = {key: value for key, value in self.request.query_params.items() if key not in ("page", "page_size", "format")}
        serializer = AnalyticsQuerySerializer(data=params)
        serializer.is_valid(raise_exception=True)
        self.analytics_filters = serializer.validated_data
        self._analytics_context = resolve_analytics_scope(
            actor=self.request.user, profile_id=self.kwargs["profile_id"], filters=self.analytics_filters,
        )
        return self._analytics_context


@method_decorator(never_cache, name="dispatch")
class AnalyticsSummaryView(AnalyticsViewMixin, generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        return Response(analytics_summary(self.analytics_context()))


@method_decorator(never_cache, name="dispatch")
class AnalyticsEmployeeListView(AnalyticsViewMixin, generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        scope = self.analytics_context()
        can_money = _can_read_money(scope)
        ordering = self.analytics_filters["ordering"]
        if "approved_value" in ordering and not can_money:
            raise ApiValidationError({"ordering": "Bạn không có quyền sắp xếp theo giá trị tài chính."})
        queryset = analytics_employees(scope, search=self.analytics_filters.get("search", ""), ordering=ordering)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response([employee_row(scope, item, can_money=can_money) for item in page])


@method_decorator(never_cache, name="dispatch")
class AnalyticsEmployeeDetailView(AnalyticsViewMixin, generics.GenericAPIView):
    def get(self, request, *args, **kwargs):
        scope = self.analytics_context()
        try:
            membership = analytics_employees(scope).filter(pk=self.kwargs["membership_id"]).first()
        except (ValidationError, ValueError, TypeError):
            raise NotFound() from None
        if membership is None:
            raise NotFound()
        page = self.paginate_queryset(employee_tasks(scope, membership))
        response = self.get_paginated_response([employee_task_row(item) for item in page])
        response.data["employee"] = employee_row(scope, membership)
        return response
