from django.db import models
from users.models import User

class MentorProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mentor_profile')
    skills = models.TextField(blank=True, default='')
    price_per_session = models.IntegerField(default=75000)
    bio = models.TextField(blank=True, default='')
    education = models.CharField(max_length=255, blank=True, default='')
    available_slots = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Profile of {self.user.username}"

    class Meta:
        verbose_name = 'Mentor Profile'
        verbose_name_plural = 'Mentor Profiles'