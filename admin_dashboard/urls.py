from django.urls import path
from drf_spectacular.utils import extend_schema
from .views import (
    AdminStatsView,
    PendingMentorsView,
    AllMentorsView,
    AllMenteesView,
    AllBookingsView,
    AllPaymentsView,
    WithdrawRequestsView,
    TransactionsView,
)


# Alias view tipis — fungsinya 100% sama dengan view asli (AllMentorsView/AllMenteesView),
# tujuannya HANYA supaya path lama (/all-mentors/, /all-mentees/) tetap berfungsi untuk
# frontend yang mungkin masih memanggilnya, TANPA membuat dokumentasi Swagger jadi dobel.
@extend_schema(exclude=True)
class AllMentorsAliasView(AllMentorsView):
    pass


@extend_schema(exclude=True)
class AllMenteesAliasView(AllMenteesView):
    pass


urlpatterns = [
    path('stats/', AdminStatsView.as_view(), name='admin-stats'),

    path('pending-mentors/', PendingMentorsView.as_view(), name='admin-pending-mentors'),

    # Mentor management — endpoint utama yang didokumentasikan di Swagger
    path('mentors/', AllMentorsView.as_view(), name='admin-mentors-list'),
    path('mentors/<int:user_id>/', AllMentorsView.as_view(), name='admin-mentors-detail'),
    # Alias lama untuk backward compatibility — disembunyikan dari Swagger (exclude=True)
    path('all-mentors/', AllMentorsAliasView.as_view(), name='admin-mentors-list-alias'),

    # Mentee management
    path('mentees/', AllMenteesView.as_view(), name='admin-mentees-list'),
    path('mentees/<int:user_id>/', AllMenteesView.as_view(), name='admin-mentees-detail'),
    # Alias lama
    path('all-mentees/', AllMenteesAliasView.as_view(), name='admin-mentees-list-alias'),

    path('bookings/', AllBookingsView.as_view(), name='admin-bookings'),
    path('payments/', AllPaymentsView.as_view(), name='admin-payments'),
    path('withdraw-requests/', WithdrawRequestsView.as_view(), name='admin-withdraw-requests'),
    path('transactions/', TransactionsView.as_view(), name='admin-transactions'),
]