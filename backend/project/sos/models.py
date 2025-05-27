from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class EmergencyRequest(models.Model):
    EMERGENCY_TYPES = [
        ('MEDICAL', 'Medical Emergency'),
        ('FIRE', 'Fire Emergency'),
        ('POLICE', 'Police Emergency'),
        ('OTHER', 'Other Emergency'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emergency_type = models.CharField(max_length=20, choices=EMERGENCY_TYPES)
    description = models.TextField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    ai_response = models.TextField(null=True, blank=True)
    nearest_facility = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f"{self.emergency_type} - {self.user.username}"
