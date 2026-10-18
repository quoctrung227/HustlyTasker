from rest_framework import serializers

from .models import Profile, Workspace


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
