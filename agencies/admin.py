from django.contrib import admin
from .models import Agency

@admin.register(Agency)
class AgencyAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'email', 'phone', 'is_active', 'created_at')
    search_fields = ('name', 'code', 'email')
    list_filter = ('is_active', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
