
import boto3
from botocore.client import Config

def list_objects():
    print("Listing objects in MinIO 'lake-data'...")
    try:
        s3 = boto3.resource('s3',
                    endpoint_url='http://localhost:9000',
                    aws_access_key_id='admin',
                    aws_secret_access_key='password',
                    config=Config(signature_version='s3v4')
        )
        bucket = s3.Bucket('lake-data')
        count = 0
        for obj in bucket.objects.all():
            print(f" - {obj.key}")
            count += 1
            if count > 10:
                print("... (truncated)")
                break
        
        if count == 0:
            print("⚠️ Bucket is empty!")
            
    except Exception as e:
        print(f"❌ Failed to list objects: {e}")

if __name__ == "__main__":
    list_objects()
