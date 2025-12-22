# Connection Architecture - Learning Guide

## 🎓 Introduction for New Engineers

Welcome to the Query Router project! This document provides a comprehensive overview of all connections, integrations, and components in our system. As a new software engineer, this will help you understand:

- **What** each component does
- **How** components connect to each other
- **Why** we chose this architecture
- **Where** to find configuration details

---

## 🏗️ System Architecture Overview

The Query Router is an intelligent SQL query routing system that connects multiple database engines, storage systems, and streaming platforms to provide optimal query performance. Think of it as a "traffic controller" that directs SQL queries to the best engine for the job.

### High-Level Component Map

```
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT LAYER                            │
│  - Dashboard (Streamlit UI)                                 │
│  - External Applications (REST API clients)                  │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP/REST
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              ROUTING LAYER (FastAPI)                         │
│  - Query parsing (SQLGlot)                                  │
│  - Routing decision logic                                   │
│  - Connection pooling                                       │
└─────┬────────┬──────────┬──────────┬──────────┬───────────┘
      │        │          │          │          │
      │        │          │          │          │
┌─────▼──┐ ┌──▼────┐ ┌───▼────┐ ┌──▼─────┐ ┌─▼──────┐
│Postgres│ │ClickH.│ │ Trino  │ │ DuckDB │ │ Kafka  │
│ (OLTP) │ │(Speed)│ │ (Join) │ │(Ad-hoc)│ │(Stream)│
└────────┘ └───┬───┘ └───┬────┘ └────┬───┘ └───┬────┘
               │         │           │          │
               └─────────┴───────────┴──────────┘
                         │                │
                         ▼                ▼
                  ┌──────────┐      ┌─────────┐
                  │  MinIO   │      │  Flink  │
                  │  (S3)    │      │ (Stream │
                  └────┬─────┘      │ Process)│
                       │            └─────────┘
                       │
                  ┌────▼─────┐
                  │  Nessie  │
                  │ (Catalog)│
                  └──────────┘
```

---

## 📊 Connection Details by Component

### 1. **Query Router (FastAPI Application)**

**File:** `router.py`  
**Port:** 8000  
**Role:** Central routing and orchestration layer

#### What it does:
- Accepts SQL queries via REST API
- Parses SQL using SQLGlot library
- Decides which engine should execute the query
- Manages connections to all backend engines
- Returns unified results to clients

#### Connections FROM Router:

| Target | Protocol | Connection Method | Purpose |
|--------|----------|-------------------|---------|
| PostgreSQL | TCP/5432 | psycopg2 | OLTP queries |
| ClickHouse | HTTP/8123 | clickhouse-connect | Analytics queries |
| Trino | HTTP/8080 | trino.dbapi | Complex joins |
| DuckDB | In-process | duckdb (embedded) | Ad-hoc queries |
| MinIO | HTTP/9000 | S3 API (via DuckDB) | Object storage |
| Nessie | HTTP/19120 | REST API (indirect) | Catalog metadata |

#### Configuration:
```python
# Environment Variables (from docker-compose.yml)
POSTGRES_HOST=postgres_app
CLICKHOUSE_HOST=clickhouse
TRINO_HOST=trino
MINIO_HOST=minio
MINIO_PORT=9000
NESSIE_URL=http://nessie:19120/api/v1
S3_ENDPOINT=http://minio:9000
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
```

#### Key Code Sections:
```python
# Connection setup (lines 16-53)
PG_CONN = {"host": PG_HOST, "user": "app_user", ...}
_CH_CLIENT = clickhouse_connect.get_client(host=CH_HOST, ...)
ddb = duckdb.connect()  # Embedded DuckDB

# Routing logic (lines 57-85)
def decide_engine(sql: str) -> str:
    # Parses SQL and decides: postgres, clickhouse, trino, or duckdb
```

---

### 2. **PostgreSQL (postgres_app)**

**Image:** postgres:15  
**Port:** 5432  
**Role:** Primary OLTP (Online Transaction Processing) database

#### What it does:
- Stores transactional data
- Handles INSERT, UPDATE, DELETE operations
- Optimized for point lookups (e.g., `WHERE id = 1`)
- Source of truth for real-time operational data

#### Connections TO PostgreSQL:

