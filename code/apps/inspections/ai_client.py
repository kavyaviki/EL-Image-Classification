# # inspections/ai_client.py
# import requests
# import logging
# from django.conf import settings
# from typing import Dict, Any, Optional

# logger = logging.getLogger(__name__)

# class AIServiceClient:
#     """Client for interacting with the EL Image AI service"""
    
#     def __init__(self):
#         self.base_url = settings.AI_SERVICE_URL.rstrip('/')
#         self.api_endpoint = f"{self.base_url}/EL-Image-AI"
    
#     def submit_images(self, files):
#         """
#         Submit images to AI service
        
#         Args:
#             files: List of file objects from request.FILES
            
#         Returns:
#             Dict with job_id and other details from AI service
#         """
#         try:
#             # Prepare files for multipart upload
#             files_payload = []
#             for file in files:
#                 files_payload.append(
#                     ('files', (file.name, file.read(), file.content_type))
#                 )
            
#             # Make request to AI service
#             response = requests.post(
#                 self.api_endpoint,
#                 files=files_payload
#             )
            
#             if response.status_code in [200, 202]:
#                 data = response.json()
#                 logger.info(f"Images submitted successfully. Job ID: {data.get('job_id')}")
#                 return data
#             else:
#                 logger.error(f"AI service error: {response.status_code} - {response.text}")
#                 return None
                
#         except Exception as e:
#             logger.error(f"Failed to submit to AI service: {e}")
#             return None
    
#     def check_status(self, job_id: str) -> Optional[Dict[str, Any]]:
#         """
#         Check job status via AI service status endpoint
#         """
#         try:
#             response = requests.get(
#                 f"{self.base_url}/EL-Image-AI/status/{job_id}"
#             )
            
#             if response.status_code == 200:
#                 return response.json()
#             return None
#         except Exception as e:
#             logger.error(f"Status check failed: {e}")
#             return None
    
#     def get_results_from_s3(self, job_id: str, filename: str) -> Optional[Dict[str, Any]]:
#         """
#         Directly fetch results from S3 using boto3
#         (Alternative to polling the status endpoint)
#         """
#         import boto3
#         import json
#         from django.conf import settings
        
#         try:
#             s3 = boto3.client(
#                 's3',
#                 aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
#                 aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
#                 region_name=settings.AWS_S3_REGION
#             )
            
#             # Results are stored at: jobs/{job_id}/output/{filename}.json
#             result_key = f"jobs/{job_id}/output/{filename}.json"
            
#             response = s3.get_object(
#                 Bucket=settings.AWS_STORAGE_BUCKET_NAME,
#                 Key=result_key
#             )
            
#             results = json.loads(response['Body'].read())
#             logger.info(f"Retrieved results from S3 for job {job_id}")
#             return results
            
#         except Exception as e:
#             logger.error(f"Failed to get results from S3: {e}")
#             return None

# inspections/ai_client.py
import boto3
import requests
import json
import logging
from django.conf import settings
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class AIServiceClient:
    def __init__(self):
        self.base_url = settings.AI_SERVICE_URL.rstrip('/')
        
        # Use the correct setting names from your settings.py
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION  # Changed from S3_BUCKET to AWS_S3_REGION
        )
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME  # Changed from S3_BUCKET to AWS_STORAGE_BUCKET_NAME
    
    def submit_images(self, files):
        """Submit images to AI service"""
        try:
            files_payload = []
            for file in files:
                file.seek(0)  # Reset file pointer
                files_payload.append(
                    ('files', (file.name, file.read(), file.content_type))
                )
            
            response = requests.post(
                f"{self.base_url}/EL-Image-AI",
                files=files_payload
            )
            
            if response.status_code in [200, 202]:
                return response.json()
            else:
                logger.error(f"AI service error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to submit to AI service: {e}")
            return None
    
    def get_results_from_s3(self, job_id, filename):
        """
        Fetch results from S3
        Results are stored at: jobs/{job_id}/output/{filename}.json
        """
        try:
            # Remove extension and add .json
            base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
            result_key = f"jobs/{job_id}/output/{base_name}.jpg.json"
            
            print(f"   📍 Looking for: s3://{self.bucket_name}/{result_key}")
            
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=result_key
            )
            
            results = json.loads(response['Body'].read())
            print(f"   ✅ Found results in S3")
            return results
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                print(f"   ⏳ Results file not ready yet")
            else:
                print(f"   ❌ S3 error: {e}")
            return None
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def check_status(self, job_id):
        """Check job status via AI service"""
        try:
            response = requests.get(
                f"{self.base_url}/EL-Image-AI/status/{job_id}"
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return None