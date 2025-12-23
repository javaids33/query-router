import time
import sqlglot
from sqlglot import exp
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

# Import our new Engine abstraction
from engines import EngineRegistry

app = FastAPI()

# --- INITIALIZATION ---
registry = EngineRegistry()

# --- ROUTING LOGIC ---

def decide_engine(sql: str) -> str:
    """
    Analyzes SQL to determine the best engine.
    This logic mimics the original heuristics for the demo.
    """
    try:
        parsed = sqlglot.parse_one(sql)
    except:
        return "duckdb"
    
    # 1. Transactional / Point Lookups -> Postgres
    if isinstance(parsed, exp.Select):
        for where in parsed.find_all(exp.Where):
            # Very simple heuristic for "id =" lookup
            if "id =" in where.sql().lower() or "id=" in where.sql().lower():
                return "postgres"

    # 2. Writes -> Postgres (Simulating OLTP primary)
    if isinstance(parsed, (exp.Insert, exp.Update, exp.Delete, exp.Create)):
        return "postgres"

    # 3. Check for Analytical / Aggregation intent
    is_agg = False
    for agg in ["COUNT", "SUM", "AVG", "MIN", "MAX"]:
        if agg in sql.upper():
            is_agg = True
            break
            
    has_join = list(parsed.find_all(exp.Join))
    
    # 4. Aggregations on single table -> ClickHouse
    if isinstance(parsed, exp.Select) and not has_join and is_agg:
        return "clickhouse"

    # 5. Joins (Federation) -> Trino
    if has_join:
        return "trino"

    # 6. Default / Ad-hoc / Local Files -> DuckDB
    return "duckdb"

# --- API ENDPOINTS ---

class QueryRequest(BaseModel):
    sql: str
    force_engine: Optional[str] = None # Backdoor for testing/demo

@app.post("/query")
def router_endpoint(req: QueryRequest):
    sql = req.sql
    
    # Decision Phase
    if req.force_engine:
        engine_name = req.force_engine.lower()
        print(f"🚦 FORCED Routing Query to: {engine_name.upper()}")
    else:
        engine_name = decide_engine(sql)
        print(f"🚦 Routing Query to: {engine_name.upper()}")
    
    engine = registry.get_engine(engine_name)
    if not engine:
        return {"error": f"Unknown engine: {engine_name}"}

    start = time.time()
    
    # Execution Phase
    result = {}
    try:
        result = engine.execute(sql)
    except Exception as e:
        error_msg = str(e)
        print(f"❌ EXECUTION ERROR on {engine_name.upper()}: {error_msg}")
        result = {"error": error_msg}
        
    duration = time.time() - start
    
    # Response hydration
    result['engine'] = engine_name
    result['duration'] = duration
    
    return result

@app.post("/ingest")
def ingest_endpoint(file_path: str, table_name: str):
    """
    Simulates ingestion by telling DuckDB to read a local CSV and write to S3.
    """
    engine = registry.get_engine("duckdb")
    if not engine:
        return {"error": "Ingestion requires DuckDB engine"}
        
    try:
        # We assume the file is accessible to the router (shared volume or uploaded to a temp path)
        res = engine.ingest_data(table_name, file_path)
        return res
    except Exception as e:
        return {"error": str(e)}

@app.get("/health")
def health():
    return {"status": "alive", "engines": list(registry.list_engines())}

