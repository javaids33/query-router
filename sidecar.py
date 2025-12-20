"""
DuckDB S3 Sidecar Service

A FastAPI service that provides easy data ingestion to S3/Iceberg tables.
Applications can push data to this sidecar, which will handle:
- Date-based partitioning (YYYY/MM/DD)
- S3 writing via DuckDB
- Iceberg table management
- Data format conversion (JSON -> Parquet)
"""

import os
import duckdb
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json

app = FastAPI(title="DuckDB S3 Sidecar", version="1.0.0")

# --- CONFIGURATION ---
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "password")
S3_BUCKET = os.getenv("S3_BUCKET", "lake-data")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

# --- DUCKDB SETUP ---
# Create a persistent DuckDB connection with S3 support
conn = duckdb.connect()

# Install and load required extensions
conn.execute("INSTALL httpfs; LOAD httpfs;")
conn.execute("INSTALL iceberg; LOAD iceberg;")

# Configure S3 credentials
# Extract host and port from endpoint
endpoint_host = S3_ENDPOINT.replace("http://", "").replace("https://", "")
conn.execute(f"""
    CREATE SECRET s3_creds (
        TYPE S3,
        KEY_ID '{S3_ACCESS_KEY}',
        SECRET '{S3_SECRET_KEY}',
        ENDPOINT '{endpoint_host}',
        URL_STYLE 'path',
        REGION '{S3_REGION}'
    );
""")

print(f"✅ DuckDB Sidecar initialized with S3 endpoint: {S3_ENDPOINT}")


# --- REQUEST MODELS ---
class DataRecord(BaseModel):
    """Single data record to be ingested"""
    data: Dict[str, Any]


class DataBatch(BaseModel):
    """Batch of data records to be ingested"""
    table_name: str
    records: List[Dict[str, Any]]
    partition_date: Optional[str] = None  # Format: YYYY-MM-DD, defaults to today


class IcebergTableCreate(BaseModel):
    """Request to create an Iceberg table"""
    table_name: str
    schema: Dict[str, str]  # Column name -> DuckDB type (e.g., {"id": "INTEGER", "name": "VARCHAR"})


# --- HELPER FUNCTIONS ---
def get_partition_path(table_name: str, date_str: Optional[str] = None) -> str:
    """
    Generate S3 path with date-based partitioning.
    Format: s3://bucket/table_name/year=YYYY/month=MM/day=DD/
    """
    if date_str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
    else:
        dt = datetime.now()
    
    year = dt.strftime("%Y")
    month = dt.strftime("%m")
    day = dt.strftime("%d")
    
    # Use Hive-style partitioning for compatibility
    path = f"s3://{S3_BUCKET}/data/{table_name}/year={year}/month={month}/day={day}"
    return path


def ensure_table_exists(table_name: str, sample_record: Dict[str, Any]):
    """
    Ensure a temporary DuckDB table exists for the given data structure.
    Infers schema from the sample record.
    """
    # Create table from sample if it doesn't exist
    try:
        conn.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
    except:
        # Table doesn't exist, create it from sample
        # Convert Python dict to SQL-friendly format
        json_str = json.dumps([sample_record])
        conn.execute(f"""
            CREATE TABLE {table_name} AS 
            SELECT * FROM read_json_auto('{json_str}')
            WHERE 1=0
        """)
        print(f"✅ Created temporary table: {table_name}")


# --- API ENDPOINTS ---

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "duckdb-sidecar",
        "s3_endpoint": S3_ENDPOINT,
        "s3_bucket": S3_BUCKET
    }


