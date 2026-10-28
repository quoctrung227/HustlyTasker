from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import generics, status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.workspace.access import TenantAccessNotFound
from apps.workspace.serializers import StrictInputSerializer

from .comment_serializers import CommentReadSerializer, CommentWriteSerializer
from .comment_services import can_comment_on_task, comments_visible_to, create_comment, delete_comment, update_comment
from .permissions import HasTaskReadAccess
from .views import TaskApiViewMixin


class HasCommentAccess(HasTaskReadAccess):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.method in ("GET", "HEAD", "OPTIONS") or can_comment_on_task(view.workspace_access_context)


class CommentApiViewMixin(TaskApiViewMixin):
    permission_classes = (HasCommentAccess,)

    def _scope(self):
        return {"actor": self.request.user,
                "profile_id": self.workspace_access_context.profile_id,
                "workspace_id": self.workspace_access_context.workspace_id,
                "task_id": self.task.id}

    def _get_comment(self):
        try:
            comment = comments_visible_to(self.workspace_access_context, self.task.id).filter(
                id=self.kwargs["comment_id"],
            ).first()
        except (KeyError, TypeError, ValueError, ValidationError, TenantAccessNotFound):
            raise NotFound() from None
        if comment is None:
            raise NotFound()
        return comment


@method_decorator(never_cache, name="dispatch")
class CommentListView(CommentApiViewMixin, generics.ListAPIView):
    serializer_class = CommentReadSerializer
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        return comments_visible_to(self.workspace_access_context, self.task.id).order_by("created_at", "id")

    def post(self, request, *args, **kwargs):
        serializer = CommentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = create_comment(**self._scope(), **serializer.validated_data)
        return Response(CommentReadSerializer(
            comment, context=self.get_serializer_context(),
        ).data, status=status.HTTP_201_CREATED)


@method_decorator(never_cache, name="dispatch")
class CommentDetailView(CommentApiViewMixin, generics.GenericAPIView):
    serializer_class = CommentReadSerializer
    http_method_names = ("get", "patch", "delete", "head", "options")

    def get(self, request, *args, **kwargs):
        return Response(CommentReadSerializer(
            self._get_comment(), context=self.get_serializer_context(),
        ).data)

    def patch(self, request, *args, **kwargs):
        comment = self._get_comment()
        if comment.user_id != request.user.id:
            raise PermissionDenied("Only the current author may edit a comment.")
        serializer = CommentWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = update_comment(**self._scope(), comment_id=comment.id, **serializer.validated_data)
        return Response(CommentReadSerializer(
            comment, context=self.get_serializer_context(),
        ).data)

    def delete(self, request, *args, **kwargs):
        comment = self._get_comment()
        serializer = StrictInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        delete_comment(**self._scope(), comment_id=comment.id)
        return Response(status=status.HTTP_204_NO_CONTENT)
