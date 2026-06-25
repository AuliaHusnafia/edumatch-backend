from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    OpenApiExample,
)

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
    def has_permission(self, request, view):
        return (
            super().has_permission(request, view)
            and request.user.role == 'admin'
        )


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

        return Response({
            'total_mentees': total_mentees,
            'total_mentors': total_mentors,
            'pending_mentors': pending_mentors,
            'total_users': total_users,
            'total_bookings': total_bookings,
            'completed_sessions': completed_sessions,
            'paid_sessions': paid_sessions,
            'platform_commission': float(platform_commission),
        })


@extend_schema(tags=['admin'])
class PendingMentorsView(generics.ListAPIView):
    """
    GET: Daftar mentor yang mendaftar tapi belum diverifikasi admin (paginated, bisa di-search).

    POST: Setujui atau tolak pendaftaran mentor.
    Body: {"mentor_id": int, "action": "approve" | "reject"}
    - approve → mentor.is_verified jadi True
    - reject  → akun mentor dihapus permanen
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
            OpenApiExample('Tolak mentor',   value={'mentor_id': 5, 'action': 'reject'}),
        ],
    )
    def post(self, request, *args, **kwargs):
        mentor_id = request.data.get('mentor_id')
        action = request.data.get('action')

        try:
            mentor = User.objects.get(id=mentor_id, role='mentor')
        except User.DoesNotExist:
            return Response({'error': 'Mentor tidak ditemukan'}, status=404)

        if action == 'approve':
            mentor.is_verified = True
            mentor.save()
            return Response({'message': f'Mentor {mentor.username} telah disetujui'})
        elif action == 'reject':
            mentor.delete()
            return Response({'message': f'Mentor {mentor.username} ditolak'})

        return Response({'error': 'Action tidak valid'}, status=400)


@extend_schema(tags=['admin'])
class AllMentorsView(generics.ListAPIView):
    """
    GET: Daftar mentor terverifikasi (paginated, bisa di-search & filter universitas).

    POST /mentors/: Admin membuat akun mentor baru (otomatis terverifikasi).
    JANGAN kirim POST ke /mentors/{id}/ — gunakan MentorDetailView untuk PUT/DELETE.
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
        description='Gunakan endpoint ini TANPA ID di path (POST /mentors/). POST ke /mentors/{id}/ akan ditolak 405.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'username':   {'type': 'string'},
                    'email':      {'type': 'string'},
                    'password':   {'type': 'string', 'default': 'mentor123'},
                    'university': {'type': 'string'},
                    'phone':      {'type': 'string'},
                },
                'required': ['username', 'email'],
            }
        },
    )
    def post(self, request, *args, **kwargs):
        username   = request.data.get('username')
        email      = request.data.get('email')
        password   = request.data.get('password', 'mentor123')
        university = request.data.get('university', '')
        phone      = request.data.get('phone', '')

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username sudah ada'}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email sudah terdaftar'}, status=400)

        from django.contrib.auth.hashers import make_password
        user = User.objects.create(
            username=username, email=email, password=make_password(password),
            role='mentor', university=university, phone=phone, is_verified=True,
        )
        MentorProfile.objects.create(user=user)
        return Response({'message': 'Mentor berhasil ditambahkan', 'id': user.id}, status=201)


@extend_schema(
    tags=['admin'],
    summary='Update atau hapus mentor berdasarkan ID',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'username':   {'type': 'string'},
                'email':      {'type': 'string'},
                'password':   {'type': 'string'},
                'university': {'type': 'string'},
                'phone':      {'type': 'string'},
            },
        }
    },
    parameters=[
        OpenApiParameter(name='user_id', type=int, location=OpenApiParameter.PATH, description='ID mentor'),
    ],
)
class MentorDetailView(APIView):
    permission_classes = [IsAdmin]

    def put(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, role='mentor')
        except User.DoesNotExist:
            return Response({'error': f'Mentor dengan id {user_id} tidak ditemukan'}, status=404)

        user.username   = request.data.get('username',   user.username)
        user.email      = request.data.get('email',      user.email)
        user.university = request.data.get('university', user.university)
        user.phone      = request.data.get('phone',      user.phone)

        if request.data.get('password'):
            from django.contrib.auth.hashers import make_password
            user.password = make_password(request.data.get('password'))

        user.save()
        return Response({'message': 'Mentor berhasil diupdate'})

    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, role='mentor')
        except User.DoesNotExist:
            return Response({'error': f'Mentor dengan id {user_id} tidak ditemukan'}, status=404)

        user.delete()
        return Response({'message': 'Mentor berhasil dihapus'})


