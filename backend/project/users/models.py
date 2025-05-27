from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    
    def __str__(self):
        return self.user.username

class Complaint(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('IN_PROGRESS', 'In Progress'),
        ('RESOLVED', 'Resolved'),
    ]

    COMPLAINT_TYPES = [
        ('POTHOLE', 'Pothole'),
        ('WATER_LEAK', 'Water Leak'),
        ('BROKEN_SIGNAL', 'Broken Signal'),
        ('GARBAGE', 'Garbage'),
        ('OTHER', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='complaints/')
    complaint_type = models.CharField(max_length=20, choices=COMPLAINT_TYPES)
    latitude = models.FloatField()
    longitude = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    ai_classification = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.complaint_type} - {self.user.username}"

class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('COMPLAINT', 'Complaint'),
        ('TRAFFIC', 'Traffic'),
        ('AIR_QUALITY', 'Air Quality'),
        ('WATER_SUPPLY', 'Water Supply'),
        ('EVENT', 'Event'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} - {self.title}"

class TrafficReport(models.Model):
    ISSUE_TYPES = [
        ('ACCIDENT', 'Traffic Accident'),
        ('BREAKDOWN', 'Vehicle Breakdown'),
        ('HAZARD', 'Road Hazard'),
        ('CONSTRUCTION', 'Construction Work'),
    ]

    type = models.CharField(max_length=20, choices=ISSUE_TYPES)
    description = models.TextField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    verified = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_type_display()} at ({self.latitude}, {self.longitude})"
