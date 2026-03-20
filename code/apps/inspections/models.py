from django.db import models

# Create your models here.
# inspections/models.py
from django.db import models
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()

class Inspection(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('human_review', 'Human Review Required'),
    ]
    
    # Basic info
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)  # Original filename
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inspections')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # AI Service tracking
    job_id = models.UUIDField(null=True, blank=True)  # From AI service
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    
    # AI Results (populated when processing completes)
    ai_confidence = models.FloatField(null=True, blank=True)
    ai_classification = models.CharField(max_length=50, blank=True)  # 'good' or 'defect'
    ai_explanation = models.TextField(blank=True)
    ai_processed_at = models.DateTimeField(null=True, blank=True)
    
    # Human override
    human_override = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.name} - {self.status}"


class HumanOverride(models.Model):
    inspection = models.OneToOneField(Inspection, on_delete=models.CASCADE, related_name='override')
    overridden_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    # Original values
    original_status = models.CharField(max_length=50)
    original_classification = models.CharField(max_length=50, blank=True)
    
    # New values
    new_status = models.CharField(max_length=50, choices=Inspection.STATUS_CHOICES)
    new_classification = models.CharField(max_length=50)  # 'good' or 'defect'
    
    # Override details
    reason = models.TextField()
    notes = models.TextField(blank=True)
    
    # Timestamps
    from_date = models.DateTimeField()
    to_date = models.DateTimeField(null=True, blank=True)
    overridden_at = models.DateTimeField(auto_now_add=True)