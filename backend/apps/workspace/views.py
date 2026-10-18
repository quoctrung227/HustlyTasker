from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import NotFound

from api.pagination import StandardResultsSetPagination

from .access import (
    TenantAccessNotFound,
    profiles_visible_to,
    workspaces_visible_to,
)
from .permissions import (
    HasActiveTenantIdentity,
    HasProfileAccess,
    HasWorkspaceReadAccess,
)
from .serializers import ProfileReadSerializer, WorkspaceReadSerializer


class TenantReadOnlyViewMixin:
    authentication_classes = (SessionAuthentication,)
    pagination_class = StandardResultsSetPagination
    http_method_names = ("get", "head", "options")

    def handle_exception(self, exc):
        if isinstance(exc, TenantAccessNotFound):
            exc = NotFound()
        return super().handle_exception(exc)


class ScopedRetrieveMixin:
    """Retrieve only from an already-scoped queryset with a generic 404."""

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        lookup_value = self.kwargs[lookup_url_kwarg]

        try:
            instance = queryset.filter(
                **{self.lookup_field: lookup_value}
            ).first()
        except (TypeError, ValueError, ValidationError):
            raise NotFound() from None

        if instance is None:
            raise NotFound()

        self.check_object_permissions(self.request, instance)
        return instance


@method_decorator(never_cache, name="dispatch")
class ProfileListView(TenantReadOnlyViewMixin, generics.ListAPIView):
    serializer_class = ProfileReadSerializer
    permission_classes = (HasActiveTenantIdentity,)

    def get_queryset(self):
        return profiles_visible_to(self.request.user).order_by(
            "created_at",
            "id",
        )


@method_decorator(never_cache, name="dispatch")
class ProfileDetailView(
    TenantReadOnlyViewMixin,
    ScopedRetrieveMixin,
    generics.RetrieveAPIView,
):
    serializer_class = ProfileReadSerializer
    permission_classes = (HasProfileAccess,)
    lookup_field = "id"
    lookup_url_kwarg = "profile_id"

    def get_queryset(self):
        return profiles_visible_to(self.request.user)


@method_decorator(never_cache, name="dispatch")
class WorkspaceListView(TenantReadOnlyViewMixin, generics.ListAPIView):
    serializer_class = WorkspaceReadSerializer
    permission_classes = (HasProfileAccess,)

    def get_queryset(self):
        return workspaces_visible_to(
            self.profile_access_context
        ).order_by(
            "created_at",
            "id",
        )


@method_decorator(never_cache, name="dispatch")
class WorkspaceDetailView(
    TenantReadOnlyViewMixin,
    ScopedRetrieveMixin,
    generics.RetrieveAPIView,
):
    serializer_class = WorkspaceReadSerializer
    permission_classes = (HasWorkspaceReadAccess,)
    lookup_field = "id"
    lookup_url_kwarg = "workspace_id"

    def get_queryset(self):
        return workspaces_visible_to(self.profile_access_context)
