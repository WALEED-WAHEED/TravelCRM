from django.urls import path

from . import views

urlpatterns = [
    path("agent/dashboard/", views.dashboard, name="agent-dashboard"),
    path("agent/bookings/", views.bookings, name="agent-bookings"),      # now redirects to My Vouchers
    path("agent/vouchers/", views.vouchers, name="agent-vouchers"),
    path("agent/vouchers/new/", views.voucher_new, name="agent-voucher-new"),
    path("agent/vouchers/save/", views.voucher_save, name="agent-voucher-save"),
    path("agent/vouchers/<int:booking_id>/edit/", views.voucher_edit, name="agent-voucher-edit"),
    path("agent/vouchers/<int:booking_id>/view/", views.voucher_print, name="agent-voucher-print"),
    path("agent/vouchers/<int:booking_id>/voucher.pdf", views.voucher_pdf, name="agent-voucher-pdf"),
    path("agent/vouchers/<int:booking_id>/delete/", views.voucher_delete, name="agent-voucher-delete"),
]
