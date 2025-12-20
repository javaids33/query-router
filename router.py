import os
import time
import duckdb
import trino
import psycopg2
import clickhouse_connect
import sqlglot
from sqlglot import exp
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

app = FastAPI()

# --- CONFIGURATION & ENV VARS ---
PG_HOST = os.getenv("POSTGRES_HOST", "postgres_app")
CH_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
TRINO_HOST = os.getenv("TRINO_HOST", "trino")
MINIO_HOST = os.getenv("MINIO_HOST", "minio")
MINIO_PORT = os.getenv("MINIO_PORT", "9000")

# --- CONNECTION POOLS ---
PG_CONN = {"host": PG_HOST, "user": "app_user", "password": "app_password", "dbname": "app_db"}

# Lazy connection for ClickHouse to avoid startup race conditions
_CH_CLIENT = None
def get_ch_client():
    global _CH_CLIENT
    if _CH_CLIENT is None:
        try:
            _CH_CLIENT = clickhouse_connect.get_client(host=CH_HOST, username='default', password='')
        except Exception as e:
            print(f"ClickHouse not ready ({CH_HOST}): {e}")
            raise
    return _CH_CLIENT

# DuckDB Setup (Same as before + Iceberg)
# In-memory DuckDB for the router
try:
    ddb = duckdb.connect()
    ddb.execute("INSTALL iceberg; LOAD iceberg; INSTALL httpfs; LOAD httpfs;")
    
    # Check if we are running locally or in docker to decide on S3 endpoint style
    # If local (localhost), we might need path style and different endpoint
    s3_endpoint = f"{MINIO_HOST}:{MINIO_PORT}"
    
    ddb.execute(f"CREATE SECRET s3 (TYPE S3, KEY_ID 'admin', SECRET 'password', ENDPOINT '{s3_endpoint}', URL_STYLE 'path');")
    
    # [FALLBACK] Create local tables for demo if S3/Docker is down
    ddb.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER, name VARCHAR, role VARCHAR)")
    ddb.execute("INSERT INTO users VALUES (1, 'Local Alice', 'Admin'), (2, 'Local Bob', 'User')")
except Exception as e:
    print(f"Warning: DuckDB setup issues: {e}")

# --- ROUTING LOGIC ---

def decide_engine(sql: str) -> str:
    try:
        parsed = sqlglot.parse_one(sql)
    except:
        return "duckdb"
    
    if isinstance(parsed, exp.Select):
        for where in parsed.find_all(exp.Where):
            if "id =" in where.sql().lower() or "id=" in where.sql().lower():
                return "postgres"

    if isinstance(parsed, (exp.Insert, exp.Update, exp.Delete, exp.Create)):
        return "postgres"

    is_agg = False
    for agg in ["COUNT", "SUM", "AVG", "MIN", "MAX"]:
        if agg in sql.upper():
            is_agg = True
            break
            
    has_join = list(parsed.find_all(exp.Join))
    
    if isinstance(parsed, exp.Select) and not has_join and is_agg:
        return "clickhouse"

    if has_join:
        return "trino"

    return "duckdb"

# --- EXECUTION HANDLERS ---

def run_postgres(sql):
    try:
        conn = psycopg2.connect(**PG_CONN)
        cur = conn.cursor()
        cur.execute(sql)
        
        if cur.description:
            res = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            conn.close()
            return {"data": [dict(zip(cols, row)) for row in res]}
        
        conn.commit()
        conn.close()
        return {"status": "ok", "message": "Query executed successfully"}
    except Exception as e:
        raise Exception(f"Postgres Error ({PG_HOST}): {e}")

def run_clickhouse(sql):
    try:
        client = get_ch_client()
        # Rewrite for S3 if needed
        if "FROM users" in sql or "from users" in sql:
             # Use the host-aware MinIO endpoint for rewriting 
             # Note: If CH runs in docker, it NEEDS 'minio' hostname, NOT localhost.
             # This is tricky: Router running locally rewrites query for CH running in Docker.
             # CH in Docker needs 'http://minio:9000'.
             # If we pass 'localhost', CH in container will look at itself.
             # So for the SQL rewrite, we MUST assume the CH container's view of the world.
             # We'll hardcode 'minio' here for the *rewrite* text, assuming CH is always in the mesh or can resolve minio.
             # If CH is external, this rewrite logic would need config.
             sql = sql.replace("users", "s3('http://minio:9000/lake-data/data/users/*.parquet', 'admin', 'password', 'Parquet')")
        
        res = client.query(sql)
        return {"data": res.result_rows, "columns": res.column_names}
    except Exception as e:
        raise Exception(f"ClickHouse Error ({CH_HOST}): {e}")

def run_trino(sql):
    try:
        conn = trino.dbapi.connect(host=TRINO_HOST, port=8080, user='admin', catalog='iceberg', schema='public')
        cur = conn.cursor()
        # Trino might fail if table doesn't exist
        cur.execute(sql)
        if cur.description:
            cols = [d[0] for d in cur.description]
            return {"data": [dict(zip(cols, row)) for row in cur.fetchall()]}
        return {"status": "ok"}
    except Exception as e:
         raise Exception(f"Trino Error ({TRINO_HOST}): {e}")

def run_duckdb(sql):
    try:
        # Try S3/Iceberg first
        s3_sql = sql
        if "users" in sql:
             s3_sql = sql.replace("users", "iceberg_scan('s3://lake-data/data/users', allow_moved_paths=true)")
        
        try:
            res = ddb.execute(s3_sql).fetchall()
            cols = [d[0] for d in ddb.description]
            return {"data": [dict(zip(cols, row)) for row in res]}
        except Exception as s3_error:
            # Fallback to local table
            print(f"⚠️ DuckDB S3 Access Failed ({s3_error}), falling back to local table.")
            res = ddb.execute(sql).fetchall()
            cols = [d[0] for d in ddb.description]
            return {"data": [dict(zip(cols, row)) for row in res]}
            
    except Exception as e:
        raise Exception(f"DuckDB Error: {e}")


class QueryRequest(BaseModel):
    sql: str
    force_engine: Optional[str] = None # Backdoor for performance testing

@app.post("/query")
def router_endpoint(req: QueryRequest):
    sql = req.sql
    
    # Decision Phase
    if req.force_engine:
        engine = req.force_engine.lower()
        print(f"🚦 FORCED Routing Query to: {engine.upper()}")
    else:
        engine = decide_engine(sql)
        print(f"🚦 Routing Query to: {engine.upper()}")
    
    start = time.time()
    
    # Execution Phase
    result = {}
    error_msg = None
    try:
        if engine == 'postgres':
            result = run_postgres(sql)
        elif engine == 'clickhouse':
            result = run_clickhouse(sql)
        elif engine == 'trino':
            result = run_trino(sql)
        elif engine == 'duckdb':
            result = run_duckdb(sql)
        else:
            result = {"error": f"Unknown engine: {engine}"}
    except Exception as e:
        error_msg = str(e)
        print(f"❌ EXECUTION ERROR on {engine.upper()}: {error_msg}")
        result = {"error": error_msg}
        
    if "error" in result:
        print(f"❌ ERROR on {engine.upper()}: {result['error']}")

    duration = time.time() - start
    
    # Response hydration
    result['engine'] = engine
    result['duration'] = duration
    
    return result

@app.get("/health")
def health():
    return {"status": "alive"}
