import trino
from trino.dbapi import connect
import time
import random
import boto3
from botocore.client import Config

def setup_demo_data():
    print("🌍 Connecting to Trino (Iceberg Catalog)...")
    try:
        conn = connect(host="localhost", port=8080, user="admin", catalog="iceberg", schema="public")
        cur = conn.cursor()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return

    print("🧹 Cleaning old data from S3 (lake-data)...")
    try:
        s3 = boto3.resource('s3',
                    endpoint_url='http://localhost:9000',
                    aws_access_key_id='admin',
                    aws_secret_access_key='password',
                    config=Config(signature_version='s3v4')
        )
        bucket = s3.Bucket('lake-data')
        bucket.objects.all().delete()
        print("   -> S3 Bucket cleaned.")
    except Exception as e:
        print(f"⚠️ S3 Cleanup failed: {e}")

    # 1. Schema
    print("📂 Ensuring schema 'iceberg.public' exists...")
    try:
        cur.execute("CREATE SCHEMA IF NOT EXISTS iceberg.public WITH (location = 's3://lake-data/data/')")
    except Exception as e:
        print(f"⚠️ Schema creation note: {e}")

    # 2. Users Table
    print("👤 Setting up 'users' table...")
    cur.execute("DROP TABLE IF EXISTS users")
    cur.execute("""
        CREATE TABLE users (
            id varchar,
            name varchar,
            role varchar
        )
    """)
    
    users_data = []
    roles = ['Admin', 'Editor', 'Viewer']
    for i in range(20):
        users_data.append(f"('{i}', 'User_{i}', '{random.choice(roles)}')")
    
    print(f"   -> Inserting {len(users_data)} users...")
    cur.execute(f"INSERT INTO users VALUES {', '.join(users_data)}")

    # 3. Events Table
    print("📅 Setting up 'events' table...")
    cur.execute("DROP TABLE IF EXISTS events")
    cur.execute("""
        CREATE TABLE events (
            event_id varchar,
            user_id varchar,
            event_type varchar,
            event_date timestamp
        )
    """)

    events_data = []
    event_types = ['login', 'view_page', 'click', 'purchase']
    for i in range(50):
        uid = random.randint(0, 19)
        etype = random.choice(event_types)
        # Random time in last 30 days
        days_ago = random.randint(0, 30)
        events_data.append(f"('evt_{i}', '{uid}', '{etype}', timestamp '2025-12-01 10:00:00' - interval '{days_ago}' day)")

    print(f"   -> Inserting {len(events_data)} events...")
    cur.execute(f"INSERT INTO events VALUES {', '.join(events_data)}")
    
    time.sleep(2) # Allow commit/IO
    print("✅ Demo Data Initialization Complete!")

if __name__ == "__main__":
    setup_demo_data()
