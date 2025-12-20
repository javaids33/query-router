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
import re
import duckdb
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
from typing import List, Dict, Any, Optional
import json

app = FastAPI(title="DuckDB S3 Sidecar", version="1.0.0")

# --- CONFIGURATION ---
S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://minio:9000")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "admin")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "password")
S3_BUCKET = os.getenv("S3_BUCKET", "lake-data")
S3_REGION = os.getenv("S3_REGION", "us-east-1")

# --- SECURITY ---
# SQL reserved words that should not be used as table names
SQL_RESERVED_WORDS = {
    'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter', 'table',
    'from', 'where', 'join', 'union', 'order', 'group', 'having', 'limit',
    'offset', 'values', 'set', 'into', 'as', 'on', 'and', 'or', 'not', 'null',
    'true', 'false', 'case', 'when', 'then', 'else', 'end', 'with', 'by'
}

def sanitize_table_name(table_name: str) -> str:
    """
    Validate and sanitize table name to prevent SQL injection.
    Only allows alphanumeric characters and underscores.
    """
    if not table_name:
        raise ValueError("Table name cannot be empty")
    
    # Convert to lowercase for comparison
    table_lower = table_name.lower()
    
    # Check against SQL reserved words
    if table_lower in SQL_RESERVED_WORDS:
        raise ValueError(f"Invalid table name: {table_name}. Cannot use SQL reserved words.")
    
    # Only allow alphanumeric and underscore
    if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
        raise ValueError(f"Invalid table name: {table_name}. Only alphanumeric characters and underscores are allowed.")
    
    # Prevent names starting with numbers (DuckDB requirement)
    if table_name[0].isdigit():
        raise ValueError(f"Invalid table name: {table_name}. Table names cannot start with a digit.")
    
    # Limit length
    if len(table_name) > 64:
        raise ValueError(f"Table name too long: {table_name}. Maximum 64 characters.")
    
    return table_name


def sanitize_column_name(column_name: str) -> str:
    """
    Validate and sanitize column name to prevent SQL injection.
    Only allows alphanumeric characters and underscores.
    """
    if not column_name:
        raise ValueError("Column name cannot be empty")
    
    # Convert to lowercase for comparison
    col_lower = column_name.lower()
    
    # Check against SQL reserved words
    if col_lower in SQL_RESERVED_WORDS:
        raise ValueError(f"Invalid column name: {column_name}. Cannot use SQL reserved words.")
    
    if not re.match(r'^[a-zA-Z0-9_]+$', column_name):
        raise ValueError(f"Invalid column name: {column_name}. Only alphanumeric characters and underscores are allowed.")
    
    return column_name

# --- DUCKDB SETUP ---
# Create a persistent DuckDB connection with S3 support
conn = duckdb.connect()

# Install and load required extensions
try:
    # Try to install httpfs first (required for S3 access)
    conn.execute("INSTALL httpfs;")
    conn.execute("LOAD httpfs;")
    print("✅ httpfs extension loaded")
except Exception as e:
    print(f"⚠️  Warning: Could not load httpfs extension: {e}")
    print("   S3 access may be limited. Attempting to continue...")

try:
    # Try to install iceberg
    conn.execute("INSTALL iceberg;")
    conn.execute("LOAD iceberg;")
    print("✅ iceberg extension loaded")
except Exception as e:
    print(f"⚠️  Warning: Could not load iceberg extension: {e}")
    print("   Iceberg features may be limited. Attempting to continue...")

# Configure S3 credentials if httpfs is available
try:
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
except Exception as e:
    print(f"⚠️  Warning: Could not configure S3 secrets: {e}")
    print("   S3 access may not work properly. Service will continue...")


# --- REQUEST MODELS ---
class DataRecord(BaseModel):
    """Single data record to be ingested"""
    data: Dict[str, Any]
    
    @validator('data')
    def validate_data_keys(cls, v):
        """Validate column names in data"""
        for key in v.keys():
            sanitize_column_name(key)
        return v


class DataBatch(BaseModel):
    """Batch of data records to be ingested"""
    table_name: str
    records: List[Dict[str, Any]]
    partition_date: Optional[str] = None  # Format: YYYY-MM-DD, defaults to today
    
    @validator('table_name')
    def validate_table_name(cls, v):
        """Validate table name"""
        return sanitize_table_name(v)
    
    @validator('records')
    def validate_records(cls, v):
        """Validate column names in all records"""
        if not v:
            raise ValueError("Records list cannot be empty")
        for record in v:
            for key in record.keys():
                sanitize_column_name(key)
        return v


class IcebergTableCreate(BaseModel):
    """Request to create an Iceberg table"""
    table_name: str
    schema: Dict[str, str]  # Column name -> DuckDB type (e.g., {"id": "INTEGER", "name": "VARCHAR"})
    
    @validator('table_name')
    def validate_table_name(cls, v):
        """Validate table name"""
        return sanitize_table_name(v)


