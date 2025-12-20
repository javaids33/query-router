import requests
import sys

ROUTER_URL = "http://localhost:8000"

def check(name, fn):
    try:
        res = fn()
        if res:
            print(f"✅ {name}: PASS")
            return True
        else:
            print(f"❌ {name}: FAIL (Logic)")
            return False
    except Exception as e:
        print(f"❌ {name}: FAIL ({str(e)})")
        return False

def test_router_health():
    res = requests.get(f"{ROUTER_URL}/health")
    return res.status_code == 200

def test_engine_query(engine):
    sql = "SELECT 1"
    res = requests.post(f"{ROUTER_URL}/query", json={"sql": sql, "force_engine": engine})
    data = res.json()
    if "error" in data:
        raise Exception(data['error'])
    return True

def test_data_existence(engine):
    # This might fail if tables aren't created yet, so treat as warning if just empty, fail if error
    sql = "SELECT count(*) FROM users"
    res = requests.post(f"{ROUTER_URL}/query", json={"sql": sql, "force_engine": engine})
    data = res.json()
    if "error" in data:
         # Some engines throw table not found error, which is useful to know
         raise Exception(data['error'])
    return True

def main():
    print("🏥 STARTING HEALTH CHECK...\n")
    
    # 1. Router Alive?
    if not check("Router Connectivity", test_router_health):
        print("\n⛔ CRITICAL: Router is down. Aborting.")
        sys.exit(1)

    print("\n🏎️  ENGINE CONNECTIVITY CHECK:")
    engines = ["postgres", "duckdb", "clickhouse", "trino"]
    results = {}
    
    for engine in engines:
        results[engine] = check(f"Engine [{engine.upper()}] Select 1", lambda: test_engine_query(engine))

    print("\n📂 DATA EXISTENCE CHECK (Users Table):")
    for engine in engines:
        # Check if they can see the 'users' table
        check(f"Engine [{engine.upper()}] Table Access", lambda: test_data_existence(engine))

    print("\n📝 SUMMARY:")
    success_count = sum(results.values())
    print(f"Engines Operational: {success_count}/{len(engines)}")
    
    if success_count < len(engines):
        print("\n⚠️ WARNING: Some engines are down. Check 'docker-compose logs <service>'")
        sys.exit(1)
    else:
        print("\n🎉 ALL SYSTEMS GO! Ready for Demo.")
        sys.exit(0)

if __name__ == "__main__":
    main()