| Source | Method | Purpose |
|--------|--------|---------|
| Router | psycopg2 (Python) | Execute OLTP queries |
| init_db.py | HTTP→Router→PostgreSQL | Database initialization |
| test_connections.py | HTTP→Router→PostgreSQL | Connection testing |

#### Credentials:
```yaml
POSTGRES_USER: app_user
POSTGRES_PASSWORD: app_password
POSTGRES_DB: app_db
```

#### Example Queries Routed Here:
- `SELECT * FROM users WHERE id = 1` (point lookup)
- `INSERT INTO users VALUES (...)` (writes)
- `UPDATE users SET role = 'Admin' WHERE id = 5`
- `CREATE TABLE users (...)`

#### Why PostgreSQL?
- **ACID compliance**: Guaranteed data consistency
- **Mature ecosystem**: Well-tested, reliable
- **Row-oriented**: Optimized for transactional workloads

---

### 3. **ClickHouse**

**Image:** clickhouse/clickhouse-server  
**Ports:** 8123 (HTTP), 9009 (Native)  
**Role:** High-speed analytical query engine

#### What it does:
- Executes aggregation queries extremely fast
- Columnar storage for analytical workloads
- Reads data from S3/Parquet files via MinIO
- Optimized for COUNT, SUM, AVG, etc.

#### Connections FROM ClickHouse:

| Target | Protocol | Purpose |
|--------|----------|---------|
| MinIO | HTTP/9000 | Read Parquet files from S3 |

#### Connections TO ClickHouse:

| Source | Method | Purpose |
|--------|--------|---------|
| Router | clickhouse-connect | Execute analytical queries |

#### Credentials:
```yaml
CLICKHOUSE_USER: default
CLICKHOUSE_PASSWORD: "" (empty)
```

#### Example Queries Routed Here:
- `SELECT COUNT(*) FROM users`
- `SELECT role, COUNT(*) FROM users GROUP BY role`
- `SELECT AVG(age) FROM users WHERE created_at > '2025-01-01'`

#### SQL Rewrite Magic:
When the router sends queries to ClickHouse, it rewrites table references:
```python
# Original: SELECT COUNT(*) FROM users
# Rewritten: SELECT COUNT(*) FROM s3('http://minio:9000/lake-data/data/users/*.parquet', ...)
```

#### Why ClickHouse?
- **Speed**: 100-1000x faster than PostgreSQL for aggregations
- **Columnar**: Only reads columns needed for query
- **Compression**: Efficient storage of large datasets

---

### 4. **Trino**

**Image:** trinodb/trino:latest  
**Port:** 8080  
**Role:** Federated query engine for complex analytics

#### What it does:
- Executes queries with JOINs across multiple tables
- Connects to Iceberg tables via Nessie catalog
- Federated queries (can join data from multiple sources)
- SQL-on-everything engine

#### Connections FROM Trino:

| Target | Protocol | Purpose |
|--------|----------|---------|
| Nessie | HTTP/19120 | Catalog metadata (table locations) |
| MinIO | HTTP/9000 | Read Iceberg data files |

#### Connections TO Trino:

| Source | Method | Purpose |
|--------|--------|---------|
| Router | trino.dbapi | Execute JOIN queries |
| Streaming scripts | HTTP→Router→Trino | Write streaming data to Iceberg |

#### Configuration:
**File:** `trino/catalog/iceberg.properties`
```properties
connector.name=iceberg
iceberg.catalog.type=nessie
iceberg.nessie-catalog.uri=http://nessie:19120/api/v2
iceberg.nessie-catalog.ref=main
iceberg.nessie-catalog.default-warehouse-dir=s3://lake-data

s3.endpoint=http://minio:9000
s3.aws-access-key=admin
s3.aws-secret-key=password
s3.path-style-access=true
```

#### Example Queries Routed Here:
- `SELECT a.name, b.role FROM users a JOIN departments b ON a.dept_id = b.id`
- `CREATE TABLE iceberg.public.users AS SELECT * FROM (...)`
- `SELECT * FROM iceberg.public.user_events`

#### Why Trino?
- **Federation**: Query across multiple data sources
- **Iceberg native**: First-class support for Iceberg tables
- **Scalability**: Can handle petabyte-scale data

