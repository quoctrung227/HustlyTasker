from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import (
    sensitive_post_parameters,
    sensitive_variables,
)
from rest_framework import generics, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import APIException, NotFound, Throttled
from rest_framework.exceptions import ValidationError as ApiValidationError
from rest_framework.response import Response

from api.pagination import StandardResultsSetPagination

from .access import (
    TenantAccessNotFound,
    profile_invitations_visible_to_managers,
    profiles_visible_to,
    workspace_members_visible_to_managers,
    workspaces_visible_to,
)
from .permissions import (
    CanCreateWorkspace,
    CanEditWorkspaceMetadata,
    CanManageProfileLifecycle,
    CanManageProfileInvitations,
    CanManageWorkspaceLifecycle,
    CanManageWorkspaceMembers,
    HasActiveTenantIdentity,
    HasProfileAccess,
    HasWorkspaceReadAccess,
)
from .serializers import (
    ProfileInvitationActionSerializer,
    ProfileInvitationCreateSerializer,
    ProfileInvitationReadSerializer,
    ProfileInvitationTokenSerializer,
    ProfileLifecycleSerializer,
    ProfileReadSerializer,
    WorkspaceCreateSerializer,
    WorkspaceLifecycleSerializer,
    WorkspaceMemberCreateSerializer,
    WorkspaceMemberReadSerializer,
    WorkspaceMemberUpdateSerializer,
    WorkspaceReadSerializer,
    WorkspaceUpdateSerializer,
)
from .invitation_delivery import InvitationDeliveryUnavailable
from .invitation_services import (
    InvitationConflict,
    InvitationRateLimitExceeded,
    accept_profile_invitation,
    create_profile_invitation,
    decline_profile_invitation,
    resend_profile_invitation,
    revoke_profile_invitation,
)
from .invitation_throttles import (
    InvitationRecipientThrottle,
    InvitationSendThrottle,
    InvitationTokenActionThrottle,
)
from .services import (
    WorkspaceMembershipConflict,
    WorkspacePeriodConflict,
    add_workspace_member,
    archive_profile,
    archive_workspace,
    create_workspace,
    restore_profile,
    restore_workspace,
    revoke_workspace_member,
    update_workspace,
    update_workspace_member,
)


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "The requested operation conflicts with current state."
    default_code = "conflict"


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Invitation delivery is currently unavailable."
    default_code = "service_unavailable"


def _django_validation_detail(exc):
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    return exc.messages


class TenantApiViewMixin:
    authentication_classes = (SessionAuthentication,)
    pagination_class = StandardResultsSetPagination

    def handle_exception(self, exc):
        if isinstance(exc, InvitationConflict):
            exc = Conflict()
        elif isinstance(exc, InvitationRateLimitExceeded):
            exc = Throttled()
        elif isinstance(exc, InvitationDeliveryUnavailable):
            exc = ServiceUnavailable()
        elif isinstance(
            exc,
            (WorkspaceMembershipConflict, WorkspacePeriodConflict),
        ):
            exc = Conflict(detail=_django_validation_detail(exc))
        elif isinstance(exc, TenantAccessNotFound):
            exc = NotFound()
        elif isinstance(exc, ValidationError):
            exc = ApiValidationError(detail=_django_validation_detail(exc))

        return super().handle_exception(exc)


class TenantReadOnlyViewMixin(TenantApiViewMixin):
    http_method_names = ("get", "head", "options")


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
class ProfileLifecycleView(TenantApiViewMixin, generics.GenericAPIView):
    serializer_class = ProfileLifecycleSerializer
    permission_classes = (CanManageProfileLifecycle,)
    http_method_names = ("post", "options")
    lifecycle_service = None

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = self.lifecycle_service(
            actor=request.user,
            profile_id=self.profile_access_context.profile_id,
        )
        return Response(ProfileReadSerializer(profile).data)


class ProfileArchiveView(ProfileLifecycleView):
    lifecycle_service = staticmethod(archive_profile)


class ProfileRestoreView(ProfileLifecycleView):
    lifecycle_service = staticmethod(restore_profile)


