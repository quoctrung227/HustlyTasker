from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import generics
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.workspace.permissions import HasActiveTenantIdentity
from apps.workspace.views import TenantApiViewMixin

from .access import notifications_visible_to
from .serializers import NotificationQuerySerializer, NotificationReadActionSerializer, NotificationReadSerializer
from .services import mark_notification_read


@method_decorator(never_cache, name="dispatch")
class NotificationListView(TenantApiViewMixin, generics.ListAPIView):
    serializer_class = NotificationReadSerializer
    permission_classes = (HasActiveTenantIdentity,)
    http_method_names = ("get", "head", "options")

    def get_queryset(self):
        query = {"is_read": self.request.query_params["is_read"]} if "is_read" in self.request.query_params else {}
        serializer = NotificationQuerySerializer(data=query)
        serializer.is_valid(raise_exception=True)
        return notifications_visible_to(self.request.user).filter(
            **serializer.validated_data,
        ).order_by("-created_at", "id")


@method_decorator(never_cache, name="dispatch")
class NotificationUnreadCountView(TenantApiViewMixin, generics.GenericAPIView):
    permission_classes = (HasActiveTenantIdentity,)
    http_method_names = ("get", "head", "options")

    def get(self, request, *args, **kwargs):
        return Response({"unread_count": notifications_visible_to(request.user).filter(is_read=False).count()})


@method_decorator(never_cache, name="dispatch")
class NotificationMarkReadView(TenantApiViewMixin, generics.GenericAPIView):
    serializer_class = NotificationReadActionSerializer
    permission_classes = (HasActiveTenantIdentity,)
    http_method_names = ("post", "options")

    def post(self, request, *args, **kwargs):
        try:
            exists = notifications_visible_to(request.user).filter(pk=kwargs["notification_id"]).exists()
        except (KeyError, ValueError, TypeError, ValidationError):
            raise NotFound() from None
        if not exists:
            raise NotFound()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notification = mark_notification_read(actor=request.user, notification_id=kwargs["notification_id"])
        return Response(NotificationReadSerializer(notification).data)
