from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Sum, Q
from utils.permissions import IsDeveloper, IsMember, IsAgent
from accounts.models import User
from agencies.models import Agency
from bookings.models import Booking
from vouchers.models import Voucher
from ledger.models import LedgerEntry
from mutamers.models import Mutamer


class DeveloperDashboardView(APIView):
    """Dashboard for Developer role"""
    permission_classes = [IsAuthenticated, IsDeveloper]

    def get(self, request):
        total_agencies = Agency.objects.count()
        total_users = User.objects.count()
        active_sessions = User.objects.filter(is_active=True).count()
        
        return Response({
            "total_agencies": total_agencies,
            "total_users": total_users,
            "active_sessions": active_sessions,
            "system_health": 99.9,
            "agencies_change": "+5 from last month",
            "users_change": "+20 from last month",
            "sessions_change": "+10% from last hour"
        })


class MemberDashboardView(APIView):
    """Dashboard for Member role"""
    permission_classes = [IsAuthenticated, IsMember]

    def get(self, request):
        agency = request.user.agency
        
        if not agency:
            return Response({"detail": "No agency assigned"}, status=400)
        
        pending_vouchers = Voucher.objects.filter(
            agent__agency=agency, 
            status='pending'
        ).count()
        
        monthly_revenue = LedgerEntry.objects.filter(
            agency=agency, 
            transaction_type='income'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        active_agents = User.objects.filter(
            agency=agency, 
            role='agent', 
            is_active=True
        ).count()
        
        total_mutamers = Mutamer.objects.filter(agency=agency).count()

        return Response({
            "pending_vouchers": pending_vouchers,
            "monthly_revenue": float(monthly_revenue),
            "active_agents": active_agents,
            "total_mutamers": total_mutamers,
            "pending_vouchers_change": "+3 from last week",
            "revenue_change": "+12% from last month",
            "agents_change": "+2 from last month",
            "mutamers_change": "+15 from last month"
        })


class AgentDashboardView(APIView):
    """Dashboard for Agent role"""
    permission_classes = [IsAuthenticated, IsAgent]

    def get(self, request):
        my_bookings = Booking.objects.filter(agent=request.user).count()
        my_vouchers = Voucher.objects.filter(agent=request.user).count()
        
        commission_earned = LedgerEntry.objects.filter(
            created_by=request.user,
            transaction_type='commission'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        active_customers = Mutamer.objects.filter(
            agent=request.user,
            is_active=True
        ).count()

        return Response({
            "my_bookings": my_bookings,
            "my_vouchers": my_vouchers,
            "commission_earned": float(commission_earned),
            "active_customers": active_customers,
            "bookings_change": "+5 this week",
            "vouchers_change": "+3 this week",
            "commission_change": "+15% from last month"
        })
