from collections.abc import Mapping

from rest_framework import serializers

from .models import Profile, ProfileInvitation, Workspace, WorkspaceMember


class StrictInputSerializer(serializers.Serializer):
    """Reject server-owned and misspelled fields instead of ignoring them."""

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            # Never reflect an unencodable key into a JSON error response.
            # Normal unknown-field errors retain their existing contract.
            for field in data:
                try:
                    if not isinstance(field, str) or "\x00" in field:
                        raise ValueError()
                    field.encode("utf-8", errors="strict")
                except (UnicodeEncodeError, ValueError):
                    raise serializers.ValidationError({
                        "non_field_errors": ["Field names must be valid Unicode text."],
                    }) from None
            unknown_fields = set(data) - set(self.fields)
            if unknown_fields:
                raise serializers.ValidationError({
                    field: ["This field is not allowed."]
                    for field in sorted(unknown_fields)
                })

        return super().to_internal_value(data)


class ProfileReadSerializer(serializers.ModelSerializer):
    """Minimal Profile metadata visible to an active Profile member."""

    class Meta:
        model = Profile
        fields = (
            "id",
            "name",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class WorkspaceReadSerializer(serializers.ModelSerializer):
    """Minimal Workspace metadata without transitional ownership data."""

    profile_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Workspace
        fields = (
            "id",
            "profile_id",
            "name",
            "description",
            "period",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class WorkspaceCreateSerializer(StrictInputSerializer):
    """Create one Workspace for an explicit canonical monthly period."""

    name = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    period = serializers.DateField()

    def validate_period(self, value):
        if value.day != 1:
            raise serializers.ValidationError(
                "Workspace period must be the first day of a month."
            )
        return value


class WorkspaceUpdateSerializer(StrictInputSerializer):
    """Mutable Workspace metadata; tenant, period, and status are server-owned."""

    name = serializers.CharField(
        required=False,
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )


class WorkspaceLifecycleSerializer(StrictInputSerializer):
    """Lifecycle actions intentionally accept no client-controlled fields."""

    pass


class ProfileLifecycleSerializer(StrictInputSerializer):
    """Profile lifecycle actions intentionally accept no writable fields."""

    pass


class ProfileInvitationReadSerializer(serializers.ModelSerializer):
    """Sanitized manager metadata; invitation credentials are never exposed."""

    profile_id = serializers.UUIDField(read_only=True)
    recipient_email = serializers.EmailField(
        source="recipient_email_normalized",
        read_only=True,
    )
    status = serializers.SerializerMethodField()

    class Meta:
        model = ProfileInvitation
        fields = (
            "id",
            "profile_id",
            "recipient_email",
            "requested_role",
            "status",
            "delivery_status",
            "expires_at",
            "delivery_attempted_at",
            "delivered_at",
            "accepted_at",
            "declined_at",
            "revoked_at",
            "expired_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_status(self, obj):
        return obj.effective_status


class ProfileInvitationCreateSerializer(StrictInputSerializer):
    recipient_email = serializers.EmailField(max_length=254)
    requested_role = serializers.ChoiceField(
        choices=ProfileInvitation.Role.choices,
        default=ProfileInvitation.Role.MEMBER,
    )


class ProfileInvitationActionSerializer(StrictInputSerializer):
    """Manager lifecycle actions have no client-controlled fields."""

    pass


class ProfileInvitationTokenSerializer(StrictInputSerializer):
    token = serializers.CharField(
        max_length=512,
        allow_blank=False,
        trim_whitespace=False,
        write_only=True,
    )


class WorkspaceMemberReadSerializer(serializers.ModelSerializer):
    """Minimal assignment metadata without User PII or a global User ID."""

    profile_membership_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = (
            "id",
            "profile_membership_id",
            "role",
            "is_active",
            "joined_at",
            "updated_at",
        )
        read_only_fields = fields


class WorkspaceMemberCreateSerializer(StrictInputSerializer):
    target_profile_membership_id = serializers.UUIDField()
    role = serializers.ChoiceField(
        choices=(
            WorkspaceMember.Role.ADMIN,
            WorkspaceMember.Role.MEMBER,
            WorkspaceMember.Role.VIEWER,
        )
    )


class WorkspaceMemberUpdateSerializer(StrictInputSerializer):
    role = serializers.ChoiceField(
        choices=(
            WorkspaceMember.Role.ADMIN,
            WorkspaceMember.Role.MEMBER,
            WorkspaceMember.Role.VIEWER,
        )
    )
