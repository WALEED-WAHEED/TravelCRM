from django.urls import path

from . import views

urlpatterns = [
    path('member/bookings/<int:booking_id>/collect-payment/', views.collect_payment, name='payments-collect'),
    path('member/bookings/<int:booking_id>/payment-plan/', views.payment_plan, name='payments-plan'),
]
