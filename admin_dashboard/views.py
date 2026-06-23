from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample

from users.models import User
from bookings.models import Booking
from mentors.models import MentorProfile
from payments.models import Payment, WithdrawalRequest
from .serializers import (
    AdminUserSerializer,
    AdminBookingSerializer,
    AdminPaymentSerializer,
    AdminTransactionSerializer,
    AdminWithdrawalSerializer,
)


class IsAdmin(IsAuthenticated):
    """Permission class — dipakai di semua view admin supaya tidak ulang-ulang cek role manual"""
    def has_permission(self, request, view):
        return super().has_permission(request, view) and request.user.role == 'admin'


@extend_schema(
    tags=['admin'],
    summary='Statistik ringkasan platform',
    description=(
        'Mengembalikan ringkasan angka penting untuk dashboard admin: total pengguna, '
        'mentor yang sudah/belum diverifikasi, total booking, sesi selesai/sudah dibayar, '
        'dan total komisi platform dari semua transaksi yang berhasil.'
    ),
)
class AdminStatsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        total_mentees = User.objects.filter(role='mentee').count()
        total_mentors = User.objects.filter(role='mentor', is_verified=True).count()
        pending_mentors = User.objects.filter(role='mentor', is_verified=False).count()
        total_users = User.objects.exclude(role='admin').count()
        total_bookings = Booking.objects.count()
        completed_sessions = Booking.objects.filter(status='completed').count()
        paid_sessions = Booking.objects.filter(status='paid').count()

        platform_commission = Payment.objects.filter(status='success').aggregate(
            total=Sum('platform_fee')
        )['total'] or 0

        data = {
            'total_mentees': total_mentees,
            'total_mentors': total_mentors,
            'pending_mentors': pending_mentors,
            'total_users': total_users,
            'total_bookings': total_bookings,
            'completed_sessions': completed_sessions,
            'paid_sessions': paid_sessions,
            'platform_commission': float(platform_commission),
        }
        return Response(data)


@extend_schema(tags=['admin'])
class PendingMentorsView(generics.ListAPIView):
    """
    GET: Daftar mentor yang mendaftar tapi belum diverifikasi admin (paginated, bisa di-search).

    POST: Setujui atau tolak pendaftaran mentor.
    Body: {"mentor_id": int, "action": "approve" | "reject"}
    - approve → mentor.is_verified jadi True, mentor bisa langsung mulai menerima booking
    - reject → akun mentor dihapus permanen dari sistem
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['university']
    search_fields = ['username', 'email']

    def get_queryset(self):
        return User.objects.filter(role='mentor', is_verified=False).order_by('-date_joined')

    @extend_schema(
        summary='Setujui atau tolak pendaftaran mentor',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'mentor_id': {'type': 'integer'},
                    'action': {'type': 'string', 'enum': ['approve', 'reject']},
                },
                'required': ['mentor_id', 'action'],
            }
        },
        examples=[
            OpenApiExample('Setujui mentor', value={'mentor_id': 5, 'action': 'approve'}),
            OpenApiExample('Tolak mentor', value={'mentor_id': 5, 'action': 'reject'}),
        ],
    )
    def post(self, request, user_id=None):
        mentor_id = request.data.get('mentor_id')
        action = request.data.get('action')

        try:
            mentor = User.objects.get(id=mentor_id, role='mentor')
            if action == 'approve':
                mentor.is_verified = True
                mentor.save()
                return Response({'message': f'Mentor {mentor.username} telah disetujui'})
            elif action == 'reject':
                mentor.delete()
                return Response({'message': f'Mentor {mentor.username} ditolak'})
        except User.DoesNotExist:
            return Response({'error': 'Mentor tidak ditemukan'}, status=404)

        return Response({'error': 'Action tidak valid'}, status=400)


@extend_schema(tags=['admin'])
class AllMentorsView(generics.ListAPIView):
    """
    GET: Daftar mentor yang sudah terverifikasi (paginated, bisa di-search & filter universitas).

    POST: Admin membuat akun mentor baru secara langsung (otomatis terverifikasi, skip alur approval).

    PUT /mentors/{user_id}/: Update data mentor (username, email, universitas, no. HP, password).

    DELETE /mentors/{user_id}/: Hapus akun mentor secara permanen.
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['university']
    search_fields = ['username', 'email']
    ordering_fields = ['username', 'date_joined']

    def get_queryset(self):
        return User.objects.filter(role='mentor', is_verified=True).order_by('-date_joined')

    @extend_schema(
        summary='Tambah mentor baru (langsung terverifikasi)',
        description='PENTING: gunakan endpoint ini TANPA ID di path (POST /mentors/). Mengirim POST ke /mentors/{id}/ akan ditolak dengan 405 — gunakan PUT untuk update data mentor yang sudah ada.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'email': {'type': 'string'},
                    'password': {'type': 'string', 'default': 'mentor123'},
                    'university': {'type': 'string'},
                    'phone': {'type': 'string'},
                },
                'required': ['username', 'email'],
            }
        },
    )
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password', 'mentor123')
        university = request.data.get('university', '')
        phone = request.data.get('phone', '')

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username sudah ada'}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email sudah terdaftar'}, status=400)

        from django.contrib.auth.hashers import make_password
        user = User.objects.create(
            username=username, email=email, password=make_password(password),
            role='mentor', university=university, phone=phone, is_verified=True
        )
        MentorProfile.objects.create(user=user)
        return Response({'message': 'Mentor berhasil ditambahkan', 'id': user.id}, status=201)

    @extend_schema(
        summary='Update data mentor',
        parameters=[OpenApiParameter('user_id', int, description='ID mentor yang diupdate')],
    )
    def put(self, request, user_id=None):
        try:
            user = User.objects.get(id=user_id, role='mentor')
            user.username = request.data.get('username', user.username)
            user.email = request.data.get('email', user.email)
            user.university = request.data.get('university', user.university)
            user.phone = request.data.get('phone', user.phone)
            if request.data.get('password'):
                from django.contrib.auth.hashers import make_password
                user.password = make_password(request.data.get('password'))
            user.save()
            return Response({'message': 'Mentor berhasil diupdate'})
        except User.DoesNotExist:
            return Response({'error': 'Mentor tidak ditemukan'}, status=404)

    @extend_schema(
        summary='Hapus akun mentor secara permanen',
        parameters=[OpenApiParameter('user_id', int, description='ID mentor yang dihapus')],
    )
    def delete(self, request, user_id=None):
        try:
            user = User.objects.get(id=user_id, role='mentor')
            user.delete()
            return Response({'message': 'Mentor berhasil dihapus'})
        except User.DoesNotExist:
            return Response({'error': 'Mentor tidak ditemukan'}, status=404)


