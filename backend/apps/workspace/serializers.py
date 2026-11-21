from collections.abc import Mapping
from functools import cached_property

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

    can_delete = serializers.SerializerMethodField()

    @cached_property
    def _deletable_profile_ids(self):
        actor = getattr(self.context.get("request"), "user", None)
        if not getattr(actor, "is_authenticated", False) or not getattr(actor, "is_active", False):
            return set()
        return set(ProfileMembership.objects.filter(user_id=actor.pk, user__is_active=True,
            is_active=True, role=ProfileMembership.Role.OWNER,
            profile__deleted_at__isnull=True).values_list("profile_id", flat=True))

    def get_can_delete(self, profile):
        return profile.deleted_at is None and profile.pk in self._deletable_profile_ids

    class Meta:
        model = Profile
        fields = (
            "id",
            "name",
            "status",
            "can_delete",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ProfileMemberReadSerializer(serializers.ModelSerializer):
    """Manager roster metadata, without account identifiers or contact details."""

    profile_id = serializers.UUIDField(read_only=True)
    display_label = serializers.SerializerMethodField()

    class Meta:
        model = ProfileMembership
        fields = ("id", "profile_id", "display_label", "role", "is_active", "joined_at")
        read_only_fields = fields

    def get_display_label(self, membership):
        name = membership.user.get_full_name().strip()
        return name or f"Thành viên {str(membership.pk)[:8]}"


class ProfileCreateSerializer(StrictInputSerializer):
    """Only the Profile name is client-owned; identity and role are not input."""

    name = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping) and "name" in data:
            value = data["name"]
            if not isinstance(value, str):
                raise serializers.ValidationError({"name": ["Enter a valid Profile name."]})
            try:
                value.encode("utf-8", errors="strict")
            except UnicodeEncodeError:
                raise serializers.ValidationError({"name": ["Enter valid Unicode text."]}) from None
        return super().to_internal_value(data)


