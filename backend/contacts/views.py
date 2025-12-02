from rest_framework import viewsets, permissions
from .models import ContactInstruction
from .serializers import ContactInstructionSerializer

class ContactPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == "developer":
            return True
        if request.user.role == "member":
            return obj.agency == request.user.agency
        if request.user.role == "agent" and request.method in permissions.SAFE_METHODS:
            return obj.agency == request.user.agency
        return False

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.role == "agent" and request.method not in permissions.SAFE_METHODS:
            return False
        return True


class ContactInstructionViewSet(viewsets.ModelViewSet):
    serializer_class = ContactInstructionSerializer
    permission_classes = [ContactPermission]

    def get_queryset(self):
        user = self.request.user
        if user.role == "developer":
            return ContactInstruction.objects.all()
        return ContactInstruction.objects.filter(agency=user.agency)

    def perform_create(self, serializer):
        serializer.save(agency=self.request.user.agency, created_by=self.request.user)
