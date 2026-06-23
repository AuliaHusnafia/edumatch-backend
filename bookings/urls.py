from django.urls import path
from . import views

urlpatterns = [
    path('mentee/my-bookings/', views.mentee_my_bookings, name='mentee-my-bookings'),
    path('mentee/ongoing-sessions/', views.mentee_ongoing_sessions, name='mentee-ongoing-sessions'),
    path('mentee/completed-sessions/', views.mentee_completed_sessions, name='mentee-completed-sessions'),
]