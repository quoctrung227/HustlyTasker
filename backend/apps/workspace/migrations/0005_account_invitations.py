"""Account-only Web invitations; existing rows remain EMAIL_TOKEN unchanged."""
import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("workspace", "0004_profileinvitation"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.AddField(model_name="profileinvitation", name="acceptance_kind",
            field=models.CharField(choices=[("EMAIL_TOKEN", "Email Token"), ("ACCOUNT", "Account")], default="EMAIL_TOKEN", editable=False, max_length=20)),
        migrations.RemoveConstraint(model_name="profileinvitation", name="uniq_pending_profile_email"),
        migrations.AddConstraint(model_name="profileinvitation", constraint=models.UniqueConstraint(
            fields=("profile", "recipient_email_normalized"), condition=models.Q(status="PENDING", acceptance_kind="EMAIL_TOKEN"), name="uniq_pending_profile_email")),
        migrations.AlterField(model_name="profileinvitation", name="token_digest",
            field=models.CharField(blank=True, editable=False, max_length=64, null=True, unique=True)),
        migrations.RemoveConstraint(model_name="profileinvitation", name="pinv_use_requires_sent"),
        migrations.AddConstraint(model_name="profileinvitation", constraint=models.CheckConstraint(
            condition=~models.Q(status__in=("ACCEPTED", "DECLINED")) | models.Q(acceptance_kind="ACCOUNT") | models.Q(delivery_status="SENT"), name="pinv_use_requires_sent")),
        migrations.AddConstraint(model_name="profileinvitation", constraint=models.CheckConstraint(
            condition=models.Q(acceptance_kind="EMAIL_TOKEN", token_digest__isnull=False) | models.Q(acceptance_kind="ACCOUNT", recipient_user__isnull=False, token_digest__isnull=True), name="pinv_identity_kind_valid")),
        migrations.AddIndex(model_name="profileinvitation", index=models.Index(fields=["recipient_user", "acceptance_kind", "-created_at", "id"], name="pinv_recipient_inbox_idx")),
        migrations.CreateModel(name="InvitationEmailAttempt", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("status", models.CharField(choices=[("PENDING", "Pending"), ("SENT", "Sent"), ("FAILED", "Failed")], default="PENDING", max_length=16)),
            ("finished_at", models.DateTimeField(blank=True, null=True)),
            ("invitation", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="email_attempts", to="workspace.profileinvitation")),
        ], options={"indexes": [models.Index(fields=["invitation", "created_at"], name="pinv_mail_attempt_window_idx")],
                    "constraints": [models.CheckConstraint(condition=models.Q(status="PENDING", finished_at__isnull=True) | models.Q(status__in=("SENT", "FAILED"), finished_at__isnull=False), name="pinv_mail_attempt_state_valid")]}),
        migrations.CreateModel(name="InvitationDirectoryAccess", fields=[
            ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("updated_at", models.DateTimeField(auto_now=True)),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="invitation_directory_accesses", to=settings.AUTH_USER_MODEL)),
        ], options={"indexes": [models.Index(fields=["user", "created_at"], name="pinv_directory_window_idx")]}),
    ]
