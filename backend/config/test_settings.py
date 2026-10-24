"""Shared application settings with strictly isolated test environment/DB/mail."""
import os

from .test_environment import test_environment

_test = test_environment(os.environ)
# Never consume local/production configuration, including SMTP or proxy flags.
# This affects this test process only; no .env or Owner environment is edited.
for _name in list(os.environ):
    if _name.startswith(("POSTGRES_", "DJANGO_", "PG")) and _name != "DJANGO_SETTINGS_MODULE":
        del os.environ[_name]
os.environ.update({
    "DJANGO_ENVIRONMENT": "development",
    "DJANGO_SECRET_KEY": "isolated-test-process-only-not-a-deployment-key",
    "DJANGO_DEBUG": "false",
    "DJANGO_ALLOWED_HOSTS": "localhost,127.0.0.1,testserver",
    "DJANGO_MAILER_BACKEND": "django.core.mail.backends.locmem.EmailBackend",
    "POSTGRES_DB": _test["control"], "POSTGRES_USER": _test["user"],
    "POSTGRES_PASSWORD": "unused-by-the-private-trust-only-test-service",
    "POSTGRES_HOST": _test["host"], "POSTGRES_PORT": str(_test["port"]),
    "DRF_NUM_PROXIES": "0",
})

from .settings import *  # noqa: E402,F403

DATABASES["default"]["TEST"] = {"NAME": _test["name"]}  # noqa: F405
# Password hashers/validators, session auth, permissions and CSRF stay unchanged.
