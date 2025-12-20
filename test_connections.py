import requests
import json
import time

ROUTER_URL = "http://localhost:8000"

def run_query(sql, force_engine=None):
    payload = {"sql": sql}
    if force_engine:
        payload["force_engine"] = force_engine
    
    try:
        response = requests.post(f"{ROUTER_URL}/query", json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def check_health():
    try:
        res = requests.get(f"{ROUTER_URL}/health")
        if res.status_code == 200:
            print("✅ Router is ONLINE")
        else:
            print(f"❌ Router returned {res.status_code}")
    except Exception as e:
        print(f"❌ Router UNREACHABLE: {e}")

def test_engines():
    engines = ["postgres", "trino", "duckdb"]
    # Clickhouse is optional/might fail if not setup, but let's test basic select
    # engines.append("clickhouse") 

    for engine in engines:
        print(f"Testing {engine}...")
        res = run_query("SELECT 1", force_engine=engine)
        if "error" in res:
             print(f"❌ {engine} FAILED: {res['error']}")
        else:
             print(f"✅ {engine} OK ({res.get('duration', 0):.4f}s)")

    # ClickHouse might need specific query or might default to system.one?
    print("Testing clickhouse...")
    res = run_query("SELECT 1", force_engine="clickhouse")
    if "error" in res:
         print(f"⚠️  ClickHouse FAILED (might be expected if not configured fully): {res['error']}")
    else:
         print(f"✅ ClickHouse OK")

def test_etl_and_trino_data():
    print("\nRunning Simulation ETL (Postgres -> Trino/Iceberg)...")
    etl_sql = "CREATE OR REPLACE TABLE iceberg.public.users AS SELECT * FROM (VALUES (1, 'Alice', 'Engineer'), (2, 'Bob', 'Manager'), (3, 'Charlie', 'Analyst')) AS t(id, name, role)"
    res = run_query(etl_sql, force_engine="trino")
    
    if "error" in res:
        print(f"❌ ETL FAILED: {res['error']}")
    else:
        print("✅ ETL Success")
        
        # Verify data
        print("Verifying data in Iceberg via Trino...")
        res = run_query("SELECT * FROM iceberg.public.users", force_engine="trino")
        if "data" in res and len(res["data"]) == 3:
             print(f"✅ Users found: {len(res['data'])}")
        else:
             print(f"❌ Data verification failed: {res}")


if __name__ == "__main__":
    check_health()
    print("-" * 20)
    test_engines()
    print("-" * 20)
    test_etl_and_trino_data()
