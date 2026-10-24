from django.urls import path

from .views import (
    CsrfTokenView,
    CurrentUserView,
    EmailVerificationConfirmView,
    EmailVerificationRequestView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)


app_name = "accounts"

urlpatterns = [
    path("csrf/", CsrfTokenView.as_view(), name="csrf"),
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", CurrentUserView.as_view(), name="me"),
    path(
        "email-verification/request/",
        EmailVerificationRequestView.as_view(),
        name="email-verification-request",
    ),
    path(
        "email-verification/confirm/",
        EmailVerificationConfirmView.as_view(),
        name="email-verification-confirm",
    ),
    path(
        "password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
]
