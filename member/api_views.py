from rest_framework import permissions, status, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response

from utils.permissions import IsMember, IsMemberOrAgent

from .models import Flight, Hotel, Mutamer, Transport
from .serializers import FlightSerializer, HotelSerializer, MutamerSerializer, TransportSerializer


class HotelViewSet(viewsets.ModelViewSet):
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


class FlightViewSet(viewsets.ModelViewSet):
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


class TransportViewSet(viewsets.ModelViewSet):
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


class MutamerViewSet(viewsets.ModelViewSet):
    """Agency mutamers — session + CSRF for HTMX, JWT for API clients."""

    serializer_class = MutamerSerializer
    authentication_classes = [SessionAuthentication, JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        # Members and agents both manage pilgrims for their agency.
        return [IsMemberOrAgent()]

    def get_queryset(self):
        user = self.request.user
        aid = getattr(user, "agency_id", None)
        if not aid:
            return Mutamer.objects.none()
        if user.role in ("member", "agent"):
            qs = Mutamer.objects.filter(agency_id=aid)
            family_id = (self.request.query_params.get("family_id") or "").strip()
            if family_id:
                qs = qs.filter(family_id=family_id)
            return qs
        return Mutamer.objects.none()

    def create(self, request, *args, **kwargs):
        if not request.user.agency_id:
            return Response(
                {"detail": "User is not associated with an agency."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save(
            agent=self.request.user,
            agency_id=self.request.user.agency_id,
        )
