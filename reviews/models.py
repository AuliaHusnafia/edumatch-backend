from django.db import models
from users.models import User
from sessions.models import MentoringSession

class Review(models.Model):
    session = models.OneToOneField(MentoringSession, on_delete=models.CASCADE, related_name='review')
    mentee = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_given')
    mentor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews_received')
    mentee_name = models.CharField(max_length=100)
    mentor_name = models.CharField(max_length=100)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review: {self.mentee_name} → {self.mentor_name} ({self.rating}⭐)"

    class Meta:
        ordering = ['-created_at']