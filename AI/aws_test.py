# aws_test.py
import os
import uuid
import boto3
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError

# Load environment variables
load_dotenv()

AWS_REGION = os.getenv("AWS_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

S3_BUCKET = os.getenv("S3_BUCKET")
S3_BUCKET_ARN = os.getenv("S3_BUCKET_ARN")

SQS_QUEUE_URL = os.getenv("SQS_QUEUE_URL")


def create_session():
    """Create AWS session"""
    return boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )


def validate_env():
    print("\n" + "=" * 50)
    print("🔍 ENV VALIDATION")
    print("=" * 50)

    required_vars = [
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_REGION",
        "S3_BUCKET",
        "SQS_QUEUE_URL"
    ]

    missing = [var for var in required_vars if not os.getenv(var)]

    if missing:
        print(f"❌ Missing env variables: {missing}")
        return False

    print("✅ All required env variables present")
    return True


def verify_s3(session):
    print("\n" + "=" * 50)
    print("🔍 S3 VERIFICATION")
    print("=" * 50)

    try:
        s3 = session.client("s3")

        # Check bucket access
        s3.head_bucket(Bucket=S3_BUCKET)
        print(f"✅ Bucket accessible: {S3_BUCKET}")
        print(f"   ARN: {S3_BUCKET_ARN}")

        # Upload test file
        test_key = f"test/{uuid.uuid4()}.txt"
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=test_key,
            Body="AWS S3 test file"
        )
        print("✅ Upload (put_object) successful")

        # Read test file
        s3.get_object(Bucket=S3_BUCKET, Key=test_key)
        print("✅ Read (get_object) successful")

        # Delete test file
        s3.delete_object(Bucket=S3_BUCKET, Key=test_key)
        print("✅ Delete (delete_object) successful")

        return True

    except NoCredentialsError:
        print("❌ No AWS credentials found")
    except ClientError as e:
        print(f"❌ S3 Error: {e.response['Error']['Code']} - {e.response['Error']['Message']}")

    return False


def verify_sqs(session):
    print("\n" + "=" * 50)
    print("🔍 SQS VERIFICATION")
    print("=" * 50)

    try:
        sqs = session.client("sqs")

        print(f"Queue URL: {SQS_QUEUE_URL}")

        # Get queue attributes
        attrs = sqs.get_queue_attributes(
            QueueUrl=SQS_QUEUE_URL,
            AttributeNames=["QueueArn"]
        )

        queue_arn = attrs["Attributes"].get("QueueArn")
        print(f"✅ GetQueueAttributes successful")
        print(f"   Queue ARN: {queue_arn}")

        # Send message (FIFO requires both fields)
        message_body = f"Test Message {uuid.uuid4()}"
        dedup_id = str(uuid.uuid4())

        send_resp = sqs.send_message(
            QueueUrl=SQS_QUEUE_URL,
            MessageBody=message_body,
            MessageGroupId="test-group",             # REQUIRED (FIFO)
            MessageDeduplicationId=dedup_id          # REQUIRED (if deduplication disabled)
        )
        print("✅ SendMessage successful")

        # Receive message
        receive_resp = sqs.receive_message(
            QueueUrl=SQS_QUEUE_URL,
            MaxNumberOfMessages=1,
            WaitTimeSeconds=2
        )

        if "Messages" in receive_resp:
            msg = receive_resp["Messages"][0]
            receipt_handle = msg["ReceiptHandle"]

            print("✅ ReceiveMessage successful")

            # Delete message
            sqs.delete_message(
                QueueUrl=SQS_QUEUE_URL,
                ReceiptHandle=receipt_handle
            )
            print("✅ DeleteMessage successful")
        else:
            print("⚠ No message received (FIFO delay possible)")

        return True

    except NoCredentialsError:
        print("❌ No AWS credentials found")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        msg = e.response["Error"]["Message"]

        print(f"❌ SQS Error: {code} - {msg}")

        if code == "AccessDenied":
            print("👉 Fix: Add IAM policy for SQS")
        elif code == "QueueDoesNotExist":
            print("👉 Fix: Check SQS_QUEUE_URL")
        elif code == "InvalidClientTokenId":
            print("👉 Fix: Invalid AWS credentials")
        elif code == "InvalidParameterValue":
            print("👉 Fix: FIFO queue requires MessageDeduplicationId")

    return False


def main():
    print("\n🚀 AWS FULL VERIFICATION STARTED")

    if not validate_env():
        return

    session = create_session()

    s3_ok = verify_s3(session)
    sqs_ok = verify_sqs(session)

    print("\n" + "=" * 50)
    print("📊 FINAL STATUS")
    print("=" * 50)

    if s3_ok and sqs_ok:
        print("🎉 ALL SERVICES WORKING PERFECTLY")
    else:
        print("⚠ SOME SERVICES FAILED — CHECK ABOVE ERRORS")


if __name__ == "__main__":
    main()