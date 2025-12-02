from django.contrib import admin
from .models import Agency


@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "created_at", "updated_at")
    search_fields = ("name", "contact_email")
