from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom admin for User model with role & agency support"""

    ordering = ["id"]
    list_display = ["username", "email", "role", "agency", "is_active", "is_staff"]
    list_filter = ["role", "agency", "is_active", "is_staff"]
    search_fields = ["username", "email"]

    fieldsets = (
        (None, {"fields": ("username", "email", "password")}),
        (_("Personal Info"), {"fields": ("first_name", "last_name")}),
        (_("Agency Info"), {"fields": ("role", "agency")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important Dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "role", "agency", "password1", "password2"),
            },
        ),
    )
