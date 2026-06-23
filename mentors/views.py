from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import MentorProfile
from .serializers import MentorProfileSerializer, MentorBookingSerializer
from bookings.models import Booking
import uuid

class MentorProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = MentorProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        profile, _ = MentorProfile.objects.get_or_create(user=self.request.user)
        return profile

    def perform_update(self, serializer):
        if self.request.user.role != 'mentor':
            return Response({'error': 'Anda bukan mentor'}, status=403)
        serializer.save()

# SESUDAH
HARI_VALID = ['Senin', 'Selasa', 'Rabu', 'Kamis', 'Jumat', 'Sabtu', 'Minggu']

class MentorAvailableSlotsView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Anda bukan mentor'}, status=403)
        profile, _ = MentorProfile.objects.get_or_create(user=request.user)
        return Response(profile.available_slots or [])

    def post(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Anda bukan mentor'}, status=403)
        profile, _ = MentorProfile.objects.get_or_create(user=request.user)

        day = request.data.get('day')
        time = request.data.get('time')

        if not day or not time:
            return Response({'error': 'Hari dan waktu harus diisi'}, status=400)

        if day not in HARI_VALID:
            return Response({'error': f'Hari tidak valid. Pilih: {", ".join(HARI_VALID)}'}, status=400)

        if not profile.available_slots:
            profile.available_slots = []

        # Cek duplikat
        for s in profile.available_slots:
            if s.get('day') == day and s.get('time') == time:
                return Response({'error': f'Jadwal {day} {time} sudah ada'}, status=400)

        new_slot = {'id': str(uuid.uuid4()), 'day': day, 'time': time}
        profile.available_slots.append(new_slot)
        profile.save()
        return Response({'message': f'Jadwal {day} {time} berhasil ditambahkan', 'slot': new_slot})

class MentorDeleteSlotView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, slot_id):
        if request.user.role != 'mentor':
            return Response({'error': 'Anda bukan mentor'}, status=403)
        profile, _ = MentorProfile.objects.get_or_create(user=request.user)
        if profile.available_slots:
            before = len(profile.available_slots)
            profile.available_slots = [s for s in profile.available_slots if s.get('id') != slot_id]
            if len(profile.available_slots) == before:
                return Response({'error': 'Jadwal tidak ditemukan'}, status=404)
            profile.save()
        return Response({'message': 'Jadwal berhasil dihapus'})

class MentorBookingRequestsView(generics.ListAPIView):
    serializer_class = MentorBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(mentor=self.request.user, status='pending').order_by('-created_at')

class MentorRespondBookingView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Anda bukan mentor'}, status=403)
        booking_id = request.data.get('booking_id')
        action = request.data.get('action')
        try:
            booking = Booking.objects.get(id=booking_id, mentor=request.user)
            if action == 'accept':
                booking.status = 'accepted'
                booking.save()
                return Response({'message': 'Booking diterima'})
            elif action == 'reject':
                booking.status = 'rejected'
                booking.save()
                return Response({'message': 'Booking ditolak'})
            return Response({'error': 'Action tidak valid'}, status=400)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking tidak ditemukan'}, status=404)

class MentorActiveSessionsView(generics.ListAPIView):
    serializer_class = MentorBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(
            mentor=self.request.user,
            status__in=['accepted', 'ongoing', 'completed', 'paid']
        ).order_by('-date')

class MentorStartSessionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Anda bukan mentor'}, status=403)
        booking_id = request.data.get('booking_id')
        meeting_link = request.data.get('meeting_link')
        if not booking_id:
            return Response({'error': 'Booking ID harus diisi'}, status=400)
        try:
            booking = Booking.objects.get(id=booking_id, mentor=request.user, status='accepted')
            booking.meeting_link = meeting_link or f"https://meet.google.com/edm-{str(uuid.uuid4())[:8]}"
            booking.status = 'ongoing'
            booking.save()
            return Response({'message': 'Sesi dimulai!', 'meeting_link': booking.meeting_link, 'booking_id': booking.id})
        except Booking.DoesNotExist:
            return Response({'error': 'Booking tidak ditemukan atau belum diterima'}, status=404)

class MentorCompleteSessionView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Anda bukan mentor'}, status=403)
        booking_id = request.data.get('booking_id')
        if not booking_id:
            return Response({'error': 'Booking ID harus diisi'}, status=400)
        try:
            booking = Booking.objects.get(id=booking_id, mentor=request.user)
            if booking.status == 'ongoing':
                booking.status = 'completed'
                booking.save()
                return Response({'message': 'Sesi selesai!'})
            return Response({'error': 'Sesi tidak dapat diselesaikan'}, status=400)
        except Booking.DoesNotExist:
            return Response({'error': 'Booking tidak ditemukan'}, status=404)

# SESUDAH
class MentorReviewsView(generics.ListAPIView):
    """List review yang diterima mentor — pagination + filter by rating"""
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['rating']
    ordering_fields = ['created_at', 'rating']

    def get_serializer_class(self):
        from rest_framework import serializers as drf_serializers
        from reviews.models import Review

        class MentorReviewSerializer(drf_serializers.ModelSerializer):
            created_at = drf_serializers.SerializerMethodField()

            class Meta:
                model = Review
                fields = ['id', 'mentee_name', 'rating', 'comment', 'created_at']

            def get_created_at(self, obj):
                return obj.created_at.strftime('%d %b %Y')

        return MentorReviewSerializer

    def get_queryset(self):
        from reviews.models import Review
        if self.request.user.role != 'mentor':
            return Review.objects.none()
        return Review.objects.filter(mentor=self.request.user).order_by('-created_at')

class MentorIncomeView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Akses ditolak'}, status=403)
        from payments.models import Payment, WithdrawalRequest
        from django.db.models import Sum
        from decimal import Decimal
        paid_payments = Payment.objects.filter(booking__mentor=request.user, status='success')
        total_revenue = sum(Decimal(str(p.mentor_revenue)) for p in paid_payments)
        total_withdrawn = WithdrawalRequest.objects.filter(mentor=request.user, status='approved').aggregate(total=Sum('net_amount'))['total'] or Decimal('0')
        unpaid_count = Booking.objects.filter(mentor=request.user, status='completed').count()
        return Response({
            'total': int(total_revenue),
            'available': int(total_revenue - total_withdrawn),
            'withdrawn': int(total_withdrawn),
            'unpaid_sessions': unpaid_count,
            'pending': 0,
        })

class MentorWithdrawView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'mentor':
            return Response({'error': 'Anda bukan mentor'}, status=403)
        from payments.views import request_withdrawal
        return request_withdrawal(request)
