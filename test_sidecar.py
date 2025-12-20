#!/usr/bin/env python3
"""
Test Script for DuckDB S3 Sidecar

This script validates the complete functionality of the sidecar service.
Run this after starting the services with: docker compose up -d
"""

import requests
import json
import time
from datetime import datetime

SIDECAR_URL = "http://localhost:8001"

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def print_result(name, result):
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"{status} - {name}")

def test_health():
    """Test 1: Health check"""
    print_header("Test 1: Health Check")
    try:
        response = requests.get(f"{SIDECAR_URL}/health", timeout=5)
        data = response.json()
        print(json.dumps(data, indent=2))
        return response.status_code == 200 and data.get("status") == "healthy"
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_root_endpoint():
    """Test 2: Root endpoint info"""
    print_header("Test 2: Root Endpoint")
    try:
        response = requests.get(f"{SIDECAR_URL}/", timeout=5)
        data = response.json()
        print(f"Service: {data.get('service')}")
        print(f"Version: {data.get('version')}")
        print(f"Available endpoints: {len(data.get('endpoints', {}))}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_batch_ingestion():
    """Test 3: Batch data ingestion"""
    print_header("Test 3: Batch Ingestion")
    try:
        payload = {
            "table_name": "test_batch",
            "records": [
                {"id": 1, "name": "Alice", "score": 95.5},
                {"id": 2, "name": "Bob", "score": 87.3},
                {"id": 3, "name": "Charlie", "score": 92.1}
            ],
            "partition_date": "2025-12-20"
        }
        
        response = requests.post(f"{SIDECAR_URL}/ingest", json=payload, timeout=10)
        data = response.json()
        
        print(f"Status: {data.get('status')}")
        print(f"Records ingested: {data.get('record_count')}")
        print(f"Table: {data.get('table_name')}")
        print(f"Partition: {data.get('partition_date')}")
        
        return response.status_code == 200 and data.get("status") == "success"
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_streaming():
    """Test 4: Streaming ingestion"""
    print_header("Test 4: Streaming Ingestion")
    try:
        table_name = "test_stream"
        records = [
            {"sensor": "temp_1", "value": 22.5},
            {"sensor": "temp_2", "value": 23.1},
            {"sensor": "temp_3", "value": 21.8}
        ]
        
        # Stream records
        for i, record in enumerate(records, 1):
            response = requests.post(
                f"{SIDECAR_URL}/ingest/stream?table_name={table_name}",
                json={"data": record},
                timeout=5
            )
            print(f"  Record {i} streamed: {response.json().get('status')}")
        
        # Check buffered count
        response = requests.get(f"{SIDECAR_URL}/table/{table_name}/count", timeout=5)
        count = response.json().get("buffered_count")
        print(f"Buffered records: {count}")
        
        return count == len(records)
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_flush():
    """Test 5: Flush buffered data"""
    print_header("Test 5: Flush Buffered Data")
    try:
        table_name = "test_stream"
        
        response = requests.post(
            f"{SIDECAR_URL}/flush?table_name={table_name}",
            timeout=10
        )
        data = response.json()
        
        print(f"Status: {data.get('status')}")
        print(f"Message: {data.get('message')}")
        print(f"Records flushed: {data.get('record_count')}")
        
        # Verify buffer is now empty
        response = requests.get(f"{SIDECAR_URL}/table/{table_name}/count", timeout=5)
        count = response.json().get("buffered_count")
        print(f"Remaining buffered records: {count}")
        
        return data.get("status") == "success" and count == 0
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_list_tables():
    """Test 6: List all tables"""
    print_header("Test 6: List Tables")
    try:
        response = requests.get(f"{SIDECAR_URL}/tables", timeout=5)
        data = response.json()
        
        tables = data.get("tables", [])
        print(f"Active tables: {len(tables)}")
        for table in tables:
            print(f"  - {table}")
        
        return response.status_code == 200 and len(tables) >= 2
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_historical_data():
    """Test 7: Historical data with different dates"""
    print_header("Test 7: Historical Data Partitioning")
    try:
        dates = ["2025-12-18", "2025-12-19", "2025-12-20"]
        success_count = 0
        
        for date in dates:
            payload = {
                "table_name": "historical_data",
                "records": [
                    {"date": date, "metric": "sales", "value": 1000 + dates.index(date) * 100}
                ],
                "partition_date": date
            }
            
            response = requests.post(f"{SIDECAR_URL}/ingest", json=payload, timeout=10)
            if response.status_code == 200:
                success_count += 1
                print(f"  ✓ Loaded data for {date}")
            else:
                print(f"  ✗ Failed for {date}")
        
        return success_count == len(dates)
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_multi_table():
    """Test 8: Multiple tables simultaneously"""
    print_header("Test 8: Multiple Tables")
    try:
        tables = [
            ("orders", [{"order_id": 1, "amount": 100}]),
            ("customers", [{"customer_id": 1, "name": "John"}]),
            ("products", [{"product_id": 1, "name": "Widget"}])
        ]
        
        success_count = 0
        for table_name, records in tables:
            payload = {
                "table_name": table_name,
                "records": records
            }
            response = requests.post(f"{SIDECAR_URL}/ingest", json=payload, timeout=10)
            if response.status_code == 200:
                success_count += 1
                print(f"  ✓ Created table: {table_name}")
        
        return success_count == len(tables)
    except Exception as e:
        print(f"Error: {e}")
        return False

def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*60)
    print("  DuckDB S3 Sidecar - Test Suite")
    print("="*60)
    print(f"Target: {SIDECAR_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("Health Check", test_health),
        ("Root Endpoint", test_root_endpoint),
        ("Batch Ingestion", test_batch_ingestion),
        ("Streaming Ingestion", test_streaming),
        ("Flush Operation", test_flush),
        ("List Tables", test_list_tables),
        ("Historical Data", test_historical_data),
        ("Multiple Tables", test_multi_table)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\nUnexpected error in {test_name}: {e}")
            results.append((test_name, False))
        time.sleep(0.5)  # Small delay between tests
    
    # Summary
    print_header("Test Summary")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        print_result(test_name, result)
    
    print(f"\n{'='*60}")
    print(f"Results: {passed}/{total} tests passed ({passed*100//total}%)")
    print(f"{'='*60}\n")
    
    if passed == total:
        print("🎉 All tests passed! The sidecar is working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    import sys
    
    print("\nWaiting for service to be ready...")
    time.sleep(2)
    
    try:
        success = run_all_tests()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        sys.exit(1)
