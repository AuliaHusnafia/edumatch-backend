from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from users.models import User
from mentors.models import MentorProfile
from bookings.models import Booking
from .serializers import MentorListSerializer, MenteeBookingSerializer
from datetime import datetime

class MentorListView(generics.ListAPIView):
    serializer_class = MentorListSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['university']
    search_fields = ['username', 'mentor_profile__skills', 'mentor_profile__bio']

    def get_queryset(self):
        return User.objects.filter(role='mentor', is_verified=True).select_related('mentor_profile')

class MentorDetailView(generics.RetrieveAPIView):
    serializer_class = MentorListSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        mentor_id = self.kwargs.get('mentor_id')
        try:
            return User.objects.get(id=mentor_id, role='mentor', is_verified=True)
        except User.DoesNotExist:
            return None

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance:
            return Response({'error': 'Mentor tidak ditemukan'}, status=404)
        serializer = self.get_serializer(instance)
        data = serializer.data
        
        # Filter available slots for today and future
        today = datetime.now().date()
        slots = data.get('available_slots', [])
        if slots:
            filtered_slots = []
            for slot in slots:
                try:
                    slot_date = datetime.strptime(slot.get('date', ''), '%Y-%m-%d').date()
                    if slot_date >= today:
                        filtered_slots.append(slot)
                except:
                    filtered_slots.append(slot)
            data['available_slots'] = filtered_slots
            
        return Response(data)

class BookMentorView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.user.role != 'mentee':
            return Response({'error': 'Hanya mentee yang bisa booking'}, status=403)
        
        mentor_id = request.data.get('mentor_id')
        slot_id = request.data.get('slot_id')
        notes = request.data.get('notes', '')
        
        if not mentor_id or not slot_id:
            return Response({'error': 'Mentor ID dan slot ID harus diisi'}, status=400)
            
        try:
            mentor = User.objects.get(id=mentor_id, role='mentor', is_verified=True)
        except User.DoesNotExist:
            return Response({'error': 'Mentor tidak ditemukan'}, status=404)
            
        profile, _ = MentorProfile.objects.get_or_create(user=mentor)
        selected_slot = next((s for s in (profile.available_slots or []) if str(s.get('id')) == str(slot_id)), None)
        
        if not selected_slot:
            return Response({'error': 'Slot jadwal tidak ditemukan'}, status=404)
            
        date_str = f"{selected_slot.get('date')} {selected_slot.get('time')}"
        try:
            booking_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M')
        except:
            booking_date = datetime.now()
            
        booking = Booking.objects.create(
            mentee=request.user,
            mentor=mentor,
            mentee_name=request.user.username,
            mentor_name=mentor.username,
            date=booking_date,
            notes=notes,
            status='pending',
            invoice_amount=profile.price_per_session
        )
        
        return Response({
            'message': 'Booking berhasil dibuat',
            'booking_id': booking.id,
            'status': booking.status,
            'date': booking.date
        })

class MyBookingsView(generics.ListAPIView):
    serializer_class = MenteeBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
 
    def list(self, request, *args, **kwargs):
        if request.user.role != 'mentee':
            return Response({'error': 'Hanya mentee yang bisa akses endpoint ini'}, status=403)
        return super().list(request, *args, **kwargs)
 
    def get_queryset(self):
        return Booking.objects.filter(mentee=self.request.user).order_by('-created_at')
 
 
class MenteeOngoingSessionsView(generics.ListAPIView):
    serializer_class = MenteeBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
 
    def list(self, request, *args, **kwargs):
        if request.user.role != 'mentee':
            return Response({'error': 'Hanya mentee yang bisa akses endpoint ini'}, status=403)
        return super().list(request, *args, **kwargs)
 
    def get_queryset(self):
        return Booking.objects.filter(
            mentee=self.request.user,
            status__in=['accepted', 'ongoing']
        ).order_by('date')
 
 
class MenteeCompletedSessionsView(generics.ListAPIView):
    serializer_class = MenteeBookingSerializer
    permission_classes = [permissions.IsAuthenticated]
 
    def list(self, request, *args, **kwargs):
        if request.user.role != 'mentee':
            return Response({'error': 'Hanya mentee yang bisa akses endpoint ini'}, status=403)
        return super().list(request, *args, **kwargs)
 
    def get_queryset(self):
        return Booking.objects.filter(
            mentee=self.request.user,
            status__in=['completed', 'paid']
        ).order_by('-date')

class MenteeOngoingSessionsView(generics.ListAPIView):
    serializer_class = MenteeBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'mentee':
            return Booking.objects.none()
        return Booking.objects.filter(
            mentee=self.request.user,
            status__in=['accepted', 'ongoing']
        ).order_by('date')

class MenteeCompletedSessionsView(generics.ListAPIView):
    serializer_class = MenteeBookingSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != 'mentee':
            return Booking.objects.none()
        return Booking.objects.filter(
            mentee=self.request.user,
            status__in=['completed', 'paid']
        ).order_by('-date')

