from django.urls import path
from . import views

urlpatterns = [
    # Agent
    path("agent/dashboard/", views.dashboard, name="agent-dashboard"),
    path("agent/bookings/", views.bookings, name="agent-bookings"),
    path("agent/vouchers/", views.vouchers, name="agent-vouchers"),
    path("agent/mutamers/", views.mutamers, name="agent-mutamers"),
]
