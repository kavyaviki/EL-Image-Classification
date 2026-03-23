# inspections/models.py
"""
Models for the Inspections app.
Handles storing inspection data, AI results, and human overrides.
"""

from django.db import models
from django.contrib.auth import get_user_model
import uuid

# Get the custom User model from the users app
User = get_user_model()


class Inspection(models.Model):
    """
    Main model for storing inspection records.
    
    Each record represents one uploaded image and its inspection results.
    """
    
    # ============================================================
    # STATUS CHOICES - Defines possible states of an inspection
    # ============================================================
    STATUS_CHOICES = [
        ('queued', 'Queued'),           # Image uploaded, waiting for AI processing
        ('processing', 'Processing'),    # AI is currently analyzing the image
        ('completed', 'Completed'),      # AI processing complete, results available
        ('failed', 'Failed'),            # AI processing failed
        ('human_review', 'Human Review Required'),  # Needs manual review (low confidence)
    ]
    
    # ============================================================
    # BASIC IDENTIFICATION FIELDS
    # ============================================================
    
    # UUID primary key
    id = models.UUIDField(
        primary_key=True,          
        default=uuid.uuid4,         # Generate a new UUID automatically
        editable=False              # Cannot be changed after creation
    )
    
    # Original filename from the user's upload Example: "solar_panel_001.jpg"
    name = models.CharField(
        max_length=255,
        help_text="Original filename of the uploaded image"
    )
    
    # Who uploaded this image - Foreign key to the User model
    # a many-to-one relationship
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,    # If user is deleted, delete all their inspections
        related_name='inspections'   # Allows user.inspections to get all their inspections
    )
    
    # When the image was uploaded - automatically set on creation
    uploaded_at = models.DateTimeField(
        auto_now_add=True,           # Set once when record is created
        help_text="Timestamp of upload"
    )
    
    # ============================================================
    # S3 STORAGE FIELDS - Where the image is stored in AWS
    # ============================================================
    
    # Direct S3 URL for public access (if bucket is public)
    # Example: "https://solar-el-images.s3.ap-south-1.amazonaws.com/jobs/123/input/image.jpg"
    s3_url = models.URLField(
        max_length=1000,
        blank=True,                  # Can be empty
        null=True,                   # Can be NULL in database
        help_text="Direct S3 URL of the image (for public buckets)"
    )
    
    # S3 key/path for generating presigned URLs (for private buckets)
    # Example: "jobs/123/input/image.jpg"
    s3_key = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        help_text="S3 key/path for generating presigned URLs (for private buckets)"
    )
    
    # ============================================================
    # AI SERVICE TRACKING
    # ============================================================
    
    # Job ID returned by the AI service when image is submitted
    # Used to track the processing status and fetch results
    job_id = models.UUIDField(
        null=True,                  
        blank=True,                  
        help_text="Job ID from AI service for tracking"
    )
    
    # Current processing status (one of the STATUS_CHOICES above)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,      # Restricts values to the list above
        default='queued',            # New inspections start as 'queued'
        help_text="Current processing status"
    )
    
    # ============================================================
    # AI RESULTS - Filled when processing completes
    # ============================================================
    
    # Confidence score from AI (0.0 to 1.0)
    # Example: 0.95 means 95% confidence
    ai_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="AI confidence score (0.0 to 1.0)"
    )
    
    # AI's classification result
    ai_classification = models.CharField(
        max_length=50,
        blank=True,
        help_text="AI classification: 'good' or 'defect'"
    )
    
    
    # When AI processing was completed
    ai_processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when AI completed processing"
    )
    
    # ============================================================
    # HUMAN OVERRIDE FLAG
    # ============================================================
    
    # Whether a human has overridden the AI decision
    # True if override exists in HumanOverride table
    human_override = models.BooleanField(
        default=False,
        help_text="Has a human overridden the AI decision?"
    )
    
    # ============================================================
    # SYSTEM TIMESTAMPS
    # ============================================================
    
    # When this record was created
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Record creation timestamp"
    )
    
    # When this record was last updated
    updated_at = models.DateTimeField(
        auto_now=True,               # Updates every time the record is saved
        help_text="Last update timestamp"
    )
    
    # ============================================================
    # META CLASS - Database configuration
    # ============================================================
    
    class Meta:
        # Default ordering: newest first (most recent uploaded_at)
        ordering = ['-uploaded_at']
        verbose_name = "Inspection"
        verbose_name_plural = "Inspections"
    
    # ============================================================
    # STRING REPRESENTATION - How the object appears in admin/shell
    # ============================================================
    
    def __str__(self):
        """
        Returns a human-readable string representation of the inspection.
        Used in Django admin, shell, and when printing the object.
        
        Returns:
            str: Example: "solar_panel_001.jpg - completed"
        """
        return f"{self.name} - {self.status}"


class HumanOverride(models.Model):
    """
    Stores records when a human overrides an AI classification.
    
    This is a one-to-one relationship with Inspection, meaning each inspection
    can have at most one override record.
    """
    
    # ============================================================
    # RELATIONSHIP FIELDS
    # ============================================================
    
    # Link to the inspection being overridden
    # OneToOneField ensures only one override per inspection
    inspection = models.OneToOneField(
        Inspection,
        on_delete=models.CASCADE,           # If inspection is deleted, delete this override too
        related_name='override'              # Allows inspection.override to access this record
    )
    
    # Who performed the override
    overridden_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,           # If user is deleted, set to NULL (keep history)
        null=True                            # Can be NULL if user is deleted
    )
    
    # ============================================================
    # ORIGINAL VALUES - What the AI said before override
    # ============================================================
    
    # Original status before override
    # Example: 'completed'
    original_status = models.CharField(
        max_length=50,
        help_text="Status before override"
    )
    
    # Original AI classification before override
    # Example: 'defect'
    original_classification = models.CharField(
        max_length=50,
        blank=True,
        help_text="AI classification before override"
    )
    
    # ============================================================
    # NEW VALUES - What the human changed it to
    # ============================================================
    
    # New status after override
    new_status = models.CharField(
        max_length=50,
        choices=Inspection.STATUS_CHOICES,   # Same status choices as Inspection
        help_text="Status after override"
    )
    
    # New classification after override
    new_classification = models.CharField(
        max_length=50,
        help_text="Classification after override: 'good' or 'defect'"
    )
    
    # ============================================================
    # OVERRIDE DETAILS
    # ============================================================
    
    # Why the override was performed
    # Examples: 'AI missed defect', 'False positive', 'Borderline case'
    reason = models.TextField(
        help_text="Reason for overriding the AI decision"
    )
    
    # Additional notes about the override
    notes = models.TextField(
        blank=True,
        help_text="Additional observations or notes"
    )
    
    # ============================================================
    # TIMESTAMP FIELDS
    # ============================================================
    
    # When the override becomes effective (when it was applied)
    from_date = models.DateTimeField(
        help_text="When the override was applied"
    )
    
    # When the override expires (if temporary)
    # If NULL, override is permanent
    to_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When override expires (if temporary, otherwise NULL)"
    )
    
    # When this override record was created
    overridden_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Record creation timestamp"
    )
    
    # ============================================================
    # STRING REPRESENTATION
    # ============================================================
    
    def __str__(self):
        """
        Returns a human-readable string representation.
        
        Returns:
            str: Example: "Override for solar_panel_001.jpg by admin"
        """
        return f"Override for {self.inspection.name} by {self.overridden_by}"