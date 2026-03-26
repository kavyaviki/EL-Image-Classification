# apps/users/management/commands/deactivate_expired_users.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.users.models import User
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Deactivate users whose auto-deactivation date has passed'
    
    def handle(self, *args, **options):
        self.stdout.write("Checking for expired users...")
        
        # Find users with auto_deactivate_date in the past
        expired_users = User.objects.filter(
            auto_deactivate_date__lte=timezone.now(),
            is_active=True,
            enable_auto_deactivation=True
        )
        
        count = expired_users.count()
        
        for user in expired_users:
            user.is_active = False
            user.save()
            self.stdout.write(f"Deactivated user: {user.email} (ID: {user.id})")
        
        self.stdout.write(self.style.SUCCESS(f"Deactivated {count} users."))