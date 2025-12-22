
import boto3
from botocore.client import Config

def create_bucket():
    print("Creating MinIO bucket 'lake-data'...")
    try:
        s3 = boto3.resource('s3',
                    endpoint_url='http://localhost:9000',
                    aws_access_key_id='admin',
                    aws_secret_access_key='password',
                    config=Config(signature_version='s3v4')
        )
        bucket = s3.Bucket('lake-data')
        if not bucket.creation_date:
            bucket.create()
            print("✅ Bucket 'lake-data' created.")
        else:
            print("ℹ️ Bucket 'lake-data' already exists.")
    except Exception as e:
        print(f"❌ Failed to create bucket: {e}")

if __name__ == "__main__":
    create_bucket()
