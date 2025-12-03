from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count
import pandas as pd
from django.http import HttpResponse
from .models import AttendanceLog
from .serializers import AttendanceLogSerializer

class IsDeveloperOrAgency(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == "developer":
            return True
        if request.user.role == "member":
            return obj.agency == request.user.agency
        if request.user.role == "agent":
            return obj.user == request.user
        return False

    def has_permission(self, request, view):
        return request.user.is_authenticated


class AttendanceLogViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceLogSerializer
    permission_classes = [IsDeveloperOrAgency]

    def get_queryset(self):
        user = self.request.user
        if user.role == "developer":
            return AttendanceLog.objects.all()
        elif user.role == "member":
            return AttendanceLog.objects.filter(agency=user.agency)
        elif user.role == "agent":
            return AttendanceLog.objects.filter(user=user)
        return AttendanceLog.objects.none()

    def perform_create(self, serializer):
        if self.request.user.role == "agent":
            serializer.save(agency=self.request.user.agency, user=self.request.user)
        else:
            # For members/developers, they might be creating attendance for other users
            serializer.save(agency=self.request.user.agency)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Return attendance summary stats"""
        qs = self.get_queryset()
        total_logs = qs.count()
        status_counts = qs.values("status").annotate(count=Count("id"))
        summary = {entry["status"]: entry["count"] for entry in status_counts}

        return Response({
            "total_logs": total_logs,
            "summary": summary
        })

    @action(detail=False, methods=["get"])
    def export(self, request):
        """Export attendance logs"""
        qs = self.get_queryset().values("user__username", "status", "check_in_time", "check_out_time", "location")
        df = pd.DataFrame(list(qs))

        export_type = request.GET.get("format", "csv")
        if export_type == "xlsx":
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = 'attachment; filename="attendance.xlsx"'
            df.to_excel(response, index=False)
            return response

        # Default CSV
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="attendance.csv"'
        df.to_csv(path_or_buf=response, index=False)
        return response