---

### 5. **DuckDB (Embedded)**

**Type:** In-process library (not a separate service)  
**Port:** N/A (embedded in Router process)  
**Role:** Ad-hoc analytics and fallback engine

#### What it does:
- Embedded analytical database (no separate server)
- Reads Iceberg tables directly from S3
- Fast in-memory processing
- Fallback for queries that don't match other patterns

#### Connections FROM DuckDB:

| Target | Protocol | Purpose |
|--------|----------|---------|
| MinIO | HTTP/9000 | Read Iceberg data via S3 API |

#### Setup in Router:
```python
ddb = duckdb.connect()  # In-memory connection
ddb.execute("INSTALL iceberg; LOAD iceberg;")
ddb.execute("INSTALL httpfs; LOAD httpfs;")  # S3 support
ddb.execute("CREATE SECRET s3 (...)")  # S3 credentials
```

#### Example Queries Routed Here:
- `SELECT * FROM users` (simple SELECT)
- `SELECT name FROM users LIMIT 10`
- Anything that doesn't match PostgreSQL/ClickHouse/Trino patterns

#### Why DuckDB?
- **Embedded**: No network latency
- **Fast**: Vectorized execution engine
- **Flexible**: Can read from CSV, Parquet, JSON, S3, etc.

---

### 6. **MinIO (S3-Compatible Storage)**

**Image:** minio/minio  
**Ports:** 9000 (API), 9001 (Console UI)  
**Role:** Object storage for data lake

#### What it does:
- Stores Parquet files for Iceberg tables
- S3-compatible API
- Data lake storage layer
- Persistent storage for all analytical data

#### Connections TO MinIO:

| Source | Protocol | Purpose |
|--------|----------|---------|
| ClickHouse | S3 API | Read Parquet files |
| Trino | S3 API | Read/Write Iceberg data |
| DuckDB | S3 API | Read Iceberg data |
| Nessie | S3 API | Store Iceberg metadata |
| Flink | S3 API | Write streaming data |

#### Credentials:
```yaml
MINIO_ROOT_USER: admin
MINIO_ROOT_PASSWORD: password
```

#### Storage Structure:
```
s3://lake-data/
  ├── data/
  │   └── users/
  │       ├── file1.parquet
  │       ├── file2.parquet
  │       └── ...
  └── metadata/
      └── (Iceberg metadata files)
```

#### Why MinIO?
- **S3 Compatible**: Drop-in replacement for AWS S3
- **Self-hosted**: No cloud costs for development
- **Performance**: Optimized for high-throughput workloads

---

### 7. **Nessie (Iceberg Catalog)**

**Image:** ghcr.io/projectnessie/nessie:latest  
**Port:** 19120  
**Role:** Git-like catalog for Iceberg tables

#### What it does:
- Tracks Iceberg table metadata (schemas, locations, snapshots)
- Git-like versioning (branches, tags, commits)
- ACID transactions across tables
- Version control for data

#### Connections FROM Nessie:

| Target | Protocol | Purpose |
|--------|----------|---------|
| postgres_catalog | JDBC/5432 | Store catalog metadata |
| MinIO | S3 API | Access warehouse data |

#### Connections TO Nessie:

| Source | Protocol | Purpose |
|--------|----------|---------|
| Trino | REST API | Query table metadata |
| Streaming scripts | REST API | Verify connectivity |

#### Configuration:
```yaml
QUARKUS_DATASOURCE_JDBC_URL: jdbc:postgresql://postgres_catalog:5432/nessie_catalog
NESSIE_CATALOG_DEFAULT_WAREHOUSE: warehouse
NESSIE_CATALOG_WAREHOUSES_WAREHOUSE_LOCATION: s3://lake-data
NESSIE_CATALOG_WAREHOUSES_WAREHOUSE_S3_ENDPOINT: http://minio:9000
```

#### Why Nessie?
- **Versioning**: Rollback bad data changes
- **Branching**: Test data pipelines safely
- **Multi-table ACID**: Atomic commits across tables
- **Audit trail**: Track all data changes

---

### 8. **Apache Kafka**

**Image:** confluentinc/cp-kafka:7.5.0  
**Ports:** 9092 (internal), 29092 (external/localhost)  
**Role:** Distributed message streaming platform

