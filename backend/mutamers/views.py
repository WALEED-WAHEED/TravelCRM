from rest_framework import viewsets, permissions
from .models import Mutamer
from .serializers import MutamerListSerializer, MutamerDetailSerializer, MutamerCreateSerializer, MutamerUpdateSerializer

class IsDeveloperOrAgency(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == "developer":
            return True
        if request.user.role == "member":
            return obj.agency == request.user.agency
        if request.user.role == "agent":
            return obj.agent == request.user
        return False

    def has_permission(self, request, view):
        return request.user.is_authenticated


class MutamerViewSet(viewsets.ModelViewSet):
    permission_classes = [IsDeveloperOrAgency]

    def get_serializer_class(self):
        if self.action == 'list':
            return MutamerListSerializer
        elif self.action in ['create']:
            return MutamerCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return MutamerUpdateSerializer
        else:
            return MutamerDetailSerializer

    def get_queryset(self):
        user = self.request.user
        if user.role == "developer":
            return Mutamer.objects.all()
        elif user.role == "member":
            return Mutamer.objects.filter(agency=user.agency)
        elif user.role == "agent":
            return Mutamer.objects.filter(agent=user)
        return Mutamer.objects.none()

    def perform_create(self, serializer):
        serializer.save(agency=self.request.user.agency, agent=self.request.user)
