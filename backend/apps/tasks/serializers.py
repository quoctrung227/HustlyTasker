from rest_framework import serializers

from apps.reviews.models import Deliverable, Review
from apps.workspace.models import ProfileMembership
from apps.workspace.serializers import StrictInputSerializer

from .models import Task


def _profile_membership_id(*, profile_id, user_id):
    """Return only a current tenant identifier, never a stale historical ID."""

    return ProfileMembership.objects.filter(
        profile_id=profile_id,
        user_id=user_id,
        user__is_active=True,
        is_active=True,
    ).order_by("joined_at", "id").values_list("id", flat=True).first()


class TaskReadSerializer(serializers.ModelSerializer):
    workspace_id = serializers.UUIDField(read_only=True)
    active_assignment = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "id",
            "workspace_id",
            "title",
            "description",
            "status",
            "priority",
            "deadline",
            "active_assignment",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_active_assignment(self, task):
        assignments = getattr(task, "_active_assignments", None)
        if assignments is None:
            assignments = list(
                task.assignments.filter(is_active=True).order_by(
                    "-assigned_at",
                    "-id",
                )[:1]
            )

        if not assignments:
            return None

        assignment = assignments[0]
        return {
            "id": assignment.id,
            "profile_membership_id": _profile_membership_id(
                profile_id=task.workspace.profile_id,
                user_id=assignment.user_id,
            ),
            "assigned_at": assignment.assigned_at,
        }


class ReviewReadSerializer(serializers.ModelSerializer):
    reviewer_profile_membership_id = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = (
            "id",
            "status",
            "comment",
            "reviewer_profile_membership_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_reviewer_profile_membership_id(self, review):
        return _profile_membership_id(
            profile_id=review.deliverable.task.workspace.profile_id,
            user_id=review.reviewer_id,
        )


class DeliverableReadSerializer(serializers.ModelSerializer):
    task_id = serializers.UUIDField(read_only=True)
    uploaded_by_profile_membership_id = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()

    class Meta:
        model = Deliverable
        fields = (
            "id",
            "task_id",
            "revision",
            "file_url",
            "status",
            "uploaded_by_profile_membership_id",
            "review",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_uploaded_by_profile_membership_id(self, deliverable):
        return _profile_membership_id(
            profile_id=deliverable.task.workspace.profile_id,
            user_id=deliverable.uploaded_by_id,
        )

    def get_review(self, deliverable):
        reviews = getattr(deliverable, "_workflow_reviews", None)
        if reviews is None:
            review = deliverable.reviews.order_by("created_at", "id").first()
        else:
            review = reviews[0] if reviews else None

        if review is None:
            return None
        return ReviewReadSerializer(review).data


class TaskCreateSerializer(StrictInputSerializer):
    title = serializers.CharField(
        max_length=255,
        allow_blank=False,
        trim_whitespace=True,
    )
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
    )
    priority = serializers.ChoiceField(
        choices=Task.Priority.choices,
        required=False,
        default=Task.Priority.MEDIUM,
    )
    deadline = serializers.DateTimeField(required=False, allow_null=True)


class TaskUpdateSerializer(StrictInputSerializer):
    title = serializers.CharField(
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
    priority = serializers.ChoiceField(
        choices=Task.Priority.choices,
        required=False,
    )
    deadline = serializers.DateTimeField(required=False, allow_null=True)


class TaskAssignSerializer(StrictInputSerializer):
    target_profile_membership_id = serializers.UUIDField()


class EmptyTaskActionSerializer(StrictInputSerializer):
    pass


class DeliverableSubmitSerializer(StrictInputSerializer):
    file_url = serializers.CharField(
        max_length=500,
        allow_blank=False,
        trim_whitespace=True,
    )


class DeliverableApproveSerializer(StrictInputSerializer):
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
        allow_null=True,
        trim_whitespace=True,
    )


class DeliverableRequestChangesSerializer(StrictInputSerializer):
    comment = serializers.CharField(
        allow_blank=False,
        allow_null=False,
        trim_whitespace=True,
    )
