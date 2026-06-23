from django.urls import path
from . import views

urlpatterns = [
    path('pay/', views.create_payment, name='create-payment'),
    path('status/<int:booking_id>/', views.check_payment_status, name='payment-status'),
    path('webhook/', views.midtrans_notification, name='midtrans-webhook'),
    path('earnings/', views.mentor_earnings, name='mentor-earnings'),
    path('withdraw/', views.request_withdrawal, name='request-withdrawal'),
    path('withdraw/history/', views.WithdrawalHistoryView.as_view(), name='withdrawal-history'),
    path('simulate-success/', views.simulate_payment_success, name='simulate-success'),
]