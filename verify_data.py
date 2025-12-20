import requests
import json

ROUTER_URL = "http://localhost:8000"

def verify_iceberg_data():
    """Check if data exists in the Iceberg table despite the error"""
    queries = [
        "SELECT * FROM iceberg.public.users",
        "SELECT * FROM iceberg.public.\"users$snapshots\"",
        "SHOW TABLES FROM iceberg.public"
    ]
    
    for sql in queries:
        print(f"\n{'='*60}")
        print(f"Query: {sql}")
        print('='*60)
        
        res = requests.post(f"{ROUTER_URL}/query", json={"sql": sql, "force_engine": "trino"})
        result = res.json()
        
        if "data" in result:
            print(f"✅ SUCCESS - Found {len(result['data'])} rows")
            print(json.dumps(result['data'], indent=2))
        elif "error" in result:
            print(f"❌ ERROR: {result['error']}")
        else:
            print(json.dumps(result, indent=2))

def check_nessie():
    """Check if Nessie is accessible"""
    print("\n" + "="*60)
    print("Checking Nessie REST catalog...")
    print("="*60)
    
    try:
        # Check Nessie health
        res = requests.get("http://localhost:19120/api/v1/config")
        print(f"✅ Nessie is accessible: {res.status_code}")
        print(json.dumps(res.json(), indent=2))
    except Exception as e:
        print(f"❌ Nessie not accessible: {e}")

if __name__ == "__main__":
    check_nessie()
    verify_iceberg_data()
