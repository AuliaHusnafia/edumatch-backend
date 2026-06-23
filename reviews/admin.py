from django.contrib import admin
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['mentee_name', 'mentor_name', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['mentee_name', 'mentor_name', 'comment']