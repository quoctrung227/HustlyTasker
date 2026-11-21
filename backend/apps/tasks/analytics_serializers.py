import calendar
from datetime import date, datetime, time, timedelta, timezone as datetime_timezone
from zoneinfo import ZoneInfo

from django.utils import timezone
from rest_framework import serializers

from apps.workspace.serializers import StrictInputSerializer


ANALYTICS_TIMEZONE = ZoneInfo("Asia/Ho_Chi_Minh")
EMPLOYEE_ORDERINGS = (
    "active_tasks", "-active_tasks", "approved_tasks", "-approved_tasks",
    "approved_value", "-approved_value",
)


class AnalyticsQuerySerializer(StrictInputSerializer):
    workspace_id = serializers.UUIDField(required=False)
    search = serializers.CharField(required=False, max_length=100, allow_blank=True)
    ordering = serializers.ChoiceField(required=False, choices=EMPLOYEE_ORDERINGS, default="-active_tasks")

    def get_fields(self):
        fields = super().get_fields()
        fields["from"] = serializers.RegexField(r"^\d{4}-\d{2}-\d{2}$", required=False)
        fields["to"] = serializers.RegexField(r"^\d{4}-\d{2}-\d{2}$", required=False)
        return fields

    def validate(self, attrs):
        now = timezone.now().astimezone(ANALYTICS_TIMEZONE)
        default_start = now.date().replace(day=1)
        default_end = default_start.replace(day=calendar.monthrange(now.year, now.month)[1])
        dates = {}
        for key, default in (("from", default_start), ("to", default_end)):
            try:
                dates[key] = date.fromisoformat(attrs[key]) if key in attrs else default
            except (ValueError, TypeError):
                raise serializers.ValidationError({key: "Chọn ngày hợp lệ theo định dạng YYYY-MM-DD."}) from None
        if dates["to"] < dates["from"]:
            raise serializers.ValidationError({"to": "Ngày kết thúc phải từ ngày bắt đầu trở đi."})
        if (dates["to"] - dates["from"]).days >= 366:
            raise serializers.ValidationError({"to": "Mỗi truy vấn hỗ trợ tối đa 366 ngày."})
        try:
            start = datetime.combine(dates["from"], time.min, ANALYTICS_TIMEZONE)
            end = datetime.combine(dates["to"] + timedelta(days=1), time.min, ANALYTICS_TIMEZONE)
            attrs["start_at"] = start.astimezone(datetime_timezone.utc)
            attrs["end_before"] = end.astimezone(datetime_timezone.utc)
        except (OverflowError, ValueError):
            raise serializers.ValidationError({"to": "Khoảng ngày nằm ngoài phạm vi hỗ trợ."}) from None
        attrs["from"] = dates["from"]
        attrs["to"] = dates["to"]
        return attrs
