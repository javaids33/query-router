import boto3
from botocore.client import Config

def list_all_objects():
    print("🔍 Listing all objects in 'lake-data' bucket...")
    try:
        s3 = boto3.resource('s3',
                    endpoint_url='http://localhost:9000',
                    aws_access_key_id='admin',
                    aws_secret_access_key='password',
                    config=Config(signature_version='s3v4')
        )
        bucket = s3.Bucket('lake-data')
        for obj in bucket.objects.all():
            print(f"📄 {obj.key}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    list_all_objects()