@extend_schema(tags=['admin'])
class AllMenteesView(generics.ListAPIView):
    """
    GET: Daftar semua mentee (paginated, bisa di-search & filter universitas).

    POST /mentees/: Admin membuat akun mentee baru.
    JANGAN kirim POST ke /mentees/{id}/ — gunakan MenteeDetailView untuk PUT/DELETE.
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
        description='Gunakan endpoint ini TANPA ID di path (POST /mentees/). POST ke /mentees/{id}/ akan ditolak 405.',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'username':   {'type': 'string'},
                    'email':      {'type': 'string'},
                    'password':   {'type': 'string', 'default': 'mentee123'},
                    'university': {'type': 'string'},
                    'phone':      {'type': 'string'},
                },
                'required': ['username', 'email'],
            }
        },
    )
    def post(self, request, *args, **kwargs):
        username   = request.data.get('username')
        email      = request.data.get('email')
        password   = request.data.get('password', 'mentee123')
        university = request.data.get('university', '')
        phone      = request.data.get('phone', '')

        if User.objects.filter(username=username).exists():
            return Response({'error': 'Username sudah ada'}, status=400)
        if User.objects.filter(email=email).exists():
            return Response({'error': 'Email sudah terdaftar'}, status=400)

        from django.contrib.auth.hashers import make_password
        user = User.objects.create(
            username=username, email=email, password=make_password(password),
            role='mentee', university=university, phone=phone,
        )
        return Response({'message': 'Mentee berhasil ditambahkan', 'id': user.id}, status=201)

@extend_schema(
    tags=['admin'],
    summary='Update atau hapus mentee berdasarkan ID',
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'username':   {'type': 'string'},
                'email':      {'type': 'string'},
                'password':   {'type': 'string'},
                'university': {'type': 'string'},
                'phone':      {'type': 'string'},
            },
        }
    },
    parameters=[
        OpenApiParameter(name='user_id', type=int, location=OpenApiParameter.PATH, description='ID mentee'),
    ],
)

class MenteeDetailView(APIView):
    permission_classes = [IsAdmin]

    def put(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, role='mentee')
        except User.DoesNotExist:
            return Response({'error': f'Mentee dengan id {user_id} tidak ditemukan'}, status=404)

        user.username   = request.data.get('username',   user.username)
        user.email      = request.data.get('email',      user.email)
        user.university = request.data.get('university', user.university)
        user.phone      = request.data.get('phone',      user.phone)

        if request.data.get('password'):
            from django.contrib.auth.hashers import make_password
            user.password = make_password(request.data.get('password'))

        user.save()
        return Response({'message': 'Mentee berhasil diupdate'})

    def delete(self, request, user_id):
        try:
            user = User.objects.get(id=user_id, role='mentee')
        except User.DoesNotExist:
            return Response({'error': f'Mentee dengan id {user_id} tidak ditemukan'}, status=404)

        user.delete()
        return Response({'message': 'Mentee berhasil dihapus'})


@extend_schema(
    tags=['admin'],
    summary='Daftar semua booking di platform',
    description='Melihat seluruh booking dari semua mentee & mentor, bisa difilter berdasarkan status.',
)
class AllBookingsView(generics.ListAPIView):
    serializer_class = AdminBookingSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['status']
    search_fields = ['mentee__username', 'mentor__username']
    ordering_fields = ['date', 'created_at']

    def get_queryset(self):
        return Booking.objects.all().order_by('-created_at')


@extend_schema(
    tags=['admin'],
    summary='Daftar semua transaksi pembayaran',
    description='Riwayat pembayaran lengkap dengan breakdown nominal, komisi platform, dan pendapatan mentor.',
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
                    'action':        {'type': 'string', 'enum': ['approve', 'reject']},
                    'admin_note':    {'type': 'string'},
                },
                'required': ['withdrawal_id', 'action'],
            }
        },
    )
    def post(self, request, *args, **kwargs):
        withdrawal_id = request.data.get('withdrawal_id')
        action        = request.data.get('action')
        admin_note    = request.data.get('admin_note', '')

        if not withdrawal_id or action not in ['approve', 'reject']:
            return Response({'error': 'withdrawal_id dan action (approve/reject) wajib diisi'}, status=400)

        try:
            withdrawal = WithdrawalRequest.objects.get(id=withdrawal_id)
        except WithdrawalRequest.DoesNotExist:
            return Response({'error': 'Permintaan pencairan tidak ditemukan'}, status=404)

        if withdrawal.status != 'pending':
            return Response(
                {'error': f'Permintaan ini sudah diproses (status: {withdrawal.status})'},
                status=400,
            )

        if action == 'approve':
            withdrawal.status     = 'approved'
            withdrawal.admin_note = admin_note or 'Disetujui oleh admin'
            withdrawal.save()
            return Response({'message': f'Pencairan Rp {int(withdrawal.net_amount):,} untuk {withdrawal.mentor.username} disetujui'})
        else:
            withdrawal.status     = 'rejected'
            withdrawal.admin_note = admin_note or 'Ditolak oleh admin'
            withdrawal.save()
            return Response({'message': f'Pencairan untuk {withdrawal.mentor.username} ditolak'})


@extend_schema(
    tags=['admin'],
    summary='Riwayat transaksi sukses (untuk laporan keuangan)',
    description='Hanya menampilkan pembayaran dengan status sukses — untuk laporan komisi platform dan rekonsiliasi keuangan.',
)
class TransactionsView(generics.ListAPIView):
    serializer_class = AdminTransactionSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['status']
    ordering_fields = ['paid_at']

    def get_queryset(self):
        return Payment.objects.filter(status='success').select_related('booking').order_by('-paid_at')


@extend_schema(
    tags=['admin'],
    summary='Info user yang sedang login (admin)',
)
class CurrentUserView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request):
        return Response({
            'id':       request.user.id,
            'username': request.user.username,
            'email':    request.user.email,
            'role':     request.user.role,
        })