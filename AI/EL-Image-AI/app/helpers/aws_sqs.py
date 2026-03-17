# # app/helpers/aws_sqs.py
# """
# SQS message handling utilities for the EL Image AI service.
# Provides functions to send messages to SQS queue for async processing.
# """

# import boto3
# import json
# import logging
# from datetime import datetime
# from botocore.exceptions import ClientError, BotoCoreError
# from typing import Optional, Dict, Any
# from app.core.config import settings

# # Configure logging
# logger = logging.getLogger(__name__)

# # Initialize SQS client with error handling
# try:
#     sqs_client = boto3.client(
#         "sqs", 
#         region_name=settings.AWS_REGION,
#         # Optional: Add retry configuration
#         config=boto3.session.Config(
#             retries={'max_attempts': 3, 'mode': 'adaptive'}
#         )
#     )
#     logger.info(f"SQS client initialized for region: {settings.AWS_REGION}")
# except Exception as e:
#     logger.error(f"Failed to initialize SQS client: {e}")
#     sqs_client = None


# def send_image_to_queue(
#     job_id: str, 
#     image_key: str, 
#     filename: str, 
#     output_prefix: str, 
#     threshold: float,
#     metadata: Optional[Dict[str, Any]] = None
# ) -> bool:
#     """
#     Send a message to SQS queue for async image processing.
    
#     Args:
#         job_id: Unique identifier for the job batch
#         image_key: S3 key where the image is stored
#         filename: Original filename of the image
#         output_prefix: S3 prefix for output results
#         threshold: Confidence threshold for classification
#         metadata: Optional additional metadata to include in message
        
#     Returns:
#         bool: True if message sent successfully, False otherwise
        
#     Raises:
#         Various exceptions are caught and logged, returns False on failure
#     """
    
#     # Check if SQS client is available
#     if sqs_client is None:
#         logger.error("SQS client not initialized. Cannot send message.")
#         return False
    
#     # Validate required settings
#     if not settings.SQS_QUEUE_URL:
#         logger.error("SQS_QUEUE_URL is not configured in settings")
#         return False
    
#     # Prepare message with all relevant data
#     message = {
#         "job_id": job_id,
#         "image_key": image_key,
#         "filename": filename,
#         "output_key": f"{output_prefix}{filename}.json",
#         "confidence_threshold": threshold,
#         "timestamp": datetime.utcnow().isoformat() + "Z",
#         "version": "1.0",  # Message schema version
#     }
    
#     # Add optional metadata if provided
#     if metadata:
#         message["metadata"] = metadata
    
#     try:
#         # Send message to SQS
#         response = sqs_client.send_message(
#             QueueUrl=settings.SQS_QUEUE_URL,
#             MessageBody=json.dumps(message, default=str),  # default=str handles datetime objects
#             MessageAttributes={
#                 'job_id': {
#                     'DataType': 'String',
#                     'StringValue': job_id
#                 },
#                 'filename': {
#                     'DataType': 'String',
#                     'StringValue': filename
#                 },
#                 'threshold': {
#                     'DataType': 'Number',
#                     'StringValue': str(threshold)
#                 }
#             }
#         )
        
#         # Log success with message ID
#         message_id = response.get('MessageId', 'unknown')
#         logger.info(f"Successfully queued {filename} for job {job_id} - MessageId: {message_id}")
        
#         return True
        
#     except ClientError as e:
#         # Handle AWS-specific errors
#         error_code = e.response.get('Error', {}).get('Code', 'Unknown')
#         error_message = e.response.get('Error', {}).get('Message', str(e))
#         logger.error(f"AWS SQS error sending message for {filename}: {error_code} - {error_message}")
        
#         # Specific handling for common errors
#         if error_code == 'AccessDenied':
#             logger.error("Access denied to SQS queue. Check IAM permissions.")
#         elif error_code == 'QueueDoesNotExist':
#             logger.error(f"SQS queue does not exist: {settings.SQS_QUEUE_URL}")
#         elif error_code == 'InvalidClientTokenId':
#             logger.error("Invalid AWS credentials. Check AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY.")
        
#         return False
        
#     except BotoCoreError as e:
#         # Handle boto3 core errors (connection issues, etc.)
#         logger.error(f"AWS SDK error sending message for {filename}: {e}")
#         return False
        
#     except json.JSONEncodeError as e:
#         # Handle JSON serialization errors
#         logger.error(f"JSON encoding error for message: {e}")
#         return False
        
