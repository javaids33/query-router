# DuckDB S3 Sidecar - Quick Start Guide

## Overview

The DuckDB S3 Sidecar is a dedicated service that provides easy data ingestion to S3/Iceberg tables with automatic date-based partitioning. It acts as a data gateway allowing any application in your cluster to push data directly to your data lake.

## Architecture

```
Your App/Pod → HTTP POST → DuckDB Sidecar → S3/Iceberg
                              (port 8001)
                                  ↓
                          Date Partitioning
                          (YYYY/MM/DD)
                                  ↓
                          Parquet Files in S3
```

## Key Features

- ✅ **Simple HTTP API** - No complex S3 configuration in your application
- ✅ **Automatic Date Partitioning** - Data organized by year/month/day
- ✅ **Batch & Stream Modes** - Choose the best ingestion pattern for your use case
- ✅ **Schema Inference** - Automatically creates tables from your data
- ✅ **Buffering** - Stream records and flush when ready
- ✅ **Parquet Format** - Efficient columnar storage for analytics

## Quick Start

### 1. Check Service Health

```bash
curl http://localhost:8001/health
```

Response:
```json
{
    "status": "healthy",
    "service": "duckdb-sidecar",
    "s3_endpoint": "http://minio:9000",
    "s3_bucket": "lake-data"
}
```

### 2. Batch Ingestion (Recommended for bulk data)

```bash
curl -X POST http://localhost:8001/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "events",
    "records": [
      {"user_id": 1, "event": "login", "timestamp": "2025-12-20T10:00:00"},
      {"user_id": 2, "event": "purchase", "timestamp": "2025-12-20T10:05:00"}
    ],
    "partition_date": "2025-12-20"
  }'
```

### 3. Streaming Ingestion (For real-time data)

Stream individual records:
```bash
curl -X POST 'http://localhost:8001/ingest/stream?table_name=metrics' \
  -H "Content-Type: application/json" \
  -d '{"data": {"metric_name": "cpu_usage", "value": 75.5, "timestamp": "2025-12-20T10:00:00"}}'
```

Flush buffered records to S3:
```bash
curl -X POST 'http://localhost:8001/flush?table_name=metrics'
```

## Usage Patterns

### Pattern 1: ETL Pipeline (Daily Batch)

Perfect for daily data exports, scheduled jobs, or batch processing.

```python
import requests

# Run this daily
def daily_etl():
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Extract data from your database
    data = extract_daily_data()
    
    # Push to sidecar
    response = requests.post(
        "http://duckdb-sidecar:8001/ingest",
        json={
            "table_name": "daily_sales",
            "records": data,
            "partition_date": today
        }
    )
    
    print(f"Loaded {response.json()['record_count']} records")
```

### Pattern 2: Real-Time Streaming

Perfect for continuous event streams, logs, or sensor data.

```python
import requests

SIDECAR_URL = "http://duckdb-sidecar:8001"

# Stream events as they occur
def process_event_stream():
    for event in event_source:
        requests.post(
            f"{SIDECAR_URL}/ingest/stream?table_name=events",
            json={"data": event}
        )
    
    # Flush every N events or every N seconds
    if should_flush():
        requests.post(f"{SIDECAR_URL}/flush?table_name=events")
```

### Pattern 3: Application Data Export

Perfect for exporting application data, user analytics, or audit logs.

```python
import requests

def export_user_activity(user_id, activities):
    """Export user activity from your application"""
    response = requests.post(
        "http://duckdb-sidecar:8001/ingest",
        json={
            "table_name": "user_activity",
            "records": activities
        }
    )
    return response.json()
```

## API Endpoints

### GET /health
Check service health

### POST /ingest
Batch data ingestion with automatic flush to S3

**Request:**
```json
{
  "table_name": "string",
  "records": [{"key": "value"}],
  "partition_date": "YYYY-MM-DD" // optional, defaults to today
}
```

### POST /ingest/stream?table_name={name}
Stream single records (buffered in memory)

