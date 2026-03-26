# # SQS consumer / polling loop
# # app\workers\inference.py
# import json
# import time
# import boto3
# from botocore.exceptions import ClientError
# from app.core.model import predict_image
# from app.core.config import settings
# import logging

# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("InferenceWorker")

# sqs = boto3.client("sqs", region_name=settings.AWS_REGION)
# s3 = boto3.client("s3", region_name=settings.AWS_REGION)

# def process_message(message):
#     body = json.loads(message["Body"])
#     receipt = message["ReceiptHandle"]

#     key = body["image_key"]
#     output_key = body["output_key"]
#     threshold = body.get("confidence_threshold", 0.7)

#     try:
#         obj = s3.get_object(Bucket=settings.S3_BUCKET, Key=key)
#         image_bytes = obj["Body"].read()

#         prediction, confidence = predict_image(image_bytes)

#         result = {
#             "filename": body["filename"],
#             "prediction": prediction,
#             "confidence": confidence,
#             "above_threshold": confidence >= threshold,
#             "processed_at": str(time.time())
#         }

#         s3.put_object(
#             Bucket=settings.S3_BUCKET,
#             Key=output_key,
#             Body=json.dumps(result, indent=2),
#             ContentType="application/json"
#         )

#         sqs.delete_message(QueueUrl=settings.SQS_QUEUE_URL, ReceiptHandle=receipt)
#         logger.info(f"Processed {body['filename']} → {prediction} ({confidence:.3f})")

#     except Exception as e:
#         logger.error(f"Failed {body['filename']}: {e}")
#         # Don't delete → visibility timeout will retry

# def start_worker():
#     logger.info("Starting EL Inference Worker")
#     while True:
#         try:
#             resp = sqs.receive_message(
#                 QueueUrl=settings.SQS_QUEUE_URL,
#                 MaxNumberOfMessages=10,
#                 WaitTimeSeconds=20,
#                 VisibilityTimeout=1800  # 30 min
#             )

#             messages = resp.get("Messages", [])
#             for msg in messages:
#                 process_message(msg)

#         except KeyboardInterrupt:
#             logger.info("Worker stopped")
#             break
#         except Exception as e:
#             logger.error(f"Polling error: {e}")
#             time.sleep(10)






# app/workers/inference.py
import json
import time
import boto3
from botocore.exceptions import ClientError
from app.core.model import predict_image
from app.core.config import settings
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InferenceWorker")

sqs = boto3.client("sqs", region_name=settings.AWS_REGION)
s3 = boto3.client("s3", region_name=settings.AWS_REGION)

def process_message(message):
    body = json.loads(message["Body"])
    receipt = message["ReceiptHandle"]

    key = body["image_key"]
    output_key = body["output_key"]
    threshold = body.get("confidence_threshold", 0.7)
    filename = body.get("filename", "unknown.jpg")
    job_id = body.get("job_id", "unknown")

    try:
        logger.info(f"Processing {filename} from job {job_id}")
        
        # Download image from S3
        obj = s3.get_object(Bucket=settings.S3_BUCKET, Key=key)
        image_bytes = obj["Body"].read()
        logger.info(f"Downloaded {len(image_bytes)} bytes from S3")

        # Run inference - NOW UNPACKING 3 VALUES
        prediction, confidence, above_threshold = predict_image(image_bytes, threshold)
        
        logger.info(f"Prediction for {filename}: {prediction} (confidence: {confidence:.4f}, above_threshold: {above_threshold})")

        # Prepare result
        result = {
            "job_id": job_id,
            "filename": filename,
            "prediction": prediction,
            "confidence": confidence,
            "above_threshold": above_threshold,
            "processed_at": datetime.utcnow().isoformat() + "Z",
            "s3_input_key": key,
            "s3_output_key": output_key
        }

        # Upload result to S3
        s3.put_object(
            Bucket=settings.S3_BUCKET,
            Key=output_key,
            Body=json.dumps(result, indent=2),
            ContentType="application/json"
        )
        logger.info(f"Uploaded results to S3: {output_key}")

        # Delete message from queue (only after successful processing)
        sqs.delete_message(QueueUrl=settings.SQS_QUEUE_URL, ReceiptHandle=receipt)
        logger.info(f"✅ Successfully processed and deleted message for {filename}")

    except Exception as e:
        logger.error(f"❌ Failed to process {filename}: {e}", exc_info=True)
        # Don't delete message - visibility timeout will retry

def start_worker():
    logger.info("🚀 Starting EL Inference Worker")
    logger.info(f"Polling SQS queue: {settings.SQS_QUEUE_URL}")
    
    while True:
        try:
            # Receive messages from SQS
            resp = sqs.receive_message(
                QueueUrl=settings.SQS_QUEUE_URL,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,  # Long polling
                VisibilityTimeout=1800  # 30 minutes
            )

            messages = resp.get("Messages", [])
            
            if messages:
                logger.info(f"Received {len(messages)} messages")
                for msg in messages:
                    process_message(msg)
            else:
                logger.debug("No messages received, waiting...")

        except KeyboardInterrupt:
            logger.info("👋 Worker stopped by user")
            break
        except Exception as e:
            logger.error(f"❌ Polling error: {e}", exc_info=True)
            time.sleep(10)  # Wait before retrying

if __name__ == "__main__":
    start_worker()