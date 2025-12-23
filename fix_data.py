
import trino
from trino.dbapi import connect
import boto3
from botocore.client import Config
import time

def setup_data():
    print("🌍 Connecting to Trino...")
    conn = connect(host="localhost", port=8080, user="admin", catalog="iceberg", schema="public")
    cur = conn.cursor()
    
    print("📂 Ensuring schema 'public' exists...")
    cur.execute("CREATE SCHEMA IF NOT EXISTS iceberg.public WITH (location = 's3://lake-data/data/')")
    
    print("🗑️ Dropping table users...")
    cur.execute("DROP TABLE IF EXISTS users")
    
    print("🔨 Creating table users...")
    cur.execute("""
        CREATE TABLE users (
            id varchar,
            name varchar,
            role varchar
        )
    """)
    
    print("📥 Inserting data...")
    val_str = ", ".join([f"('{i}', 'User{i}', 'User')" for i in range(10)])
    cur.execute(f"INSERT INTO users VALUES {val_str}")
    
    # Wait for file write
    time.sleep(2)
    print("✅ Data inserted.")

def find_parquet_path():
    print("🔍 Searching MinIO for parquet files...")
    s3 = boto3.resource('s3',
                endpoint_url='http://localhost:9000',
                aws_access_key_id='admin',
                aws_secret_access_key='password',
                config=Config(signature_version='s3v4')
    )
    bucket = s3.Bucket('lake-data')
    found = False
    for obj in bucket.objects.all():
        if "users" in obj.key and obj.key.endswith(".parquet"):
            print(f"🎯 FOUND: {obj.key}")
            found = True
            # We assume structure is public/users/data/...
            # Let's guess the glob pattern for Router
            return
    if not found:
        print("❌ No parquet files found for 'users'")

if __name__ == "__main__":
    setup_data()
    find_parquet_path()
