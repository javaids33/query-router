import abc
import os
import time
import duckdb
import trino
import psycopg2
import clickhouse_connect
from typing import Dict, Any, Optional

class QueryEngine(abc.ABC):
    """Abstract base class for all query engines."""
    
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @abc.abstractmethod
    def execute(self, sql: str) -> Dict[str, Any]:
        """Executes the SQL and returns a standard result dict: {'data': [...], 'columns': [...]}"""
        pass

    @abc.abstractmethod
    def health_check(self) -> bool:
        pass

class PostgresEngine(QueryEngine):
    def __init__(self):
        self.host = os.getenv("POSTGRES_HOST", "postgres_app")
        self.conn_params = {
            "host": self.host,
            "user": "app_user",
            "password": "app_password",
            "dbname": "app_db"
        }

    def name(self) -> str:
        return "postgres"

    def execute(self, sql: str) -> Dict[str, Any]:
        try:
            conn = psycopg2.connect(**self.conn_params)
            cur = conn.cursor()
            cur.execute(sql)
            
            result = {}
            if cur.description:
                cols = [desc[0] for desc in cur.description]
                res = cur.fetchall()
                result = {"data": [dict(zip(cols, row)) for row in res], "columns": cols}
            else:
                conn.commit()
                result = {"status": "ok", "message": "Query executed successfully"}
                
            conn.close()
            return result
        except Exception as e:
            raise Exception(f"Postgres Error ({self.host}): {e}")

    def health_check(self) -> bool:
        try:
            self.execute("SELECT 1")
            return True
        except:
            return False

class ClickHouseEngine(QueryEngine):
    def __init__(self):
        self.host = os.getenv("CLICKHOUSE_HOST", "clickhouse")
        self._client = None
    
    def _get_client(self):
        if self._client is None:
            self._client = clickhouse_connect.get_client(host=self.host, username='default', password='')
        return self._client

    def name(self) -> str:
        return "clickhouse"

    def execute(self, sql: str) -> Dict[str, Any]:
        try:
            client = self._get_client()
            # Rewrite logic for Demo (S3 Access) - Uses Iceberg table location
            if "FROM users" in sql or "from users" in sql:
                 # Path matches Iceberg table location set in fix_data.py, using recursive glob
                 sql = sql.replace("users", "s3('http://minio:9000/lake-data/data/users*/**/*.parquet', 'admin', 'password', 'Parquet')")
            
            print(f"🐘 [DEBUG] Executing ClickHouse SQL: {sql}")
            res = client.query(sql)
            return {"data": res.result_rows, "columns": res.column_names}
        except Exception as e:
            raise Exception(f"ClickHouse Error ({self.host}): {e}")

    def health_check(self) -> bool:
        try:
            self._get_client().query("SELECT 1")
            return True
        except:
            return False

class TrinoEngine(QueryEngine):
    def __init__(self):
        self.host = os.getenv("TRINO_HOST", "trino")

    def name(self) -> str:
        return "trino"

    def execute(self, sql: str) -> Dict[str, Any]:
        try:
            conn = trino.dbapi.connect(host=self.host, port=8080, user='admin', catalog='iceberg', schema='public')
            cur = conn.cursor()
            cur.execute(sql)
            if cur.description:
                cols = [d[0] for d in cur.description]
                return {"data": [dict(zip(cols, row)) for row in cur.fetchall()], "columns": cols}
            return {"status": "ok"}
        except Exception as e:
             raise Exception(f"Trino Error ({self.host}): {e}")

    def health_check(self) -> bool:
        try:
            self.execute("SELECT 1")
            return True
        except:
            return False

