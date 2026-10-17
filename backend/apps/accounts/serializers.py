from django.contrib.auth import authenticate, get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.views.decorators.debug import sensitive_variables
from rest_framework import serializers


User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Public representation of the authenticated user."""

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "created_at",
        )
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        max_length=128,
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )
    password_confirm = serializers.CharField(
        max_length=128,
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = (
            "email",
            "username",
            "first_name",
            "last_name",
            "password",
            "password_confirm",
        )

    def validate_email(self, value):
        email = value.strip().casefold()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(
                "A user with this email address already exists."
            )
        return email

    def validate_username(self, value):
        username = value.strip()
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError(
                "A user with this username already exists."
            )
        return username

    @sensitive_variables("attrs")
    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "The two password fields did not match."}
            )

        candidate = User(
            email=attrs["email"],
            username=attrs["username"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            password_validation.validate_password(
                attrs["password"],
                user=candidate,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {"password": list(exc.messages)}
            ) from exc

        return attrs

    @sensitive_variables("validated_data", "password")
    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("password_confirm")

        try:
            with transaction.atomic():
                return User.objects.create_user(
                    password=password,
                    **validated_data,
                )
        except IntegrityError as exc:
            # Close the validation/write race without exposing which unique
            # identifier won it.
            raise serializers.ValidationError(
                {"detail": "An account with these details already exists."}
            ) from exc


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(
        max_length=128,
        write_only=True,
        trim_whitespace=False,
        style={"input_type": "password"},
    )

    default_error_messages = {
        "invalid_credentials": "Invalid email or password.",
    }

    @sensitive_variables("attrs")
    def validate(self, attrs):
        email = attrs["email"].strip()
        matching_emails = list(
            User.objects.filter(email__iexact=email)
            .values_list("email", flat=True)[:2]
        )
        authentication_email = (
            matching_emails[0] if len(matching_emails) == 1 else email
        )

        user = authenticate(
            request=self.context.get("request"),
            username=authentication_email,
            password=attrs["password"],
        )
        if len(matching_emails) != 1 or user is None:
            raise serializers.ValidationError(
                {"detail": self.error_messages["invalid_credentials"]},
                code="authorization",
            )

        attrs["user"] = user
        return attrs
