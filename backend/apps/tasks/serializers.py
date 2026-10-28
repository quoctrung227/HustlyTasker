from datetime import timezone as datetime_timezone
from functools import cached_property

from rest_framework import serializers

from apps.reviews.models import Deliverable, Review
from apps.workspace.access import can_execute_workspace_tasks, can_review_workspace_deliverables
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
    parent_id = serializers.UUIDField(read_only=True, allow_null=True)
    active_assignment = serializers.SerializerMethodField()
    can_start = serializers.SerializerMethodField()
    can_submit = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = (
            "id",
            "workspace_id",
            "parent_id",
            "title",
            "description",
            "status",
            "priority",
            "deadline",
            "active_assignment",
            "can_start",
            "can_submit",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def _active_assignments(self, task):
        assignments = getattr(task, "_active_assignments", None)
        if assignments is None:
            assignments = list(
                task.assignments.filter(is_active=True).order_by(
                    "-assigned_at",
                    "-id",
                )[:1]
            )
            # Detail and mutation responses use the same loaded assignment for
            # identity and capability fields; list responses already prefetch.
            task._active_assignments = assignments
        return assignments

    def get_active_assignment(self, task):
        assignments = self._active_assignments(task)

        if not assignments:
            return None

        assignment = assignments[0]
        membership_id = getattr(assignment, "_profile_membership_id", None)
        if not hasattr(assignment, "_profile_membership_id"):
            membership_id = _profile_membership_id(
                profile_id=task.workspace.profile_id,
                user_id=assignment.user_id,
            )
        return {
            "id": assignment.id,
            "profile_membership_id": membership_id,
            "assigned_at": assignment.assigned_at,
        }

    @cached_property
    def _execution_allowed(self):
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
        # Reuse the live role/lifecycle predicate once for a serialized page.
        # POST start still repeats authorization under its existing locks.
        return can_execute_workspace_tasks(context)

    def get_can_start(self, task):
        context = self.context.get("workspace_access_context")
        if (
            context is None
            or task.workspace_id != getattr(context, "workspace_id", None)
            or task.status != Task.Status.ASSIGNED
            or not self._execution_allowed
        ):
            return False
        assignments = self._active_assignments(task)
        return bool(assignments and assignments[0].user_id == context.user_id)

    def get_can_submit(self, task):
        context = self.context.get("workspace_access_context")
        if (
            context is None
            or task.workspace_id != getattr(context, "workspace_id", None)
            or task.status != Task.Status.WORKING
            or not self._execution_allowed
        ):
            return False
        assignments = self._active_assignments(task)
        if not assignments or assignments[0].user_id != context.user_id:
            return False
        unresolved = getattr(task, "_has_unresolved_deliverable", None)
        if unresolved is None:
            unresolved = task.deliverables.filter(
                status__in=(Deliverable.Status.PENDING, Deliverable.Status.SUBMITTED),
            ).exists()
        # A UI hint only: submission repeats every check under service locks.
        return not unresolved


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
        if hasattr(review, "_reviewer_profile_membership_id"):
            return review._reviewer_profile_membership_id
        return _profile_membership_id(
            profile_id=review.deliverable.task.workspace.profile_id,
            user_id=review.reviewer_id,
        )


class DeliverableReadSerializer(serializers.ModelSerializer):
    task_id = serializers.UUIDField(read_only=True)
    uploaded_by_profile_membership_id = serializers.SerializerMethodField()
    review = serializers.SerializerMethodField()
    can_approve = serializers.SerializerMethodField()
    can_request_changes = serializers.SerializerMethodField()

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
            "can_approve",
            "can_request_changes",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_uploaded_by_profile_membership_id(self, deliverable):
        if hasattr(deliverable, "_uploaded_by_profile_membership_id"):
            return deliverable._uploaded_by_profile_membership_id
        return _profile_membership_id(
            profile_id=deliverable.task.workspace.profile_id,
            user_id=deliverable.uploaded_by_id,
        )

    def _reviews(self, deliverable):
        reviews = getattr(deliverable, "_workflow_reviews", None)
        if reviews is None:
            review = deliverable.reviews.order_by("created_at", "id").first()
            reviews = [review] if review is not None else []
            deliverable._workflow_reviews = reviews
        return reviews

    def get_review(self, deliverable):
        reviews = self._reviews(deliverable)
        if not reviews:
            return None
        return ReviewReadSerializer(reviews[0], context=self.context).data

    @cached_property
    def _review_allowed(self):
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
        return can_review_workspace_deliverables(context)

    def _can_review(self, deliverable):
        context = self.context.get("workspace_access_context")
        if (
            context is None
            or deliverable.task.workspace_id != getattr(context, "workspace_id", None)
            or deliverable.task.status != Task.Status.REVIEW
            or deliverable.status != Deliverable.Status.SUBMITTED
            or deliverable.uploaded_by_id == context.user_id
            or not self._review_allowed
        ):
            return False
        latest_id = getattr(deliverable, "_latest_deliverable_id", None)
        if latest_id is None:
            latest_id = deliverable.task.deliverables.order_by(
                "-created_at", "-id",
            ).values_list("id", flat=True).first()
            deliverable._latest_deliverable_id = latest_id
        # Mirror the mutation service's chronological revision selection and
        # rejection of every existing Review, including legacy pending rows.
        return latest_id == deliverable.id and not self._reviews(deliverable)

    def get_can_approve(self, deliverable):
        return self._can_review(deliverable)

    def get_can_request_changes(self, deliverable):
        return self._can_review(deliverable)


class TaskDeadlineField(serializers.DateTimeField):
    """Normalize API instants and fail safely at datetime timezone boundaries."""

    default_error_messages = {
        "out_of_range": "Datetime is outside the supported range.",
    }

    def to_internal_value(self, value):
        try:
            parsed = super().to_internal_value(value)
            return parsed.astimezone(datetime_timezone.utc)
        except (OverflowError, ValueError):
            self.fail("out_of_range")


class TaskListQuerySerializer(StrictInputSerializer):
    status = serializers.ChoiceField(choices=Task.Status.choices, required=False)
    priority = serializers.ChoiceField(choices=Task.Priority.choices, required=False)
    parent_id = serializers.UUIDField(required=False)
    root_only = serializers.BooleanField(required=False)
    deadline_before = TaskDeadlineField(required=False)
    deadline_after = TaskDeadlineField(required=False)
    ordering = serializers.ChoiceField(
        choices=("created_at", "-created_at", "deadline", "-deadline", "priority", "-priority"),
        required=False,
        default="created_at",
    )
    def validate(self, data):
        if data.get("root_only") and "parent_id" in data:
            raise serializers.ValidationError({
                "parent_id": "Use either parent_id or root_only=true.",
            })
        if (
            "deadline_before" in data and "deadline_after" in data
            and data["deadline_after"] > data["deadline_before"]
        ):
            raise serializers.ValidationError({
                "deadline_after": "Must not be later than deadline_before.",
            })
        return data


class TaskCreateSerializer(StrictInputSerializer):
    parent_id = serializers.UUIDField(required=False, allow_null=True)
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
    deadline = TaskDeadlineField(required=False, allow_null=True)


class TaskUpdateSerializer(StrictInputSerializer):
    parent_id = serializers.UUIDField(required=False, allow_null=True)
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
    deadline = TaskDeadlineField(required=False, allow_null=True)


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