@method_decorator(never_cache, name="dispatch")
class ProfileInvitationListView(TenantApiViewMixin, generics.ListAPIView):
    serializer_class = ProfileInvitationReadSerializer
    permission_classes = (CanManageProfileInvitations,)
    http_method_names = ("get", "post", "head", "options")

    def get_throttles(self):
        if self.request.method == "POST":
            return [InvitationSendThrottle(), InvitationRecipientThrottle()]
        return []

    def get_queryset(self):
        return profile_invitations_visible_to_managers(
            self.profile_access_context
        ).order_by("-created_at", "-id")

    def post(self, request, *args, **kwargs):
        serializer = ProfileInvitationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = create_profile_invitation(
            actor=request.user,
            profile_id=self.profile_access_context.profile_id,
            **serializer.validated_data,
        )
        invitation.refresh_from_db()
        return Response(
            ProfileInvitationReadSerializer(invitation).data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(never_cache, name="dispatch")
class ProfileInvitationDetailView(
    TenantReadOnlyViewMixin,
    ScopedRetrieveMixin,
    generics.RetrieveAPIView,
):
    serializer_class = ProfileInvitationReadSerializer
    permission_classes = (CanManageProfileInvitations,)
    lookup_field = "id"
    lookup_url_kwarg = "invitation_id"

    def get_queryset(self):
        return profile_invitations_visible_to_managers(
            self.profile_access_context
        )


@method_decorator(never_cache, name="dispatch")
class ProfileInvitationManagerActionView(
    TenantApiViewMixin,
    ScopedRetrieveMixin,
    generics.GenericAPIView,
):
    serializer_class = ProfileInvitationActionSerializer
    permission_classes = (CanManageProfileInvitations,)
    http_method_names = ("post", "options")
    lookup_field = "id"
    lookup_url_kwarg = "invitation_id"
    invitation_service = None
    throttle_classes = ()

    def get_queryset(self):
        return profile_invitations_visible_to_managers(
            self.profile_access_context
        )

    def post(self, request, *args, **kwargs):
        invitation = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invitation = self.invitation_service(
            actor=request.user,
            profile_id=self.profile_access_context.profile_id,
            invitation_id=invitation.id,
        )
        invitation.refresh_from_db()
        return Response(ProfileInvitationReadSerializer(invitation).data)


class ProfileInvitationRevokeView(ProfileInvitationManagerActionView):
    invitation_service = staticmethod(revoke_profile_invitation)


class ProfileInvitationResendView(ProfileInvitationManagerActionView):
    invitation_service = staticmethod(resend_profile_invitation)
    throttle_classes = (InvitationSendThrottle,)


@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters("token"), name="dispatch")
class ProfileInvitationRecipientActionView(
    TenantApiViewMixin,
    generics.GenericAPIView,
):
    serializer_class = ProfileInvitationTokenSerializer
    permission_classes = (HasActiveTenantIdentity,)
    throttle_classes = (InvitationTokenActionThrottle,)
    http_method_names = ("post", "options")
    invitation_service = None

    @sensitive_variables()
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = self.invitation_service(
            actor=request.user,
            token=serializer.validated_data["token"],
        )
        return Response(self.response_data(result))


class ProfileInvitationAcceptView(ProfileInvitationRecipientActionView):
    invitation_service = staticmethod(accept_profile_invitation)

    def response_data(self, membership):
        return {
            "status": "ACCEPTED",
            "profile_id": str(membership.profile_id),
            "membership_id": str(membership.id),
            "role": membership.role,
        }


class ProfileInvitationDeclineView(ProfileInvitationRecipientActionView):
    invitation_service = staticmethod(decline_profile_invitation)

    def response_data(self, invitation):
        return {"status": invitation.status}


@method_decorator(never_cache, name="dispatch")
class WorkspaceListView(TenantApiViewMixin, generics.ListAPIView):
    serializer_class = WorkspaceReadSerializer
    permission_classes = (HasProfileAccess,)
    http_method_names = ("get", "post", "head", "options")

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.request.method == "POST":
            permission_classes = (CanCreateWorkspace,)
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        return workspaces_visible_to(
            self.profile_access_context
        ).order_by(
            "created_at",
            "id",
        )

    def post(self, request, *args, **kwargs):
        serializer = WorkspaceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workspace = create_workspace(
            actor=request.user,
            profile_id=self.profile_access_context.profile_id,
            **serializer.validated_data,
        )
        response_serializer = WorkspaceReadSerializer(workspace)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
        )