#### What it does:
- Pub/sub messaging for real-time events
- High-throughput event ingestion
- Durable message storage
- Decouples producers from consumers

#### Connections FROM Kafka:

| Target | Protocol | Purpose |
|--------|----------|---------|
| Zookeeper | TCP/2181 | Cluster coordination |

#### Connections TO Kafka:

| Source | Protocol | Purpose |
|--------|----------|---------|
| Streaming producers | Kafka protocol/9092 | Publish events |
| Flink | Kafka protocol/9092 | Consume event streams |
| Streaming consumers | Kafka protocol/9092 | Read events |

#### Configuration:
```yaml
KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:29092
KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
```

#### Topics Used:
- `user_events` - User interaction events (example from streaming_ingestion.py)

#### Why Kafka?
- **Scalability**: Handles millions of events/second
- **Durability**: Persists messages to disk
- **Decoupling**: Producers and consumers are independent

---

### 9. **Apache Zookeeper**

**Image:** confluentinc/cp-zookeeper:7.5.0  
**Port:** 2181  
**Role:** Coordination service for Kafka

#### What it does:
- Manages Kafka cluster metadata
- Leader election for Kafka brokers
- Configuration management
- Cluster coordination

#### Connections TO Zookeeper:

| Source | Protocol | Purpose |
|--------|----------|---------|
| Kafka | ZooKeeper protocol | Cluster coordination |

#### Configuration:
```yaml
ZOOKEEPER_CLIENT_PORT: 2181
ZOOKEEPER_TICK_TIME: 2000
```

#### Why Zookeeper?
- **Required by Kafka**: (Note: Newer Kafka versions can use KRaft instead)
- **Proven**: Battle-tested coordination system
- **Simple**: Easy to deploy for development

---

### 10. **Apache Flink**

**Image:** flink:1.18-java11  
**Ports:** 8081 (JobManager UI)  
**Role:** Real-time stream processing engine

#### Components:
1. **JobManager** - Coordinates stream processing jobs
2. **TaskManager** - Executes stream processing tasks

#### What it does:
- Consumes events from Kafka
- Applies transformations and aggregations
- Writes results to Iceberg tables
- Exactly-once processing guarantees

#### Connections FROM Flink:

| Target | Protocol | Purpose |
|--------|----------|---------|
| Kafka | Kafka protocol | Consume event streams |
| Nessie | REST API | Get Iceberg table metadata |
| MinIO | S3 API | Write Iceberg data files |

#### Configuration:
```yaml
jobmanager.rpc.address: flink-jobmanager
taskmanager.numberOfTaskSlots: 2
```

#### Example Processing Flow:
```
Kafka (raw events)
  → Flink (transformation/aggregation)
    → Iceberg via Nessie (persistent storage)
      → Query engines (Trino/DuckDB)
```

#### Why Flink?
- **True streaming**: Not micro-batching
- **Exactly-once**: Guarantees no duplicates
- **Iceberg native**: Direct integration with Iceberg tables
- **Stateful**: Can maintain state across events

---

### 11. **Dashboard (Streamlit UI)**

**File:** `dashboard.py`  
**Port:** 8501 (when running locally)  
**Role:** Interactive web UI for testing

#### What it does:
- Provides user-friendly interface for queries
- Visualizes query results
- Demonstrates routing behavior
- Performance comparison between engines

#### Connections FROM Dashboard:

| Target | Protocol | Purpose |
|--------|----------|---------|
| Router | HTTP/8000 | Submit SQL queries |

#### How to run:
```bash
pip install streamlit requests pandas plotly
streamlit run dashboard.py
```

---

### 12. **postgres_catalog (Supporting DB)**

**Image:** postgres:15  
**Port:** Not exposed (internal only)  
**Role:** Backend database for Nessie catalog

#### What it does:
- Stores Nessie catalog metadata
- Not directly accessed by users
- Supporting infrastructure for Nessie

#### Connections TO postgres_catalog:

| Source | Protocol | Purpose |
|--------|----------|---------|
| Nessie | JDBC/5432 | Persist catalog metadata |

#### Credentials:
```yaml
POSTGRES_USER: catalog_user
POSTGRES_PASSWORD: catalog_password
POSTGRES_DB: nessie_catalog
```

