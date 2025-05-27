from django.db import models

# Create your models here.

class SmokeData(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)
    smoke_level = models.IntegerField()
    status = models.CharField(max_length=20, choices=[
        ('safe', 'Safe'),
        ('warning', 'Warning'),
        ('danger', 'Danger')
    ])

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"Smoke Level: {self.smoke_level} PPM at {self.timestamp}"
