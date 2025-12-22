# DuckDB S3 Sidecar - Data Flow Diagram

## Complete Data Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         YOUR APPLICATION                             │
│  (Can be any service/pod in the cluster)                            │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ HTTP POST /ingest
                               │ { table_name, records, partition_date }
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DuckDB S3 SIDECAR (Port 8001)                     │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │  FastAPI Service                                                 │ │
│ │  - /health - Health check                                       │ │
│ │  - /ingest - Batch data ingestion                               │ │
│ │  - /ingest/stream - Stream single records                       │ │
│ │  - /flush - Flush buffered data                                 │ │
│ │  - /tables - List active tables                                 │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                               │                                      │
│ ┌─────────────────────────────▼───────────────────────────────────┐ │
│ │  DuckDB In-Memory Processing                                    │ │
│ │  - Schema inference from data                                   │ │
│ │  - Temporary table buffering                                    │ │
│ │  - Data validation                                              │ │
│ └─────────────────────────────┬───────────────────────────────────┘ │
│                               │                                      │
│ ┌─────────────────────────────▼───────────────────────────────────┐ │
│ │  Date Partitioning Logic                                        │ │
│ │  - Automatic YYYY/MM/DD structure                               │ │
│ │  - Hive-style partitioning                                      │ │
│ │  - Parquet file generation                                      │ │
│ └─────────────────────────────┬───────────────────────────────────┘ │
└───────────────────────────────┼───────────────────────────────────────┘
                                │
                                │ COPY TO s3://...
                                │ (Parquet format)
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       MINIO S3 STORAGE                               │
│                                                                      │
│  s3://lake-data/data/                                               │
│  ├── events/                                                        │
│  │   └── year=2025/                                                 │
│  │       └── month=12/                                              │
│  │           ├── day=18/                                            │
│  │           │   └── data_100530.parquet                            │
│  │           ├── day=19/                                            │
│  │           │   └── data_143022.parquet                            │
│  │           └── day=20/                                            │
│  │               └── data_095511.parquet                            │
│  │                                                                  │
│  ├── metrics/                                                       │
│  │   └── year=2025/month=12/day=20/data_*.parquet                  │
│  │                                                                  │
│  └── orders/                                                        │
│      └── year=2025/month=12/day=20/data_*.parquet                  │
│                                                                      │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               │ Query/Read Access
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│    Trino     │      │  ClickHouse  │      │   DuckDB     │
│   (Joins)    │      │  (Analytics) │      │  (Ad-hoc)    │
└──────────────┘      └──────────────┘      └──────────────┘
```

## Usage Patterns

### Pattern 1: Batch ETL Pipeline

```
Application Data → Batch Ingestion → Immediate S3 Write
                    (/ingest)
                    
Timeline: Minutes to Hours
Use Case: Daily exports, scheduled jobs, bulk transfers
```

### Pattern 2: Real-Time Streaming

```
Event Stream → Stream Records → Buffer → Flush → S3
               (/ingest/stream)           (/flush)
               
Timeline: Seconds to Minutes
Use Case: Logs, events, sensors, real-time analytics
```

### Pattern 3: Historical Backfill

```
Historical Data → Multiple Batch Ingests with Different Dates → Partitioned S3
                  (partition_date parameter)
                  
Timeline: Hours to Days
Use Case: Data migration, historical analysis, backfilling
```

## Key Features

✅ **Zero Configuration** - No S3 setup needed in your application
✅ **Automatic Partitioning** - Data organized by date for efficient querying
✅ **Schema Inference** - Tables created automatically from your data
✅ **Dual Mode** - Batch for bulk, streaming for real-time
✅ **Format Optimization** - Automatic Parquet conversion
✅ **Buffering** - Efficient memory usage with manual flush control
✅ **Multi-Tenant** - Multiple applications can share the same sidecar

## Example Data Flow

1. Your application generates events:
   ```json
   {"user_id": 123, "action": "purchase", "amount": 99.99}
   ```

2. POST to sidecar:
   ```bash
   curl -X POST http://duckdb-sidecar:8001/ingest -d '{
     "table_name": "events",
     "records": [{"user_id": 123, "action": "purchase", "amount": 99.99}]
   }'
   ```

3. Sidecar processes:
   - Creates table if needed
   - Inserts into DuckDB buffer
   - Writes to S3: `s3://lake-data/data/events/year=2025/month=12/day=20/data_HHMMSS.parquet`

4. Query engines can now read:
   ```sql
   -- Trino
   SELECT * FROM iceberg.public.events WHERE year=2025 AND month=12;
   
   -- ClickHouse
   SELECT count(*) FROM s3('http://minio:9000/lake-data/data/events/**/*.parquet');
   
   -- DuckDB
   SELECT * FROM iceberg_scan('s3://lake-data/data/events');
   ```

## Benefits

- **Simplified Integration**: One endpoint for all S3 writes
- **Performance**: DuckDB's efficient processing and Parquet format
- **Scalability**: Horizontal scaling by running multiple sidecar instances
- **Flexibility**: Works with any language/framework via HTTP
- **Observability**: Built-in endpoints for monitoring buffer state
- **Reliability**: Graceful error handling and automatic retry support
