"""Shared serial PostgreSQL checks/tests for the local launcher and GitHub CI."""
import argparse
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import traceback
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from config.test_environment import CONTROL_DATABASE, TEST_USER, test_environment


def parse_arguments(arguments=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("labels", nargs="*", help="Optional dotted Django test labels")
    parser.add_argument("--verbosity", type=int, choices=(1, 2), default=1)
    options = parser.parse_args(arguments)
    if any(not re.fullmatch(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*", label, re.ASCII)
           for label in options.labels):
        parser.error("Only dotted test labels are allowed; no paths/settings/runner overrides.")
    return options


def check_cluster(connection, config):
    """Read-only gate before creating anything; a test_ name is not proof."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_user, current_setting('server_version_num')::int, system_identifier::text FROM pg_control_system()")
        user, version, system_id = cursor.fetchone()
        if user != TEST_USER or not 160000 <= version < 170000:
            raise RuntimeError("The disposable PostgreSQL 16 identity does not match.")
        cursor.execute("SELECT datname FROM pg_database")
        names = {row[0] for row in cursor.fetchall()}
        if names != {"postgres", "template0", "template1", CONTROL_DATABASE}:
            raise RuntimeError("Cluster is not fresh/isolated; existing databases are never removed.")
        cursor.execute("SELECT datname,pg_get_userbyid(datdba) FROM pg_database WHERE datname=%s", (CONTROL_DATABASE,))
        if cursor.fetchone() != (CONTROL_DATABASE, TEST_USER):
            raise RuntimeError("Test control database ownership does not match.")
    return system_id


def drop_owned_database(connection, config, system_id):
    from psycopg import sql
    with connection.cursor() as cursor:
        cursor.execute("SELECT system_identifier::text FROM pg_control_system()")
        if cursor.fetchone()[0] != system_id:
            raise RuntimeError("Cluster changed; refusing cleanup.")
        cursor.execute("SELECT pg_get_userbyid(datdba),shobj_description(oid,'pg_database') FROM pg_database WHERE datname=%s", (config["name"],))
        row = cursor.fetchone()
        if row is None:
            return
        if row != (TEST_USER, config["marker"]):
            raise RuntimeError("Database ownership marker mismatch; refusing cleanup.")
        cursor.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(config["name"])))


def run(options):
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("This baseline requires Python 3.12; use the Docker launcher.")
    os.environ["HT_TEST_RUN_ID"] = uuid.uuid4().hex
    config = test_environment(os.environ)
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.test_settings"
    import django
    import psycopg
    from psycopg import sql
    django.setup()
    from django.core.management import call_command
    from django.db import connections
    from django.db.migrations.executor import MigrationExecutor
    from django.test.runner import DiscoverRunner

    print("Checking dependencies, Django and migration graph/model drift...", flush=True)
    result = subprocess.run([sys.executable, "-m", "pip", "check"], check=False)
    if result.returncode:
        return result.returncode
    connection_args = {"host": config["host"], "port": config["port"],
        "user": TEST_USER, "dbname": "postgres", "connect_timeout": 10}
    created = False
    maintenance = psycopg.connect(**connection_args, autocommit=True)
    try:
        system_id = check_cluster(maintenance, config)
        # The control DB must be empty and is only ever used for read-only checks.
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace")
            if cursor.fetchone()[0]:
                raise RuntimeError("Test control database is not empty; refusing the run.")
        call_command("check")
        call_command("makemigrations", check=True, dry_run=True, interactive=False)
        executor = MigrationExecutor(connections["default"])
        executor.loader.check_consistent_history(connections["default"])
        executor.loader.graph.validate_consistency()
        print("Migration graph/history/model drift: PASS", flush=True)
        with maintenance.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0").format(
                sql.Identifier(config["name"]), sql.Identifier(TEST_USER)))
            created = True
            cursor.execute(sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                sql.Identifier(config["name"]), sql.Literal(config["marker"])))

        class CheckedRunner(DiscoverRunner):
            def get_databases(self, suite):
                databases = super().get_databases(suite)
                # Even a health-only SimpleTestCase slice verifies the chain.
                databases.setdefault("default", False)
                return databases

            def run_checks(self, databases):
                super().run_checks(databases)
                connection = connections["default"]
                if connection.settings_dict["NAME"] != config["name"]:
                    raise RuntimeError("Django did not select the owned test database.")
                migrated = MigrationExecutor(connection)
                migrated.loader.check_consistent_history(connection)
                if migrated.migration_plan(migrated.loader.graph.leaf_nodes()):
                    raise RuntimeError("The isolated test database has pending migrations.")
                print("Complete migration chain applied to isolated test DB: PASS", flush=True)

        # Internal keepdb only reuses the database we just created and marked.
        # It prevents Django autoclobbering anything; finally drops only our DB.
        runner = CheckedRunner(verbosity=options.verbosity, interactive=False,
            keepdb=True, parallel=1)
        failures = runner.run_tests(options.labels)
        return 1 if failures else 0
    finally:
        connections.close_all()
        try:
            if created:
                drop_owned_database(maintenance, config, system_id)
                print("Owned test database removed.", flush=True)
        finally:
            maintenance.close()


def main(arguments=None):
    options = parse_arguments(arguments)
    os.chdir(ROOT / "backend")
    def interrupted(signum, frame):
        raise KeyboardInterrupt()
    signal.signal(signal.SIGTERM, interrupted)
    try:
        return run(options)
    except KeyboardInterrupt:
        print("Test run interrupted; owned-resource cleanup attempted.", file=sys.stderr)
        return 130
    except Exception as exc:
        if type(exc).__module__.startswith("psycopg"):
            # Avoid DSNs/credentials while preserving useful PostgreSQL diagnostics.
            print(f"Isolated PostgreSQL operation failed (SQLSTATE {getattr(exc, 'sqlstate', None)}).", file=sys.stderr)
        else:
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