**Request:**
```json
{
  "data": {"key": "value"}
}
```

### POST /flush?table_name={name}&partition_date={date}
Flush buffered records to S3

### GET /tables
List all active tables

### GET /table/{name}/count
Get buffered record count for a table

## Data Organization

Data is automatically organized in S3 with Hive-style partitioning:

```
s3://lake-data/data/
├── events/
│   ├── year=2025/
│   │   ├── month=12/
│   │   │   ├── day=19/
│   │   │   │   ├── data_100530.parquet
│   │   │   │   └── data_143022.parquet
│   │   │   └── day=20/
│   │   │       └── data_095511.parquet
```

This structure enables efficient querying by date range in Trino, DuckDB, or other query engines.

## Integration Examples

### From Docker Compose Services

In your `docker-compose.yml`, other services can access the sidecar:

```yaml
your-app:
  image: your-app-image
  environment:
    SIDECAR_URL: http://duckdb-sidecar:8001
  depends_on:
    - duckdb-sidecar
```

### From Kubernetes Pods

Deploy the sidecar as a service in your cluster:

```yaml
apiVersion: v1
kind: Service
metadata:
  name: duckdb-sidecar
spec:
  selector:
    app: duckdb-sidecar
  ports:
    - port: 8001
      targetPort: 8001
```

Applications can then use `http://duckdb-sidecar:8001` as the endpoint.

## Monitoring & Management

### Check Buffered Data

Before flushing, check how many records are buffered:

```bash
curl http://localhost:8001/table/events/count
```

### List Active Tables

```bash
curl http://localhost:8001/tables
```

### View Logs

```bash
docker compose logs -f duckdb-sidecar
```

## Best Practices

1. **Choose the Right Pattern**
   - Use **batch ingestion** for scheduled jobs and bulk transfers
   - Use **streaming + flush** for continuous, real-time data

2. **Partition by Date**
   - Always specify `partition_date` for historical data
   - Let it default to today for current data

3. **Flush Regularly**
   - When streaming, flush every N records or every N seconds
   - Don't let too much data buffer in memory

4. **Monitor Buffer Size**
   - Check buffered counts periodically
   - Implement alerts if buffers grow too large

5. **Table Naming**
   - Use descriptive table names (e.g., `user_events`, `sensor_readings`)
   - Avoid special characters
   - Use lowercase for consistency

## Troubleshooting

### Service Not Available

```bash
# Check if service is running
docker compose ps duckdb-sidecar

# Restart if needed
docker compose restart duckdb-sidecar

# View logs
docker compose logs duckdb-sidecar
```

### Schema Mismatch

If you change the structure of your data, you may need to drop and recreate the table. The sidecar creates tables on first insert and keeps them for the session.

### S3 Connection Issues

In development environments without proper S3 extensions, you may see warnings about S3 writes. The service will continue to work for testing and will succeed in production environments with proper extensions installed.

## Advanced Configuration

### Environment Variables

Configure the sidecar via environment variables in `docker-compose.yml`:

```yaml
duckdb-sidecar:
  environment:
    S3_ENDPOINT: http://minio:9000
    S3_ACCESS_KEY: admin
    S3_SECRET_KEY: password
    S3_BUCKET: lake-data
    S3_REGION: us-east-1
```

### Custom Ports

Change the port mapping in `docker-compose.yml`:

```yaml
duckdb-sidecar:
  ports:
    - "9001:8001"  # Expose on port 9001 instead
```

## Next Steps

1. Try the example script: `python example_sidecar_usage.py`
2. Integrate with your application using the patterns above
3. Query your data using Trino, ClickHouse, or DuckDB
4. Monitor data growth in MinIO console: http://localhost:9001

## Support

For issues or questions, check:
- Service logs: `docker compose logs duckdb-sidecar`
- API documentation: http://localhost:8001/docs (FastAPI auto-generated docs)
- Health endpoint: http://localhost:8001/health
