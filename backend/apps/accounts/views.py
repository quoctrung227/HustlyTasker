from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from django.core.exceptions import ValidationError as DjangoValidationError
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import serializers, status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .serializers import LoginSerializer, RegisterSerializer, UserSerializer
from .email_delivery import AccountSecurityDeliveryUnavailable
from .security_services import (
    AccountSecurityConflict,
    confirm_email_verification,
    confirm_password_reset,
    request_email_verification,
    request_password_reset,
)
from .security_throttles import (
    EmailVerificationConfirmThrottle,
    EmailVerificationRequestThrottle,
    PasswordResetConfirmIpThrottle,
    PasswordResetConfirmThrottle,
    PasswordResetRequestEmailThrottle,
    PasswordResetRequestIpThrottle,
)
from .serializers import (
    EmailVerificationConfirmSerializer,
    EmailVerificationRequestSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)


@method_decorator(ensure_csrf_cookie, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class CsrfTokenView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(never_cache, name="dispatch")
@method_decorator(
    sensitive_post_parameters("password", "password_confirm"),
    name="dispatch",
)
class RegisterView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_register"

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters("password"), name="dispatch")
class LoginView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (ScopedRateThrottle,)
    throttle_scope = "auth_login"

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        django_login(request, user)
        return Response({"user": UserSerializer(user).data})


class LogoutView(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        django_logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(never_cache, name="dispatch")
class CurrentUserView(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return Response({"user": UserSerializer(request.user).data})


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class EmailVerificationRequestView(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (EmailVerificationRequestThrottle,)

    def post(self, request):
        serializer = EmailVerificationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            request_email_verification(user=request.user)
        except AccountSecurityDeliveryUnavailable:
            return Response(
                {"detail": "Account security email delivery is unavailable."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AccountSecurityConflict:
            return Response(
                {"detail": "Account security action could not be completed."},
                status=status.HTTP_409_CONFLICT,
            )
        return Response(
            {"detail": "Verification request accepted."},
            status=status.HTTP_202_ACCEPTED,
        )


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(never_cache, name="dispatch")
@method_decorator(sensitive_post_parameters("token"), name="dispatch")
class EmailVerificationConfirmView(APIView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    throttle_classes = (EmailVerificationConfirmThrottle,)

    def post(self, request):
        serializer = EmailVerificationConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_email_verification(
                actor=request.user,
                raw_token=serializer.validated_data["token"],
            )
        except AccountSecurityConflict:
            return Response(
                {"detail": "Invalid or unavailable account security token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Email verified."})


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(never_cache, name="dispatch")
class PasswordResetRequestView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (
        PasswordResetRequestEmailThrottle,
        PasswordResetRequestIpThrottle,
    )

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            request_password_reset(email=serializer.validated_data["email"])
        except AccountSecurityDeliveryUnavailable:
            # Keep this public response identical for every address, including
            # when the configured delivery channel is unavailable.
            pass
        except AccountSecurityConflict:
            # Race outcomes must remain indistinguishable from an ineligible
            # or unknown email address.
            pass
        return Response(
            {
                "detail": (
                    "If an eligible account exists, the request has been "
                    "accepted."
                )
            },
            status=status.HTTP_202_ACCEPTED,
        )


@method_decorator(csrf_protect, name="dispatch")
@method_decorator(never_cache, name="dispatch")
@method_decorator(
    sensitive_post_parameters(
        "token",
        "new_password",
        "new_password_confirm",
    ),
    name="dispatch",
)
class PasswordResetConfirmView(APIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)
    throttle_classes = (
        PasswordResetConfirmThrottle,
        PasswordResetConfirmIpThrottle,
    )

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            confirm_password_reset(
                raw_token=serializer.validated_data["token"],
                new_password=serializer.validated_data["new_password"],
            )
        except AccountSecurityConflict:
            return Response(
                {"detail": "Invalid or unavailable account security token."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({
                "new_password": list(exc.messages),
            }) from exc
        return Response(status=status.HTTP_204_NO_CONTENT)
