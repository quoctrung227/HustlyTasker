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


def private_test_mailbox(run_id):
    """Container-local bridge only, after the caller verifies DB ownership."""
    import stat

    if uuid.UUID(run_id).hex != run_id:
        raise RuntimeError("Invalid isolated mailbox identity.")
    directory = Path("/tmp") / f"ht-fe-test-mail-{run_id}"
    metadata = directory.lstat()
    if directory.is_symlink() or not directory.is_dir() or metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o700:
        raise RuntimeError("Isolated mailbox ownership mismatch.")
    return directory


def install_test_mailbox(run_id):
    """Copy only locmem-accepted account mail into this disposable container.

    No HTTP endpoint, deployment setting, mail provider or application email
    service changes. This private bridge lets Node receive delivered test
    credentials in memory without printing them or putting them on the host.
    """
    import fcntl
    import json
    import re
    import tempfile
    from django.conf import settings
    from django.core.mail.backends.locmem import EmailBackend

    if settings.SETTINGS_MODULE != "config.test_settings" or settings.MAILERS["default"]["BACKEND"] != "django.core.mail.backends.locmem.EmailBackend":
        raise RuntimeError("Isolated locmem settings required.")
    directory = Path("/tmp") / f"ht-fe-test-mail-{run_id}"
    directory.mkdir(mode=0o700)
    private_test_mailbox(run_id)
    recipient = f"acceptance.{run_id}@example.test"
    purposes = {
        "Verify your HustlyTasker email": "verification",
        "Reset your HustlyTasker password": "password-reset",
    }
    original = EmailBackend.send_messages

    def send_messages(backend, messages):
        messages = list(messages)
        accepted = original(backend, messages)
        if accepted != len(messages):
            raise RuntimeError("Isolated locmem acceptance count mismatch.")
        for message in messages:
            purpose = purposes.get(message.subject)
            if purpose is None or message.to != [recipient]:
                continue
            parts = message.body.split("\n\n")
            token = parts[1] if len(parts) > 1 else ""
            if not re.fullmatch(r"[A-Za-z0-9_-]{43}", token):
                raise RuntimeError("Unexpected isolated security mail format.")
            lock = os.open(directory / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX)
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as target:
                        temporary = target.name
                        os.fchmod(target.fileno(), 0o600)
                        json.dump({"purpose": purpose, "recipient": recipient, "token": token}, target)
                        target.flush()
                        os.fsync(target.fileno())
                    os.replace(temporary, directory / f"{purpose}.json")
                finally:
                    if temporary and os.path.exists(temporary):
                        os.unlink(temporary)
            finally:
                os.close(lock)
        return accepted

    EmailBackend.send_messages = send_messages

    def cleanup():
        EmailBackend.send_messages = original
        for entry in directory.iterdir():
            if entry.is_file() and not entry.is_symlink():
                entry.unlink()
        directory.rmdir()
    return cleanup


