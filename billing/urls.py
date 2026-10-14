from django.urls import path

from . import views

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('member/billing/', views.billing_home, name='member-billing'),
    path('member/billing/subscribe/<int:plan_id>/', views.submit_payment, name='member-billing-subscribe'),
]