@method_decorator(never_cache, name="dispatch")
class WorkspaceDetailView(
    TenantApiViewMixin,
    ScopedRetrieveMixin,
    generics.RetrieveAPIView,
):
    serializer_class = WorkspaceReadSerializer
    permission_classes = (HasWorkspaceReadAccess,)
    http_method_names = ("get", "patch", "head", "options")
    lookup_field = "id"
    lookup_url_kwarg = "workspace_id"

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.request.method == "PATCH":
            permission_classes = (CanEditWorkspaceMetadata,)
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        return workspaces_visible_to(self.profile_access_context)

    def patch(self, request, *args, **kwargs):
        serializer = WorkspaceUpdateSerializer(
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)

        workspace = update_workspace(
            actor=request.user,
            profile_id=self.workspace_access_context.profile_id,
            workspace_id=self.workspace_access_context.workspace_id,
            **serializer.validated_data,
        )
        response_serializer = WorkspaceReadSerializer(workspace)
        return Response(response_serializer.data)


@method_decorator(never_cache, name="dispatch")
class WorkspaceLifecycleView(TenantApiViewMixin, generics.GenericAPIView):
    serializer_class = WorkspaceLifecycleSerializer
    permission_classes = (CanManageWorkspaceLifecycle,)
    http_method_names = ("post", "options")
    lifecycle_service = None

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        workspace = self.lifecycle_service(
            actor=request.user,
            profile_id=self.workspace_access_context.profile_id,
            workspace_id=self.workspace_access_context.workspace_id,
        )
        return Response(WorkspaceReadSerializer(workspace).data)


class WorkspaceArchiveView(WorkspaceLifecycleView):
    lifecycle_service = staticmethod(archive_workspace)


class WorkspaceRestoreView(WorkspaceLifecycleView):
    lifecycle_service = staticmethod(restore_workspace)


@method_decorator(never_cache, name="dispatch")
class WorkspaceMemberListView(TenantApiViewMixin, generics.ListAPIView):
    serializer_class = WorkspaceMemberReadSerializer
    permission_classes = (CanManageWorkspaceMembers,)
    http_method_names = ("get", "post", "head", "options")

    def get_queryset(self):
        return workspace_members_visible_to_managers(
            self.workspace_access_context
        ).order_by("joined_at", "id")

    def post(self, request, *args, **kwargs):
        serializer = WorkspaceMemberCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = add_workspace_member(
            actor=request.user,
            profile_id=self.workspace_access_context.profile_id,
            workspace_id=self.workspace_access_context.workspace_id,
            **serializer.validated_data,
        )
        membership.profile_membership_id = serializer.validated_data[
            "target_profile_membership_id"
        ]
        response_serializer = WorkspaceMemberReadSerializer(membership)
        return Response(
            response_serializer.data,
            status=(
                status.HTTP_200_OK
                if membership.was_reactivated
                else status.HTTP_201_CREATED
            ),
        )


@method_decorator(never_cache, name="dispatch")
class WorkspaceMemberDetailView(TenantApiViewMixin, generics.GenericAPIView):
    serializer_class = WorkspaceMemberReadSerializer
    permission_classes = (CanManageWorkspaceMembers,)
    http_method_names = ("patch", "delete", "options")
    lookup_field = "id"
    lookup_url_kwarg = "membership_id"

    def get_queryset(self):
        return workspace_members_visible_to_managers(
            self.workspace_access_context
        )

    def _get_membership(self):
        try:
            membership = self.get_queryset().filter(
                id=self.kwargs[self.lookup_url_kwarg]
            ).first()
        except (TypeError, ValueError, ValidationError):
            raise NotFound() from None

        if membership is None:
            raise NotFound()
        return membership

    def patch(self, request, *args, **kwargs):
        membership = self._get_membership()
        profile_membership_id = membership.profile_membership_id
        serializer = WorkspaceMemberUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        membership = update_workspace_member(
            actor=request.user,
            profile_id=self.workspace_access_context.profile_id,
            workspace_id=self.workspace_access_context.workspace_id,
            membership_id=membership.id,
            **serializer.validated_data,
        )
        membership.profile_membership_id = profile_membership_id
        response_serializer = WorkspaceMemberReadSerializer(membership)
        return Response(response_serializer.data)

    def delete(self, request, *args, **kwargs):
        membership = self._get_membership()
        revoke_workspace_member(
            actor=request.user,
            profile_id=self.workspace_access_context.profile_id,
            workspace_id=self.workspace_access_context.workspace_id,
            membership_id=membership.id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
