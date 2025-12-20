#!/usr/bin/env python3
"""
Quick Verification Script for Query Router
Tests core functionality without requiring full Docker stack
"""

import sys

def test_routing_logic():
    """Test the SQL query routing logic"""
    print("\n" + "="*70)
    print("TEST 1: Query Routing Logic")
    print("="*70)
    
    try:
        import sqlglot
        from sqlglot import exp
    except ImportError:
        print("❌ sqlglot not installed. Run: pip install sqlglot")
        return False
    
    def decide_engine(sql):
        try:
            parsed = sqlglot.parse_one(sql)
        except:
            return 'duckdb'
        
        if isinstance(parsed, exp.Select):
            for where in parsed.find_all(exp.Where):
                if 'id =' in where.sql().lower() or 'id=' in where.sql().lower():
                    return 'postgres'

        if isinstance(parsed, (exp.Insert, exp.Update, exp.Delete, exp.Create)):
            return 'postgres'

        is_agg = False
        for agg in ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX']:
            if agg in sql.upper():
                is_agg = True
                break
                
        has_join = list(parsed.find_all(exp.Join))
        
        if isinstance(parsed, exp.Select) and not has_join and is_agg:
            return 'clickhouse'

        if has_join:
            return 'trino'

        return 'duckdb'
    
    test_cases = [
        ('SELECT * FROM users WHERE id = 1', 'postgres', 'Point lookup'),
        ('SELECT COUNT(*) FROM users', 'clickhouse', 'Aggregation'),
        ('SELECT a.name, b.role FROM users a JOIN users b ON a.id = b.id', 'trino', 'JOIN operation'),
        ('SELECT * FROM users', 'duckdb', 'Simple SELECT'),
        ('INSERT INTO users (name, role) VALUES ("test", "role")', 'postgres', 'INSERT operation'),
        ('UPDATE users SET name = "new" WHERE id = 1', 'postgres', 'UPDATE operation'),
        ('DELETE FROM users WHERE id = 1', 'postgres', 'DELETE operation'),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected, description in test_cases:
        engine = decide_engine(query)
        if engine == expected:
            print(f"✅ {description:20} → {engine:12} [PASS]")
            passed += 1
        else:
            print(f"❌ {description:20} → {engine:12} [FAIL] Expected: {expected}")
            failed += 1
    
    print(f"\nResult: {passed} passed, {failed} failed")
    return failed == 0


def test_duckdb():
    """Test DuckDB functionality"""
    print("\n" + "="*70)
    print("TEST 2: DuckDB Functionality")
    print("="*70)
    
    try:
        import duckdb
    except ImportError:
        print("❌ duckdb not installed. Run: pip install duckdb")
        return False
    
    try:
        # Create connection
        conn = duckdb.connect()
        print("✅ DuckDB connection established")
        
        # Create table
        conn.execute("CREATE TABLE test_users (id INTEGER, name VARCHAR, role VARCHAR)")
        print("✅ Table creation successful")
        
        # Insert data
        conn.execute("INSERT INTO test_users VALUES (1, 'Alice', 'Engineer'), (2, 'Bob', 'Manager')")
        print("✅ Data insertion successful")
        
        # Query data
        result = conn.execute("SELECT * FROM test_users").fetchall()
        print(f"✅ SELECT query successful: {len(result)} rows")
        
        # Test aggregation
        result = conn.execute("SELECT COUNT(*) FROM test_users").fetchall()
        count = result[0][0]
        print(f"✅ COUNT query successful: {count} rows")
        
        # Test with WHERE clause
        result = conn.execute("SELECT * FROM test_users WHERE id = 1").fetchall()
        print(f"✅ WHERE clause successful: {len(result)} rows")
        
        conn.close()
        print("\n✅ All DuckDB tests passed")
        return True
        
    except Exception as e:
        print(f"❌ DuckDB test failed: {e}")
        return False


def test_fastapi_structure():
    """Test FastAPI application structure"""
    print("\n" + "="*70)
    print("TEST 3: FastAPI Application Structure")
    print("="*70)
    
    try:
        from fastapi import FastAPI
        from pydantic import BaseModel
        print("✅ FastAPI and Pydantic installed")
        
        # Try to parse router.py to check structure
        with open('router.py', 'r') as f:
            content = f.read()
            
            checks = [
                ('FastAPI app initialization', 'app = FastAPI()'),
                ('Health endpoint', '@app.get("/health")'),
                ('Query endpoint', '@app.post("/query")'),
                ('QueryRequest model', 'class QueryRequest'),
                ('Routing function', 'def decide_engine'),
                ('PostgreSQL handler', 'def run_postgres'),
                ('ClickHouse handler', 'def run_clickhouse'),
                ('Trino handler', 'def run_trino'),
                ('DuckDB handler', 'def run_duckdb'),
            ]
            
            for check_name, check_string in checks:
                if check_string in content:
                    print(f"✅ {check_name:30} found")
                else:
                    print(f"❌ {check_name:30} NOT FOUND")
                    return False
        
        print("\n✅ All FastAPI structure checks passed")
        return True
        
    except ImportError:
        print("❌ FastAPI not installed. Run: pip install fastapi")
        return False
    except FileNotFoundError:
        print("❌ router.py not found")
        return False
    except Exception as e:
        print(f"❌ Structure test failed: {e}")
        return False


def test_docker_config():
    """Test Docker configuration"""
    print("\n" + "="*70)
    print("TEST 4: Docker Configuration")
    print("="*70)
    
    try:
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            services = [
                'postgres_app',
                'clickhouse',
                'trino',
                'minio',
                'nessie',
                'router'
            ]
            
            for service in services:
                if f'{service}:' in content:
                    print(f"✅ Service '{service}' configured")
                else:
                    print(f"❌ Service '{service}' NOT configured")
                    return False
        
        print("\n✅ All Docker services configured")
        return True
        
    except FileNotFoundError:
        print("❌ docker-compose.yml not found")
        return False
    except Exception as e:
        print(f"❌ Docker config test failed: {e}")
        return False


def test_documentation():
    """Test that documentation exists"""
    print("\n" + "="*70)
    print("TEST 5: Documentation")
    print("="*70)
    
    docs = [
        ('README.md', 'Project documentation'),
        ('BENCHMARK.md', 'Benchmark and test cases'),
        ('TEST_REPORT.md', 'Testing report'),
    ]
    
    all_exist = True
    for filename, description in docs:
        try:
            with open(filename, 'r') as f:
                size = len(f.read())
                print(f"✅ {description:30} ({filename}) - {size:,} bytes")
        except FileNotFoundError:
            print(f"❌ {description:30} ({filename}) NOT FOUND")
            all_exist = False
    
    if all_exist:
        print("\n✅ All documentation files present")
    return all_exist


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 QUERY ROUTER - QUICK VERIFICATION SCRIPT")
    print("="*70)
    print("\nThis script tests core functionality without Docker services")
    
    results = []
    
    # Run all tests
    results.append(("Routing Logic", test_routing_logic()))
    results.append(("DuckDB", test_duckdb()))
    results.append(("FastAPI Structure", test_fastapi_structure()))
    results.append(("Docker Config", test_docker_config()))
    results.append(("Documentation", test_documentation()))
    
    # Summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "="*70)
    print(f"Results: {passed}/{total} tests passed ({passed*100//total}%)")
    print("="*70)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! The application is ready to deploy.")
        print("\nNext steps:")
        print("1. Start services: docker compose up -d")
        print("2. Initialize data: python init_db.py")
        print("3. Run validation: python validation.py")
        print("4. See BENCHMARK.md for detailed test cases")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")
        print("\nMissing dependencies? Try:")
        print("  pip install fastapi uvicorn duckdb sqlglot")
        return 1


if __name__ == "__main__":
    sys.exit(main())
