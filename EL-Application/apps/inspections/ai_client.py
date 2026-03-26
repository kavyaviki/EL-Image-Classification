# inspections/ai_client.py
"""
AI Service Client - Handles all communication between Django and the FastAPI AI service.
This is the bridge that allows Django to send images to the AI service and retrieve results.
"""

import boto3
import requests
import json
import logging
from django.conf import settings
from botocore.exceptions import ClientError

# Set up logging for debugging and monitoring
logger = logging.getLogger(__name__)


class AIServiceClient:
    """
    Client class for interacting with the EL Image AI service.
    
    This class handles:
    1. Sending images to the AI service (submit_images)
    2. Checking processing status (check_status)
    3. Retrieving results from S3 (get_results_from_s3)
    4. Generating presigned URLs for private images (get_presigned_image_url)
    """
    
    def __init__(self):
        """
        Initialize the client with connections to both AI service and AWS S3.
        
        This runs automatically when you create a new AIServiceClient object.
        It sets up:
        - AI service URL (FastAPI endpoint)
        - S3 client for accessing stored images and results
        """
        # ============================================================
        # AI SERVICE CONNECTION
        # ============================================================
        # Get the base URL from Django settings (e.g., http://localhost:8001)
        # Remove trailing slash to avoid double slashes when joining paths
        self.base_url = settings.AI_SERVICE_URL.rstrip('/')
        
        # ============================================================
        # AWS S3 CONNECTION
        # ============================================================
        # Create S3 client using credentials from Django settings
        # This allows Django to read/write to your S3 bucket
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION
        )
        
        # Store bucket name for later use in S3 operations
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        
        # Log successful initialization (for debugging)
        logger.info(f"✅ AIServiceClient initialized - Bucket: {self.bucket_name}, AI URL: {self.base_url}")
    
    # ============================================================
    # METHOD 1: Submit Images to AI Service
    # ============================================================
    def submit_images(self, files):
        """
        Send images to the AI service for processing.
        
        This method is called when a user uploads images. It forwards the images
        to the FastAPI AI service, which then:
        1. Uploads images to S3
        2. Queues them for processing via SQS
        3. Returns a job_id for tracking
        
        Args:
            files: List of file objects from request.FILES (uploaded images)
            
        Returns:
            dict or None: 
                - On success: Dictionary with job_id, status, etc.
                  Example: {
                      "success": True,
                      "job_id": "99a59843-8ac2-4c4a-aa94-9d2d0f69151d",
                      "status": "queued",
                      "file_count": 1,
                      "status_check_url": "/EL-Image-AI/status/99a59843-..."
                  }
                - On failure: None
        """
        try:
            # ============================================================
            # Prepare files for multipart/form-data upload
            # ============================================================
            files_payload = []
            for file in files:
                # Reset file pointer to beginning (important after previous reads)
                file.seek(0)
                
                # Format: ('field_name', (filename, file_content, content_type))
                files_payload.append(
                    ('files', (file.name, file.read(), file.content_type))
                )
            
            logger.info(f"📤 Submitting {len(files)} images to AI service at {self.base_url}/EL-Image-AI")
            
            # ============================================================
            # Make HTTP POST request to FastAPI endpoint
            # ============================================================
            response = requests.post(
                f"{self.base_url}/EL-Image-AI",
                files=files_payload,
                timeout=30  # Wait up to 30 seconds for response
            )
            
            # ============================================================
            # Handle response
            # ============================================================
            if response.status_code in [200, 202]:
                # Success: Return the JSON response
                data = response.json()
                logger.info(f"✅ Images submitted successfully. Job ID: {data.get('job_id')}")
                return data
            else:
                # Failure: Log error and return None
                logger.error(f"❌ AI service error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.ConnectionError:
            # AI service not running
            logger.error(f"❌ Cannot connect to AI service at {self.base_url}. Is it running?")
            return None
        except Exception as e:
            # Any other error
            logger.error(f"❌ Failed to submit to AI service: {e}")
            return None
    
    # ============================================================
    # METHOD 2: Check Status via AI Service Endpoint
    # ============================================================
    def check_status(self, job_id):
        """
        Check the status of a processing job by calling the AI service's status endpoint.
        
        Note: Your AI service currently returns 501 (Not Implemented) for this endpoint.
        The actual results are retrieved from S3 via get_results_from_s3() instead.
        
        Args:
            job_id: The UUID of the processing job to check
            
        Returns:
            dict or None: Status information from AI service, or None if failed
        """
        try:
            # Make GET request to status endpoint
            response = requests.get(
                f"{self.base_url}/EL-Image-AI/status/{job_id}"
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"❌ Status check failed: {e}")
            return None
    
    # ============================================================
    # METHOD 3: Fetch Results Directly from S3
    # ============================================================
    def get_results_from_s3(self, job_id, filename):
        """
        Fetch AI results directly from S3 storage.
        
        This is the primary method for retrieving processing results.
        The AI service writes results to S3 at:
            s3://{bucket}/jobs/{job_id}/output/{filename}.json
        
        Called by:
        - The polling worker (poll_ai_results.py) to check for completed jobs
        - The detail view (inspection_detail) when user views a pending inspection
        
        Args:
            job_id: The UUID of the processing job
            filename: Original filename (e.g., "image11.jpg")
            
        Returns:
            dict or None:
                - On success: Dictionary with AI results
                  Example: {
                      "prediction": "good",
                      "confidence": 0.9355,
                      "above_threshold": True,
                      "processed_at": "2026-03-23T10:30:45Z"
                  }
                - On failure (not ready or error): None
        """
        try:
            # ============================================================
            # Construct the S3 key where results are stored
            # ============================================================
            # Remove file extension and add .json
            # Example: "image11.jpg" -> "image11.jpg.json"
            base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
            result_key = f"jobs/{job_id}/output/{base_name}.jpg.json"
            
            # Debug print to show what we're looking for
            print(f"   📍 Looking for: s3://{self.bucket_name}/{result_key}")
            
            # ============================================================
            # Try to fetch the result file from S3
            # ============================================================
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=result_key
            )
            
            # Parse JSON results
            results = json.loads(response['Body'].read())
            print(f"   ✅ Found results in S3")
            logger.info(f"✅ Retrieved results from S3 for job {job_id}")
            return results
            
        except ClientError as e:
            # Handle AWS-specific errors
            if e.response['Error']['Code'] == 'NoSuchKey':
                # File doesn't exist yet - results not ready
                print(f"   ⏳ Results file not ready yet")
                logger.debug(f"Results not ready for job {job_id}, file {filename}")
            else:
                # Other AWS error (permissions, bucket not found, etc.)
                print(f"   ❌ S3 error: {e}")
                logger.error(f"❌ S3 error: {e}")
            return None
        except Exception as e:
            # Handle any other errors (JSON parsing, etc.)
            print(f"   ❌ Error: {e}")
            logger.error(f"❌ Failed to get results from S3: {e}")
            return None
    
    # ============================================================
    # METHOD 4: Generate Presigned URL for Private Images
    # ============================================================
    def get_presigned_image_url(self, s3_key, expiration=3600):
        """
        Generate a temporary URL that allows access to a private S3 image.
        
        This is used for displaying images from private S3 buckets.
        The generated URL is valid only for the specified duration.
        
        Why use presigned URLs?
        - S3 bucket is private (Block all public access = ON)
        - Users cannot access images directly
        - This creates a temporary, authenticated URL that expires
        
        Called by:
        - serve_image view in views.py when displaying an image
        
        Args:
            s3_key: The S3 key/path to the image
                    Example: "jobs/123/input/image11.jpg"
            expiration: How long the URL is valid (in seconds)
                        Default: 3600 seconds = 1 hour
            
        Returns:
            str or None:
                - On success: Temporary URL string
                  Example: "https://solar-el-images.s3.ap-south-1.amazonaws.com/...?AWSAccessKeyId=..."
                - On failure: None
        """
        try:
            # Generate presigned URL using AWS SDK
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=expiration
            )
            logger.debug(f"🔑 Generated presigned URL for {s3_key} (expires in {expiration}s)")
            return url
        except Exception as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            return None