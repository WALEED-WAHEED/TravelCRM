from django.urls import path

from . import views

urlpatterns = [
    path('member/reports/', views.reports_home, name='reports-home'),
    path('member/reports/revenue/', views.revenue_report, name='reports-revenue'),
    path('member/reports/bookings/', views.bookings_report, name='reports-bookings'),
    path('member/reports/ledger-summary/', views.ledger_summary_report, name='reports-ledger-summary'),
]
