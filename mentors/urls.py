from django.urls import path
from . import views

urlpatterns = [
    path('profile/', views.MentorProfileView.as_view(), name='mentor-profile'),
    path('available-slots/', views.MentorAvailableSlotsView.as_view(), name='mentor-available-slots'),
    path('available-slots/<str:slot_id>/', views.MentorDeleteSlotView.as_view(), name='mentor-delete-slot'),
    path('booking-requests/', views.MentorBookingRequestsView.as_view(), name='mentor-booking-requests'),
    path('respond-booking/', views.MentorRespondBookingView.as_view(), name='mentor-respond-booking'),
    path('active-sessions/', views.MentorActiveSessionsView.as_view(), name='mentor-active-sessions'),
    path('start-session/', views.MentorStartSessionView.as_view(), name='mentor-start-session'),
    path('complete-session/', views.MentorCompleteSessionView.as_view(), name='mentor-complete-session'),
    path('reviews/', views.MentorReviewsView.as_view(), name='mentor-reviews'),
    path('income/', views.MentorIncomeView.as_view(), name='mentor-income'),
    path('withdraw/', views.MentorWithdrawView.as_view(), name='mentor-withdraw'),
]