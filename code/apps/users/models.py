# apps/users/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from datetime import timedelta

class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser
    """
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    
    # Login tracking
    first_login_date = models.DateTimeField(null=True, blank=True)
    last_login_date = models.DateTimeField(null=True, blank=True)
    auto_deactivate_date = models.DateTimeField(null=True, blank=True)
    
    # Feature toggle for auto-deactivation
    enable_auto_deactivation = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Is active
    is_active = models.BooleanField(default=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['auto_deactivate_date']),
        ]
    
    def __str__(self):
        return self.email
    
    def set_auto_deactivation(self):
        """
        Set fixed auto-deactivation date based on first login
        """
        from django.conf import settings
        
        # Check if we should deactivate admins
        deactivate_admins = getattr(settings, 'AUTO_DEACTIVATE_ADMINS', False)
        
        # Skip for superusers if deactivate_admins is False
        if self.is_superuser and not deactivate_admins:
            return
        
        if not self.first_login_date:
            self.first_login_date = timezone.now()
            
            if getattr(settings, 'AUTO_DEACTIVATE_USERS', False):
                deactivation_days = getattr(settings, 'AUTO_DEACTIVATE_DAYS', 30)
                self.auto_deactivate_date = self.first_login_date + timedelta(days=deactivation_days)
                self.enable_auto_deactivation = True
        
        self.save(update_fields=['first_login_date', 'auto_deactivate_date', 'enable_auto_deactivation'])
    
    def update_last_login(self):
        """Update last login timestamp only"""
        self.last_login_date = timezone.now()
        self.save(update_fields=['last_login_date'])
    
    def check_and_deactivate(self):
        """
        Check if user should be auto-deactivated based on fixed date
        SKIP for superusers (admins)
        """
        # Skip auto-deactivation for superusers
        if self.is_superuser:
            return False
        
        if self.enable_auto_deactivation and self.auto_deactivate_date and self.is_active:
            if timezone.now() >= self.auto_deactivate_date:
                self.is_active = False
                self.save(update_fields=['is_active'])
                return True
        return False
    
    def get_days_remaining(self):
        """
        Get number of days remaining before deactivation
        Returns None for superusers (no expiry)
        """
        # Superusers (admins) never expire
        if self.is_superuser:
            return None
        
        if self.auto_deactivate_date and self.is_active:
            remaining = self.auto_deactivate_date - timezone.now()
            return max(0, remaining.days)
        return None