---

## 🔄 Data Flow Examples

### Example 1: Simple SELECT Query

```
User → Dashboard
  → Router (/query endpoint)
    → Router decides: "duckdb" (simple SELECT)
      → DuckDB executes query
        → (if accessing Iceberg data) DuckDB → MinIO → S3 data
      ← Results
    ← JSON response
  ← Display in UI
```

### Example 2: Aggregation Query

```
User → Router
  → Router decides: "clickhouse" (aggregation)
    → ClickHouse
      → MinIO (read Parquet files)
    ← Results
  ← JSON response
```

### Example 3: Complex JOIN Query

```
User → Router
  → Router decides: "trino" (JOIN detected)
    → Trino
      → Nessie (get table metadata)
      → MinIO (read Iceberg data files)
    ← Results
  ← JSON response
```

### Example 4: Streaming Data Pipeline

```
Event Source
  → Kafka producer (publish to topic)
    → Kafka (store in topic partition)
      → Flink (consume and transform)
        → Nessie (get table location)
        → MinIO (write Parquet files)
        → Nessie (commit new snapshot)
          → Users query via Router
            → Trino/DuckDB
              → Nessie (get latest snapshot)
              → MinIO (read data)
            ← Fresh streaming data!
```

---

## 🔐 Security and Credentials Summary

### Default Credentials (Development Only!)

| Service | Username | Password | Port |
|---------|----------|----------|------|
| PostgreSQL (app) | app_user | app_password | 5432 |
| PostgreSQL (catalog) | catalog_user | catalog_password | internal |
| ClickHouse | default | (empty) | 8123 |
| Trino | admin | (none) | 8080 |
| MinIO | admin | password | 9000 |
| Kafka | - | - | 9092 |

**⚠️ WARNING:** These are default development credentials. **NEVER** use these in production!

### Security Best Practices:

1. **Change all passwords** in production
2. **Use secrets management** (e.g., Vault, AWS Secrets Manager)
3. **Enable TLS/SSL** for all connections
4. **Implement authentication/authorization** at the Router level
5. **Use network policies** to restrict inter-service communication
6. **Enable audit logging** on all databases

---

## 🌐 Network Architecture

All services run in Docker and communicate via Docker's internal DNS:

```
Docker Network: query-router_default

Services can reach each other by hostname:
- postgres_app (PostgreSQL)
- clickhouse (ClickHouse)
- trino (Trino)
- minio (MinIO)
- nessie (Nessie)
- kafka (Kafka)
- zookeeper (Zookeeper)
- flink-jobmanager (Flink)
- flink-taskmanager (Flink)
- router (Query Router)
```

### Port Mappings (Host → Container):

| Service | Internal Port | External Port | Access From |
|---------|---------------|---------------|-------------|
| Router | 8000 | 8000 | localhost:8000 |
| PostgreSQL | 5432 | 5432 | localhost:5432 |
| ClickHouse | 8123 | 8123 | localhost:8123 |
| Trino | 8080 | 8080 | localhost:8080 |
| MinIO API | 9000 | 9000 | localhost:9000 |
| MinIO Console | 9001 | 9001 | localhost:9001 |
| Nessie | 19120 | 19120 | localhost:19120 |
| Kafka (external) | 9092 | 29092 | localhost:29092 |
| Flink UI | 8081 | 8081 | localhost:8081 |
| Zookeeper | 2181 | 2181 | localhost:2181 |

---

## 📁 Configuration Files Reference

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Service definitions, environment variables, networking |
| `router.py` | Main application, connection logic, routing decisions |
| `trino/catalog/iceberg.properties` | Trino connection to Nessie and S3 |
| `Dockerfile` | Router container build instructions |
| `examples/streaming_ingestion.py` | Kafka producer/consumer example |
| `test_connections.py` | Verify all engine connectivity |
| `validation.py` | Health check script |
| `init_db.py` | PostgreSQL initialization |

---

## 🧪 Testing Connections

### 1. Test Router Health

```bash
curl http://localhost:8000/health
# Expected: {"status": "alive"}
```

### 2. Test All Engines

```bash
python test_connections.py
```

