from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Sum
from .models import LedgerEntry
from .serializers import LedgerEntrySerializer
import pandas as pd
from django.http import HttpResponse

class IsDeveloperOrMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == "developer":
            return True
        if request.user.role == "member":
            return obj.agency == request.user.agency
        return False

    def has_permission(self, request, view):
        return request.user.is_authenticated


class LedgerEntryViewSet(viewsets.ModelViewSet):
    serializer_class = LedgerEntrySerializer
    permission_classes = [IsDeveloperOrMember]

    def get_queryset(self):
        user = self.request.user
        if user.role == "developer":
            return LedgerEntry.objects.all()
        elif user.role == "member":
            return LedgerEntry.objects.filter(agency=user.agency)
        return LedgerEntry.objects.none()

    def perform_create(self, serializer):
        serializer.save(agency=self.request.user.agency, created_by=self.request.user)

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Monthly summary of income vs expenses"""
        user = request.user
        qs = self.get_queryset()

        # Filter by year and month if provided
        year = request.query_params.get('year')
        month = request.query_params.get('month')
        
        if year and month:
            from datetime import datetime
            try:
                # Create start and end dates for the month
                start_date = datetime(int(year), int(month), 1)
                if int(month) == 12:
                    end_date = datetime(int(year) + 1, 1, 1)
                else:
                    end_date = datetime(int(year), int(month) + 1, 1)
                
                qs = qs.filter(date__gte=start_date.date(), date__lt=end_date.date())
            except (ValueError, TypeError):
                pass  # Invalid year/month, use all data

        income = qs.filter(entry_type="income").aggregate(total=Sum("amount"))["total"] or 0
        expense = qs.filter(entry_type="expense").aggregate(total=Sum("amount"))["total"] or 0
        supplier = qs.filter(entry_type="supplier_payment").aggregate(total=Sum("amount"))["total"] or 0
        net = income - (expense + supplier)

        return Response({
            "income": str(income),
            "expense": str(expense),
            "supplier_payments": str(supplier),
            "net": str(net)
        })

    @action(detail=False, methods=["get"])
    def export(self, request):
        """Export ledger entries to CSV/XLSX"""
        qs = self.get_queryset().values(
            "entry_type", "description", "amount", "date", "created_by__username"
        )
        df = pd.DataFrame(list(qs))

        export_type = request.GET.get("format", "csv")
        if export_type == "xlsx":
            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            response["Content-Disposition"] = 'attachment; filename="ledger.xlsx"'
            df.to_excel(response, index=False)
            return response

        # Default CSV
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="ledger.csv"'
        df.to_csv(path_or_buf=response, index=False)
        return response
