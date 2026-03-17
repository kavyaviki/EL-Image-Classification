# upload / download / presigned
# app\helpers\aws_s3.py
import boto3
from botocore.exceptions import ClientError
from app.core.config import settings
import uuid

s3_client = boto3.client("s3", region_name=settings.AWS_REGION)

def upload_image_to_s3(image_bytes: bytes, filename: str, job_id: str) -> str:
    key = f"jobs/{job_id}/input/{filename}"
    try:
        s3_client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=image_bytes,
            ContentType="image/jpeg"  # adjust if needed
        )
        return key
    except ClientError as e:
        raise RuntimeError(f"S3 upload failed: {e}")

def get_presigned_url(key: str, expires_in=3600) -> str:
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=expires_in
    )