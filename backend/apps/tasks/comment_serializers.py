from rest_framework import serializers

from apps.workspace.models import ProfileMembership
from apps.workspace.serializers import StrictInputSerializer

from .models import TaskComment


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

    class Meta:
        model = TaskComment
        fields = ("id", "task_id", "author_profile_membership_id", "content",
                  "is_deleted", "edited_at", "deleted_at", "created_at", "updated_at")
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
