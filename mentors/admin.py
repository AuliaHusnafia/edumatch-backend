from django.contrib import admin
from .models import MentorProfile

@admin.register(MentorProfile)
class MentorProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'price_per_session', 'skills', 'created_at']
    search_fields = ['user__username', 'user__email']