This script tests:
- ✅ Router connectivity
- ✅ PostgreSQL (SELECT 1)
- ✅ Trino (SELECT 1)
- ✅ DuckDB (SELECT 1)
- ✅ ClickHouse (SELECT 1)
- ✅ ETL simulation (Postgres → Iceberg)
- ✅ Data verification

### 3. Test Streaming Pipeline

```bash
python examples/streaming_ingestion.py
```

This tests:
- ✅ Nessie connectivity
- ✅ Kafka producer
- ✅ Kafka consumer
- ✅ Iceberg table creation
- ✅ Data ingestion
- ✅ Query via Trino

### 4. Manual Engine Testing

```bash
# PostgreSQL
psql -h localhost -U app_user -d app_db

# ClickHouse
curl 'http://localhost:8123/?query=SELECT%201'

# Trino (via CLI)
docker compose exec trino trino --server localhost:8080 --catalog iceberg --schema public

# MinIO Console
open http://localhost:9001  # admin / password

# Flink UI
open http://localhost:8081

# Nessie API
curl http://localhost:19120/api/v1/config
```

---

## 🚀 Startup Sequence

When you run `docker compose up -d`, services start in this order:

1. **Zookeeper** - First (Kafka dependency)
2. **postgres_catalog** - PostgreSQL for Nessie
3. **MinIO** - Object storage
4. **Nessie** - Waits for postgres_catalog and MinIO
5. **Kafka** - Waits for Zookeeper
6. **postgres_app** - Application database
7. **ClickHouse** - Waits for MinIO
8. **Trino** - Waits for Nessie and MinIO
9. **Flink** - JobManager then TaskManager
10. **Router** - Waits for postgres_app, Trino, ClickHouse

**⏱️ Total startup time:** ~30-60 seconds

---

## 🎯 Routing Decision Logic

The router uses these rules to decide which engine to use:

```python
def decide_engine(sql: str) -> str:
    # 1. POSTGRES: Point lookups and writes
    if "WHERE id = X" or INSERT/UPDATE/DELETE/CREATE:
        return "postgres"
    
    # 2. CLICKHOUSE: Aggregations without JOINs
    if (COUNT/SUM/AVG/MIN/MAX) and no JOINs:
        return "clickhouse"
    
    # 3. TRINO: Queries with JOINs
    if has JOINs:
        return "trino"
    
    # 4. DUCKDB: Everything else (fallback)
    return "duckdb"
```

### Examples:

| Query | Engine | Reason |
|-------|--------|--------|
| `SELECT * FROM users WHERE id = 1` | PostgreSQL | Point lookup |
| `INSERT INTO users VALUES (...)` | PostgreSQL | Write operation |
| `SELECT COUNT(*) FROM users` | ClickHouse | Aggregation, no JOIN |
| `SELECT role, COUNT(*) GROUP BY role` | ClickHouse | Aggregation, no JOIN |
| `SELECT a.* FROM users a JOIN depts b ON ...` | Trino | Has JOIN |
| `SELECT * FROM users` | DuckDB | Simple SELECT (fallback) |

---

## 💡 Key Insights for New Engineers

### 1. **Why Multiple Engines?**

Each engine is optimized for different workloads:

- **PostgreSQL**: Best for transactional consistency (OLTP)
- **ClickHouse**: 100-1000x faster for aggregations (OLAP)
- **Trino**: Best for complex analytics and federating data sources
- **DuckDB**: Fast, embedded, great for ad-hoc analysis

**One size doesn't fit all!** This architecture leverages the strengths of each.

### 2. **Iceberg + Nessie = Modern Data Lake**

- **Iceberg**: Open table format (like "SQL for data files")
- **Nessie**: Git for data (branch, commit, rollback)
- **MinIO**: Storage layer (S3-compatible)

Together they provide:
- ACID transactions
- Schema evolution
- Time travel
- Version control for data

### 3. **Streaming Architecture**

The streaming pipeline (Kafka → Flink → Iceberg) enables:

- **Real-time ingestion**: Events appear in queries within seconds
- **Exactly-once semantics**: No duplicates or data loss
- **Unified batch + streaming**: Same tables for both use cases
- **Late data handling**: Flink handles out-of-order events

### 4. **Connection Patterns**