@extend_schema(tags=['admin'])
class AllMenteesView(generics.ListAPIView):
    """
    GET: Daftar semua mentee (paginated, bisa di-search & filter universitas).

    POST: Admin membuat akun mentee baru secara langsung.

    PUT /mentees/{user_id}/: Update data mentee.

    DELETE /mentees/{user_id}/: Hapus akun mentee secara permanen.
    """
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['university']
    search_fields = ['username', 'email']
    ordering_fields = ['username', 'date_joined']

    def get_queryset(self):
        return User.objects.filter(role='mentee').order_by('-date_joined')

    @extend_schema(
        summary='Tambah mentee baru',
        description='PENTING: gunakan endpoint ini TANPA ID di path (POST /mentees/). Mengirim POST ke /mentees/{id}/ akan ditolak dengan 405 — gunakan PUT untuk update data mentee yang sudah ada.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'email': {'type': 'string'},
                    'password': {'type': 'string', 'default': 'mentee123'},
                    'university': {'type': 'string'},
                    'phone': {'type': 'string'},
                },
                'required': ['username', 'email'],
            }
        },
    )
    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password', 'mentee123')
        university = request.data.get('university', '')
        phone = request.data.get('phone', '')

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username sudah ada'}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email sudah terdaftar'}, status=400)

        from django.contrib.auth.hashers import make_password
        user = User.objects.create(
            username=username, email=email, password=make_password(password),
            role='mentee', university=university, phone=phone
        )
        return Response({'message': 'Mentee berhasil ditambahkan', 'id': user.id}, status=201)

    @extend_schema(
        summary='Update data mentee',
        parameters=[OpenApiParameter('user_id', int, description='ID mentee yang diupdate')],
    )
    def put(self, request, user_id=None):
        try:
            user = User.objects.get(id=user_id, role='mentee')
            user.username = request.data.get('username', user.username)
            user.email = request.data.get('email', user.email)
            user.university = request.data.get('university', user.university)
            user.phone = request.data.get('phone', user.phone)
            if request.data.get('password'):
                from django.contrib.auth.hashers import make_password
                user.password = make_password(request.data.get('password'))
            user.save()
            return Response({'message': 'Mentee berhasil diupdate'})
        except User.DoesNotExist:
            return Response({'error': 'Mentee tidak ditemukan'}, status=404)

    @extend_schema(
        summary='Hapus akun mentee secara permanen',
        parameters=[OpenApiParameter('user_id', int, description='ID mentee yang dihapus')],
    )
    def delete(self, request, user_id=None):
        try:
            user = User.objects.get(id=user_id, role='mentee')
            user.delete()
            return Response({'message': 'Mentee berhasil dihapus'})
        except User.DoesNotExist:
            return Response({'error': 'Mentee tidak ditemukan'}, status=404)


