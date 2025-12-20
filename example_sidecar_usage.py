"""
Example Usage of DuckDB S3 Sidecar

This script demonstrates how to use the DuckDB sidecar to push data directly to S3
with automatic date-based partitioning.

Usage:
    python example_sidecar_usage.py
"""

import requests
import json
from datetime import datetime, timedelta
import time


SIDECAR_URL = "http://localhost:8001"


def check_health():
    """Check if the sidecar is running"""
    print("\n=== Checking Sidecar Health ===")
    try:
        response = requests.get(f"{SIDECAR_URL}/health")
        print(f"✅ Sidecar is healthy: {response.json()}")
        return True
    except Exception as e:
        print(f"❌ Sidecar is not available: {e}")
        return False


def example_batch_ingestion():
    """Example 1: Batch ingestion with automatic date partitioning"""
    print("\n=== Example 1: Batch Ingestion ===")
    
    # Prepare sample data
    data = {
        "table_name": "user_events",
        "records": [
            {"user_id": 1, "event_type": "login", "timestamp": "2025-12-20T10:00:00", "value": 100},
            {"user_id": 2, "event_type": "purchase", "timestamp": "2025-12-20T10:05:00", "value": 250},
            {"user_id": 3, "event_type": "logout", "timestamp": "2025-12-20T10:10:00", "value": 0},
            {"user_id": 1, "event_type": "view", "timestamp": "2025-12-20T10:15:00", "value": 50}
        ],
        "partition_date": "2025-12-20"  # Optional: defaults to today
    }
    
    print(f"📤 Sending {len(data['records'])} records to sidecar...")
    response = requests.post(f"{SIDECAR_URL}/ingest", json=data)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success! Data written to S3")
        print(f"   - S3 Path: {result['s3_path']}")
        print(f"   - Records: {result['record_count']}")
        print(f"   - Partition: {result['partition_date']}")
    else:
        print(f"❌ Failed: {response.text}")


def example_streaming_ingestion():
    """Example 2: Streaming ingestion with manual flush"""
    print("\n=== Example 2: Streaming Ingestion ===")
    
    table_name = "sensor_data"
    
    # Stream individual records
    print(f"📤 Streaming 5 sensor readings...")
    for i in range(5):
        record = {
            "data": {
                "sensor_id": f"sensor_{i+1}",
                "temperature": 20 + i * 2,
                "humidity": 50 + i * 5,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        response = requests.post(
            f"{SIDECAR_URL}/ingest/stream?table_name={table_name}",
            json=record
        )
        
        if response.status_code == 200:
            print(f"   ✓ Record {i+1} buffered")
        else:
            print(f"   ✗ Record {i+1} failed: {response.text}")
        
        time.sleep(0.1)  # Simulate streaming delay
    
    # Check buffered count
    print("\n📊 Checking buffered records...")
    response = requests.get(f"{SIDECAR_URL}/table/{table_name}/count")
    if response.status_code == 200:
        count = response.json()['buffered_count']
        print(f"   Buffered records: {count}")
    
    # Flush to S3
    print("\n💾 Flushing buffered records to S3...")
    response = requests.post(f"{SIDECAR_URL}/flush?table_name={table_name}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Flush successful!")
        print(f"   - S3 Path: {result['s3_path']}")
        print(f"   - Records: {result['record_count']}")


def example_historical_data():
    """Example 3: Loading historical data with custom date partitions"""
    print("\n=== Example 3: Historical Data with Date Partitions ===")
    
    # Simulate loading historical data for the past 3 days
    for days_ago in range(3, 0, -1):
        date = (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d")
        
        data = {
            "table_name": "daily_sales",
            "records": [
                {"date": date, "product_id": 101, "quantity": 5, "revenue": 500},
                {"date": date, "product_id": 102, "quantity": 3, "revenue": 300},
                {"date": date, "product_id": 103, "quantity": 7, "revenue": 700}
            ],
            "partition_date": date
        }
        
        print(f"📤 Loading data for {date}...")
        response = requests.post(f"{SIDECAR_URL}/ingest", json=data)
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Loaded to {result['s3_path']}")
        else:
            print(f"   ❌ Failed: {response.text}")


def example_multi_table():
    """Example 4: Working with multiple tables"""
    print("\n=== Example 4: Multiple Tables ===")
    
    # Ingest to multiple tables
    tables = ["orders", "inventory", "customers"]
    
    for table in tables:
        data = {
            "table_name": table,
            "records": [
                {"id": 1, "name": f"{table}_item_1", "value": 100},
                {"id": 2, "name": f"{table}_item_2", "value": 200}
            ]
        }
        
        print(f"📤 Ingesting to {table}...")
        response = requests.post(f"{SIDECAR_URL}/ingest", json=data)
        
        if response.status_code == 200:
            print(f"   ✅ Success")
        else:
            print(f"   ❌ Failed: {response.text}")
    
    # List all tables
    print("\n📋 Listing all tables...")
    response = requests.get(f"{SIDECAR_URL}/tables")
    if response.status_code == 200:
        tables = response.json()['tables']
        print(f"   Active tables: {', '.join(tables)}")


def show_usage_patterns():
    """Display common usage patterns"""
    print("\n" + "="*60)
    print("COMMON USAGE PATTERNS")
    print("="*60)
    
    patterns = [
        {
            "name": "Real-time Event Streaming",
            "description": "Stream events as they occur, flush periodically",
            "code": """
# In your application loop:
for event in event_stream:
    requests.post(
        "http://duckdb-sidecar:8001/ingest/stream?table_name=events",
        json={"data": event}
    )

# Every N minutes or N records:
requests.post("http://duckdb-sidecar:8001/flush?table_name=events")
            """
        },
        {
            "name": "Bulk Data Transfer",
            "description": "Transfer large batches efficiently",
            "code": """
# Load data from your database
records = fetch_data_from_db()

# Send to sidecar
requests.post(
    "http://duckdb-sidecar:8001/ingest",
    json={
        "table_name": "analytics",
        "records": records,
        "partition_date": "2025-12-20"
    }
)
            """
        },
        {
            "name": "Daily Data Pipeline",
            "description": "ETL pipeline with date partitioning",
            "code": """
# Daily job (runs at midnight)
today = datetime.now().strftime("%Y-%m-%d")
data = extract_daily_data()

requests.post(
    "http://duckdb-sidecar:8001/ingest",
    json={
        "table_name": "daily_metrics",
        "records": data,
        "partition_date": today
    }
)
            """
        }
    ]
    
    for i, pattern in enumerate(patterns, 1):
        print(f"\n{i}. {pattern['name']}")
        print(f"   {pattern['description']}")
        print(f"   Example code:")
        for line in pattern['code'].strip().split('\n'):
            print(f"   {line}")


def main():
    """Run all examples"""
    print("="*60)
    print("DuckDB S3 Sidecar - Usage Examples")
    print("="*60)
    
    if not check_health():
        print("\n⚠️  Make sure the sidecar is running:")
        print("   docker compose up -d duckdb-sidecar")
        return
    
    # Run examples
    try:
        example_batch_ingestion()
        time.sleep(1)
        
        example_streaming_ingestion()
        time.sleep(1)
        
        example_historical_data()
        time.sleep(1)
        
        example_multi_table()
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
    
    # Show patterns
    show_usage_patterns()
    
    print("\n" + "="*60)
    print("✅ Examples complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Check MinIO console: http://localhost:9001")
    print("2. Browse to lake-data bucket to see partitioned data")
    print("3. Query data using Trino or ClickHouse")
    print("4. View API docs: http://localhost:8001/docs")


if __name__ == "__main__":
    main()
