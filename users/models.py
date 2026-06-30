from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ('mentee', 'Mentee'),
        ('mentor', 'Mentor'),
        ('admin', 'Admin'),
    )
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='mentee')
    is_verified = models.BooleanField(default=False)
    university = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"

    class Meta:
        ordering = ['-date_joined']