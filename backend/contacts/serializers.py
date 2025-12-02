from rest_framework import serializers
from .models import ContactInstruction

class ContactInstructionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactInstruction
        fields = "__all__"
        read_only_fields = ["agency", "created_by"]
