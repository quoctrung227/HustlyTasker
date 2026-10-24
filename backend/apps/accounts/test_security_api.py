import json
import re
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from .models import AccountSecurityToken
from .security_throttles import (
    EmailVerificationConfirmThrottle,
    EmailVerificationRequestThrottle,
    PasswordResetConfirmIpThrottle,
    PasswordResetConfirmThrottle,
    PasswordResetRequestEmailThrottle,
    PasswordResetRequestIpThrottle,
)


User = get_user_model()
CURRENT_PASSWORD = "Z3bra!River$9284"
NEW_PASSWORD = "V10let!Harbor$7316"
LOCMEM_MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    }
}
UNSAFE_MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    }
}
TOKEN_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_-])([A-Za-z0-9_-]{40,128})(?![A-Za-z0-9_-])"
)


def extract_latest_token():
    """Read a high-entropy credential only from the isolated test mailbox."""

    if not mail.outbox:
        raise AssertionError("The test mail backend did not receive a message.")
    matches = TOKEN_PATTERN.findall(mail.outbox[-1].body)
    if len(matches) != 1:
        raise AssertionError(
            f"Expected exactly one opaque token in the test message, got {len(matches)}."
        )
    return matches[0]


@override_settings(MAILERS=LOCMEM_MAILERS)
class AccountSecurityApiTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(
            email="security-api@example.test",
            username="security-api",
            password=CURRENT_PASSWORD,
        )
        self.other_user = User.objects.create_user(
            email="other-security-api@example.test",
            username="other-security-api",
            password=CURRENT_PASSWORD,
        )
        self.verification_request_url = reverse(
            "accounts:email-verification-request"
        )
        self.verification_confirm_url = reverse(
            "accounts:email-verification-confirm"
        )
        self.reset_request_url = reverse("accounts:password-reset-request")
        self.reset_confirm_url = reverse("accounts:password-reset-confirm")
        self.me_url = reverse("accounts:me")

    def post_with_callbacks(self, client, url, payload):
        with self.captureOnCommitCallbacks(execute=True):
            return client.post(url, payload, format="json")

    def request_verification(self, *, client=None):
        client = client or self.client
        client.force_login(self.user)
        response = self.post_with_callbacks(
            client,
            self.verification_request_url,
            {},
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(
            response.data,
            {"detail": "Verification request accepted."},
        )
        return response, extract_latest_token()

    def request_password_reset(self, email=None, *, client=None):
        client = client or self.client
        response = self.post_with_callbacks(
            client,
            self.reset_request_url,
            {"email": email or self.user.email},
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(
            response.data,
            {
                "detail": "If an eligible account exists, the request has been accepted."
            },
        )
        return response

    def assert_private_no_store(self, response):
        cache_control = response.headers.get("Cache-Control", "")
        self.assertIn("no-store", cache_control)
        self.assertIn("private", cache_control)

    def test_verification_requires_session_and_confirms_current_email_once(self):
        anonymous_request = self.client.post(
            self.verification_request_url,
            {},
            format="json",
        )
        anonymous_confirm = self.client.post(
            self.verification_confirm_url,
            {"token": "invalid-token"},
            format="json",
        )
        self.assertEqual(anonymous_request.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(anonymous_confirm.status_code, status.HTTP_403_FORBIDDEN)

        response, raw_token = self.request_verification()
        serialized_request = json.dumps(response.data)
        self.assertNotIn(raw_token, serialized_request)
        self.assertNotIn("token_digest", serialized_request)
        self.assert_private_no_store(response)

        token_record = AccountSecurityToken.objects.get(
            user=self.user,
            purpose=AccountSecurityToken.Purpose.EMAIL_VERIFICATION,
        )
        self.assertEqual(token_record.status, AccountSecurityToken.Status.PENDING)
        self.assertEqual(
            token_record.delivery_status,
            AccountSecurityToken.DeliveryStatus.SENT,
        )
        self.assertNotEqual(token_record.token_digest, raw_token)
        self.assertNotIn(raw_token, token_record.token_digest)

        confirm = self.client.post(
            self.verification_confirm_url,
            {"token": raw_token},
            format="json",
        )
        replay = self.client.post(
            self.verification_confirm_url,
            {"token": raw_token},
            format="json",
        )

        self.assertEqual(confirm.status_code, status.HTTP_200_OK)
        self.assertEqual(confirm.data, {"detail": "Email verified."})
        self.assertEqual(replay.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertNotIn(raw_token, json.dumps(replay.data))
        self.assert_private_no_store(confirm)
        self.user.refresh_from_db()
        token_record.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)
        self.assertEqual(
            self.user.verified_email_normalized,
            self.user.email.strip().casefold(),
        )
        self.assertIsNotNone(self.user.email_verified_at)
        self.assertEqual(token_record.status, AccountSecurityToken.Status.CONSUMED)
        self.assertIsNotNone(token_record.consumed_at)

    def test_verification_rejects_wrong_actor_and_changed_email_generically(self):
        _, wrong_actor_token = self.request_verification()
        self.client.force_login(self.other_user)
        wrong_actor = self.client.post(
            self.verification_confirm_url,
            {"token": wrong_actor_token},
            format="json",
        )

        self.client.force_login(self.user)
        invalid = self.client.post(
            self.verification_confirm_url,
            {"token": "unrecognized-token-with-sufficient-length-0001"},
            format="json",
        )
        self.assertEqual(wrong_actor.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(wrong_actor.data, invalid.data)

        AccountSecurityToken.objects.all().delete()
        mail.outbox.clear()
        _, stale_email_token = self.request_verification()
        User.objects.filter(id=self.user.id).update(
            email="changed-security-api@example.test"
        )
        changed_email = self.client.post(
            self.verification_confirm_url,
            {"token": stale_email_token},
            format="json",
        )
        self.assertEqual(changed_email.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_email_verified)

    def test_verification_request_rotates_old_token_and_expiry_is_terminal(self):
        _, first_token = self.request_verification()
        first_record = AccountSecurityToken.objects.get(
            user=self.user,
            purpose=AccountSecurityToken.Purpose.EMAIL_VERIFICATION,
        )

        _, second_token = self.request_verification()
        first_record.refresh_from_db()
        replacement = AccountSecurityToken.objects.get(replaces=first_record)
        self.assertNotEqual(first_token, second_token)
        self.assertEqual(first_record.status, AccountSecurityToken.Status.REVOKED)
        self.assertEqual(replacement.status, AccountSecurityToken.Status.PENDING)

        old_response = self.client.post(
            self.verification_confirm_url,
            {"token": first_token},
            format="json",
        )
        self.assertEqual(old_response.status_code, status.HTTP_400_BAD_REQUEST)

        expired_at = timezone.now() - timedelta(seconds=1)
        AccountSecurityToken.objects.filter(id=replacement.id).update(
            created_at=expired_at - timedelta(hours=25),
            expires_at=expired_at,
        )
        expired = self.client.post(
            self.verification_confirm_url,
            {"token": second_token},
            format="json",
        )
        self.assertEqual(expired.status_code, status.HTTP_400_BAD_REQUEST)
        replacement.refresh_from_db()
        self.assertEqual(replacement.status, AccountSecurityToken.Status.EXPIRED)
        self.assertIsNotNone(replacement.expired_at)

    @override_settings(MAILERS=UNSAFE_MAILERS)
    def test_verification_reports_delivery_unavailable_without_false_success(self):
        self.client.force_login(self.user)

        response = self.client.post(
            self.verification_request_url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertFalse(
            AccountSecurityToken.objects.filter(
                user=self.user,
                purpose=AccountSecurityToken.Purpose.EMAIL_VERIFICATION,
            ).exists()
        )

    def test_reset_request_is_public_neutral_and_does_not_expose_token(self):
        existing = self.request_password_reset()
        raw_token = extract_latest_token()
        existing_body = json.dumps(existing.data)
        self.assertNotIn(raw_token, existing_body)
        self.assertNotIn("token", existing_body)
        self.assertNotIn("email", existing_body)
        self.assert_private_no_store(existing)
        sent_count = len(mail.outbox)

        unknown = self.request_password_reset("unknown-account@example.test")
        self.assertEqual(unknown.status_code, existing.status_code)
        self.assertEqual(unknown.data, existing.data)
        self.assertEqual(len(mail.outbox), sent_count)

        inactive = User.objects.create_user(
            email="inactive-security-api@example.test",
            username="inactive-security-api",
            password=CURRENT_PASSWORD,
            is_active=False,
        )
        inactive_response = self.request_password_reset(inactive.email)
        self.assertEqual(inactive_response.data, existing.data)
        self.assertEqual(len(mail.outbox), sent_count)

    def test_reset_confirm_changes_hash_consumes_token_and_invalidates_sessions(self):
        first_session = APIClient()
        second_session = APIClient()
        self.assertTrue(
            first_session.login(email=self.user.email, password=CURRENT_PASSWORD)
        )
        self.assertTrue(
            second_session.login(email=self.user.email, password=CURRENT_PASSWORD)
        )

        self.request_password_reset(client=APIClient())
        raw_token = extract_latest_token()
        reset_client = APIClient()
        confirm = reset_client.post(
            self.reset_confirm_url,
            {
                "token": raw_token,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )

        self.assertEqual(confirm.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(confirm.content)
        self.assertNotIn("_auth_user_id", reset_client.session)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertFalse(self.user.check_password(CURRENT_PASSWORD))
        token_record = AccountSecurityToken.objects.get(
            user=self.user,
            purpose=AccountSecurityToken.Purpose.PASSWORD_RESET,
        )
        self.assertEqual(token_record.status, AccountSecurityToken.Status.CONSUMED)
        self.assertIsNotNone(token_record.consumed_at)

        for old_client in (first_session, second_session):
            response = old_client.get(self.me_url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            self.assertNotIn("_auth_user_id", old_client.session)

        replay = reset_client.post(
            self.reset_confirm_url,
            {
                "token": raw_token,
                "new_password": "An0ther!Password$921",
                "new_password_confirm": "An0ther!Password$921",
            },
            format="json",
        )
        self.assertEqual(replay.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_password_validation_error_does_not_consume_usable_token(self):
        self.request_password_reset()
        raw_token = extract_latest_token()

        weak = self.client.post(
            self.reset_confirm_url,
            {
                "token": raw_token,
                "new_password": "password",
                "new_password_confirm": "password",
            },
            format="json",
        )
        self.assertEqual(weak.status_code, status.HTTP_400_BAD_REQUEST)
        token_record = AccountSecurityToken.objects.get(
            user=self.user,
            purpose=AccountSecurityToken.Purpose.PASSWORD_RESET,
        )
        token_record.refresh_from_db()
        self.assertEqual(token_record.status, AccountSecurityToken.Status.PENDING)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(CURRENT_PASSWORD))

        valid = self.client.post(
            self.reset_confirm_url,
            {
                "token": raw_token,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(valid.status_code, status.HTTP_204_NO_CONTENT)

    def test_reset_invalid_expired_and_replayed_tokens_share_generic_error(self):
        self.request_password_reset()
        raw_token = extract_latest_token()
        token_record = AccountSecurityToken.objects.get(
            user=self.user,
            purpose=AccountSecurityToken.Purpose.PASSWORD_RESET,
        )
        expired_at = timezone.now() - timedelta(seconds=1)
        AccountSecurityToken.objects.filter(id=token_record.id).update(
            created_at=expired_at - timedelta(hours=2),
            expires_at=expired_at,
        )

        expired = self.client.post(
            self.reset_confirm_url,
            {
                "token": raw_token,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )
        invalid = self.client.post(
            self.reset_confirm_url,
            {
                "token": "unrecognized-token-with-sufficient-length-0002",
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(expired.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(invalid.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(expired.data, invalid.data)
        token_record.refresh_from_db()
        self.assertEqual(token_record.status, AccountSecurityToken.Status.EXPIRED)

    def test_reset_changed_or_ambiguous_email_fails_closed_neutrally(self):
        self.request_password_reset()
        stale_token = extract_latest_token()
        User.objects.filter(id=self.user.id).update(
            email="changed-reset-security-api@example.test"
        )

        changed = self.client.post(
            self.reset_confirm_url,
            {
                "token": stale_token,
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )
        self.assertEqual(changed.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(CURRENT_PASSWORD))

        first = User.objects.create_user(
            email="Ambiguous.Reset@example.test",
            username="ambiguous-reset-first",
            password=CURRENT_PASSWORD,
        )
        second = User.objects.create_user(
            email="ambiguous.reset@example.test",
            username="ambiguous-reset-second",
            password=CURRENT_PASSWORD,
        )
        mail_count = len(mail.outbox)
        ambiguous = self.request_password_reset("AMBIGUOUS.RESET@example.test")
        self.assertEqual(
            ambiguous.data,
            {
                "detail": "If an eligible account exists, the request has been accepted."
            },
        )
        self.assertEqual(len(mail.outbox), mail_count)
        self.assertFalse(
            AccountSecurityToken.objects.filter(user__in=(first, second)).exists()
        )

    def test_reset_delivery_failure_is_neutral_and_persisted_as_failed(self):
        with patch(
            "apps.common.email_delivery.EmailMessage.send",
            side_effect=RuntimeError("test-only delivery failure"),
        ):
            response = self.request_password_reset()

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        token_record = AccountSecurityToken.objects.get(
            user=self.user,
            purpose=AccountSecurityToken.Purpose.PASSWORD_RESET,
        )
        self.assertEqual(
            token_record.delivery_status,
            AccountSecurityToken.DeliveryStatus.FAILED,
        )
        self.assertIsNotNone(token_record.delivery_attempted_at)
        self.assertIsNone(token_record.delivered_at)

    @override_settings(MAILERS=UNSAFE_MAILERS)
    def test_reset_unavailable_backend_is_neutral_for_every_email(self):
        existing = self.client.post(
            self.reset_request_url,
            {"email": self.user.email},
            format="json",
        )
        unknown = self.client.post(
            self.reset_request_url,
            {"email": "unknown-unavailable@example.test"},
            format="json",
        )

        self.assertEqual(existing.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(existing.data, unknown.data)
        self.assertFalse(
            AccountSecurityToken.objects.filter(
                purpose=AccountSecurityToken.Purpose.PASSWORD_RESET,
            ).exists()
        )

    def test_public_security_endpoints_reject_malformed_unicode_without_500(self):
        malformed = "\ud800" * 32

        request_response = self.client.post(
            self.reset_request_url,
            json.dumps({"email": f"{malformed}@example.test"}).encode("ascii"),
            content_type="application/json",
        )
        confirm_response = self.client.post(
            self.reset_confirm_url,
            json.dumps(
                {
                    "token": malformed,
                    "new_password": NEW_PASSWORD,
                    "new_password_confirm": NEW_PASSWORD,
                }
            ).encode("ascii"),
            content_type="application/json",
        )

        self.assertEqual(
            request_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            confirm_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("token", confirm_response.data)

    def test_all_four_security_posts_enforce_csrf(self):
        session_client = APIClient(enforce_csrf_checks=True)
        session_client.force_login(self.user)
        denied_verification_request = session_client.post(
            self.verification_request_url,
            {},
            format="json",
        )
        denied_verification_confirm = session_client.post(
            self.verification_confirm_url,
            {"token": "invalid-token"},
            format="json",
        )

        public_client = APIClient(enforce_csrf_checks=True)
        denied_reset_request = public_client.post(
            self.reset_request_url,
            {"email": self.user.email},
            format="json",
        )
        denied_reset_confirm = public_client.post(
            self.reset_confirm_url,
            {
                "token": "invalid-token",
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            },
            format="json",
        )

        for response in (
            denied_verification_request,
            denied_verification_confirm,
            denied_reset_request,
            denied_reset_confirm,
        ):
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        csrf_response = public_client.get(reverse("accounts:csrf"))
        allowed_reset = public_client.post(
            self.reset_request_url,
            {"email": "unknown-csrf@example.test"},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_response.data["csrf_token"],
        )
        self.assertEqual(allowed_reset.status_code, status.HTTP_202_ACCEPTED)

    def test_verification_request_and_confirm_have_separate_user_throttles(self):
        self.client.force_login(self.user)
        with patch.object(
            EmailVerificationRequestThrottle,
            "get_rate",
            return_value="1/day",
        ):
            with self.captureOnCommitCallbacks(execute=True):
                first_request = self.client.post(
                    self.verification_request_url,
                    {},
                    format="json",
                )
            second_request = self.client.post(
                self.verification_request_url,
                {},
                format="json",
            )

        self.assertEqual(first_request.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(
            second_request.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

        cache.clear()
        with patch.object(
            EmailVerificationConfirmThrottle,
            "get_rate",
            return_value="1/day",
        ):
            first_confirm = self.client.post(
                self.verification_confirm_url,
                {"token": "first-invalid-token-with-sufficient-length-0001"},
                format="json",
            )
            second_confirm = self.client.post(
                self.verification_confirm_url,
                {"token": "second-invalid-token-with-sufficient-length-0002"},
                format="json",
            )

        self.assertEqual(first_confirm.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            second_confirm.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

    def test_reset_request_normalizes_email_throttle_across_client_addresses(self):
        with patch.object(
            PasswordResetRequestEmailThrottle,
            "get_rate",
            return_value="1/day",
        ), patch.object(
            PasswordResetRequestIpThrottle,
            "get_rate",
            return_value="100/day",
        ):
            first = self.client.post(
                self.reset_request_url,
                {"email": " Unknown.Throttle@example.test "},
                format="json",
                REMOTE_ADDR="198.51.100.10",
            )
            second = self.client.post(
                self.reset_request_url,
                {"email": "unknown.throttle@EXAMPLE.TEST"},
                format="json",
                REMOTE_ADDR="198.51.100.11",
            )

        self.assertEqual(first.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_reset_request_ip_throttle_limits_rotating_email_identities(self):
        with patch.object(
            PasswordResetRequestEmailThrottle,
            "get_rate",
            return_value="100/day",
        ), patch.object(
            PasswordResetRequestIpThrottle,
            "get_rate",
            return_value="1/day",
        ):
            first = self.client.post(
                self.reset_request_url,
                {"email": "first-unknown-throttle@example.test"},
                format="json",
                REMOTE_ADDR="198.51.100.80",
            )
            second = self.client.post(
                self.reset_request_url,
                {"email": "second-unknown-throttle@example.test"},
                format="json",
                REMOTE_ADDR="198.51.100.80",
            )

        self.assertEqual(first.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_reset_confirm_throttle_limits_repeated_token_attempts(self):
        payload = {
            "token": "same-invalid-token-with-sufficient-length-0001",
            "new_password": NEW_PASSWORD,
            "new_password_confirm": NEW_PASSWORD,
        }
        with patch.object(
            PasswordResetConfirmThrottle,
            "get_rate",
            return_value="1/day",
        ):
            first = self.client.post(
                self.reset_confirm_url,
                payload,
                format="json",
            )
            second = self.client.post(
                self.reset_confirm_url,
                payload,
                format="json",
            )

        self.assertEqual(first.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_reset_confirm_ip_throttle_limits_rotating_invalid_tokens(self):
        def payload(suffix):
            return {
                "token": f"rotating-invalid-token-with-sufficient-length-{suffix}",
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
            }

        with patch.object(
            PasswordResetConfirmThrottle,
            "get_rate",
            return_value="100/day",
        ), patch.object(
            PasswordResetConfirmIpThrottle,
            "get_rate",
            return_value="1/day",
        ):
            first = self.client.post(
                self.reset_confirm_url,
                payload("0001"),
                format="json",
                REMOTE_ADDR="198.51.100.90",
            )
            second = self.client.post(
                self.reset_confirm_url,
                payload("0002"),
                format="json",
                REMOTE_ADDR="198.51.100.90",
            )

        self.assertEqual(first.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(second.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_security_endpoints_reject_unknown_fields_and_unsupported_methods(self):
        self.client.force_login(self.user)
        strict_request = self.client.post(
            self.verification_request_url,
            {"email": self.user.email},
            format="json",
        )
        strict_confirm = self.client.post(
            self.verification_confirm_url,
            {"token": "invalid-token", "user_id": str(self.other_user.id)},
            format="json",
        )
        strict_reset = self.client.post(
            self.reset_request_url,
            {"email": self.user.email, "username": self.user.username},
            format="json",
        )
        strict_reset_confirm = self.client.post(
            self.reset_confirm_url,
            {
                "token": "invalid-token-with-sufficient-length-0003",
                "new_password": NEW_PASSWORD,
                "new_password_confirm": NEW_PASSWORD,
                "user_id": str(self.user.id),
            },
            format="json",
        )
        for response in (
            strict_request,
            strict_confirm,
            strict_reset,
            strict_reset_confirm,
        ):
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        for url in (
            self.verification_request_url,
            self.verification_confirm_url,
            self.reset_request_url,
            self.reset_confirm_url,
        ):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )
