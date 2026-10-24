from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    model = User

    readonly_fields = (
        "created_at",
        "updated_at",
        "email_verified_at",
        "verified_email_normalized",
    )

    list_display = (
        "email",
        "username",
        "email_is_verified",
        "is_staff",
        "is_active",
    )

    ordering = (
        "email",
    )

    fieldsets = (
        (None, {
            "fields": (
                "email",
                "username",
                "password",
            )
        }),

        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),

        ("Account security", {
            "fields": (
                "email_verified_at",
                "verified_email_normalized",
            )
        }),

        ("Important dates", {
            "fields": (
                "last_login",
                "date_joined",
                "created_at",
                "updated_at",
            )
        }),
    )


    add_fieldsets = (
        (None, {
            "classes": (
                "wide",
            ),

            "fields": (
                "email",
                "username",
                "password1",
                "password2",
            ),
        }),
    )

    @admin.display(boolean=True, description="Email verified")
    def email_is_verified(self, obj):
        return obj.is_email_verified
