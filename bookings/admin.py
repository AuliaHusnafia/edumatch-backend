from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['mentee_name', 'mentor_name', 'date', 'status', 'created_at']
    list_filter = ['status', 'date']
    search_fields = ['mentee_name', 'mentor_name']