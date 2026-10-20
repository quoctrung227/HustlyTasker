from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.reviews.models import Deliverable, Review
from apps.workspace.access import TenantAccessNotFound
from apps.workspace.permissions import HasWorkspaceReadAccess
from apps.workspace.views import Conflict, TenantApiViewMixin

from .access import resolve_task_in_scope, tasks_visible_to
from .models import TaskAssignment
from .permissions import (
    CanExecuteWorkspaceTasks,
    CanManageWorkspaceTasks,
    CanReviewWorkspaceDeliverables,
    HasTaskReadAccess,
)
from .serializers import (
    DeliverableApproveSerializer,
    DeliverableReadSerializer,
    DeliverableRequestChangesSerializer,
    DeliverableSubmitSerializer,
    EmptyTaskActionSerializer,
    TaskAssignSerializer,
    TaskCreateSerializer,
    TaskReadSerializer,
    TaskUpdateSerializer,
)
from .services import (
    TaskWorkflowConflict,
    approve_deliverable,
    assign_task,
    create_task,
    request_deliverable_changes,
    start_task,
    submit_deliverable,
    update_task,
)


def _django_validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return exc.messages


def _task_read_queryset(context):
    active_assignments = TaskAssignment.objects.filter(
        is_active=True,
    ).only(
        "id",
        "task_id",
        "user_id",
        "assigned_at",
    )
    return tasks_visible_to(context).select_related(
        "workspace",
    ).prefetch_related(
        Prefetch(
            "assignments",
            queryset=active_assignments,
            to_attr="_active_assignments",
        )
    )


def _deliverable_read_queryset(context, task_id):
    scoped_task_ids = tasks_visible_to(context).filter(
        id=task_id,
    ).values("id")
    reviews = Review.objects.select_related(
        "deliverable__task__workspace",
    ).order_by("created_at", "id")
    return Deliverable.objects.filter(
        task_id__in=scoped_task_ids,
    ).select_related(
        "task__workspace",
    ).prefetch_related(
        Prefetch(
            "reviews",
            queryset=reviews,
            to_attr="_workflow_reviews",
        )
    )


class TaskApiViewMixin(TenantApiViewMixin):
    """Translate workflow conflicts while retaining tenant API conventions."""

    def handle_exception(self, exc):
        if isinstance(exc, TaskWorkflowConflict):
            exc = Conflict(detail=_django_validation_detail(exc))
        return super().handle_exception(exc)