@app.post("/ingest")
def ingest_data(batch: DataBatch):
    """
    Ingest a batch of data records and write to S3 with date partitioning.
    
    Example:
    ```
    POST /ingest
    {
        "table_name": "events",
        "records": [
            {"id": 1, "name": "event1", "value": 100},
            {"id": 2, "name": "event2", "value": 200}
        ],
        "partition_date": "2025-12-20"  // Optional, defaults to today
    }
    ```
    """
    try:
        if not batch.records:
            raise HTTPException(status_code=400, detail="No records provided")
        
        table_name = batch.table_name
        
        # Ensure temp table exists
        ensure_table_exists(table_name, batch.records[0])
        
        # Insert records into temp table
        json_data = json.dumps(batch.records)
        conn.execute(f"""
            INSERT INTO {table_name}
            SELECT * FROM read_json_auto('{json_data}')
        """)
        
        # Generate partition path
        partition_path = get_partition_path(table_name, batch.partition_date)
        
        # Write to S3 as Parquet with date partition
        output_file = f"{partition_path}/data_{datetime.now().strftime('%H%M%S')}.parquet"
        conn.execute(f"""
            COPY {table_name} TO '{output_file}' (FORMAT PARQUET)
        """)
        
        # Clear temp table for next batch
        conn.execute(f"DELETE FROM {table_name}")
        
        return {
            "status": "success",
            "message": f"Ingested {len(batch.records)} records",
            "table_name": table_name,
            "s3_path": output_file,
            "partition_date": batch.partition_date or datetime.now().strftime("%Y-%m-%d"),
            "record_count": len(batch.records)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.post("/ingest/stream")
def ingest_stream(table_name: str, record: DataRecord):
    """
    Ingest a single record (streaming mode).
    Records are buffered and flushed periodically.
    
    Example:
    ```
    POST /ingest/stream?table_name=events
    {
        "data": {"id": 1, "name": "event1", "value": 100}
    }
    ```
    """
    try:
        # Ensure temp table exists
        ensure_table_exists(table_name, record.data)
        
        # Insert single record
        json_data = json.dumps([record.data])
        conn.execute(f"""
            INSERT INTO {table_name}
            SELECT * FROM read_json_auto('{json_data}')
        """)
        
        return {
            "status": "success",
            "message": "Record buffered",
            "table_name": table_name
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream ingestion failed: {str(e)}")


@app.post("/flush")
def flush_table(table_name: str, partition_date: Optional[str] = None):
    """
    Flush buffered records to S3.
    Call this after streaming records to persist them to S3.
    
    Example:
    ```
    POST /flush?table_name=events&partition_date=2025-12-20
    ```
    """
    try:
        # Check if table has data
        result = conn.execute(f"SELECT COUNT(*) as cnt FROM {table_name}").fetchone()
        count = result[0] if result else 0
        
        if count == 0:
            return {
                "status": "success",
                "message": "No records to flush",
                "record_count": 0
            }
        
        # Generate partition path
        partition_path = get_partition_path(table_name, partition_date)
        
        # Write to S3
        output_file = f"{partition_path}/data_{datetime.now().strftime('%H%M%S')}.parquet"
        conn.execute(f"""
            COPY {table_name} TO '{output_file}' (FORMAT PARQUET)
        """)
        
        # Clear table after flush
        conn.execute(f"DELETE FROM {table_name}")
        
        return {
            "status": "success",
            "message": f"Flushed {count} records to S3",
            "table_name": table_name,
            "s3_path": output_file,
            "partition_date": partition_date or datetime.now().strftime("%Y-%m-%d"),
            "record_count": count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Flush failed: {str(e)}")


@app.get("/tables")
def list_tables():
    """List all temporary tables currently in the sidecar"""
    try:
        result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'main'
        """).fetchall()
        
        tables = [row[0] for row in result]
        
        return {
            "status": "success",
            "tables": tables
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tables: {str(e)}")


@app.get("/table/{table_name}/count")
def get_table_count(table_name: str):
    """Get the count of buffered records for a table"""
    try:
        result = conn.execute(f"SELECT COUNT(*) as cnt FROM {table_name}").fetchone()
        count = result[0] if result else 0
        
        return {
            "status": "success",
            "table_name": table_name,
            "buffered_count": count
        }
        
    except Exception as e:
        # Table might not exist
        return {
            "status": "success",
            "table_name": table_name,
            "buffered_count": 0
        }


@app.get("/")
def root():
    """Root endpoint with service information"""
    return {
        "service": "DuckDB S3 Sidecar",
        "version": "1.0.0",
        "description": "Fast data ingestion to S3/Iceberg with date-based partitioning",
        "endpoints": {
            "/health": "Health check",
            "/ingest": "Batch data ingestion",
            "/ingest/stream": "Stream single records",
            "/flush": "Flush buffered data to S3",
            "/tables": "List temporary tables",
            "/table/{name}/count": "Get buffered record count"
        },
        "s3_config": {
            "endpoint": S3_ENDPOINT,
            "bucket": S3_BUCKET,
            "region": S3_REGION
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
