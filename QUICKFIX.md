# Open Data Garage - Quick Fix Guide

## Common Issues & Resolutions

### 1. ClickHouse S3 Error: "No files with provided path"

**Symptom:** `CANNOT_EXTRACT_TABLE_STRUCTURE` error when routing to ClickHouse.

**Cause:** Parquet files don't exist at the expected S3 path.

**Fix:**

```bash
# Create the Iceberg tables (users, events) with sample data
python init_demo.py
```

This script:

1. Creates the `public` schema in Iceberg/Nessie
2. Creates and populates the `users` and `events` tables
3. Verifies parquet files exist in MinIO

---

### 2. Trino Error: "Schema public not found" or "Table not found"

**Symptom:** Queries routed to Trino fail with schema/table not found errors.

**Fix:** Run `init_demo.py` to ensure all demo schemas and tables exist.

---

### 3. Services Not Starting

**Fix:**

```bash
docker compose down -v
docker compose up -d
# Wait 30-60 seconds for all services to initialize
docker compose ps  # Verify all services are "Up"
```

---

### 4. Dashboard Not Accessible

**Fix:** Start Streamlit manually:

```bash
streamlit run dashboard.py
# Access at http://localhost:8501
```

---

## Quick Validation Commands

```bash
# Check all services
docker compose ps

# View logs for specific service
docker compose logs router --tail=20
docker compose logs trino --tail=20
docker compose logs clickhouse --tail=20

# Test router health
curl http://localhost:8000/health

# Run connection tests
python test_connections.py

# Run routing logic tests
python test_routing_logic.py
```
