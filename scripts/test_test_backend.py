"""Safety regression tests for the harness, independent of business fixtures."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

import test_backend as harness
from config.test_environment import CONTROL_DATABASE, TEST_USER, test_environment

RUN_ID = "a" * 32
ENVIRONMENT = {"HT_TEST_RUN_ID": RUN_ID, "HT_TEST_MODE": "docker",
    "HT_TEST_DB_HOST": "postgres", "HT_TEST_DB_PORT": "5432"}


def connection_with(*rows):
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchone.side_effect = rows
    return connection, cursor


def query_text(query):
    return query.as_string() if hasattr(query, "as_string") else query


class HarnessSafetyTests(unittest.TestCase):
    def setUp(self):
        self.config = test_environment(ENVIRONMENT)

    def test_development_environment_never_supplies_test_target(self):
        config = test_environment({**ENVIRONMENT, "POSTGRES_DB":"hustlytasker_db",
            "POSTGRES_HOST":"production.invalid", "POSTGRES_USER":"deployment-user"})
        self.assertEqual(config["control"], CONTROL_DATABASE)
        self.assertEqual(config["user"], TEST_USER)
        self.assertEqual(config["host"], "postgres")

    def test_missing_or_unapproved_endpoint_fails_closed(self):
        for changes in ({"HT_TEST_RUN_ID":""}, {"HT_TEST_MODE":"production"},
                        {"HT_TEST_DB_HOST":"127.0.0.1"}, {"HT_TEST_DB_PORT":"invalid"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                test_environment({**ENVIRONMENT, **changes})

    def test_github_requires_job_metadata_and_random_service_port(self):
        github = {**ENVIRONMENT, "HT_TEST_MODE":"github", "HT_TEST_DB_HOST":"127.0.0.1",
            "HT_TEST_DB_PORT":"32781", "GITHUB_ACTIONS":"true", "GITHUB_RUN_ID":"42"}
        self.assertEqual(test_environment(github)["port"], 32781)
        for changes in ({"GITHUB_ACTIONS":"false"}, {"HT_TEST_DB_PORT":"5432"}):
            with self.assertRaises(ValueError):
                test_environment({**github, **changes})

    def test_targeted_labels_are_allowed(self):
        self.assertEqual(harness.parse_arguments(["apps.accounts.tests"]).labels,
            ["apps.accounts.tests"])

    def test_cli_cannot_override_settings_runner_or_keepdb(self):
        for arguments in (["--settings=config.settings"], ["--keepdb"],
                          ["--parallel=2"], ["../backend"]):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    harness.parse_arguments(arguments)
                self.assertNotEqual(error.exception.code, 0)

    def test_cluster_with_existing_test_database_is_never_autoclobbered(self):
        connection, cursor = connection_with((TEST_USER,160014,"cluster-id"))
        cursor.fetchall.return_value = [(name,) for name in
            ("postgres","template0","template1",CONTROL_DATABASE,self.config["name"])]
        with self.assertRaisesRegex(RuntimeError, "not fresh/isolated"):
            harness.check_cluster(connection,self.config)
        self.assertFalse(any("DROP" in query_text(call.args[0]) for call in cursor.execute.call_args_list))

    def test_development_database_on_cluster_is_refused(self):
        connection, cursor = connection_with((TEST_USER,160014,"cluster-id"))
        cursor.fetchall.return_value = [(name,) for name in
            ("postgres","template0","template1",CONTROL_DATABASE,"hustlytasker_db")]
        with self.assertRaises(RuntimeError):
            harness.check_cluster(connection,self.config)

    def test_wrong_role_or_postgres_version_is_refused(self):
        for row in (("hustlytasker_user",160014,"cluster-id"),(TEST_USER,170000,"cluster-id")):
            connection, _ = connection_with(row)
            with self.assertRaises(RuntimeError):
                harness.check_cluster(connection,self.config)

    def test_cleanup_refuses_wrong_owner_or_marker(self):
        for row in ((TEST_USER,"someone-elses-run"),("other-owner",self.config["marker"])):
            connection, cursor = connection_with(("cluster-id",),row)
            with self.assertRaises(RuntimeError):
                harness.drop_owned_database(connection,self.config,"cluster-id")
            self.assertFalse(any("DROP" in query_text(call.args[0]) for call in cursor.execute.call_args_list))

    def test_cleanup_refuses_changed_cluster(self):
        connection, cursor = connection_with(("different-cluster",))
        with self.assertRaises(RuntimeError):
            harness.drop_owned_database(connection,self.config,"cluster-id")
        self.assertEqual(cursor.execute.call_count,1)

    def test_cleanup_only_drops_the_exact_owned_database(self):
        connection, cursor = connection_with(("cluster-id",),(TEST_USER,self.config["marker"]))
        harness.drop_owned_database(connection,self.config,"cluster-id")
        self.assertEqual(query_text(cursor.execute.call_args.args[0]),
            f'DROP DATABASE "{self.config["name"]}" WITH (FORCE)')

    def test_cleanup_absent_database_is_noop(self):
        connection, cursor = connection_with(("cluster-id",),None)
        harness.drop_owned_database(connection,self.config,"cluster-id")
        self.assertEqual(cursor.execute.call_count,2)

    def test_failure_exit_code_is_propagated(self):
        with patch.object(harness,"run",return_value=7), patch.object(harness.os,"chdir"):
            self.assertEqual(harness.main([]),7)

    def test_test_settings_ignore_production_security_db_and_mail_flags(self):
        environment = {**os.environ, **ENVIRONMENT, "PYTHONPATH":str(harness.ROOT / "backend"),
            "DJANGO_ENVIRONMENT":"production", "DJANGO_SECURE_SSL_REDIRECT":"true",
            "DJANGO_MAILER_BACKEND":"django.core.mail.backends.smtp.EmailBackend",
            "POSTGRES_DB":"hustlytasker_db", "PGSERVICE":"do-not-use-deployment-service"}
        code = (
            "import os; import config.test_settings as s; "
            "assert s.DATABASES['default']['NAME']=='hustlytasker_test_control'; "
            "assert s.DATABASES['default']['HOST']=='postgres'; "
            "assert s.DATABASES['default']['TEST']['NAME']=='test_hustlytasker_" + RUN_ID + "'; "
            "assert s.ENVIRONMENT=='development' and not s.SECURE_SSL_REDIRECT; "
            "assert s.MAILERS['default']['BACKEND']=='django.core.mail.backends.locmem.EmailBackend'; "
            "assert 'PGSERVICE' not in os.environ"
        )
        result = subprocess.run([sys.executable,"-c",code],env=environment,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode())


if __name__ == "__main__":
    unittest.main()
