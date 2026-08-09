from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    model = User

    list_display = (
        "email",
        "username",
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