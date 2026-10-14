from django.urls import path

from . import views

urlpatterns = [
    path('preferences/', views.preferences, name='notifications-preferences'),
    path('delivery-log/', views.delivery_log, name='notifications-delivery-log'),
    path('test-email/', views.send_test_email, name='notifications-test-email'),
]