@method_decorator(never_cache, name="dispatch")
class TaskListView(TaskApiViewMixin, generics.ListAPIView):
    serializer_class = TaskReadSerializer
    permission_classes = (HasWorkspaceReadAccess,)
    http_method_names = ("get", "post", "head", "options")

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.request.method == "POST":
            permission_classes = (CanManageWorkspaceTasks,)
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        return _task_read_queryset(
            self.workspace_access_context
        ).order_by("created_at", "id")

    def post(self, request, *args, **kwargs):
        serializer = TaskCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = create_task(
            actor=request.user,
            profile_id=self.workspace_access_context.profile_id,
            workspace_id=self.workspace_access_context.workspace_id,
            **serializer.validated_data,
        )
        return Response(
            TaskReadSerializer(task).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(never_cache, name="dispatch")
class TaskDetailView(TaskApiViewMixin, generics.GenericAPIView):
    serializer_class = TaskReadSerializer
    permission_classes = (HasTaskReadAccess,)
    http_method_names = ("get", "patch", "head", "options")

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.request.method == "PATCH":
            permission_classes = (CanManageWorkspaceTasks,)
        return [permission() for permission in permission_classes]

    def _get_task(self):
        try:
            return resolve_task_in_scope(
                self.workspace_access_context,
                self.kwargs["task_id"],
            )
        except (KeyError, TenantAccessNotFound):
            raise NotFound() from None

    def get(self, request, *args, **kwargs):
        return Response(TaskReadSerializer(self._get_task()).data)

    def patch(self, request, *args, **kwargs):
        task = self._get_task()
        serializer = TaskUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = update_task(
            actor=request.user,
            profile_id=self.workspace_access_context.profile_id,
            workspace_id=self.workspace_access_context.workspace_id,
            task_id=task.id,
            **serializer.validated_data,
        )
        return Response(TaskReadSerializer(task).data)


class TaskActionView(TaskApiViewMixin, generics.GenericAPIView):
    http_method_names = ("post", "options")


@method_decorator(never_cache, name="dispatch")
class TaskAssignView(TaskActionView):
    serializer_class = TaskAssignSerializer
    permission_classes = (CanManageWorkspaceTasks,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = assign_task(
            actor=request.user,
            profile_id=self.workspace_access_context.profile_id,
            workspace_id=self.workspace_access_context.workspace_id,
            task_id=self.task.id,
            **serializer.validated_data,
        )
        return Response(TaskReadSerializer(assignment.task).data)


@method_decorator(never_cache, name="dispatch")
class TaskStartView(TaskActionView):
    serializer_class = EmptyTaskActionSerializer
    permission_classes = (CanExecuteWorkspaceTasks,)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = start_task(
            actor=request.user,
            profile_id=self.workspace_access_context.profile_id,
            workspace_id=self.workspace_access_context.workspace_id,
            task_id=self.task.id,
        )
        return Response(TaskReadSerializer(task).data)


@method_decorator(never_cache, name="dispatch")
class DeliverableListView(TaskApiViewMixin, generics.ListAPIView):
    serializer_class = DeliverableReadSerializer
    permission_classes = (HasTaskReadAccess,)
    http_method_names = ("get", "post", "head", "options")

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.request.method == "POST":
            permission_classes = (CanExecuteWorkspaceTasks,)
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        return _deliverable_read_queryset(
            self.workspace_access_context,
            self.task.id,
        ).order_by("created_at", "id")

    def post(self, request, *args, **kwargs):
        serializer = DeliverableSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deliverable = submit_deliverable(
            actor=request.user,
            profile_id=self.workspace_access_context.profile_id,
            workspace_id=self.workspace_access_context.workspace_id,
            task_id=self.task.id,
            **serializer.validated_data,
        )
        return Response(
            DeliverableReadSerializer(deliverable).data,
            status=status.HTTP_201_CREATED,
        )


class DeliverableReviewView(TaskActionView):
    permission_classes = (CanReviewWorkspaceDeliverables,)
    review_service = None

    def _get_deliverable(self):
        try:
            deliverable = _deliverable_read_queryset(
                self.workspace_access_context,
                self.task.id,
            ).filter(id=self.kwargs["deliverable_id"]).first()
        except (KeyError, TypeError, ValueError, ValidationError):
            raise NotFound() from None

        if deliverable is None:
            raise NotFound()
        return deliverable

    def post(self, request, *args, **kwargs):
        # Resolve the nested resource before parsing action data so a
        # wrong-parent ID always receives the same non-disclosing 404.
        deliverable = self._get_deliverable()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        review = self.review_service(
            actor=request.user,
            profile_id=self.workspace_access_context.profile_id,
            workspace_id=self.workspace_access_context.workspace_id,
            task_id=self.task.id,
            deliverable_id=deliverable.id,
            **serializer.validated_data,
        )
        return Response(DeliverableReadSerializer(review.deliverable).data)


@method_decorator(never_cache, name="dispatch")
class DeliverableApproveView(DeliverableReviewView):
    serializer_class = DeliverableApproveSerializer
    review_service = staticmethod(approve_deliverable)


@method_decorator(never_cache, name="dispatch")
class DeliverableRequestChangesView(DeliverableReviewView):
    serializer_class = DeliverableRequestChangesSerializer
    review_service = staticmethod(request_deliverable_changes)