#     except Exception as e:
#         # Catch any other unexpected errors
#         logger.error(f"Unexpected error sending message to SQS for {filename}: {e}", exc_info=True)
#         return False


# def send_batch_to_queue(messages: list) -> Dict[str, Any]:
#     """
#     Send multiple messages to SQS in a batch (up to 10 messages per batch).
    
#     Args:
#         messages: List of tuples (job_id, image_key, filename, output_prefix, threshold)
        
#     Returns:
#         Dict with success/failure counts and details
#     """
#     if sqs_client is None:
#         logger.error("SQS client not initialized. Cannot send batch messages.")
#         return {"success": 0, "failed": len(messages), "errors": ["SQS client not initialized"]}
    
#     if not messages:
#         return {"success": 0, "failed": 0, "errors": []}
    
#     # SQS batch limit is 10 messages
#     batch_size = 10
#     results = {
#         "success": 0,
#         "failed": 0,
#         "errors": [],
#         "successful_ids": []
#     }
    
#     for i in range(0, len(messages), batch_size):
#         batch = messages[i:i+batch_size]
#         entries = []
        
#         for idx, (job_id, image_key, filename, output_prefix, threshold, metadata) in enumerate(batch):
#             message = {
#                 "job_id": job_id,
#                 "image_key": image_key,
#                 "filename": filename,
#                 "output_key": f"{output_prefix}{filename}.json",
#                 "confidence_threshold": threshold,
#                 "timestamp": datetime.utcnow().isoformat() + "Z",
#             }
            
#             if metadata:
#                 message["metadata"] = metadata
            
#             entries.append({
#                 'Id': str(idx),
#                 'MessageBody': json.dumps(message, default=str),
#                 'MessageAttributes': {
#                     'job_id': {
#                         'DataType': 'String',
#                         'StringValue': job_id
#                     },
#                     'filename': {
#                         'DataType': 'String',
#                         'StringValue': filename
#                     }
#                 }
#             })
        
#         try:
#             response = sqs_client.send_message_batch(
#                 QueueUrl=settings.SQS_QUEUE_URL,
#                 Entries=entries
#             )
            
#             # Count successful messages
#             successful = response.get('Successful', [])
#             failed = response.get('Failed', [])
            
#             results["success"] += len(successful)
#             results["failed"] += len(failed)
            
#             for succ in successful:
#                 results["successful_ids"].append(succ.get('MessageId'))
            
#             for fail in failed:
#                 results["errors"].append({
#                     'code': fail.get('Code'),
#                     'message': fail.get('Message'),
#                     'filename': batch[int(fail.get('Id'))][2] if fail.get('Id') else 'unknown'
#                 })
                
#         except Exception as e:
#             logger.error(f"Error sending batch: {e}")
#             results["failed"] += len(batch)
#             results["errors"].append(f"Batch error: {str(e)}")
    
#     logger.info(f"Batch send complete: {results['success']} succeeded, {results['failed']} failed")
#     return results


# def get_queue_attributes() -> Optional[Dict[str, Any]]:
#     """
#     Get SQS queue attributes (message count, etc.)
    
#     Returns:
#         Dict of queue attributes or None if error
#     """
#     if sqs_client is None:
#         logger.error("SQS client not initialized")
#         return None
    
#     try:
#         response = sqs_client.get_queue_attributes(
#             QueueUrl=settings.SQS_QUEUE_URL,
#             AttributeNames=['All']
#         )
#         return response.get('Attributes', {})
#     except Exception as e:
#         logger.error(f"Error getting queue attributes: {e}")
#         return None


# def get_queue_message_count() -> Optional[int]:
#     """
#     Get approximate number of messages in the queue.
    
#     Returns:
#         Approximate message count or None if error
#     """
#     attrs = get_queue_attributes()
#     if attrs:
#         try:
#             return int(attrs.get('ApproximateNumberOfMessages', 0))
#         except (ValueError, TypeError):
#             return 0
#     return None


# # Optional: Add a test function for debugging
# def test_sqs_connection() -> bool:
#     """
#     Test SQS connection by sending a simple test message.
    
#     Returns:
#         bool: True if connection works, False otherwise
#     """
#     if sqs_client is None:
#         logger.error("SQS client not initialized")
#         return False
    
#     try:
#         # Just check queue attributes as a lightweight test
#         response = sqs_client.get_queue_attributes(
#             QueueUrl=settings.SQS_QUEUE_URL,
#             AttributeNames=['QueueArn']
#         )
#         queue_arn = response.get('Attributes', {}).get('QueueArn')
#         logger.info(f"SQS connection test successful. Queue ARN: {queue_arn}")
#         return True
#     except Exception as e:
#         logger.error(f"SQS connection test failed: {e}")
#         return False


