from rest_framework import serializers
from users.models import User
from mentors.models import MentorProfile
from bookings.models import Booking

class MentorListSerializer(serializers.ModelSerializer):
    skills = serializers.CharField(source='mentor_profile.skills', read_only=True)
    price_per_session = serializers.IntegerField(source='mentor_profile.price_per_session', read_only=True)
    bio = serializers.CharField(source='mentor_profile.bio', read_only=True)
    education = serializers.CharField(source='mentor_profile.education', read_only=True)
    available_slots = serializers.JSONField(source='mentor_profile.available_slots', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'university', 'skills', 'price_per_session', 'bio', 'education', 'available_slots']

class MenteeBookingSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_status = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = ['id', 'mentor_name', 'date', 'notes', 'status', 'status_display', 'meeting_link', 'invoice_amount', 'payment_status', 'created_at']

    def get_payment_status(self, obj):
        try:
            return obj.payment.status
        except AttributeError:
            return None
