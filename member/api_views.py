from rest_framework import permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from utils.api import TenantScopedAPIMixin
from utils.permissions import IsMember, IsMemberOrAgent

from .models import Flight, Hotel, Package, Transport
from .serializers import FlightSerializer, HotelSerializer, PackageSerializer, TransportSerializer


class HotelViewSet(TenantScopedAPIMixin, viewsets.ModelViewSet):
    """
    Agency hotels. Browser forms use session auth + CSRF; API clients may use JWT.
    """

    serializer_class = HotelSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsMemberOrAgent()]
        return [IsMember()]

    def get_queryset(self):
        user = self.request.user
        aid = getattr(user, "agency_id", None)
        if not aid:
            return Hotel.objects.none()
        if user.role in ("member", "agent"):
            return Hotel.objects.filter(agency_id=aid)
        return Hotel.objects.none()

    def create(self, request, *args, **kwargs):
        if not request.user.agency_id:
            return Response(
                {"detail": "User is not associated with an agency."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            agency_id=self.request.user.agency_id,
            created_by=self.request.user,
        )


class FlightViewSet(TenantScopedAPIMixin, viewsets.ModelViewSet):
    """Agency flights — session + CSRF for HTMX, JWT for API clients."""

    serializer_class = FlightSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsMemberOrAgent()]
        return [IsMember()]

    def get_queryset(self):
        user = self.request.user
        aid = getattr(user, "agency_id", None)
        if not aid:
            return Flight.objects.none()
        if user.role in ("member", "agent"):
            return Flight.objects.filter(agency_id=aid)
        return Flight.objects.none()

    def create(self, request, *args, **kwargs):
        if not request.user.agency_id:
            return Response(
                {"detail": "User is not associated with an agency."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            agency_id=self.request.user.agency_id,
            created_by=self.request.user,
        )


class TransportViewSet(TenantScopedAPIMixin, viewsets.ModelViewSet):
    """Agency transports — session + CSRF for HTMX, JWT for API clients."""

    serializer_class = TransportSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsMemberOrAgent()]
        return [IsMember()]

    def get_queryset(self):
        user = self.request.user
        aid = getattr(user, "agency_id", None)
        if not aid:
            return Transport.objects.none()
        if user.role in ("member", "agent"):
            return Transport.objects.filter(agency_id=aid)
        return Transport.objects.none()

    def create(self, request, *args, **kwargs):
        if not request.user.agency_id:
            return Response(
                {"detail": "User is not associated with an agency."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            agency_id=self.request.user.agency_id,
            created_by=self.request.user,
        )


class PackageViewSet(TenantScopedAPIMixin, viewsets.ModelViewSet):
    """Agency packages — agents can read (to quote), members manage."""

    serializer_class = PackageSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsMemberOrAgent()]
        return [IsMember()]

    def get_queryset(self):
        aid = getattr(self.request.user, "agency_id", None)
        if not aid:
            return Package.objects.none()
        return Package.objects.filter(agency_id=aid).select_related("makkah_hotel", "madina_hotel", "flight", "return_flight", "transport")

    def create(self, request, *args, **kwargs):
        if not request.user.agency_id:
            return Response(
                {"detail": "User is not associated with an agency."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            agency_id=self.request.user.agency_id,
            created_by=self.request.user,
        )
