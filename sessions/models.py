from django.db import models
from users.models import User
from bookings.models import Booking

class MentoringSession(models.Model):
    STATUS_CHOICES = (
        ('scheduled', 'Dijadwalkan'),
        ('ongoing', 'Berlangsung'),
        ('completed', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
    )
    
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='session')
    mentee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions_as_mentee')
    mentor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions_as_mentor')
    mentee_name = models.CharField(max_length=100)
    mentor_name = models.CharField(max_length=100)
    date = models.DateTimeField()
    meeting_link = models.URLField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    duration = models.IntegerField(default=60)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Session: {self.mentee_name} - {self.mentor_name}"