# # Run test when module is executed directly
# if __name__ == "__main__":
#     # Configure basic logging for testing
#     logging.basicConfig(level=logging.INFO)
    
#     print("Testing SQS connection...")
#     if test_sqs_connection():
#         print("✓ SQS connection successful")
#         count = get_queue_message_count()
#         print(f"✓ Approximate messages in queue: {count}")
#     else:
#         print("✗ SQS connection failed")










# app/helpers/aws_sqs.py
import boto3
import json
import logging
import hashlib
from datetime import datetime
from botocore.exceptions import ClientError, BotoCoreError
from typing import Optional, Dict, Any, List
from app.core.config import settings

logger = logging.getLogger(__name__)

# Create SQS client with explicit credentials from settings
def get_sqs_client():
    """Get SQS client with credentials from settings"""
    try:
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            sqs = boto3.client(
                "sqs",
                region_name=settings.AWS_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
            logger.info("SQS client created with credentials from settings")
        else:
            sqs = boto3.client("sqs", region_name=settings.AWS_REGION)
            logger.info("SQS client created with default credentials")
        return sqs
    except Exception as e:
        logger.error(f"Failed to create SQS client: {e}")
        raise

# Initialize SQS client
sqs_client = get_sqs_client()

def is_fifo_queue() -> bool:
    """Check if the configured queue is a FIFO queue"""
    return settings.SQS_QUEUE_URL.endswith('.fifo')

def generate_deduplication_id(filename: str, job_id: str) -> str:
    """Generate a unique deduplication ID for FIFO queues"""
    content = f"{job_id}-{filename}-{datetime.utcnow().isoformat()}"
    return hashlib.sha256(content.encode()).hexdigest()

def send_image_to_queue(
    job_id: str, 
    image_key: str, 
    filename: str, 
    output_prefix: str, 
    threshold: float,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Send a message to SQS queue for async image processing.
    Supports both Standard and FIFO queues.
    """
    
    if sqs_client is None:
        logger.error("SQS client not initialized. Cannot send message.")
        return False
    
    if not settings.SQS_QUEUE_URL:
        logger.error("SQS_QUEUE_URL is not configured in settings")
        return False
    
    # Prepare message body
    message = {
        "job_id": job_id,
        "image_key": image_key,
        "filename": filename,
        "output_key": f"{output_prefix}{filename}.json",
        "confidence_threshold": threshold,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0",
    }
    
    if metadata:
        message["metadata"] = metadata
    
    # Prepare base send parameters
    send_params = {
        'QueueUrl': settings.SQS_QUEUE_URL,
        'MessageBody': json.dumps(message, default=str),
        'MessageAttributes': {
            'job_id': {
                'DataType': 'String',
                'StringValue': job_id
            },
            'filename': {
                'DataType': 'String',
                'StringValue': filename
            },
            'threshold': {
                'DataType': 'Number',
                'StringValue': str(threshold)
            }
        }
    }
    
    # Add FIFO-specific parameters if needed
    if is_fifo_queue():
        # MessageGroupId is REQUIRED for FIFO queues
        send_params['MessageGroupId'] = f"job-{job_id}"
        
        # MessageDeduplicationId is REQUIRED if content-based deduplication is NOT enabled
        # Generate a unique ID based on content to prevent duplicate processing
        send_params['MessageDeduplicationId'] = generate_deduplication_id(filename, job_id)
        
        logger.debug(f"FIFO queue detected. Added MessageGroupId and MessageDeduplicationId")
    
    try:
        # Send message to SQS
        response = sqs_client.send_message(**send_params)
        
        message_id = response.get('MessageId', 'unknown')
        logger.info(f"✅ Successfully queued {filename} for job {job_id} - MessageId: {message_id}")
        
        return True
        
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        logger.error(f"❌ AWS SQS error sending message for {filename}: {error_code} - {error_message}")
        
        # Specific handling for FIFO queue errors
        if error_code == 'MissingParameter' and 'MessageGroupId' in error_message:
            logger.error("   → FIFO queue requires MessageGroupId parameter")
        elif error_code == 'InvalidParameterValue' and 'DeduplicationId' in error_message:
            logger.error("   → FIFO queue requires MessageDeduplicationId parameter")
        elif error_code == 'AccessDenied':
            logger.error("   → Access denied to SQS queue. Check IAM permissions.")
        elif error_code == 'QueueDoesNotExist':
            logger.error(f"   → SQS queue does not exist: {settings.SQS_QUEUE_URL}")
        
        return False
        
    except BotoCoreError as e:
        logger.error(f"❌ AWS SDK error sending message for {filename}: {e}")
        return False
        
    except Exception as e:
        logger.error(f"❌ Unexpected error sending message to SQS for {filename}: {e}", exc_info=True)
        return False


def send_batch_to_queue(messages: List[tuple]) -> Dict[str, Any]:
    """
    Send multiple messages to SQS in a batch (up to 10 messages per batch).
    Supports both Standard and FIFO queues.
    
    Args:
        messages: List of tuples (job_id, image_key, filename, output_prefix, threshold, metadata)
        
    Returns:
        Dict with success/failure counts and details
    """
    if sqs_client is None:
        logger.error("SQS client not initialized. Cannot send batch messages.")
        return {"success": 0, "failed": len(messages), "errors": ["SQS client not initialized"]}
    
    if not messages:
        return {"success": 0, "failed": 0, "errors": []}
    
    # Note: FIFO queues have limitations with batch operations
    if is_fifo_queue():
        logger.info("FIFO queue detected - processing messages individually (batch not fully supported)")
        # Process individually for FIFO queues
        results = {"success": 0, "failed": 0, "errors": [], "successful_ids": []}
        for msg in messages:
            job_id, image_key, filename, output_prefix, threshold, metadata = msg
            success = send_image_to_queue(job_id, image_key, filename, output_prefix, threshold, metadata)
            if success:
                results["success"] += 1
            else:
                results["failed"] += 1
                results["errors"].append(f"Failed to queue {filename}")
        return results
    
    # For standard queues, use batch send
    # SQS batch limit is 10 messages
    batch_size = 10
    results = {
        "success": 0,
        "failed": 0,
        "errors": [],
        "successful_ids": []
    }
    
    for i in range(0, len(messages), batch_size):
        batch = messages[i:i+batch_size]
        entries = []
        
        for idx, (job_id, image_key, filename, output_prefix, threshold, metadata) in enumerate(batch):
            message = {
                "job_id": job_id,
                "image_key": image_key,
                "filename": filename,
                "output_key": f"{output_prefix}{filename}.json",
                "confidence_threshold": threshold,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            
            if metadata:
                message["metadata"] = metadata
            
            entries.append({
                'Id': str(idx),
                'MessageBody': json.dumps(message, default=str),
                'MessageAttributes': {
                    'job_id': {
                        'DataType': 'String',
                        'StringValue': job_id
                    },
                    'filename': {
                        'DataType': 'String',
                        'StringValue': filename
                    }
                }
            })
        
        try:
            response = sqs_client.send_message_batch(
                QueueUrl=settings.SQS_QUEUE_URL,
                Entries=entries
            )
            
            successful = response.get('Successful', [])
            failed = response.get('Failed', [])
            
            results["success"] += len(successful)
            results["failed"] += len(failed)
            
            for succ in successful:
                results["successful_ids"].append(succ.get('MessageId'))
            
            for fail in failed:
                results["errors"].append({
                    'code': fail.get('Code'),
                    'message': fail.get('Message'),
                    'filename': batch[int(fail.get('Id'))][2] if fail.get('Id') else 'unknown'
                })
                
        except Exception as e:
            logger.error(f"Error sending batch: {e}")
            results["failed"] += len(batch)
            results["errors"].append(f"Batch error: {str(e)}")
    
    logger.info(f"Batch send complete: {results['success']} succeeded, {results['failed']} failed")
    return results


def get_queue_attributes() -> Optional[Dict[str, Any]]:
    """Get SQS queue attributes"""
    if sqs_client is None:
        logger.error("SQS client not initialized")
        return None
    
    try:
        response = sqs_client.get_queue_attributes(
            QueueUrl=settings.SQS_QUEUE_URL,
            AttributeNames=['All']
        )
        return response.get('Attributes', {})
    except Exception as e:
        logger.error(f"Error getting queue attributes: {e}")
        return None


def get_queue_type() -> str:
    """Determine if queue is FIFO or Standard"""
    return "FIFO" if is_fifo_queue() else "Standard"


# Optional: Test function
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"Queue URL: {settings.SQS_QUEUE_URL}")
    print(f"Queue Type: {get_queue_type()}")
    print(f"Is FIFO: {is_fifo_queue()}")