@extend_schema(
    tags=['admin'],
    summary='Daftar semua booking di platform',
    description='Melihat seluruh booking dari semua mentee & mentor, bisa difilter berdasarkan status (pending/accepted/ongoing/completed/paid/rejected/cancelled).',
)
class AllBookingsView(generics.ListAPIView):
    serializer_class = AdminBookingSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['status']
    search_fields = ['mentee_name', 'mentor_name']
    ordering_fields = ['date', 'created_at']

    def get_queryset(self):
        return Booking.objects.all().order_by('-created_at')


@extend_schema(
    tags=['admin'],
    summary='Daftar semua transaksi pembayaran',
    description='Riwayat pembayaran lengkap dengan breakdown nominal, komisi platform (platform_fee), dan pendapatan mentor (mentor_revenue) — data asli dari model Payment, bukan hardcode.',
)
class AllPaymentsView(generics.ListAPIView):
    serializer_class = AdminPaymentSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['status']
    ordering_fields = ['paid_at', 'amount']

    def get_queryset(self):
        return Payment.objects.select_related('booking').order_by('-paid_at')


@extend_schema(tags=['admin'])
class WithdrawRequestsView(generics.ListAPIView):
    """
    GET: Daftar permintaan pencairan dana dari mentor (paginated, filter by status).

    POST: Setujui atau tolak permintaan pencairan.
    Body: {"withdrawal_id": int, "action": "approve" | "reject", "admin_note": str (opsional)}
    """
    serializer_class = AdminWithdrawalSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['status']
    ordering_fields = ['created_at']

    def get_queryset(self):
        return WithdrawalRequest.objects.select_related('mentor').order_by('-created_at')

    @extend_schema(
        summary='Setujui atau tolak permintaan pencairan dana',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'withdrawal_id': {'type': 'integer'},
                    'action': {'type': 'string', 'enum': ['approve', 'reject']},
                    'admin_note': {'type': 'string'},
                },
                'required': ['withdrawal_id', 'action'],
            }
        },
    )
    def post(self, request):
        withdrawal_id = request.data.get('withdrawal_id')
        action = request.data.get('action')
        admin_note = request.data.get('admin_note', '')

        if not withdrawal_id or action not in ['approve', 'reject']:
            return Response(
                {'error': 'withdrawal_id dan action (approve/reject) wajib diisi'}, status=400
            )

        try:
            withdrawal = WithdrawalRequest.objects.get(id=withdrawal_id)
        except WithdrawalRequest.DoesNotExist:
            return Response({'error': 'Permintaan pencairan tidak ditemukan'}, status=404)

        if withdrawal.status != 'pending':
            return Response(
                {'error': f'Permintaan ini sudah diproses sebelumnya (status: {withdrawal.status})'},
                status=400
            )

        if action == 'approve':
            withdrawal.status = 'approved'
            withdrawal.admin_note = admin_note or 'Disetujui oleh admin'
            withdrawal.save()
            return Response({
                'message': f'Pencairan Rp {int(withdrawal.net_amount):,} untuk {withdrawal.mentor.username} disetujui'
            })
        else:
            withdrawal.status = 'rejected'
            withdrawal.admin_note = admin_note or 'Ditolak oleh admin'
            withdrawal.save()
            return Response({
                'message': f'Pencairan untuk {withdrawal.mentor.username} ditolak'
            })


@extend_schema(
    tags=['admin'],
    summary='Riwayat transaksi sukses (untuk laporan keuangan)',
    description='Hanya menampilkan pembayaran dengan status sukses — dipakai untuk laporan komisi platform dan rekonsiliasi keuangan.',
)
class TransactionsView(generics.ListAPIView):
    serializer_class = AdminTransactionSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['status']
    ordering_fields = ['paid_at']

    def get_queryset(self):
        return Payment.objects.filter(status='success').select_related('booking').order_by('-paid_at')