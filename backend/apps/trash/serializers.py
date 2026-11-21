from rest_framework import serializers

from apps.workspace.serializers import StrictInputSerializer


class EmptyActionSerializer(StrictInputSerializer):
    pass


class PurgeSerializer(StrictInputSerializer):
    confirm = serializers.BooleanField()
    confirmation_name = serializers.CharField(max_length=255, required=False, trim_whitespace=False)

    def to_internal_value(self, data):
        if isinstance(data, dict) and data.get("confirm") is not True:
            raise serializers.ValidationError({"confirm": ["Xác nhận phải là true."]})
        return super().to_internal_value(data)


class TrashQuerySerializer(StrictInputSerializer):
    object_type = serializers.ChoiceField(choices=("TASK", "WORKSPACE", "PROFILE"), required=False)
    search = serializers.CharField(max_length=100, required=False, allow_blank=True)
    page = serializers.IntegerField(min_value=1, required=False)
    profile_id = serializers.UUIDField(required=False)

    def validate_search(self, value):
        if "\ufffd" in value or any(ord(char) < 32 or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise serializers.ValidationError("Nhập nội dung tìm kiếm hợp lệ.")
        return value

    def to_internal_value(self, data):
        if hasattr(data, "getlist") and any(len(data.getlist(key)) != 1 for key in data):
            raise serializers.ValidationError({"non_field_errors": ["Tham số truy vấn không được lặp."]})
        if "search" in data:
            value = data["search"]
            if not isinstance(value, str) or "\ufffd" in value or any(ord(char) < 32 or 127 <= ord(char) <= 159 or 0xD800 <= ord(char) <= 0xDFFF for char in value):
                raise serializers.ValidationError({"search": ["Nhập nội dung tìm kiếm hợp lệ."]})
        return super().to_internal_value(data)
