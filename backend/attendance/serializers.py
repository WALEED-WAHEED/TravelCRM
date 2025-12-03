from rest_framework import serializers
from .models import AttendanceLog

class AttendanceLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttendanceLog
        fields = "__all__"
        read_only_fields = ["agency", "user"]
