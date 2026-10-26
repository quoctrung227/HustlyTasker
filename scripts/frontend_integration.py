"""Serve real Django APIs against an owned, disposable PostgreSQL database.

This is integration-test infrastructure, never a development server launcher.
Deployment environment variables and credentials are intentionally ignored by
config.test_settings. All private fixture values come from the runner process.
"""
import os
from pathlib import Path
import signal
from socketserver import ThreadingMixIn
import sys
import uuid
from wsgiref.simple_server import WSGIRequestHandler, WSGIServer, make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))


def fixture_id(run_id, label):
    return uuid.uuid5(uuid.UUID(run_id), label)


def select_owned_database(config, maintenance):
    """Check ownership before selecting any non-control application database."""
    from django.conf import settings
    from django.db import connections

    with maintenance.cursor() as cursor:
        cursor.execute(
            "SELECT current_user,current_setting('server_version_num')::int"
        )
        user, version = cursor.fetchone()
        if user != config["user"] or not 160000 <= version < 170000:
            raise RuntimeError("Isolated PostgreSQL identity mismatch.")
        cursor.execute("SELECT datname FROM pg_database")
        names = {row[0] for row in cursor.fetchall()}
        if names != {
            "postgres", "template0", "template1", config["control"], config["name"],
        }:
            raise RuntimeError("The isolated cluster contains unexpected databases.")
        cursor.execute(
            "SELECT pg_get_userbyid(datdba),shobj_description(oid,'pg_database') "
            "FROM pg_database WHERE datname=%s", (config["name"],),
        )
        if cursor.fetchone() != (config["user"], config["marker"]):
            raise RuntimeError("Owned integration database marker mismatch.")
    connections.close_all()
    settings.DATABASES["default"]["NAME"] = config["name"]
    connections["default"].settings_dict["NAME"] = config["name"]


def seed_fixtures(run_id):
    """Only runs after the fresh cluster and exact test database pass gates."""
    from datetime import date
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember

    email = os.environ["HT_FRONTEND_TEST_EMAIL"]
    owner_email = os.environ["HT_FRONTEND_TEST_OWNER_EMAIL"]
    password = os.environ["HT_FRONTEND_TEST_PASSWORD"]
    if not email.endswith("@example.test") or not owner_email.endswith("@example.test") or len(password) < 32:
        raise RuntimeError("Generated isolated fixture credentials are required.")
    User = get_user_model()
    with transaction.atomic():
        owner = User.objects.create_user(
            username="fixture_owner", email=owner_email, password=password,
            first_name="Chủ", last_name="Tổ chức",
        )
        member = User.objects.create_user(
            username="fixture_member", email=email, password=password,
            first_name="Thành viên", last_name="Kiểm thử",
        )
        profile = Profile.objects.create(
            id=fixture_id(run_id, "profile"), name="Studio Integration",
        )
        other_profile = Profile.objects.create(
            id=fixture_id(run_id, "other_profile"), name="Other Tenant Integration",
        )
        for organization in (profile, other_profile):
            ProfileMembership.objects.create(
                profile=organization, user=owner, role=ProfileMembership.Role.OWNER,
            )
        ProfileMembership.objects.create(
            profile=profile, user=member, role=ProfileMembership.Role.MEMBER,
        )
        workspace = Workspace.objects.create(
            id=fixture_id(run_id, "workspace"), profile=profile, owner=owner,
            name="Workspace Integration", description="Isolated HTTP integration fixture.",
            period=date(2026, 10, 1),
        )
        archived = Workspace.objects.create(
            id=fixture_id(run_id, "archived_workspace"), profile=profile, owner=owner,
            name="Archived Integration", period=date(2026, 11, 1),
            status=Workspace.Status.ARCHIVED,
        )
        Workspace.objects.create(
            id=fixture_id(run_id, "hidden_workspace"), profile=profile, owner=owner,
            name="Unassigned Integration", period=date(2026, 12, 1),
        )
        for child in (workspace, archived):
            WorkspaceMember.objects.create(
                id=fixture_id(run_id, "membership" if child == workspace else "archived_membership"),
                workspace=child, user=member, role=WorkspaceMember.Role.VIEWER,
            )


class QuietRequestHandler(WSGIRequestHandler):
    # Never emit cookie headers, credentials, request payloads or private rows.
    def log_message(self, format, *args):
        pass


class ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def run(mode):
    if mode not in ("serve", "expire-sessions"):
        raise ValueError("Unknown integration operation.")
    if sys.version_info[:2] != (3, 12):
        raise RuntimeError("Use the existing Python 3.12 test image.")
    from config.test_environment import test_environment

    config = test_environment(os.environ)
    os.environ["DJANGO_SETTINGS_MODULE"] = "config.test_settings"
    import django
    import psycopg
    from psycopg import sql
    django.setup()
    from django.core.management import call_command
    from django.db import connections
    from test_backend import check_cluster, drop_owned_database

    maintenance = psycopg.connect(
        host=config["host"], port=config["port"], user=config["user"],
        dbname="postgres", connect_timeout=10, autocommit=True,
    )
    created = False
    system_id = None
    try:
        if mode == "expire-sessions":
            select_owned_database(config, maintenance)
            from django.contrib.sessions.models import Session
            Session.objects.all().delete()
            print("OWNED_ISOLATED_SESSIONS_EXPIRED", flush=True)
            return 0

        system_id = check_cluster(maintenance, config)
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_class WHERE relnamespace='public'::regnamespace")
            if cursor.fetchone()[0]:
                raise RuntimeError("Fresh integration control database must be empty.")
        call_command("check")
        call_command("makemigrations", check=True, dry_run=True, interactive=False)
        with maintenance.cursor() as cursor:
            cursor.execute(sql.SQL("CREATE DATABASE {} OWNER {} TEMPLATE template0").format(
                sql.Identifier(config["name"]), sql.Identifier(config["user"]),
            ))
            created = True
            cursor.execute(sql.SQL("COMMENT ON DATABASE {} IS {}").format(
                sql.Identifier(config["name"]), sql.Literal(config["marker"]),
            ))
        select_owned_database(config, maintenance)
        call_command("migrate", interactive=False, verbosity=0)
        call_command("migrate", check=True, interactive=False)
        seed_fixtures(os.environ["HT_TEST_RUN_ID"])
        connections.close_all()
        from django.core.wsgi import get_wsgi_application

        def interrupted(signum, frame):
            raise KeyboardInterrupt()

        signal.signal(signal.SIGTERM, interrupted)
        signal.signal(signal.SIGINT, interrupted)
        with make_server(
            "0.0.0.0", 8000, get_wsgi_application(),
            server_class=ThreadedServer, handler_class=QuietRequestHandler,
        ) as server:
            print("FRONTEND_ISOLATED_SERVER_READY", flush=True)
            try:
                server.serve_forever(poll_interval=0.2)
            except KeyboardInterrupt:
                pass
        return 0
    finally:
        connections.close_all()
        try:
            if created:
                drop_owned_database(maintenance, config, system_id)
                print("Owned integration database removed.", flush=True)
        finally:
            maintenance.close()


def main():
    mode = sys.argv[1] if len(sys.argv) == 2 else "serve"
    os.chdir(ROOT / "backend")
    try:
        return run(mode)
    except KeyboardInterrupt:
        return 0
    except Exception as error:
        # Driver messages and tracebacks can contain DSNs or fixture values.
        print(f"Isolated frontend integration stopped ({type(error).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