Notice these patterns:

- **Router is the hub**: All client requests go through it
- **Engines are specialized**: Each does one thing well
- **Storage is shared**: MinIO is the single source of truth
- **Catalog is centralized**: Nessie tracks all table metadata

---

## 🔧 Troubleshooting Guide

### Problem: "Connection Refused" Errors

**Possible Causes:**
1. Services haven't finished starting (wait 30-60s)
2. Docker isn't running
3. Port conflicts on host machine

**Debug Steps:**
```bash
# Check all services are running
docker compose ps

# Check logs for specific service
docker compose logs router
docker compose logs postgres_app
docker compose logs kafka

# Restart everything
docker compose down -v
docker compose up -d
```

### Problem: ClickHouse Queries Fail

**Possible Causes:**
1. MinIO not accessible
2. No data in S3 bucket
3. S3 credentials incorrect

**Debug Steps:**
```bash
# Test MinIO directly
curl http://localhost:9000/minio/health/live

# Check MinIO console
open http://localhost:9001

# Test ClickHouse directly
docker compose exec clickhouse clickhouse-client --query "SELECT 1"
```

### Problem: Trino Can't Find Tables

**Possible Causes:**
1. Nessie not running
2. Table doesn't exist in Iceberg catalog
3. S3 configuration incorrect in Trino

**Debug Steps:**
```bash
# Test Nessie
curl http://localhost:19120/api/v1/config

# Connect to Trino CLI
docker compose exec trino trino

# List catalogs and schemas
SHOW CATALOGS;
SHOW SCHEMAS FROM iceberg;
SHOW TABLES FROM iceberg.public;
```

### Problem: Kafka Connection Issues

**Possible Causes:**
1. Zookeeper not running
2. Kafka not fully started
3. Wrong bootstrap servers address

**Debug Steps:**
```bash
# Check Zookeeper
docker compose logs zookeeper

# Check Kafka
docker compose logs kafka

# Test Kafka connectivity
docker compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092

# List topics
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

---

## 📚 Additional Learning Resources

### Understanding Query Routing
- Read: `BENCHMARK.md` - Performance comparison between engines
- Read: `README.md` - Usage examples and API documentation

### Understanding Streaming
- Read: `STREAMING.md` - Detailed streaming architecture
- Run: `examples/streaming_ingestion.py` - Hands-on streaming demo
- Read: `QUICKSTART_STREAMING.md` - Quick streaming setup guide

### Understanding Each Component
- [DuckDB Docs](https://duckdb.org/docs/) - Embedded analytics
- [Trino Docs](https://trino.io/docs/current/) - Federated queries
- [ClickHouse Docs](https://clickhouse.com/docs/) - OLAP engine
- [Iceberg Docs](https://iceberg.apache.org/) - Table format
- [Nessie Docs](https://projectnessie.org/) - Data versioning
- [Kafka Docs](https://kafka.apache.org/documentation/) - Streaming platform
- [Flink Docs](https://nightlies.apache.org/flink/) - Stream processing

---

## 🎓 Conclusion

You now have a comprehensive understanding of all connections in the Query Router system! Here's a summary:

**11 Major Components:**
1. Query Router (FastAPI) - Central orchestration
2. PostgreSQL - OLTP database
3. ClickHouse - Fast analytics
4. Trino - Complex joins and federation
5. DuckDB - Embedded ad-hoc analytics
6. MinIO - S3 storage
7. Nessie - Data catalog with versioning
8. Kafka - Message streaming
9. Zookeeper - Kafka coordination
10. Flink - Stream processing
11. postgres_catalog - Nessie backend

**Key Connection Patterns:**
- All queries route through FastAPI
- All analytical data stored in MinIO (S3)
- All table metadata tracked in Nessie
- Streaming data flows: Kafka → Flink → Iceberg

**Next Steps:**
1. Run `docker compose up -d` to start all services
2. Run `python test_connections.py` to verify connectivity
3. Try the dashboard: `streamlit run dashboard.py`
4. Experiment with streaming: `python examples/streaming_ingestion.py`
5. Read the other documentation files for deeper dives

Welcome to the team! 🎉

---

*Document created: 2025-12-22*  
*Author: Query Router Team*  
*Version: 1.0*
