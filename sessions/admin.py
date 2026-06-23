from django.contrib import admin
from .models import MentoringSession

@admin.register(MentoringSession)
class MentoringSessionAdmin(admin.ModelAdmin):
    list_display = ['mentee_name', 'mentor_name', 'date', 'status', 'meeting_link']
    list_filter = ['status', 'date']
    search_fields = ['mentee_name', 'mentor_name']