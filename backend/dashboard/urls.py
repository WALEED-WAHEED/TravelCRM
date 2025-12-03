from django.urls import path
from .views import DeveloperDashboardView, MemberDashboardView, AgentDashboardView

urlpatterns = [
    path("developer/", DeveloperDashboardView.as_view(), name="developer_dashboard"),
    path("member/", MemberDashboardView.as_view(), name="member_dashboard"),
    path("agent/", AgentDashboardView.as_view(), name="agent_dashboard"),
]