class WorkspaceReadSerializer(serializers.ModelSerializer):
    """Minimal Workspace metadata without transitional ownership data."""

    profile_id = serializers.UUIDField(read_only=True)
    can_delete = serializers.SerializerMethodField()

    @cached_property
    def _deletion_management_profiles(self):
        actor = getattr(self.context.get("request"), "user", None)
        if not getattr(actor, "is_authenticated", False) or not getattr(actor, "is_active", False):
            return set()
        return set(ProfileMembership.objects.filter(user_id=actor.pk, user__is_active=True,
            is_active=True, role__in=(ProfileMembership.Role.OWNER, ProfileMembership.Role.ADMIN),
            profile__deleted_at__isnull=True, profile__status=Profile.Status.ACTIVE).values_list("profile_id", flat=True))

    def get_can_delete(self, workspace):
        return workspace.deleted_at is None and workspace.profile_id in self._deletion_management_profiles

    class Meta:
        model = Workspace
        fields = (
            "id",
            "profile_id",
            "name",
            "description",
            "period",
            "status",
            "can_delete",
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
    source_workspace_id = serializers.UUIDField(required=False)
    initial_profile_membership_ids = serializers.ListField(
        child=serializers.UUIDField(), required=False,
    )

    def validate(self, attrs):
        if "source_workspace_id" in attrs and "initial_profile_membership_ids" in attrs:
            raise serializers.ValidationError({
                "initial_profile_membership_ids": ["Choose a source or initial members, not both."],
            })
        ids = attrs.get("initial_profile_membership_ids", [])
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError({
                "initial_profile_membership_ids": ["Duplicate membership references are not allowed."],
            })
        return attrs

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
    recipient_email = serializers.SerializerMethodField()
    recipient_display_label = serializers.SerializerMethodField()
    recipient_username = serializers.SerializerMethodField()
    recipient_masked_email = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = ProfileInvitation
        fields = (
            "id",
            "profile_id",
            "recipient_email",
            "acceptance_kind", "recipient_display_label", "recipient_username", "recipient_masked_email",
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

    def get_recipient_email(self, obj):
        return obj.recipient_email_normalized if obj.acceptance_kind == "EMAIL_TOKEN" else None

    def get_recipient_display_label(self, obj):
        from .account_invitations import safe_account_display_label
        return safe_account_display_label(obj.recipient_user) if obj.recipient_user_id else "Tài khoản chưa đăng ký"

    def get_recipient_username(self, obj):
        from .account_invitations import safe_account_username
        return safe_account_username(obj.recipient_user) if obj.recipient_user_id else None

    def get_recipient_masked_email(self, obj):
        from .account_invitations import masked_account_email
        return masked_account_email(obj.recipient_user) if obj.recipient_user_id and not self.get_recipient_username(obj) else None


class ProfileInvitationCreateSerializer(StrictInputSerializer):
    recipient_user_id = serializers.UUIDField()
    requested_role = serializers.ChoiceField(
        choices=ProfileInvitation.Role.choices,
        default=ProfileInvitation.Role.MEMBER,
    )


class ProfileInvitationActionSerializer(StrictInputSerializer):
    """Manager lifecycle actions have no client-controlled fields."""

    pass


class ProfileInvitationCandidateQuerySerializer(StrictInputSerializer):
    search = serializers.CharField(required=False, allow_blank=True, max_length=100, trim_whitespace=True)
    page = serializers.IntegerField(required=False, min_value=1)

    def to_internal_value(self, data):
        value = data.get("search") if isinstance(data, Mapping) else None
        if isinstance(value, str):
            try:
                self.validate_search(value)
            except serializers.ValidationError as error:
                raise serializers.ValidationError({"search": error.detail}) from None
        return super().to_internal_value(data)

    def validate_search(self, value):
        if "\ufffd" in value or any(ord(c) < 32 or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF for c in value):
            raise serializers.ValidationError("Search must contain valid text without control characters.")
        return value


class ProfileInvitationRecipientSerializer(serializers.ModelSerializer):
    profile_id = serializers.UUIDField(read_only=True)
    profile_name = serializers.CharField(source="profile.name", read_only=True)
    inviter_display_label = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    can_accept = serializers.SerializerMethodField()
    can_decline = serializers.SerializerMethodField()
    can_open_profile = serializers.SerializerMethodField()

    class Meta:
        model = ProfileInvitation
        fields = ("id", "profile_id", "profile_name", "inviter_display_label", "requested_role",
                  "status", "expires_at", "can_accept", "can_decline", "can_open_profile")
        read_only_fields = fields

    def get_inviter_display_label(self, obj):
        from .account_invitations import safe_account_display_label
        return safe_account_display_label(obj.invited_by_membership.user)

    def get_status(self, obj):
        return obj.effective_status

    def _capabilities(self, obj):
        from .account_invitations import recipient_invitation_capabilities
        # A per-serializer-instance cache shares the live projection between its
        # three fields; no permission result survives a request or mutation.
        key = str(obj.pk)
        cache = getattr(self, "_invitation_capabilities", None)
        if cache is None:
            cache = self._invitation_capabilities = {}
        if key not in cache:
            request = self.context["request"]
            rows = getattr(request, "_invitation_current_memberships", None)
            if rows is None:
                rows = {}
                for membership in ProfileMembership.objects.filter(user_id=request.user.pk).values("profile_id", "role", "is_active"):
                    rows.setdefault(str(membership["profile_id"]), []).append(membership)
                request._invitation_current_memberships = rows
            cache[key] = recipient_invitation_capabilities(obj, request.user, rows)
        return cache[key]

    def get_can_accept(self, obj):
        return self._capabilities(obj)["can_accept"]

    def get_can_decline(self, obj):
        return self._capabilities(obj)["can_decline"]

    def get_can_open_profile(self, obj):
        return self._capabilities(obj)["can_open_profile"]


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
    capabilities = serializers.SerializerMethodField()

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
            "capabilities",
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


    def get_capabilities(self, membership):
        management = self.context.get("workspace_member_capabilities", {})
        allowed_roles = management.get("allowed_roles", [])
        mutable = bool(
            management.get("can_add", False)
            and membership.is_active
            and membership.role in allowed_roles
        )
        profile_role = getattr(membership, "_target_profile_role", None)
        if profile_role is None:
            # Individual POST/PATCH responses are not annotated roster rows.
            # Their new write hints fail closed without a verified context;
            # still accurately explain the target's inherited authority.
            profile_role = ProfileMembership.objects.filter(
                id=getattr(membership, "profile_membership_id", None),
                profile_id=membership.workspace.profile_id,
                user_id=membership.user_id,
                user__is_active=True,
                is_active=True,
            ).values_list("role", flat=True).first()
        return {
            "can_update": mutable,
            "can_revoke": mutable,
            "allowed_roles": list(allowed_roles) if mutable else [],
            "has_inherited_access": profile_role in (
                ProfileMembership.Role.OWNER,
                ProfileMembership.Role.ADMIN,
            ),
        }


class WorkspaceMemberCandidateReadSerializer(serializers.ModelSerializer):
    """Selection identity uses ProfileMembership, never a global User ID."""

    profile_membership_id = serializers.UUIDField(source="id", read_only=True)
    profile_role = serializers.CharField(source="role", read_only=True)
    display_label = serializers.SerializerMethodField()
    has_inherited_access = serializers.SerializerMethodField()

    class Meta:
        model = ProfileMembership
        fields = (
            "profile_membership_id", "display_label", "profile_role",
            "has_inherited_access",
        )
        read_only_fields = fields

    def get_display_label(self, membership):
        return membership.user.get_full_name().strip() or f"Thành viên {str(membership.pk)[:8]}"

    def get_has_inherited_access(self, membership):
        return membership.role in (
            ProfileMembership.Role.OWNER,
            ProfileMembership.Role.ADMIN,
        )


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
