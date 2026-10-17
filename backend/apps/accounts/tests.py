from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase


User = get_user_model()
VALID_PASSWORD = "Z3bra!River$9284"


class RegistrationApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.url = reverse("accounts:register")
        self.payload = {
            "email": "new.user@example.com",
            "username": "new.user",
            "first_name": "New",
            "last_name": "User",
            "password": VALID_PASSWORD,
            "password_confirm": VALID_PASSWORD,
        }

    def test_registers_user_with_hashed_password_without_logging_in(self):
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email=self.payload["email"])
        self.assertTrue(user.check_password(VALID_PASSWORD))
        self.assertNotEqual(user.password, VALID_PASSWORD)
        self.assertNotIn("password", response.data["user"])
        self.assertEqual(response.data["user"]["email"], self.payload["email"])
        self.assertEqual(
            self.client.get(reverse("accounts:me")).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_rejects_duplicate_email_case_insensitively(self):
        User.objects.create_user(
            email="NEW.USER@example.com",
            username="existing.user",
            password=VALID_PASSWORD,
        )

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_rejects_duplicate_username_case_insensitively(self):
        User.objects.create_user(
            email="existing@example.com",
            username="NEW.USER",
            password=VALID_PASSWORD,
        )

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", response.data)
        self.assertEqual(User.objects.count(), 1)

    def test_canonicalizes_email_for_new_accounts(self):
        self.payload["email"] = "New.User@EXAMPLE.COM"

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="new.user@example.com").exists())
        self.assertEqual(response.data["user"]["email"], "new.user@example.com")

    def test_rejects_weak_password(self):
        self.payload["password"] = "password"
        self.payload["password_confirm"] = "password"

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.exists())

    def test_rejects_password_confirmation_mismatch(self):
        self.payload["password_confirm"] = "Different!Password$493"

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password_confirm", response.data)
        self.assertFalse(User.objects.exists())

    def test_rejects_password_longer_than_128_characters(self):
        self.payload["password"] = "A" * 129
        self.payload["password_confirm"] = "A" * 129

        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data)
        self.assertFalse(User.objects.exists())

    def test_register_is_throttled(self):
        self.payload["password_confirm"] = "Different!Password$493"

        for attempt in range(5):
            response = self.client.post(
                self.url,
                self.payload,
                format="json",
                HTTP_X_FORWARDED_FOR=f"203.0.113.{attempt}",
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(
            self.url,
            self.payload,
            format="json",
            HTTP_X_FORWARDED_FOR="203.0.113.250",
        )
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class SessionAuthenticationApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")
        self.me_url = reverse("accounts:me")
        self.user = User.objects.create_user(
            email="member@example.com",
            username="member",
            password=VALID_PASSWORD,
        )

    def test_login_creates_session_and_me_returns_current_user(self):
        login_response = self.client.post(
            self.login_url,
            {"email": "MEMBER@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        self.assertIn("_auth_user_id", self.client.session)

        me_response = self.client.get(self.me_url)
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["user"]["id"], str(self.user.id))
        self.assertNotIn("is_staff", me_response.data["user"])
        self.assertIn("no-store", me_response["Cache-Control"])

    def test_login_failure_is_neutral_for_wrong_or_unknown_credentials(self):
        wrong_password = self.client.post(
            self.login_url,
            {"email": self.user.email, "password": "Wrong!Password$493"},
            format="json",
        )
        unknown_user = self.client.post(
            self.login_url,
            {"email": "unknown@example.com", "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(wrong_password.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(unknown_user.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(wrong_password.data, unknown_user.data)
        self.assertEqual(
            wrong_password.data["detail"][0],
            "Invalid email or password.",
        )

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        response = self.client.post(
            self.login_url,
            {"email": self.user.email, "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"][0], "Invalid email or password.")

    def test_me_requires_authentication(self):
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_logout_invalidates_current_session(self):
        self.client.login(email=self.user.email, password=VALID_PASSWORD)

        logout_response = self.client.post(self.logout_url, format="json")

        self.assertEqual(logout_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            self.client.get(self.me_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_logout_only_accepts_post(self):
        self.client.login(email=self.user.email, password=VALID_PASSWORD)

        response = self.client.get(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_login_is_throttled(self):
        payload = {
            "email": self.user.email,
            "password": "Wrong!Password$493",
        }

        for _ in range(10):
            response = self.client.post(self.login_url, payload, format="json")
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(self.login_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class SessionCsrfTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient(enforce_csrf_checks=True)
        self.csrf_url = reverse("accounts:csrf")
        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")
        self.register_url = reverse("accounts:register")
        self.user = User.objects.create_user(
            email="csrf.user@example.com",
            username="csrf.user",
            password=VALID_PASSWORD,
        )

    def get_csrf_token(self):
        response = self.client.get(self.csrf_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrftoken", self.client.cookies)
        return response.data["csrf_token"]

    def test_login_requires_csrf_token(self):
        response = self.client.post(
            self.login_url,
            {"email": self.user.email, "password": VALID_PASSWORD},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_register_requires_csrf_token(self):
        payload = {
            "email": "csrf.registration@example.com",
            "username": "csrf.registration",
            "password": VALID_PASSWORD,
            "password_confirm": VALID_PASSWORD,
        }

        denied_response = self.client.post(
            self.register_url,
            payload,
            format="json",
        )
        csrf_token = self.get_csrf_token()
        allowed_response = self.client.post(
            self.register_url,
            payload,
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(denied_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(allowed_response.status_code, status.HTTP_201_CREATED)

    def test_authenticated_logout_requires_csrf_token(self):
        csrf_token = self.get_csrf_token()
        login_response = self.client.post(
            self.login_url,
            {"email": self.user.email, "password": VALID_PASSWORD},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        denied_response = self.client.post(self.logout_url, format="json")
        refreshed_csrf_token = self.get_csrf_token()
        allowed_response = self.client.post(
            self.logout_url,
            format="json",
            HTTP_X_CSRFTOKEN=refreshed_csrf_token,
        )

        self.assertEqual(denied_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(allowed_response.status_code, status.HTTP_204_NO_CONTENT)


class UserAdminTests(APITestCase):
    def test_user_change_page_renders_auto_managed_timestamps_as_readonly(self):
        administrator = User.objects.create_superuser(
            email="administrator@example.com",
            username="administrator",
            password=VALID_PASSWORD,
        )
        self.client.force_login(administrator)

        response = self.client.get(
            reverse("admin:accounts_user_change", args=(administrator.pk,))
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
