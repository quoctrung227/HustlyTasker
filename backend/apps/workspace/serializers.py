from collections.abc import Mapping

from rest_framework import serializers

from .models import Profile, Workspace, WorkspaceMember


class StrictInputSerializer(serializers.Serializer):
    """Reject server-owned and misspelled fields instead of ignoring them."""

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
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
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class WorkspaceWriteSerializer(StrictInputSerializer):
    """The complete client-writable Workspace metadata contract."""

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


class WorkspaceMemberReadSerializer(serializers.ModelSerializer):
    """Minimal assignment metadata without User PII or a global User ID."""

    profile_membership_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = WorkspaceMember
        fields = (
            "id",
            "profile_membership_id",
            "role",
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
