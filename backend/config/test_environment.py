"""Fail-closed configuration for the disposable PostgreSQL harness only."""
import re

CONTROL_DATABASE = "hustlytasker_test_control"
TEST_USER = "ht_test_runner"


def test_environment(environ):
    run_id = environ.get("HT_TEST_RUN_ID", "")
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        raise ValueError("Use the test harness; a generated test run ID is required.")
    mode = environ.get("HT_TEST_MODE")
    host = environ.get("HT_TEST_DB_HOST")
    try:
        port = int(environ.get("HT_TEST_DB_PORT", ""))
    except ValueError:
        raise ValueError("An explicit isolated PostgreSQL port is required.") from None
    if mode == "docker":
        allowed = host == "postgres" and port == 5432
    elif mode == "github":
        allowed = (
            environ.get("GITHUB_ACTIONS") == "true"
            and environ.get("GITHUB_RUN_ID", "").isdigit()
            and host == "127.0.0.1"
            and 1024 <= port <= 65535 and port != 5432
        )
    else:
        allowed = False
    if not allowed:
        raise ValueError("Only the owned Docker cluster or GitHub test service is allowed.")
    return {
        "host": host, "port": port, "user": TEST_USER,
        "control": CONTROL_DATABASE, "name": f"test_hustlytasker_{run_id}",
        "marker": f"hustlytasker-test:{run_id}",
    }
