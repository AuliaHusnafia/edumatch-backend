from rest_framework import serializers
from .models import MentorProfile
from bookings.models import Booking

class MentorProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    university = serializers.CharField(source='user.university', read_only=True)

    class Meta:
        model = MentorProfile
        fields = ['id', 'username', 'email', 'university', 'skills', 'price_per_session', 'bio', 'education', 'available_slots']

class MentorBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ['id', 'mentee_name', 'date', 'notes', 'status', 'meeting_link', 'invoice_amount']
