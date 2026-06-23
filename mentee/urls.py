from django.urls import path
from . import views

urlpatterns = [
    path('mentors/', views.MentorListView.as_view(), name='list-mentors'),
    path('mentors/<int:mentor_id>/', views.MentorDetailView.as_view(), name='mentor-detail'),
    path('book/', views.BookMentorView.as_view(), name='book-mentor'),
    path('bookings/', views.MyBookingsView.as_view(), name='my-bookings'),
    path('ongoing-sessions/', views.MenteeOngoingSessionsView.as_view(), name='mentee-ongoing-sessions'),
    path('completed-sessions/', views.MenteeCompletedSessionsView.as_view(), name='mentee-completed-sessions'),
]