class DuckDBEngine(QueryEngine):
    def __init__(self):
        self.conn = duckdb.connect()
        try:
            self.conn.execute("INSTALL iceberg; LOAD iceberg; INSTALL httpfs; LOAD httpfs;")
            minio_host = os.getenv("MINIO_HOST", "minio")
            minio_port = os.getenv("MINIO_PORT", "9000")
            s3_endpoint = f"{minio_host}:{minio_port}"
            self.conn.execute(f"CREATE SECRET s3 (TYPE S3, KEY_ID 'admin', SECRET 'password', ENDPOINT '{s3_endpoint}', URL_STYLE 'path', USE_SSL false);")
            
            # [FALLBACK] Local tables for demo
            self.conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER, name VARCHAR, role VARCHAR)")
            self.conn.execute("INSERT OR IGNORE INTO users VALUES (1, 'Local Alice', 'Admin'), (2, 'Local Bob', 'User')")
        except Exception as e:
            print(f"Warning: DuckDB setup issues: {e}")

    def name(self) -> str:
        return "duckdb"

    def health_check(self) -> bool:
        return True

    def execute(self, sql: str) -> Dict[str, Any]:
        try:
            # S3/Iceberg Rewrite - Uses Iceberg table location
            s3_sql = sql
            if "users" in sql:
                 # Try direct parquet read since Iceberg metadata might not be accessible
                 s3_sql = sql.replace("users", "read_parquet('s3://lake-data/data/users*/data/*.parquet')")
            
            try:
                res = self.conn.execute(s3_sql).fetchall()
                cols = [d[0] for d in self.conn.description]
                return {"data": [dict(zip(cols, row)) for row in res], "columns": cols}
            except Exception as s3_error:
                print(f"⚠️ DuckDB S3 Usage Failed ({s3_error}), falling back to local table.")
                res = self.conn.execute(sql).fetchall()
                cols = [d[0] for d in self.conn.description]
                return {"data": [dict(zip(cols, row)) for row in res], "columns": cols}
        except Exception as e:
            raise Exception(f"DuckDB Error: {e}")

    def ingest_data(self, table_name: str, csv_path: str):
        """
        Ingests a CSV file into an Iceberg table via DuckDB.
        """
        try:
            # 1. Create Iceberg table if not exists (using S3 path)
            # This is a simplification. Ideally we use Nessie catalog directly or Trino.
            # But DuckDB's Iceberg support can create tables.
            
            s3_table_path = f"s3://lake-data/data/{table_name}"
            
            # Create a table from the CSV Schema
            self.conn.execute(f"CREATE TABLE IF NOT EXISTS iceberg_tmp AS SELECT * FROM read_csv_auto('{csv_path}') LIMIT 0")
            
            # Copy to Iceberg (This might be complex with pure DuckDB Iceberg writer which is still experimental/limited)
            # Alternative: Use DuckDB to write Parquet to S3, then register?
            # Better for Demo: Use Trino for reliable Iceberg writes if DuckDB fails, but let's try DuckDB's native Iceberg write or just "Parquet Export" which is safer for a "Data Garage" concept.
            
            # APPROACH: Write as Parquet to MinIO, simulating an "External Table" or "Data Lake" file.
            # Real Iceberg WRITE support in DuckDB is tricky without a catalog service.
            # Let's write to S3 Parquet and assume we can query it via read_parquet in the future.
            
            upload_path = f"{s3_table_path}/{int(time.time())}.parquet"
            self.conn.execute(f"COPY (SELECT * FROM read_csv_auto('{csv_path}')) TO '{upload_path}' (FORMAT 'parquet')")
            
            return {"status": "ok", "path": upload_path}
            
        except Exception as e:
            raise Exception(f"Ingestion Error: {e}")


class EngineRegistry:
    def __init__(self):
        self.engines: Dict[str, QueryEngine] = {}
        self._init_conn()

    def _init_conn(self):
        # Register default engines
        self.register(PostgresEngine())
        self.register(ClickHouseEngine())
        self.register(TrinoEngine())
        self.register(DuckDBEngine())

    def register(self, engine: QueryEngine):
        self.engines[engine.name()] = engine

    def get_engine(self, name: str) -> Optional[QueryEngine]:
        return self.engines.get(name.lower())

    def list_engines(self):
        return self.engines.keys()