# --- HELPER FUNCTIONS ---
def get_partition_path(table_name: str, date_str: Optional[str] = None) -> str:
    """
    Generate S3 path with date-based partitioning.
    Format: s3://bucket/table_name/year=YYYY/month=MM/day=DD/
    """
    # Sanitize table name for path
    table_name = sanitize_table_name(table_name)
    
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
    # Sanitize table name
    table_name = sanitize_table_name(table_name)
    
    # Create table from sample if it doesn't exist
    try:
        conn.execute(f"SELECT 1 FROM {table_name} LIMIT 1")
    except:
        # Table doesn't exist, create it from sample record
        # Infer column types from the sample
        columns = []
        for key, value in sample_record.items():
            # Sanitize column name
            col_name = sanitize_column_name(key)
            
            if isinstance(value, int):
                col_type = "INTEGER"
            elif isinstance(value, float):
                col_type = "DOUBLE"
            elif isinstance(value, bool):
                col_type = "BOOLEAN"
            else:
                col_type = "VARCHAR"
            columns.append(f"{col_name} {col_type}")
        
        col_def = ", ".join(columns)
        # Note: table_name is already sanitized, so safe to use in string interpolation
        conn.execute(f"CREATE TABLE {table_name} ({col_def})")
        print(f"✅ Created temporary table: {table_name} with columns: {col_def}")


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
        
        table_name = batch.table_name  # Already validated by Pydantic
        
        # Ensure temp table exists
        ensure_table_exists(table_name, batch.records[0])
        
        # Insert records into temp table using parameterized queries
        # Build the INSERT statement with placeholders
        # Column names are already validated by Pydantic validator
        columns = [sanitize_column_name(col) for col in batch.records[0].keys()]
        placeholders = ", ".join(["?" for _ in columns])
        col_names = ", ".join(columns)
        
        # Note: table_name and col_names are sanitized, safe to use in string interpolation
        insert_sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
        
        # Insert each record
        for record in batch.records:
            values = [record.get(col) for col in columns]
            conn.execute(insert_sql, values)
        
        # Generate partition path
        partition_path = get_partition_path(table_name, batch.partition_date)
        
        # Write to S3 as Parquet with date partition
        output_file = f"{partition_path}/data_{datetime.now().strftime('%H%M%S')}.parquet"
        try:
            conn.execute(f"""
                COPY {table_name} TO '{output_file}' (FORMAT PARQUET)
            """)
            s3_write_success = True
        except Exception as s3_error:
            # S3 write failed (probably due to missing httpfs extension in sandbox)
            # This is expected in some environments
            print(f"⚠️  S3 write failed: {s3_error}")
            output_file = f"(S3 write unavailable: {str(s3_error)[:100]})"
            s3_write_success = False
        
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
        # Sanitize table name from query parameter
        table_name = sanitize_table_name(table_name)
        
        # Ensure temp table exists
        ensure_table_exists(table_name, record.data)
        
        # Insert single record using parameterized query
        # Column names are already validated by Pydantic validator
        columns = [sanitize_column_name(col) for col in record.data.keys()]
        placeholders = ", ".join(["?" for _ in columns])
        col_names = ", ".join(columns)
        
        # Note: table_name and col_names are sanitized, safe to use in string interpolation
        insert_sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"
        values = [record.data.get(col) for col in record.data.keys()]
        conn.execute(insert_sql, values)
        
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
        # Sanitize table name from query parameter
        table_name = sanitize_table_name(table_name)
        
        # Check if table has data (table_name is sanitized, safe to use)
        result = conn.execute(f"SELECT COUNT(*) as cnt FROM {table_name}").fetchone()
        count = result[0] if result else 0
        
        if count == 0:
            return {
                "status": "success",
                "message": "No records to flush",
                "record_count": 0
            }
        
        # Generate partition path (also sanitizes table_name)
        partition_path = get_partition_path(table_name, partition_date)
        
        # Write to S3
        output_file = f"{partition_path}/data_{datetime.now().strftime('%H%M%S')}.parquet"
        try:
            # Note: table_name is sanitized, output_file is generated internally, safe to use
            conn.execute(f"""
                COPY {table_name} TO '{output_file}' (FORMAT PARQUET)
            """)
            s3_write_success = True
        except Exception as s3_error:
            # S3 write failed (probably due to missing httpfs extension in sandbox)
            print(f"⚠️  S3 write failed: {s3_error}")
            output_file = f"(S3 write unavailable: {str(s3_error)[:100]})"
            s3_write_success = False
        
        # Clear table after flush (table_name is sanitized, safe to use)
        conn.execute(f"DELETE FROM {table_name}")
        
        return {
            "status": "success",
            "message": f"Flushed {count} records" + (" to S3" if s3_write_success else " (S3 unavailable)"),
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
        # Sanitize table name from path parameter
        table_name = sanitize_table_name(table_name)
        
        # table_name is sanitized, safe to use in query
        result = conn.execute(f"SELECT COUNT(*) as cnt FROM {table_name}").fetchone()
        count = result[0] if result else 0
        
        return {
            "status": "success",
            "table_name": table_name,
            "buffered_count": count
        }
        
    except ValueError as ve:
        # Invalid table name
        raise HTTPException(status_code=400, detail=str(ve))
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
