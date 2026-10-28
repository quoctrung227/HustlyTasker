from collections.abc import Mapping

from rest_framework import serializers

from .models import Profile, ProfileInvitation, ProfileMembership, Workspace, WorkspaceMember


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
    """Manager-only roster labels, without email or a global User identifier."""

    profile_membership_id = serializers.UUIDField(read_only=True)
    display_label = serializers.SerializerMethodField()
    is_assignable = serializers.SerializerMethodField()

    class Meta:
        model = WorkspaceMember
        fields = (
            "id",
            "profile_membership_id",
            "display_label",
            "is_assignable",
            "role",
            "is_active",
            "joined_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_display_label(self, membership):
        name = membership.user.get_full_name().strip()
        if name:
            return name
        # A username can itself be an email address. Never use it as fallback.
        membership_id = getattr(membership, "profile_membership_id", membership.pk)
        return f"Thành viên {str(membership_id)[:8]}"

    def get_is_assignable(self, membership):
        workspace = membership.workspace
        if (
            not membership.is_active
            or membership.role != WorkspaceMember.Role.MEMBER
            or not membership.user.is_active
            or workspace.status != Workspace.Status.ACTIVE
            or workspace.profile.status != Profile.Status.ACTIVE
        ):
            return False
        eligible_profile_membership = getattr(
            membership, "_has_assignable_profile_membership", None,
        )
        if eligible_profile_membership is None:
            # Existing member mutation responses are individual objects rather
            # than the roster queryset. Keep their additive fields consistent.
            eligible_profile_membership = ProfileMembership.objects.filter(
                profile_id=workspace.profile_id,
                user_id=membership.user_id,
                user__is_active=True,
                is_active=True,
                role=ProfileMembership.Role.MEMBER,
            ).exists()
        # These are the current assignment service's target predicates. This
        # read-only hint cannot replace its locked mutation-time validation.
        return bool(eligible_profile_membership)


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
