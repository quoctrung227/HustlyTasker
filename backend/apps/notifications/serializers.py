from django.urls import reverse
from rest_framework import serializers

from apps.workspace.serializers import StrictInputSerializer

from .content import EVENT_CONTENT
from .models import Notification


class NotificationReadSerializer(serializers.ModelSerializer):
    profile_id = serializers.UUIDField(read_only=True)
    workspace_id = serializers.UUIDField(read_only=True)
    task_id = serializers.UUIDField(read_only=True)
    title = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()
    target_url = serializers.SerializerMethodField()
    target_type = serializers.SerializerMethodField()
    invitation_id = serializers.UUIDField(read_only=True, allow_null=True)
    invitation = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = ("id", "event_type", "profile_id", "workspace_id", "task_id",
                  "title", "message", "target_url", "is_read", "created_at", "updated_at",
                  "target_type", "invitation_id", "invitation")
        read_only_fields = fields

    def get_title(self, notification):
        return EVENT_CONTENT[notification.event_type][0]

    def get_message(self, notification):
        return EVENT_CONTENT[notification.event_type][1]

    def get_target_url(self, notification):
        if notification.event_type == Notification.EventType.PROFILE_INVITED:
            return reverse("workspace:profile-invitation-recipient-detail", kwargs={
                "invitation_id": notification.invitation_id,
            })
        return reverse("tasks:task-detail", kwargs={
            "profile_id": notification.profile_id,
            "workspace_id": notification.workspace_id,
            "task_id": notification.task_id,
        })

    def get_target_type(self, notification):
        return ("PROFILE_INVITATION" if notification.event_type == Notification.EventType.PROFILE_INVITED
                else "TASK")

    def get_invitation(self, notification):
        if notification.event_type != Notification.EventType.PROFILE_INVITED:
            return None
        # Import at serialization time; workspace mutations explicitly call the
        # notification service after their own persisted audit event.
        from apps.workspace.serializers import ProfileInvitationRecipientSerializer
        return ProfileInvitationRecipientSerializer(notification.invitation, context=self.context).data


class NotificationQuerySerializer(StrictInputSerializer):
    is_read = serializers.BooleanField(required=False)


class NotificationReadActionSerializer(StrictInputSerializer):
    pass
