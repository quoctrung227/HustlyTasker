from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, override_settings
from django.urls import URLPattern, URLResolver, reverse
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from rest_framework.views import APIView

from api.views import HealthCheckView
from apps.accounts.views import (
    CsrfTokenView,
    LoginView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RegisterView,
)
from config import urls as root_urls


User = get_user_model()


class DefaultPermissionProbeView(APIView):
    """Test-only view with no authentication or permission override."""

    def get(self, request):
        return Response({"status": "authenticated"})


def iter_url_view_classes(urlpatterns, prefix=""):
    for entry in urlpatterns:
        route = f"{prefix}{entry.pattern}"
        if isinstance(entry, URLResolver):
            yield from iter_url_view_classes(entry.url_patterns, route)
        elif isinstance(entry, URLPattern):
            callback = entry.callback
            view_class = getattr(callback, "view_class", None) or getattr(
                callback,
                "cls",
                None,
            )
            yield route, view_class


def get_api_view_classes():
    return {
        view_class
        for route, view_class in iter_url_view_classes(root_urls.urlpatterns)
        if route.startswith("api/")
    }


class ApiConfigurationTests(SimpleTestCase):
    def test_all_api_routes_use_drf_views(self):
        view_classes = get_api_view_classes()

        self.assertTrue(view_classes)
        self.assertNotIn(None, view_classes)
        for view_class in view_classes:
            with self.subTest(view_class=view_class):
                self.assertTrue(issubclass(view_class, APIView))

    def test_only_intended_api_views_explicitly_allow_anonymous_access(self):
        view_classes = get_api_view_classes()
        for view_class in view_classes:
            with self.subTest(view_class=view_class):
                self.assertTrue(view_class.permission_classes)

        actual_public_views = {
            view_class
            for view_class in view_classes
            if AllowAny in view_class.permission_classes
        }
        intended_public_views = {
            HealthCheckView,
            CsrfTokenView,
            RegisterView,
            LoginView,
            PasswordResetRequestView,
            PasswordResetConfirmView,
        }

        self.assertEqual(actual_public_views, intended_public_views)

    def test_default_drf_configuration_is_session_and_deny_by_default(self):
        self.assertEqual(
            DefaultPermissionProbeView.authentication_classes,
            [SessionAuthentication],
        )
        self.assertEqual(
            DefaultPermissionProbeView.permission_classes,
            [IsAuthenticated],
        )

    def test_default_permission_rejects_anonymous_and_accepts_authenticated_user(self):
        view = DefaultPermissionProbeView.as_view()
        factory = APIRequestFactory()

        anonymous_response = view(factory.get("/private-probe/"))
        self.assertEqual(anonymous_response.status_code, 403)

        user = User(email="member@example.com", username="member")
        authenticated_request = factory.get("/private-probe/")
        force_authenticate(authenticated_request, user=user)
        authenticated_response = view(authenticated_request)
        self.assertEqual(authenticated_response.status_code, 200)


@override_settings(SECURE_SSL_REDIRECT=False)
class HealthCheckApiTests(SimpleTestCase):
    def setUp(self):
        self.url = reverse("health")
        self.client = APIClient()

    def test_health_is_public_database_independent_and_minimal(self):
        # SimpleTestCase rejects database access, so this request fails if the
        # liveness endpoint (or its middleware path) starts querying a database.
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {"status": "ok"})
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn("no-store", response["Cache-Control"])

    def test_health_is_json_only(self):
        response = self.client.get(self.url, HTTP_ACCEPT="text/html")

        self.assertEqual(response.status_code, 406)
        self.assertEqual(response["Content-Type"], "application/json")

    def test_health_rejects_unsupported_methods(self):
        for method in ("POST", "PUT", "PATCH", "DELETE", "TRACE"):
            with self.subTest(method=method):
                response = self.client.generic(method, self.url)
                self.assertEqual(response.status_code, 405)

    def test_health_supports_standard_head_and_options_methods(self):
        head_response = self.client.head(self.url)
        options_response = self.client.options(self.url)

        self.assertEqual(head_response.status_code, 200)
        self.assertEqual(head_response.content, b"")
        self.assertEqual(options_response.status_code, 200)
        self.assertEqual(
            set(options_response["Allow"].replace(" ", "").split(",")),
            {"GET", "HEAD", "OPTIONS"},
        )

    def test_legacy_test_endpoint_is_removed(self):
        response = self.client.get("/api/test/")

        self.assertEqual(response.status_code, 404)

    def test_admin_is_outside_drf_and_uses_django_admin_authentication(self):
        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])
