from functools import cached_property

from rest_framework import serializers

from apps.workspace.access import can_manage_workspace_tasks
from apps.workspace.models import ProfileMembership
from apps.workspace.serializers import StrictInputSerializer

from .models import TaskComment
from .comment_services import can_comment_on_task


class CommentContentField(serializers.CharField):
    def to_internal_value(self, value):
        if not isinstance(value, str):
            self.fail("invalid")
        try:
            value.encode("utf-8", errors="strict")
        except UnicodeEncodeError:
            self.fail("invalid")
        if "\x00" in value:
            self.fail("invalid")
        return super().to_internal_value(value)


class CommentWriteSerializer(StrictInputSerializer):
    content = CommentContentField(max_length=TaskComment.CONTENT_MAX_LENGTH,
                                  allow_blank=False, trim_whitespace=True)


class CommentReadSerializer(serializers.ModelSerializer):
    task_id = serializers.UUIDField(read_only=True)
    author_profile_membership_id = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()
    is_deleted = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = TaskComment
        fields = ("id", "task_id", "author_profile_membership_id", "content",
                  "is_deleted", "can_edit", "can_delete", "edited_at", "deleted_at", "created_at", "updated_at")
        read_only_fields = fields

    def get_author_profile_membership_id(self, comment):
        if hasattr(comment, "_author_profile_membership_id"):
            membership_id = comment._author_profile_membership_id
        else:
            membership_id = ProfileMembership.objects.filter(
                profile_id=comment.task.workspace.profile_id, user_id=comment.user_id,
                user__is_active=True, is_active=True,
            ).order_by("joined_at", "id").values_list("id", flat=True).first()
        return str(membership_id) if membership_id is not None else None

    def get_content(self, comment):
        return None if comment.deleted_at is not None else comment.content

    def get_is_deleted(self, comment):
        return comment.deleted_at is not None

    @cached_property
    def _comment_allowed(self):
        context = self.context.get("workspace_access_context")
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if (
            context is None
            or not getattr(user, "is_authenticated", False)
            or not getattr(user, "is_active", False)
            or getattr(context, "user_id", None) != user.pk
        ):
            return False
        return can_comment_on_task(context)

    @cached_property
    def _moderation_allowed(self):
        return self._comment_allowed and can_manage_workspace_tasks(
            self.context["workspace_access_context"],
        )

    def _can_mutate(self, comment):
        context = self.context.get("workspace_access_context")
        return (
            context is not None
            and comment.task.workspace_id == getattr(context, "workspace_id", None)
            and comment.deleted_at is None
            and self._comment_allowed
        )

    def get_can_edit(self, comment):
        return bool(
            self._can_mutate(comment)
            and comment.user_id == self.context["workspace_access_context"].user_id
        )

    def get_can_delete(self, comment):
        # Tombstones offer no UI action even though repeat DELETE is idempotent.
        return bool(
            self._can_mutate(comment)
            and (
                comment.user_id == self.context["workspace_access_context"].user_id
                or self._moderation_allowed
            )
        )
