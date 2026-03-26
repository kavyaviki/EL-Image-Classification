from django.core.management.base import BaseCommand
from apps.inspections.models import Inspection
from apps.inspections.ai_client import AIServiceClient
import time
import logging
import sys

# Configure logging to show in console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Poll AI service for completed jobs'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=' * 50))
        self.stdout.write(self.style.SUCCESS('🚀 Starting poll_ai_results worker...'))
        self.stdout.write(self.style.SUCCESS('=' * 50))
        
        client = AIServiceClient()
        loop_count = 0
        
        while True:
            try:
                loop_count += 1
                self.stdout.write(f"\n[{time.strftime('%H:%M:%S')}] Polling cycle #{loop_count}")
                
                # Get inspections that are still queued/processing
                inspections = Inspection.objects.filter(
                    status__in=['queued', 'processing']
                ).exclude(job_id__isnull=True)
                
                count = inspections.count()
                if count > 0:
                    self.stdout.write(self.style.WARNING(f"📊 Found {count} inspections to check"))
                else:
                    self.stdout.write(self.style.WARNING("📊 No pending inspections found"))
                
                for inspection in inspections:
                    self.stdout.write(f"\n🔍 Checking job {inspection.job_id} for {inspection.name}")
                    self.stdout.write(f"   Current status: {inspection.status}")
                    
                    # Try to fetch results from S3
                    results = client.get_results_from_s3(
                        str(inspection.job_id),
                        inspection.name
                    )
                    
                    if results:
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Results found!"))
                        self.stdout.write(f"      Prediction: {results.get('prediction')}")
                        self.stdout.write(f"      Confidence: {results.get('confidence')}")
                        
                        # Update inspection
                        inspection.status = 'completed'
                        inspection.ai_classification = results.get('prediction')
                        inspection.ai_confidence = results.get('confidence')
                        inspection.ai_processed_at = results.get('processed_at')
                        inspection.save()
                        
                        self.stdout.write(self.style.SUCCESS(f"   ✅ Updated inspection {inspection.id}"))
                    else:
                        self.stdout.write(f"   ⏳ No results yet for {inspection.name}")
                
                # Wait before next poll
                self.stdout.write(f"\n💤 Waiting 5 seconds before next poll...")
                time.sleep(5)
                
            except KeyboardInterrupt:
                self.stdout.write(self.style.WARNING('\n\n👋 Stopping poll_ai_results worker...'))
                break
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"\n❌ Error: {e}"))
                import traceback
                traceback.print_exc()
                self.stdout.write(f"\n💤 Waiting 10 seconds before retrying...")
                time.sleep(10)