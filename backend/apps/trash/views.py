from django.core.exceptions import PermissionDenied, ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import APIException, NotFound, ValidationError as ApiValidationError
from rest_framework.generics import GenericAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.workspace.access import TenantAccessNotFound
from apps.workspace.permissions import HasActiveTenantIdentity

from .serializers import EmptyActionSerializer, PurgeSerializer, TrashQuerySerializer
from .services import TrashConflict, item_data, mutate, read_page_entries, resolve_entry


class TrashPagination(PageNumberPagination):
    page_size = 20


class Conflict(APIException):
    status_code = 409
    default_code = "trash_conflict"


class TrashView(GenericAPIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (HasActiveTenantIdentity,)

    def handle_exception(self, exc):
        if isinstance(exc, TrashConflict):
            exc = Conflict(detail={"detail": exc.message, "code": exc.code, "blockers": exc.blockers})
        elif isinstance(exc, TenantAccessNotFound):
            exc = NotFound()
        elif isinstance(exc, ValidationError):
            exc = ApiValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return super().handle_exception(exc)


@method_decorator(never_cache, name="dispatch")
class TrashListView(TrashView):
    http_method_names = ("get", "options")
    pagination_class = TrashPagination

    def get(self, request):
        query = TrashQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        entries = read_page_entries(request.user, query.validated_data)
        page = self.paginate_queryset(entries)
        data = []
        for entry in page:
            try:
                obj = resolve_entry(entry["object_type"], entry["id"])
            except TenantAccessNotFound:
                # An already-paginated object may be purged concurrently.
                continue
            # Revalidate at serialization time if permissions changed after count.
            from .permissions import can_manage
            if obj.deleted_at is not None and can_manage(request.user, obj):
                data.append(item_data(obj, request.user))
        return self.get_paginated_response(data)


@method_decorator(never_cache, name="dispatch")
class TrashActionView(TrashView):
    http_method_names = ("post", "options")

    def post(self, request, object_type, object_id, action):
        serializer = PurgeSerializer(data=request.data) if action == "purge" else EmptyActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        obj = mutate(actor=request.user, object_type=object_type.upper(), object_id=object_id,
                     action=action, **serializer.validated_data)
        return Response(item_data(obj, request.user)) if action == "delete" else Response(status=204)
