# 🏁 Query Router Benchmark & Test Cases

This document provides comprehensive test case scenarios to showcase the Query Router application's capabilities, routing logic, and performance characteristics.

## 📋 Table of Contents

1. [Overview](#overview)
2. [Test Environment Setup](#test-environment-setup)
3. [Test Case Categories](#test-case-categories)
4. [Detailed Test Scenarios](#detailed-test-scenarios)
5. [Performance Benchmarks](#performance-benchmarks)
6. [Expected Results](#expected-results)
7. [Troubleshooting](#troubleshooting)

## 🎯 Overview

The Query Router benchmarks demonstrate:
- **Intelligent Routing** - Automatic query analysis and engine selection
- **Performance Optimization** - Right engine for the right workload
- **Multi-Engine Comparison** - Side-by-side performance analysis
- **Fallback Mechanisms** - Graceful degradation when engines are unavailable

## 🔧 Test Environment Setup

### Prerequisites

```bash
# Ensure all services are running
docker compose ps

# Expected output: All services should be "Up"
# - postgres_app
# - clickhouse
# - trino
# - minio
# - nessie
# - router
```

### Initial Data Setup

```bash
# Method 1: Using API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, name TEXT, role TEXT)"
  }'

curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "INSERT INTO users (name, role) VALUES ('"'"'Alice'"'"', '"'"'Engineer'"'"'), ('"'"'Bob'"'"', '"'"'Manager'"'"'), ('"'"'Charlie'"'"', '"'"'Analyst'"'"')"
  }'

# Method 2: Using Python script
python init_db.py

# Method 3: Using Dashboard
# Navigate to http://localhost:8501 and use the UI
```

### Verify Setup

```bash
python validation.py
```

Expected output:
```
✅ Router Connectivity: PASS
✅ Engine [POSTGRES] Select 1: PASS
✅ Engine [DUCKDB] Select 1: PASS
✅ Engine [CLICKHOUSE] Select 1: PASS
✅ Engine [TRINO] Select 1: PASS
🎉 ALL SYSTEMS GO! Ready for Demo.
```

## 📊 Test Case Categories

### Category 1: Routing Logic Validation
Tests that verify queries are routed to the correct engine based on query patterns.

### Category 2: Performance Benchmarks
Comparative performance tests across different engines for the same query.

### Category 3: Edge Cases & Fallbacks
Tests for error handling, fallback mechanisms, and unusual query patterns.

### Category 4: End-to-End Workflows
Complete data pipeline tests including ETL and cross-engine queries.

## 🧪 Detailed Test Scenarios

---

## Test Category 1: Routing Logic Validation

### TC-1.1: Point Lookup (PostgreSQL)

**Objective:** Verify that queries with exact ID lookups route to PostgreSQL.

**Query:**
```sql
SELECT * FROM users WHERE id = 1
```

**Expected Routing:** PostgreSQL

**Test Command:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users WHERE id = 1"}'
```

**Expected Response:**
```json
{
  "data": [{"id": 1, "name": "Alice", "role": "Engineer"}],
  "engine": "postgres",
  "duration": 0.015
}
```

**Why PostgreSQL?**
- Optimized for point lookups with indexed primary keys
- OLTP workload pattern
- Low latency for single-row retrieval

---

### TC-1.2: Aggregation (ClickHouse)

**Objective:** Verify that aggregation queries without JOINs route to ClickHouse.

**Query:**
```sql
SELECT COUNT(*) FROM users
```

**Expected Routing:** ClickHouse

**Test Command:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT COUNT(*) FROM users"}'
```

**Expected Response:**
```json
{
  "data": [[3]],
  "columns": ["count()"],
  "engine": "clickhouse",
  "duration": 0.025
}
```

**Why ClickHouse?**
- Columnar storage optimized for aggregations
- Very fast for COUNT, SUM, AVG operations
- No JOINs involved (ClickHouse sweet spot)

---

### TC-1.3: Complex Join (Trino)

**Objective:** Verify that queries with JOINs route to Trino.

**Query:**
```sql
SELECT a.name, b.role FROM users a JOIN users b ON a.id = b.id
```

**Expected Routing:** Trino

**Test Command:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT a.name, b.role FROM users a JOIN users b ON a.id = b.id"}'
```

**Expected Response:**
```json
{
  "data": [
    {"name": "Alice", "role": "Engineer"},
    {"name": "Bob", "role": "Manager"},
    {"name": "Charlie", "role": "Analyst"}
  ],
  "engine": "trino",
  "duration": 0.150
}
```

**Why Trino?**
- Optimized for complex multi-table queries
- Distributed join processing
- Can federate across multiple data sources

---

### TC-1.4: Simple Select (DuckDB)

**Objective:** Verify that simple SELECT queries route to DuckDB.

**Query:**
```sql
SELECT * FROM users
```

**Expected Routing:** DuckDB

**Test Command:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users"}'
```

**Expected Response:**
```json
{
  "data": [
    {"id": 1, "name": "Alice", "role": "Engineer"},
    {"id": 2, "name": "Bob", "role": "Manager"},
    {"id": 3, "name": "Charlie", "role": "Analyst"}
  ],
  "engine": "duckdb",
  "duration": 0.010
}
```

**Why DuckDB?**
- Fast ad-hoc queries
- Low overhead for simple operations
- Fallback for queries that don't match other patterns

---

### TC-1.5: Write Operations (PostgreSQL)

**Objective:** Verify that INSERT/UPDATE/DELETE operations route to PostgreSQL.

**Insert Query:**
```sql
INSERT INTO users (name, role) VALUES ('David', 'Developer')
```

**Expected Routing:** PostgreSQL

**Test Command:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "INSERT INTO users (name, role) VALUES ('"'"'David'"'"', '"'"'Developer'"'"')"}'
```

**Expected Response:**
```json
{
  "status": "ok",
  "message": "Query executed successfully",
  "engine": "postgres",
  "duration": 0.020
}
```

**Why PostgreSQL?**
- ACID-compliant transactional database
- Primary source of truth for application data
- Handles all write operations

---

## Test Category 2: Performance Benchmarks

### TC-2.1: Engine Speed Comparison - Simple Select

**Objective:** Compare performance of all engines on a simple SELECT query.

**Query:**
```sql
SELECT * FROM users
```

**Test Process:**

```bash
# Test PostgreSQL
time curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users", "force_engine": "postgres"}'

# Test ClickHouse
time curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users", "force_engine": "clickhouse"}'

# Test Trino
time curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users", "force_engine": "trino"}'

# Test DuckDB
time curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM users", "force_engine": "duckdb"}'
```

**Expected Results (Typical):**

| Engine     | Duration (ms) | Notes                           |
|-----------|---------------|---------------------------------|
| DuckDB     | 10-15        | Fastest - in-memory, local      |
| PostgreSQL | 15-25        | Fast - indexed, small dataset   |
| ClickHouse | 25-40        | Overhead of S3 rewrite          |
| Trino      | 100-200      | Slowest - distributed overhead  |

**Visualization:**
```
DuckDB      ████ 10ms
PostgreSQL  ██████ 20ms
ClickHouse  ██████████ 35ms
Trino       ████████████████████████ 150ms
```

---

### TC-2.2: Engine Speed Comparison - Aggregation

**Objective:** Compare performance on COUNT aggregation.

**Query:**
```sql
SELECT COUNT(*) FROM users
```

**Test Process:**

```bash
# Test each engine with force_engine parameter
for engine in postgres clickhouse trino duckdb; do
  echo "Testing $engine..."
  curl -X POST http://localhost:8000/query \
    -H "Content-Type: application/json" \
    -d "{\"sql\": \"SELECT COUNT(*) FROM users\", \"force_engine\": \"$engine\"}" \
    | jq '.duration'
done
```

**Expected Results:**

| Engine     | Duration (ms) | Winner? |
|-----------|---------------|---------|
| ClickHouse | 15-25        | ⭐ YES  |
| DuckDB     | 20-30        | Close   |
| PostgreSQL | 25-35        | Good    |
| Trino      | 100-150      | Slow    |

**Why ClickHouse Wins:**
- Columnar storage optimized for aggregations
- Vectorized execution
- Minimal data scanning required

---

### TC-2.3: Engine Speed Comparison - Complex Join

**Objective:** Compare performance on JOIN operations.

**Query:**
```sql
SELECT a.name, b.role FROM users a JOIN users b ON a.id = b.id
```

**Expected Results:**

| Engine     | Duration (ms) | Winner?     |
|-----------|---------------|-------------|
| PostgreSQL | 30-50        | ⭐ Best     |
| DuckDB     | 40-60        | Good        |
| Trino      | 150-250      | Acceptable  |
| ClickHouse | May Fail     | N/A         |

**Why PostgreSQL/DuckDB Win:**
- Small dataset fits in memory
- Local execution without network overhead
- Optimized for in-database joins

**Note:** Trino's advantage appears with larger datasets across multiple sources.

---

## Test Category 3: Edge Cases & Fallbacks

### TC-3.1: Malformed SQL

**Objective:** Verify graceful handling of invalid SQL.

**Query:**
```sql
SELECT * FORM users
```

**Expected Routing:** DuckDB (fallback)

**Test Command:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FORM users"}'
```

**Expected Response:**
```json
{
  "error": "DuckDB Error: Parser Error: syntax error at or near \"FORM\"",
  "engine": "duckdb",
  "duration": 0.005
}
```

---

### TC-3.2: Non-existent Table

**Objective:** Test behavior when querying non-existent tables.

**Query:**
```sql
SELECT * FROM nonexistent_table
```

**Test Command:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM nonexistent_table"}'
```

**Expected Response:**
```json
{
  "error": "DuckDB Error: Catalog Error: Table 'nonexistent_table' not found",
  "engine": "duckdb",
  "duration": 0.008
}
```

---

### TC-3.3: S3/Iceberg Fallback (DuckDB)

**Objective:** Test DuckDB's fallback to local table when S3 is unavailable.

**Query:**
```sql
SELECT * FROM users
```

**Scenario:** MinIO is down or unreachable

**Expected Behavior:**
- DuckDB attempts Iceberg scan from S3
- Fails with S3 error
- Automatically falls back to local in-memory table
- Returns data from local fallback table

**Router Log Output:**
```
⚠️ DuckDB S3 Access Failed (IO Error: Failed to connect to S3), falling back to local table.
```

---

## Test Category 4: End-to-End Workflows

### TC-4.1: Complete Data Pipeline

**Objective:** Demonstrate full ETL workflow from Postgres to Iceberg.

**Steps:**

1. **Insert data into PostgreSQL:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "INSERT INTO users (name, role) VALUES ('"'"'Eve'"'"', '"'"'Designer'"'"')"}'
```

2. **Simulate ETL to Iceberg (via Trino):**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "CREATE OR REPLACE TABLE iceberg.public.users AS SELECT * FROM (VALUES (1, '"'"'Alice'"'"', '"'"'Engineer'"'"'), (2, '"'"'Bob'"'"', '"'"'Manager'"'"'), (3, '"'"'Charlie'"'"', '"'"'Analyst'"'"'), (4, '"'"'Eve'"'"', '"'"'Designer'"'"')) AS t(id, name, role)",
    "force_engine": "trino"
  }'
```

3. **Query Iceberg table via Trino:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM iceberg.public.users",
    "force_engine": "trino"
  }'
```

4. **Query via ClickHouse (S3 direct):**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT COUNT(*) FROM users",
    "force_engine": "clickhouse"
  }'
```

**Expected Flow:**
```
PostgreSQL (Source) → Trino (ETL) → Iceberg (MinIO) → ClickHouse/DuckDB (Analytics)
```

---

### TC-4.2: Mixed Workload Test

**Objective:** Simulate realistic mixed workload with concurrent operations.

**Workload Mix:**
1. 40% OLTP queries (PostgreSQL)
2. 30% Aggregations (ClickHouse)
3. 20% Ad-hoc queries (DuckDB)
4. 10% Complex joins (Trino)

**Test Script:**
```bash
# Create a test script to run mixed workload
cat > mixed_workload_test.sh << 'EOF'
#!/bin/bash

ROUTER="http://localhost:8000/query"

# Run 10 iterations
for i in {1..10}; do
  # OLTP queries (40%)
  for j in {1..4}; do
    curl -s -X POST $ROUTER -H "Content-Type: application/json" \
      -d '{"sql": "SELECT * FROM users WHERE id = 1"}' > /dev/null &
  done
  
  # Aggregations (30%)
  for j in {1..3}; do
    curl -s -X POST $ROUTER -H "Content-Type: application/json" \
      -d '{"sql": "SELECT COUNT(*) FROM users"}' > /dev/null &
  done
  
  # Ad-hoc queries (20%)
  for j in {1..2}; do
    curl -s -X POST $ROUTER -H "Content-Type: application/json" \
      -d '{"sql": "SELECT * FROM users"}' > /dev/null &
  done
  
  # Complex joins (10%)
  curl -s -X POST $ROUTER -H "Content-Type: application/json" \
    -d '{"sql": "SELECT a.name, b.role FROM users a JOIN users b ON a.id = b.id"}' > /dev/null &
  
  wait
done

echo "Mixed workload test completed!"
EOF

chmod +x mixed_workload_test.sh
./mixed_workload_test.sh
```

---

## 📈 Performance Benchmarks Summary

### Benchmark Results Matrix

| Query Type         | Best Engine | Typical Latency | Runner-up    |
|-------------------|-------------|-----------------|--------------|
| Point Lookup      | PostgreSQL  | 10-20ms        | DuckDB       |
| Simple Aggregation| ClickHouse  | 15-25ms        | DuckDB       |
| Complex Join      | PostgreSQL* | 30-50ms        | DuckDB       |
| Ad-hoc Select     | DuckDB      | 10-15ms        | PostgreSQL   |
| Write Operations  | PostgreSQL  | 15-30ms        | N/A          |

*For small datasets. Trino wins for large distributed datasets.

### Engine Strengths & Weaknesses

#### PostgreSQL
**Strengths:**
- ✅ Excellent for OLTP workloads
- ✅ ACID compliance
- ✅ Fast point lookups with indexes
- ✅ Reliable for write operations

**Weaknesses:**
- ❌ Slower for large analytical scans
- ❌ Limited columnar optimization
- ❌ Not designed for massive parallelism

#### ClickHouse
**Strengths:**
- ✅ Lightning-fast aggregations
- ✅ Columnar storage
- ✅ Excellent for time-series data
- ✅ Scalable for huge datasets

**Weaknesses:**
- ❌ Not optimized for point lookups
- ❌ Limited JOIN performance
- ❌ Not ACID-compliant by default
- ❌ Requires data in correct format (S3/Parquet)

#### Trino
**Strengths:**
- ✅ Excellent for complex joins
- ✅ Federates multiple data sources
- ✅ Scales horizontally
- ✅ Iceberg table native support

**Weaknesses:**
- ❌ Higher latency for simple queries
- ❌ Resource intensive
- ❌ Startup/planning overhead
- ❌ Overkill for small datasets

#### DuckDB
**Strengths:**
- ✅ Very fast for small-medium datasets
- ✅ Zero configuration (embedded)
- ✅ SQL-compliant
- ✅ Excellent Parquet/Iceberg support
- ✅ Low resource overhead

**Weaknesses:**
- ❌ Single-node (no distribution)
- ❌ Limited for very large datasets
- ❌ In-memory constraints
- ❌ Not designed for concurrent writes

---

## 🎯 Expected Results

### Success Criteria

A successful benchmark run should demonstrate:

1. **Correct Routing (100% accuracy)**
   - Point lookups → PostgreSQL
   - Aggregations → ClickHouse
   - Joins → Trino
   - Simple selects → DuckDB

2. **Performance Optimization**
   - ClickHouse faster than PostgreSQL for COUNT queries
   - PostgreSQL faster than Trino for point lookups
   - DuckDB fastest for ad-hoc simple queries

3. **Reliability**
   - All engines respond without errors (when properly configured)
   - Fallback mechanisms work when engines unavailable
   - Graceful error handling for invalid queries

4. **Latency Targets**
   - Point lookups: < 50ms
   - Aggregations: < 100ms
   - Simple selects: < 50ms
   - Complex joins: < 500ms (small dataset)

---

## 🔍 Troubleshooting

### Issue: All queries fail with connection errors

**Solution:**
```bash
# Check all services are running
docker compose ps

# Restart services if needed
docker compose restart

# Wait 30-60 seconds for initialization
sleep 60

# Re-run validation
python validation.py
```

### Issue: ClickHouse queries fail

**Likely Cause:** MinIO not accessible or data not in S3

**Solution:**
```bash
# Check MinIO is running
docker compose logs minio

# Verify MinIO console
open http://localhost:9001
# Login: admin / password

# Check if bucket exists
docker compose exec minio mc ls local/lake-data
```

### Issue: Trino queries fail

**Likely Cause:** Nessie catalog not ready or Iceberg table doesn't exist

**Solution:**
```bash
# Check Nessie
curl http://localhost:19120/api/v1/config

# Check Trino logs
docker compose logs trino

# Recreate Iceberg table
python test_connections.py
```

### Issue: Router returns incorrect engine

**Likely Cause:** Query pattern doesn't match expected rules

**Solution:**
- Review routing logic in router.py
- Check SQL syntax
- Use `force_engine` parameter to test specific engine

---

## 📊 Running the Complete Benchmark Suite

### Automated Benchmark Script

Create a comprehensive benchmark runner:

```python
# benchmark_runner.py
import requests
import time
import json
from statistics import mean, stdev

ROUTER_URL = "http://localhost:8000/query"

test_cases = [
    {
        "name": "Point Lookup (PostgreSQL)",
        "sql": "SELECT * FROM users WHERE id = 1",
        "expected_engine": "postgres",
        "iterations": 10
    },
    {
        "name": "Aggregation (ClickHouse)",
        "sql": "SELECT COUNT(*) FROM users",
        "expected_engine": "clickhouse",
        "iterations": 10
    },
    {
        "name": "Complex Join (Trino)",
        "sql": "SELECT a.name, b.role FROM users a JOIN users b ON a.id = b.id",
        "expected_engine": "trino",
        "iterations": 10
    },
    {
        "name": "Simple Select (DuckDB)",
        "sql": "SELECT * FROM users",
        "expected_engine": "duckdb",
        "iterations": 10
    }
]

def run_benchmark():
    results = []
    
    for test in test_cases:
        print(f"\n🧪 Running: {test['name']}")
        durations = []
        
        for i in range(test['iterations']):
            response = requests.post(
                ROUTER_URL,
                json={"sql": test['sql']}
            )
            result = response.json()
            
            actual_engine = result.get('engine')
            duration = result.get('duration', 0)
            
            if actual_engine == test['expected_engine']:
                print(f"  ✅ Iteration {i+1}: {duration:.4f}s")
                durations.append(duration)
            else:
                print(f"  ❌ Iteration {i+1}: Routed to {actual_engine}, expected {test['expected_engine']}")
        
        if durations:
            avg = mean(durations)
            std = stdev(durations) if len(durations) > 1 else 0
            
            results.append({
                "test": test['name'],
                "engine": test['expected_engine'],
                "avg_duration": f"{avg:.4f}s",
                "std_dev": f"{std:.4f}s",
                "min": f"{min(durations):.4f}s",
                "max": f"{max(durations):.4f}s"
            })
    
    print("\n" + "="*80)
    print("📊 BENCHMARK RESULTS SUMMARY")
    print("="*80)
    
    for result in results:
        print(f"\n{result['test']}")
        print(f"  Engine: {result['engine']}")
        print(f"  Average: {result['avg_duration']}")
        print(f"  Std Dev: {result['std_dev']}")
        print(f"  Min: {result['min']}")
        print(f"  Max: {result['max']}")

if __name__ == "__main__":
    run_benchmark()
```

Run it:
```bash
python benchmark_runner.py
```

---

## 🎓 Key Takeaways

1. **Right Tool for the Job:** Different engines excel at different workloads
2. **Routing Matters:** Intelligent routing can improve performance by 10-100x
3. **Trade-offs Exist:** Speed vs. features, simplicity vs. scalability
4. **Testing is Critical:** Verify routing logic and performance in your environment
5. **Monitor & Tune:** Use these benchmarks as a baseline, then optimize for your data

---

## 📝 Notes

- All benchmarks assume small dataset (< 1000 rows)
- Results will vary with dataset size, hardware, and network
- Production deployments should use proper indexes and optimization
- Consider data locality and caching effects
- Test with your actual workload patterns

---

## 🚀 Next Steps

1. Run all test cases in order
2. Document your specific results
3. Identify bottlenecks in your environment
4. Tune configurations based on findings
5. Scale up dataset size and re-benchmark
6. Implement monitoring and alerting

---

*Last Updated: 2025-12-20*
