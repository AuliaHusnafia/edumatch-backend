from django.urls import path
from .views import (
    AdminStatsView,
    PendingMentorsView,
    AllMentorsView,
    MentorDetailView,
    AllMenteesView,
    MenteeDetailView,
    AllBookingsView,
    AllPaymentsView,
    WithdrawRequestsView,
    TransactionsView,
    CurrentUserView,
)

urlpatterns = [
    path("stats/", AdminStatsView.as_view(), name="admin-stats"),
    path("me/", CurrentUserView.as_view(), name="admin-me"),
    path("pending-mentors/", PendingMentorsView.as_view(), name="admin-pending-mentors"),
    path("mentors/", AllMentorsView.as_view(), name="admin-mentors-list"),
    path("mentors/<int:user_id>/", MentorDetailView.as_view(), name="admin-mentors-detail"),
    path("all-mentors/", AllMentorsView.as_view(), name="admin-mentors-alias"),
    path("mentees/", AllMenteesView.as_view(), name="admin-mentees-list"),
    path("mentees/<int:user_id>/", MenteeDetailView.as_view(), name="admin-mentees-detail"),
    path("all-mentees/", AllMenteesView.as_view(), name="admin-mentees-alias"),
    path("bookings/", AllBookingsView.as_view(), name="admin-bookings"),
    path("payments/", AllPaymentsView.as_view(), name="admin-payments"),
    path("withdraw-requests/", WithdrawRequestsView.as_view(), name="admin-withdraw-requests"),
    path("transactions/", TransactionsView.as_view(), name="admin-transactions"),
]
