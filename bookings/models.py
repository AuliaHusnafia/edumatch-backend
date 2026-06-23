from django.db import models
from users.models import User

class Booking(models.Model):
    STATUS_CHOICES = (
        ('pending_payment', 'Menunggu Pembayaran'),
        ('pending', 'Menunggu'),
        ('accepted', 'Diterima'),
        ('rejected', 'Ditolak'),
        ('ongoing', 'Berlangsung'),
        ('completed', 'Selesai'),
        ('cancelled', 'Dibatalkan'),
        ('paid', 'Lunas'),
    )
    
    mentee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings_as_mentee')
    mentor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings_as_mentor')
    mentee_name = models.CharField(max_length=100)
    mentor_name = models.CharField(max_length=100)
    date = models.DateTimeField()
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invoice_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    meeting_link = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.mentee_name} → {self.mentor_name} ({self.date})"

    class Meta:
        ordering = ['-created_at']