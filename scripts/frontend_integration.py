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


def install_test_mailbox(run_id, *, fail_first_invitation=False, invitation_v2=False):
    """Copy only locmem-accepted credential mail into this disposable container.

    No HTTP endpoint, deployment setting, mail provider or application email
    service changes. This private bridge lets Node receive delivered test
    credentials in memory without printing them or putting them on the host.
    """
    import fcntl
    import json
    import re
    import tempfile
    from threading import Lock
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
        "Your HustlyTasker Profile invitation": "invitation",
    }
    original = EmailBackend.send_messages
    failure_lock = Lock()
    failure_pending = fail_first_invitation
    # V2 delivery probes are synthetic, container-local failures; no SMTP or
    # development configuration is read. Fail only the first attempt per target.
    v2_failure_targets = {
        f"invitation_v2_{label}.{run_id}@example.test"
        for label in ("failed", "retry")
    } if invitation_v2 else set()

    def send_messages(backend, messages):
        nonlocal failure_pending
        messages = list(messages)
        with failure_lock:
            for message in messages:
                if message.subject == "Your HustlyTasker Profile invitation" and len(message.to) == 1 and message.to[0] in v2_failure_targets:
                    v2_failure_targets.remove(message.to[0])
                    raise RuntimeError("Deliberate isolated account-invitation transport failure.")
        if fail_first_invitation:
            invitations = [message for message in messages if message.subject == "Your HustlyTasker Profile invitation"]
            if invitations:
                if len(messages) != 1 or len(invitations) != 1 or invitations[0].to != [recipient]:
                    raise RuntimeError("Isolated invitation failure fixture target mismatch.")
                with failure_lock:
                    if failure_pending:
                        failure_pending = False
                        # Fail before locmem accepts anything. The real business
                        # callback must persist FAILED after its transaction has
                        # committed; the next explicit resend can use locmem.
                        raise RuntimeError("Deliberate isolated invitation transport failure.")
        accepted = original(backend, messages)
        if accepted != len(messages):
            raise RuntimeError("Isolated locmem acceptance count mismatch.")
        for message in messages:
            purpose = purposes.get(message.subject)
            if purpose is None or message.to != [recipient]:
                continue
            parts = message.body.split("\n\n")
            token_index = 2 if purpose == "invitation" else 1
            token = parts[token_index] if len(parts) > token_index else ""
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

    if recipient_alias != "registered" or purpose not in ("verification", "password-reset", "invitation"):
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
        # FE05: independent first-time identities, intentionally without any
        # Profile/Workspace membership. Only the owned isolated database is
        # selected before this seed function; Profile creation itself is UI E2E.
        for label in ("onboarding", "onboarding_security", "onboarding_keyboard"):
            User.objects.create_user(
                username=f"fixture_{label}", email=f"{label}.{run_id}@example.test",
                password=password, first_name="Người mới", last_name="Kiểm thử",
            )
        # Membership inheritance has its own actors/tenant so the previous
        # membership/Invitation suites retain their exact access assumptions.
        # This function only runs after fresh isolated-cluster/database gates.
        inheritance_owner = User.objects.create_user(
            username="fixture_inheritance_owner", email=f"inheritance_owner.{run_id}@example.test",
            password=password, first_name="Chủ", last_name="Kế thừa",
        )
        inheritance_profile = Profile.objects.create(
            id=fixture_id(run_id, "inheritance_profile"), name="Workspace Inheritance Integration",
        )
        ProfileMembership.objects.create(
            profile=inheritance_profile, user=inheritance_owner, role=ProfileMembership.Role.OWNER,
        )
        current_month = datetime.now(timezone.utc).date().replace(day=1)
        previous_month = (current_month - timedelta(days=1)).replace(day=1)
        next_month = (current_month + timedelta(days=32)).replace(day=1)
        inheritance_source = Workspace.objects.create(
            id=fixture_id(run_id, "inheritance_source"), profile=inheritance_profile,
            owner=inheritance_owner, name="Nguồn kế thừa kiểm thử", period=previous_month,
        )
        Workspace.objects.create(
            id=fixture_id(run_id, "inheritance_future"), profile=inheritance_profile,
            owner=inheritance_owner, name="Workspace tương lai kiểm thử", period=next_month,
        )
        for label, role, profile_active, workspace_active in (
            ("inheritance_admin", "ADMIN", True, True),
            ("inheritance_member", "MEMBER", True, True),
            ("inheritance_viewer", "VIEWER", True, True),
            ("inheritance_revoked", "MEMBER", True, False),
            ("inheritance_inactive", "MEMBER", False, True),
        ):
            actor = User.objects.create_user(
                username=f"fixture_{label}", email=f"{label}.{run_id}@example.test",
                password=password, first_name=label, last_name="Kiểm thử",
            )
            profile_membership = ProfileMembership.objects.create(
                id=fixture_id(run_id, f"{label}_profile_membership"), profile=inheritance_profile,
                user=actor, role="MEMBER", is_active=True,
            )
            WorkspaceMember.objects.create(
                id=fixture_id(run_id, f"{label}_source_membership"), workspace=inheritance_source,
                user=actor, role=role, is_active=workspace_active,
            )
            if not profile_active:
                # Simulate a once-valid Workspace assignment whose Profile
                # membership was later revoked. Creation must still respect
                # WorkspaceMember's normal active-Profile validation.
                ProfileMembership.objects.filter(pk=profile_membership.pk).update(is_active=False)
        Task.objects.create(
            id=fixture_id(run_id, "inheritance_source_task"), workspace=inheritance_source,
            created_by=inheritance_owner, title="Source work must not be copied",
        )
        first_profile = Profile.objects.create(
            id=fixture_id(run_id, "inheritance_first_profile"), name="First Workspace Inheritance Integration",
        )
        ProfileMembership.objects.create(profile=first_profile, user=inheritance_owner, role="OWNER")
        ProfileMembership.objects.create(
            id=fixture_id(run_id, "inheritance_first_candidate"), profile=first_profile,
            user=User.objects.get(username="fixture_inheritance_member"), role="MEMBER",
        )
        # Dedicated AI fixture actors/empty Workspaces keep quotas and state
        # independent. No proposal or Task is seeded in these new scopes.
        ai_profiles = {}
        for label in ("ai_manager", "ai_recovery", "ai_keyboard"):
            actor = User.objects.create_user(
                username=f"fixture_{label}", email=f"{label}.{run_id}@example.test",
                password=password, first_name="Quản lý", last_name="Demo",
            )
            organization = Profile.objects.create(
                id=fixture_id(run_id, label + "_profile"), name=f"AI {label} Integration",
            )
            ProfileMembership.objects.create(
                profile=organization, user=actor, role=ProfileMembership.Role.OWNER,
            )
            child = Workspace.objects.create(
                id=fixture_id(run_id, label + "_workspace"), profile=organization,
                owner=actor, name=f"AI {label} Workspace", period=date(2027, 1, 1),
            )
            ai_profiles[label] = (organization, child)
        ai_profile, ai_workspace = ai_profiles["ai_manager"]
        for label, role, workspace_role in (
            ("ai_peer", ProfileMembership.Role.ADMIN, WorkspaceMember.Role.ADMIN),
            ("ai_viewer", ProfileMembership.Role.MEMBER, WorkspaceMember.Role.VIEWER),
        ):
            actor = User.objects.create_user(
                username=f"fixture_{label}", email=f"{label}.{run_id}@example.test",
                password=password, first_name="Thành viên", last_name="Demo",
            )
            ProfileMembership.objects.create(profile=ai_profile, user=actor, role=role)
            WorkspaceMember.objects.create(workspace=ai_workspace, user=actor, role=workspace_role)
        # P4-03C sources exist only in the exact owned isolated database.
        # Separate tenants keep Generator's empty scopes and prior suites intact.
        from apps.reviews.models import Deliverable, Review
        from apps.tasks.models import TaskComment
        analyzer_owner = User.objects.create_user(
            username="fixture_analyzer_org_owner", email=f"analyzer_org_owner.{run_id}@example.test",
            password=password,
        )
        analyzer_scopes = {}
        for label in ("analyzer_manager", "analyzer_privacy", "analyzer_keyboard"):
            actor = User.objects.create_user(
                username=f"fixture_{label}", email=f"{label}.{run_id}@example.test",
                password=password, first_name="Quản lý", last_name="Phản hồi",
            )
            organization = Profile.objects.create(
                id=fixture_id(run_id, label + "_profile"), name=f"Feedback {label} Integration",
            )
            ProfileMembership.objects.create(profile=organization, user=analyzer_owner, role="OWNER")
            ProfileMembership.objects.create(profile=organization, user=actor, role="MEMBER")
            child = Workspace.objects.create(
                id=fixture_id(run_id, label + "_workspace"), profile=organization, owner=analyzer_owner,
                name=f"Feedback {label} Workspace", period=date(2027, 1, 1),
            )
            WorkspaceMember.objects.create(workspace=child, user=actor, role="ADMIN")
            task = Task.objects.create(
                id=fixture_id(run_id, label + "_task"), workspace=child,
                created_by=analyzer_owner, title=f"Feedback {label} Task", status="WORKING",
            )
            Task.objects.create(
                id=fixture_id(run_id, label + "_empty_task"), workspace=child,
                created_by=analyzer_owner, title=f"Feedback {label} Empty Task",
            )
            deliverable = Deliverable.objects.create(
                id=fixture_id(run_id, label + "_deliverable"), task=task, uploaded_by=actor,
                revision=1, status="REJECTED", file_url="https://example.test/synthetic-feedback-output",
            )
            Review.objects.create(
                id=fixture_id(run_id, label + "_review"), deliverable=deliverable,
                reviewer=analyzer_owner, status="REQUEST_CHANGE",
                comment="ANALYZER_SYNTHETIC_REVIEW: kiểm tra phụ đề trong ví dụ giả lập.",
            )
            TaskComment.objects.create(
                id=fixture_id(run_id, label + "_comment"), task=task, user=actor,
                content="ANALYZER_SYNTHETIC_DISCUSSION: nhận xét minh họa về âm thanh.",
            )
            tombstone = TaskComment.objects.create(
                id=fixture_id(run_id, label + "_deleted_comment"), task=task, user=actor,
                content="DELETED_ANALYZER_CONTENT_MUST_STAY_HIDDEN",
            )
            TaskComment.objects.filter(pk=tombstone.pk).update(deleted_at=datetime.now(timezone.utc))
            analyzer_scopes[label] = (organization, child)
        for label, role in (("analyzer_viewer", "VIEWER"), ("analyzer_editor", "MEMBER")):
            actor = User.objects.create_user(
                username=f"fixture_{label}", email=f"{label}.{run_id}@example.test", password=password,
            )
            organization, child = analyzer_scopes["analyzer_manager"]
            ProfileMembership.objects.create(profile=organization, user=actor, role="MEMBER")
            WorkspaceMember.objects.create(workspace=child, user=actor, role=role)
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
            file_url="https://example.test/isolated-deliverable-v2",
        )
        approve_deliverable(
            actor=participants["manager"], **scope, task_id=history_task.id,
            deliverable_id=second_revision.id, comment="Approved contrast revision.",
        )
        # Isolated historical fixture only: legacy storage accepted non-URL text.
        # New submit APIs reject it; history must still read as escaped text.
        history_task.deliverables.filter(pk=second_revision.id).update(
            file_url="javascript:unsafe-deliverable-text",
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
        seed_reassignment_analytics_fixtures(run_id, password)


def seed_reassignment_analytics_fixtures(run_id, password):
    """Independent synthetic tenant; never called before owned DB selection.

    Setup is deliberately distinguished from UI actions in the browser spec.
    Legacy unknown compensation is represented explicitly, never guessed.
    """
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    from django.contrib.auth import get_user_model
    from django.utils import timezone
    from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
    from apps.tasks.models import Task, TaskAssignment
    from apps.reviews.models import Deliverable, Review
    from apps.tasks.services import assign_task, start_task, submit_deliverable, approve_deliverable

    current = timezone.now().astimezone(ZoneInfo("Asia/Ho_Chi_Minh"))
    month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    actors = {}
    for label, first, last in (
        ("owner", "Chủ", "Thống kê"), ("manager", "Quản lý", "Thống kê"),
        ("editor_a", "Nguyễn", "Editor A"), ("editor_b", "", ""),
        ("viewer", "Người xem", "Thống kê"),
    ):
        actors[label] = get_user_model().objects.create_user(
            username=f"analytics_{label}", email=f"analytics_{label}.{run_id}@example.test",
            password=password, first_name=first, last_name=last,
        )
    profile = Profile.objects.create(id=fixture_id(run_id, "analytics_profile"), name="Analytics Workspace Studio")
    memberships = {}
    for label, actor in actors.items():
        memberships[label] = ProfileMembership.objects.create(
            id=fixture_id(run_id, f"analytics_{label}_membership"), profile=profile,
            user=actor, role="OWNER" if label == "owner" else "MEMBER",
        )
    main = Workspace.objects.create(
        id=fixture_id(run_id, "analytics_workspace"), profile=profile, owner=actors["owner"],
        name="Analytics Main Workspace", period=current.date().replace(day=1),
    )
    sibling = Workspace.objects.create(
        id=fixture_id(run_id, "analytics_sibling_workspace"), profile=profile, owner=actors["owner"],
        name="Analytics Other Workspace", period=(month_start.date() - timedelta(days=1)).replace(day=1),
    )
    for workspace in (main, sibling):
        for label in ("manager", "editor_a", "editor_b", "viewer"):
            WorkspaceMember.objects.create(
                workspace=workspace, user=actors[label],
                role="VIEWER" if label == "viewer" else ("ADMIN" if label == "manager" and workspace == main else "MEMBER"),
            )
    def task(label, title, amount, workspace=main):
        return Task.objects.create(
            id=fixture_id(run_id, "analytics_" + label), workspace=workspace, created_by=actors["owner"],
            title=title, estimated_compensation_vnd=amount,
            description="Synthetic analytics fixture; no customer data.",
        )
    scope = {"profile_id": profile.pk, "workspace_id": main.pk}
    transfer = task("transfer_task", "Chuyển giao an toàn", "500000")
    working = task("working_task", "Công việc đang dựng", "100000")
    task("unassigned_task", "Chưa phân công và chưa định giá", None)
    task("large_task", "Giá trị nguyên lớn", "999999999999999999")
    for item in (transfer, working):
        assign_task(actor=actors["manager"], **scope, task_id=item.pk, target_profile_membership_id=memberships["editor_a"].pk)
    start_task(actor=actors["editor_a"], **scope, task_id=working.pk)
    completed = task("completed_task", "Đã nghiệm thu trong kỳ", "700000")
    # Created in a previous cohort; accepted now. These two date bases differ.
    Task.objects.filter(pk=completed.pk).update(created_at=month_start - timedelta(days=2))
    assign_task(actor=actors["manager"], **scope, task_id=completed.pk, target_profile_membership_id=memberships["editor_b"].pk)
    start_task(actor=actors["editor_b"], **scope, task_id=completed.pk)
    product = submit_deliverable(actor=actors["editor_b"], **scope, task_id=completed.pk, file_url="https://example.test/analytics-completed")
    approved = approve_deliverable(actor=actors["manager"], **scope, task_id=completed.pk, deliverable_id=product.pk)
    if not approved.compensation_snapshot_recorded or str(approved.compensation_snapshot_vnd) != "700000":
        raise RuntimeError("Isolated approval snapshot fixture was not captured.")
    # Current estimate is deliberately different; the historical value is700000.
    Task.objects.filter(pk=completed.pk).update(estimated_compensation_vnd="999000")
    legacy = task("legacy_task", "Lịch sử chưa có snapshot giá", "9000000")
    Task.objects.filter(pk=legacy.pk).update(status=Task.Status.COMPLETED)
    TaskAssignment.objects.create(task=legacy, user=actors["editor_a"])
    old_product = Deliverable.objects.create(
        task=legacy, uploaded_by=actors["editor_a"], revision=1,
        status=Deliverable.Status.APPROVED, file_url="https://example.test/analytics-legacy",
    )
    Review.objects.create(deliverable=old_product, reviewer=actors["manager"], status=Review.Status.APPROVED)
    task("sibling_task", "Workspace khác không được quản lý", "123000", workspace=sibling)


def seed_invitation_v2_fixtures(run_id):
    """Synthetic actors only, after owned isolated schema/mailbox gates.

    Account creation/roles are API-driven setup, not claimed as UI E2E. The
    invitation sends and decisions under test are performed through React.
    """
    from datetime import timedelta
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.utils import timezone
    from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
    from apps.workspace.invitation_services import create_profile_invitation

    password = os.environ["HT_FRONTEND_TEST_PASSWORD"]
    User = get_user_model()
    with transaction.atomic():
        actors = {}
        for label, first, last in (
            ("owner", "V2", "Chủ tổ chức"), ("admin", "V2", "Quản trị viên"),
            ("member", "V2", "Thành viên"), ("recipient", "V2", "Người nhận"),
            ("decliner", "V2", "Từ chối"), ("failed", "V2", "Email lỗi"),
            ("retry", "V2", "Thử lại email"), ("switcher", "V2", "Nhiều tổ chức"),
            ("foreign", "V2", "Chủ tổ chức khác"),
        ):
            actors[label] = User.objects.create_user(
                id=fixture_id(run_id, f"invitation_v2_{label}"),
                username=f"fixture_v2_{label}", email=f"invitation_v2_{label}.{run_id}@example.test",
                password=password, first_name=first, last_name=last,
            )
        profile = Profile.objects.create(id=fixture_id(run_id, "invitation_v2_profile"), name="V2 Invitation Studio")
        foreign = Profile.objects.create(id=fixture_id(run_id, "invitation_v2_foreign_profile"), name="V2 Other Studio")
        ProfileMembership.objects.create(profile=profile, user=actors["owner"], role="OWNER")
        ProfileMembership.objects.create(profile=profile, user=actors["admin"], role="ADMIN")
        ProfileMembership.objects.create(profile=profile, user=actors["member"], role="MEMBER")
        ProfileMembership.objects.create(profile=foreign, user=actors["foreign"], role="OWNER")
        ProfileMembership.objects.create(profile=foreign, user=actors["switcher"], role="MEMBER")
        month = timezone.localdate(timezone.now(), timezone.get_default_timezone()).replace(day=1)
        for label, period in (("current", month), ("previous", (month - timedelta(days=1)).replace(day=1))):
            workspace = Workspace.objects.create(
                id=fixture_id(run_id, f"invitation_v2_workspace_{label}"), profile=profile,
                owner=actors["owner"], name=f"V2 Workspace {label}", period=period,
            )
            WorkspaceMember.objects.create(workspace=workspace, user=actors["member"], role="VIEWER")
        for index in range(25):
            User.objects.create_user(
                id=fixture_id(run_id, f"invitation_v2_candidate_{index}"),
                username=f"v2_candidate_{index:02d}", email=f"v2candidate{index}.{run_id}@example.test",
                password=None, first_name="V2 Candidate", last_name=f"{index:02d}",
            )
        # This fixture represents an invitation already issued before cutover.
        # The private legacy service remains test-only here; public email-create
        # is explicitly denied by the V2 API and exercised by browser negatives.
        legacy = User.objects.create_user(
            id=fixture_id(run_id, "invitation_v2_legacy"), username="fixture_v2_legacy",
            email=f"acceptance.{run_id}@example.test", password=password,
            first_name="V2", last_name="Legacy recipient",
        )
        create_profile_invitation(
            actor=actors["owner"], profile_id=profile.pk,
            recipient_email=legacy.email, requested_role="MEMBER",
        )


def seed_legacy_inheritance_invitation(run_id):
    """Pre-cutover invitation for the existing legacy-registration browser case."""
    from django.contrib.auth import get_user_model
    from apps.workspace.invitation_services import create_profile_invitation
    owner = get_user_model().objects.get(username="fixture_inheritance_owner")
    create_profile_invitation(
        actor=owner, profile_id=fixture_id(run_id, "inheritance_profile"),
        recipient_email=f"acceptance.{run_id}@example.test", requested_role="MEMBER",
    )


def seed_legacy_workspace_member_invitation(run_id):
    """Issued pre-cutover token fixture; never recreate the removed invite UI.

    This preserves the legacy consent/no-Workspace case while the browser tests
    Workspace grants and later role mutations through the current React UI.
    Only called after the owned disposable database and locmem gates below.
    """
    from django.contrib.auth import get_user_model
    from apps.workspace.invitation_services import create_profile_invitation
    create_profile_invitation(
        actor=get_user_model().objects.get(username="fixture_owner"),
        profile_id=fixture_id(run_id, "management_profile"),
        recipient_email=f"acceptance.{run_id}@example.test", requested_role="MEMBER",
    )


class QuietRequestHandler(WSGIRequestHandler):
    # Never emit cookie headers, credentials, request payloads or private rows.
    def log_message(self, format, *args):
        pass


class ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def seed_trash_fixtures(run_id):
    """Synthetic Trash-only data, after fresh cluster/database ownership gates."""
    from datetime import date, timedelta
    from django.contrib.auth import get_user_model
    from django.db import transaction
    from django.utils import timezone
    from apps.workspace.models import Profile, ProfileMembership, Workspace, WorkspaceMember
    from apps.tasks.models import Task
    from apps.reviews.models import Deliverable, Review

    password = os.environ["HT_FRONTEND_TEST_PASSWORD"]
    User = get_user_model()
    now = timezone.now()
    recent = now - timedelta(days=2)
    expired = now - timedelta(days=31)
    with transaction.atomic():
        actors = {label: User.objects.create_user(
            username=f"fixture_trash_{label}", email=f"trash_{label}.{run_id}@example.test",
            password=password, first_name="Thùng rác", last_name=label,
        ) for label in ("owner", "manager", "viewer", "foreign_owner", "solo_owner")}
        owner = actors["owner"]

        def profile(label, title, *, deleted=None, actor=owner):
            item = Profile.objects.create(id=fixture_id(run_id,label), name=title)
            ProfileMembership.objects.create(profile=item, user=actor, role="OWNER")
            if deleted is not None:
                Profile.objects.filter(pk=item.pk).update(created_at=deleted-timedelta(days=1), deleted_at=deleted, deleted_by=actor, purge_after=deleted+timedelta(days=30))
            return item

        organization = profile("trash_profile", "Trash Organization Integration")
        profile("trash_solo_profile", "Trash Solo Profile Integration", actor=actors["solo_owner"])
        profile("trash_deleted_profile", "Trash Deleted Profile Integration", deleted=recent)
        profile("trash_expired_profile", "Trash Expired Profile Integration", deleted=expired)
        foreign = profile("trash_foreign_profile", "Trash Foreign Organization Integration", actor=actors["foreign_owner"])
        for label, role in (("manager", "ADMIN"), ("viewer", "MEMBER")):
            ProfileMembership.objects.create(profile=organization, user=actors[label], role=role)

        def workspace(label, title, month, *, parent=organization, deleted=None, actor=owner):
            item = Workspace.objects.create(id=fixture_id(run_id,label), profile=parent, owner=actor,
                name=title, period=date(2025, month, 1))
            if deleted is not None:
                Workspace.objects.filter(pk=item.pk).update(created_at=deleted-timedelta(days=1), deleted_at=deleted, deleted_by=actor, purge_after=deleted+timedelta(days=30))
            return item

        child = workspace("trash_workspace", "Trash Workspace Integration", 1)
        deleted_child = workspace("trash_deleted_workspace", "Trash Deleted Workspace Integration", 2, deleted=recent)
        workspace("trash_expired_workspace", "Trash Expired Workspace Integration", 3, deleted=expired)
        foreign_child = workspace("trash_foreign_workspace", "Trash Foreign Workspace Integration", 1, parent=foreign, actor=actors["foreign_owner"])
        WorkspaceMember.objects.create(workspace=child,user=actors["viewer"],role="VIEWER")

        def task(label, title, *, parent=child, deleted=None, status="PENDING", actor=owner):
            item = Task.objects.create(id=fixture_id(run_id,label), workspace=parent, created_by=actor, title=title,status=status)
            if deleted is not None:
                Task.objects.filter(pk=item.pk).update(created_at=deleted-timedelta(days=1),deleted_at=deleted,deleted_by=actor,purge_after=deleted+timedelta(days=30))
            return item

        task("trash_live_task", "Trash live task Integration")
        task("trash_recent_task", "Trash recent task Integration", deleted=recent)
        task("trash_expired_task", "Trash expired task Integration", deleted=expired)
        history = task("trash_history_task", "Trash protected history Integration", deleted=expired, status="COMPLETED")
        submitted = Deliverable.objects.create(task=history,uploaded_by=actors["manager"],file_url="https://example.test/trash-approved",revision=1,status="APPROVED")
        Review.objects.create(deliverable=submitted,reviewer=owner,status="APPROVED",compensation_snapshot_recorded=True,compensation_snapshot_vnd=500000)
        task("trash_inherited_task", "Trash inherited task Integration", parent=deleted_child)
        task("trash_independent_task", "Trash independent task Integration", parent=deleted_child,deleted=recent)
        task("trash_foreign_task", "Trash Foreign task Integration", parent=foreign_child,actor=actors["foreign_owner"])
        for index in range(21):
            task(f"trash_paged_{index:02}", f"Trash pagination task {index:02}", deleted=recent)


def run(mode, arguments=()):
    if mode not in ("serve", "serve-ai", "serve-ai-mvp", "serve-ai-mvp-groq", "serve-invitation-delivery-failure", "serve-invitation-v2", "serve-invitation-regression", "serve-workspace-members", "serve-trash", "expire-sessions", "consume-test-mail", "feedback-state"):
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
    from test_backend import check_cluster, drop_owned_database, is_governance_migration

    maintenance = psycopg.connect(
        host=config["host"], port=config["port"], user=config["user"],
        dbname="postgres", connect_timeout=10, autocommit=True,
    )
    created = False
    system_id = None
    mailbox_cleanup = None
    try:
        if mode == "feedback-state":
            select_owned_database(config, maintenance)
            import hashlib
            import json
            from django.apps import apps
            # Only count/fingerprint state, never print source text or identities.
            snapshot = {}
            for model in apps.get_models():
                rows = list(model.objects.order_by("pk").values())
                encoded = json.dumps(rows, default=str, sort_keys=True).encode("utf-8")
                snapshot[model._meta.label] = {
                    "count": len(rows), "sha256": hashlib.sha256(encoded).hexdigest(),
                }
            print(json.dumps(snapshot, sort_keys=True), flush=True)
            return 0
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
        if mode in ("serve-invitation-v2", "serve-invitation-regression", "serve-workspace-members", "serve-trash"):
            # Only full backend regression needs AI governance. This scoped
            # browser suite applies every other leaf while retaining ai.0001,
            # keeping the AI0002 exception confined to its approved full suite.
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connections["default"])
            targets = [target if target[0] != "ai" else ("ai", "0001_initial") for target in executor.loader.graph.leaf_nodes()]
            for app, name in targets:
                plan = MigrationExecutor(connections["default"]).migration_plan([(app, name)])
                if any(is_governance_migration(item.app_label, item.name) for item, _ in plan):
                    raise RuntimeError("AI governance is outside this browser suite.")
                call_command("migrate", app, name, interactive=False, verbosity=0)
            executor = MigrationExecutor(connections["default"])
            if any(is_governance_migration(*item) for item in executor.loader.applied_migrations) or executor.migration_plan(targets):
                raise RuntimeError("Scoped invitation browser migration history mismatch.")
            print("INVITATION_V2_SCOPED_MIGRATIONS_READY; AI0002_UNAPPLIED", flush=True)
        else:
            call_command("migrate", interactive=False, verbosity=0)
            call_command("migrate", check=True, interactive=False)
        if mode == "serve-ai":
            # Only after exact isolated cluster/database ownership checks.
            # config.test_settings ignores deployment env; no persistent flag.
            from django.conf import settings
            if settings.SETTINGS_MODULE != "config.test_settings":
                raise RuntimeError("AI fixtures require owned test settings.")
            settings.AI_FIXTURE_ENABLED = True
        elif mode in ("serve-ai-mvp", "serve-ai-mvp-groq"):
            from django.conf import settings
            from apps.ai import live_runtime
            from ai_mvp_test_transport import BrowserFakeTransport, groq_browser_post, unexpected_ai_transport
            if settings.SETTINGS_MODULE != "config.test_settings":
                raise RuntimeError("AI browser test requires owned test settings.")
            if mode == "serve-ai-mvp-groq":
                settings.AI_PROVIDER = "groq"
                settings.AI_MODEL = live_runtime.GROQ_MODEL
                settings.AI_GROQ_FREE_TIER_CONFIRMED = True
                live_runtime._groq_api_key = lambda: "synthetic-browser-test-key-not-a-credential"
                live_runtime.GroqHttpsTransport.post = groq_browser_post
                live_runtime.OpenAIHttpsTransport.post = unexpected_ai_transport
            else:
                settings.AI_PROVIDER = "openai"
                settings.AI_MODEL = "gpt-5.4-mini"
                live_runtime.OpenAIHttpsTransport = BrowserFakeTransport
                live_runtime.GroqHttpsTransport.post = unexpected_ai_transport
                os.environ["OPENAI_API_KEY"] = "synthetic-browser-test-key-not-a-credential"
            settings.AI_LIVE_ENABLED = True
        seed_fixtures(os.environ["HT_TEST_RUN_ID"])
        mailbox_cleanup = install_test_mailbox(
            os.environ["HT_TEST_RUN_ID"],
            fail_first_invitation=mode == "serve-invitation-delivery-failure",
            invitation_v2=mode == "serve-invitation-v2",
        )
        if mode == "serve-invitation-v2":
            seed_invitation_v2_fixtures(os.environ["HT_TEST_RUN_ID"])
        elif mode == "serve-invitation-regression":
            seed_legacy_inheritance_invitation(os.environ["HT_TEST_RUN_ID"])
        elif mode == "serve-workspace-members":
            seed_legacy_workspace_member_invitation(os.environ["HT_TEST_RUN_ID"])
        elif mode == "serve-trash":
            from django.conf import settings
            if settings.SETTINGS_MODULE != "config.test_settings":
                raise RuntimeError("Trash fixtures require owned test settings.")
            settings.TRASH_PURGE_ENABLED = True
            seed_trash_fixtures(os.environ["HT_TEST_RUN_ID"])
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