def consume_test_mail(run_id, recipient_alias, purpose):
    """Return one credential to the invoking Node process; never a host log."""
    import fcntl
    import json
    import re
    import stat

    if recipient_alias != "registered" or purpose not in ("verification", "password-reset"):
        raise RuntimeError("Unknown isolated mailbox selection.")
    directory = private_test_mailbox(run_id)
    lock = os.open(directory / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX)
        target = directory / f"{purpose}.json"
        descriptor = os.open(target, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(descriptor, "r", encoding="utf-8") as source:
            metadata = os.fstat(source.fileno())
            if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
                raise RuntimeError("Isolated mail permissions mismatch.")
            payload = json.load(source)
        if payload.get("purpose") != purpose or payload.get("recipient") != f"acceptance.{run_id}@example.test" or not re.fullmatch(r"[A-Za-z0-9_-]{43}", payload.get("token", "")):
            raise RuntimeError("Isolated mail content mismatch.")
        target.unlink()
        return payload["token"]
    finally:
        os.close(lock)


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
    from datetime import date, datetime, timedelta, timezone
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
    from apps.tasks.models import Task, TaskAssignment

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

        # FE02 fixtures have an independent tenant and users. The foundation
        # member's one Profile/two visible Workspaces remain unchanged, even
        # when its membership is revoked by the existing foundation suite.
        management = Profile.objects.create(
            id=fixture_id(run_id, "management_profile"), name="Team Management Integration",
        )
        ProfileMembership.objects.create(
            profile=management, user=owner, role=ProfileMembership.Role.OWNER,
        )
        management_workspace = Workspace.objects.create(
            id=fixture_id(run_id, "management_workspace"), profile=management, owner=owner,
            name="Team Workspace Integration", description="Isolated work-management fixture.",
            period=date(2027, 1, 1),
        )
        # A Workspace MEMBER row does not make a Profile Owner an Editor.
        # Read eligibility must preserve the assignment service's role ceiling.
        WorkspaceMember.objects.create(
            workspace=management_workspace, user=owner, role=WorkspaceMember.Role.MEMBER,
        )
        management_archived = Workspace.objects.create(
            id=fixture_id(run_id, "management_archived_workspace"), profile=management, owner=owner,
            name="Archived Team Integration", period=date(2027, 2, 1),
            status=Workspace.Status.ARCHIVED,
        )
        foreign_workspace = Workspace.objects.create(
            id=fixture_id(run_id, "foreign_workspace"), profile=other_profile, owner=owner,
            name="Foreign Workspace Integration", period=date(2027, 1, 1),
        )
        participants = {}
        for label, role in (
            ("manager", WorkspaceMember.Role.ADMIN),
            ("editor", WorkspaceMember.Role.MEMBER),
            ("other_editor", WorkspaceMember.Role.MEMBER),
            ("viewer", WorkspaceMember.Role.VIEWER),
        ):
            user = User.objects.create_user(
                username=f"fixture_{label}", email=f"{label}.{run_id}@example.test", password=password,
                first_name={"manager": "Quản lý", "editor": "Nhân viên", "other_editor": "Đồng nghiệp", "viewer": "Người xem"}[label],
                last_name="Kiểm thử",
            )
            participants[label] = user
            ProfileMembership.objects.create(
                id=fixture_id(run_id, f"{label}_profile_membership"),
                profile=management, user=user, role=ProfileMembership.Role.MEMBER,
            )
            for target in (management_workspace, management_archived):
                WorkspaceMember.objects.create(
                    id=fixture_id(run_id, f"{label}_{'active' if target == management_workspace else 'archived'}_membership"),
                    workspace=target, user=user, role=role,
                )
        deadline = datetime(2027, 1, 20, 10, 30, tzinfo=timezone.utc)
        priorities = (Task.Priority.LOW, Task.Priority.MEDIUM, Task.Priority.HIGH, Task.Priority.URGENT)
        for number in range(24):
            Task.objects.create(
                id=fixture_id(run_id, f"task_page_{number:02d}"),
                workspace=management_workspace, created_by=owner,
                title=f"Integration task {number:02d}", description="Synthetic pagination fixture.",
                priority=priorities[number % len(priorities)],
                deadline=deadline + timedelta(hours=number) if number % 2 == 0 else None,
            )
        parent = None
        for label, title in (
            ("task_root", "Hierarchy root Integration"),
            ("task_child", "Hierarchy child Integration"),
            ("task_grandchild", "Hierarchy grandchild Integration"),
            ("task_depth_three", "Hierarchy depth three Integration"),
        ):
            parent = Task.objects.create(
                id=fixture_id(run_id, label), workspace=management_workspace, created_by=owner,
                title=title, parent=parent,
            )
        assigned = Task.objects.create(
            id=fixture_id(run_id, "task_assigned"), workspace=management_workspace, created_by=owner,
            title="Assigned editor Integration", status=Task.Status.ASSIGNED,
        )
        TaskAssignment.objects.create(task=assigned, user=participants["editor"])
        other_assigned = Task.objects.create(
            id=fixture_id(run_id, "task_other_assigned"), workspace=management_workspace, created_by=owner,
            title="Other editor assignment Integration", status=Task.Status.ASSIGNED,
        )
        TaskAssignment.objects.create(task=other_assigned, user=participants["other_editor"])
        Task.objects.create(
            id=fixture_id(run_id, "task_foreign"), workspace=foreign_workspace, created_by=owner,
            title="Foreign task Integration",
        )

        # FE03 collaboration fixtures remain inside this freshly created,
        # ownership-checked isolated DB. Revisions/reviews/events are produced
        # by existing services rather than synthetic workflow state changes.
        from apps.tasks.comment_services import create_comment, delete_comment
        from apps.tasks.services import (
            approve_deliverable, assign_task, request_deliverable_changes,
            start_task, submit_deliverable,
        )
        scope = {"profile_id": management.id, "workspace_id": management_workspace.id}
        history_task = Task.objects.create(
            id=fixture_id(run_id, "collaboration_history_task"),
            workspace=management_workspace, created_by=owner,
            title="Collaboration history Integration",
        )
        working_task = Task.objects.create(
            id=fixture_id(run_id, "collaboration_working_task"),
            workspace=management_workspace, created_by=owner,
            title="Collaboration API workflow Integration",
        )
        comment_task = Task.objects.create(
            id=fixture_id(run_id, "collaboration_comment_task"),
            workspace=management_workspace, created_by=owner,
            title="Collaboration discussion Integration",
        )
        for collaboration_task in (history_task, working_task, comment_task):
            assign_task(
                actor=participants["manager"], **scope, task_id=collaboration_task.id,
                target_profile_membership_id=fixture_id(run_id, "editor_profile_membership"),
            )
            start_task(actor=participants["editor"], **scope, task_id=collaboration_task.id)
        first_revision = submit_deliverable(
            actor=participants["editor"], **scope, task_id=history_task.id,
            file_url="https://example.test/isolated-deliverable-v1",
        )
        request_deliverable_changes(
            actor=participants["manager"], **scope, task_id=history_task.id,
            deliverable_id=first_revision.id, comment="Improve contrast in the first revision.",
        )
        second_revision = submit_deliverable(
            actor=participants["editor"], **scope, task_id=history_task.id,
            # Stored URLs are arbitrary text in the existing backend. This
            # proves the UI does not turn unsafe protocols into active links.
            file_url="javascript:unsafe-deliverable-text",
        )
        approve_deliverable(
            actor=participants["manager"], **scope, task_id=history_task.id,
            deliverable_id=second_revision.id, comment="Approved contrast revision.",
        )
        for number in range(22):
            create_comment(
                actor=participants["editor"], **scope, task_id=comment_task.id,
                content=f"Existing discussion comment {number:02d} Integration",
            )
        tombstone = create_comment(
            actor=participants["editor"], **scope, task_id=comment_task.id,
            content="Deleted private discussion fixture body",
        )
        delete_comment(
            actor=participants["editor"], **scope, task_id=comment_task.id,
            comment_id=tombstone.id,
        )

        # Negative self-review fixture only: a historical manager-uploaded
        # submission cannot be produced by the current Editor-only submit UI.
        # Keep it outside the acceptance journey, whose successful mutations
        # are all performed through React against this owned isolated DB.
        from apps.reviews.models import Deliverable
        self_review_task = Task.objects.create(
            id=fixture_id(run_id, "acceptance_self_review_task"),
            workspace=management_workspace, created_by=owner,
            title="Self review restriction Integration", status=Task.Status.REVIEW,
        )
        Deliverable.objects.create(
            task=self_review_task, uploaded_by=participants["manager"],
            revision=1, status=Deliverable.Status.SUBMITTED,
            file_url="https://example.test/negative-self-review-fixture",
        )


class QuietRequestHandler(WSGIRequestHandler):
    # Never emit cookie headers, credentials, request payloads or private rows.
    def log_message(self, format, *args):
        pass


class ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def run(mode, arguments=()):
    if mode not in ("serve", "expire-sessions", "consume-test-mail"):
        raise ValueError("Unknown integration operation.")
    if mode != "consume-test-mail" and arguments:
        raise ValueError("Unexpected integration arguments.")
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
    mailbox_cleanup = None
    try:
        if mode == "consume-test-mail":
            if len(arguments) != 2:
                raise ValueError("Isolated mailbox selection required.")
            select_owned_database(config, maintenance)
            token = consume_test_mail(os.environ["HT_TEST_RUN_ID"], *arguments)
            # stdout is consumed only by execFileSync and kept in Node memory.
            print(token, flush=True)
            return 0
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
        mailbox_cleanup = install_test_mailbox(os.environ["HT_TEST_RUN_ID"])
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
        try:
            if mailbox_cleanup is not None:
                mailbox_cleanup()
        finally:
            connections.close_all()
            try:
                if created:
                    drop_owned_database(maintenance, config, system_id)
                    print("Owned integration database removed.", flush=True)
            finally:
                maintenance.close()


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "serve"
    os.chdir(ROOT / "backend")
    try:
        return run(mode, sys.argv[2:])
    except KeyboardInterrupt:
        return 0
    except Exception as error:
        # Driver messages and tracebacks can contain DSNs or fixture values.
        print(f"Isolated frontend integration stopped ({type(error).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
