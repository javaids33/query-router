# 🏎️ SQL Query Router

An intelligent SQL query router that automatically directs queries to the optimal database engine based on query characteristics and workload patterns.

## 🎯 Overview

The Query Router is a FastAPI-based application that implements intelligent query routing across multiple database engines:

- **PostgreSQL** - OLTP workloads and transactional queries
- **ClickHouse** - Fast analytical aggregations
- **Trino** - Complex joins and federated queries
- **DuckDB** - Ad-hoc analytics and Iceberg table access

The router automatically analyzes incoming SQL queries and routes them to the most appropriate engine based on query patterns, optimizing for performance and resource utilization.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Client Application                    │
│                   (Dashboard/API)                        │
└────────────────────┬───────────┬────────────────────────┘
                     │           │
                     │           │ POST /ingest (data)
                     │           │
                     ▼           ▼
┌─────────────────────────────┐  ┌──────────────────────┐
│   Query Router (FastAPI)    │  │ DuckDB S3 Sidecar 🆕 │
│ - SQL Parsing (SQLGlot)     │  │ - Data Ingestion     │
│ - Routing Logic             │  │ - S3 Writing         │
│ - DuckDB Integration        │  │ - Date Partitioning  │
└─────┬───────┬────────┬──────┘  └──────────┬───────────┘
      │       │        │                    │
      ▼       ▼        ▼                    │
  ┌────────┐ ┌──────┐ ┌──────┐             │
  │Postgres│ │ClickH│ │Trino │             │
  │ (OLTP) │ │(Speed)│ │(Join)│             │
  └────────┘ └───┬──┘ └───┬──┘             │
                 │        │                │
                 └────────┴────────────────┘
                          │
                          ▼
              ┌─────────────────────────┐
              │  MinIO (S3 Storage)      │
              │  + Nessie Catalog        │
              │  (Iceberg Tables)        │
              │                          │
              │  lake-data/              │
              │  └─ data/                │
              │     └─ {table}/          │
              │        └─ year=YYYY/     │
              │           └─ month=MM/   │
              │              └─ day=DD/  │
              │                 └─ *.parquet │
              └─────────────────────────┘
```

## 🚀 Components

### Core Components

1. **Query Router (`router.py`)**
   - FastAPI application handling query routing
   - SQL parsing and analysis using SQLGlot
   - Connection management for all engines
   - Intelligent routing decision logic

2. **PostgreSQL (postgres_app)**
   - Primary OLTP database
   - Handles INSERT, UPDATE, DELETE operations
   - Point lookups (queries with `WHERE id = X`)
   - Source of truth for transactional data

3. **ClickHouse**
   - High-speed analytical queries
   - Aggregation functions (COUNT, SUM, AVG, etc.)
   - Reads from S3/Parquet via MinIO
   - Optimized for columnar operations

4. **Trino**
   - Complex JOIN operations
   - Federated query engine
   - Iceberg table access via Nessie catalog
   - Multi-source data integration

5. **DuckDB (Embedded)**
   - Ad-hoc analytical queries
   - Iceberg table scanning
   - Fallback engine for simple queries
   - In-memory processing with S3 integration

6. **MinIO**
   - S3-compatible object storage
   - Stores Iceberg table data (Parquet files)
   - Warehouse location for data lake

7. **Nessie**
   - Git-like catalog for Iceberg tables
   - Version control for data
   - REST catalog endpoint for metadata

8. **DuckDB S3 Sidecar (`sidecar.py`)** 🆕
   - Dedicated service for data ingestion to S3
   - Automatic date-based partitioning (YYYY/MM/DD)
   - FastAPI endpoints for batch and streaming data
   - Direct Parquet writing to S3/Iceberg
   - Easy integration for any application in the cluster

### Supporting Components

- **Dashboard (`dashboard.py`)** - Streamlit web UI for interactive testing
- **Validation (`validation.py`)** - Health checks and connectivity tests
- **Test Utilities** - Connection testing and data verification scripts

## 📋 Prerequisites

- Docker and Docker Compose
- Python 3.9+ (for local development)
- 8GB+ RAM recommended for running all services

## 🔧 Installation & Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd query-router
```

### 2. Start All Services

```bash
docker compose up -d
```

This starts:
- PostgreSQL (port 5432)
- ClickHouse (port 8123, 9009)
- Trino (port 8080)
- MinIO (port 9000, 9001)
- Nessie (port 19120)
- Query Router (port 8000)
- **DuckDB S3 Sidecar (port 8001)** 🆕

### 3. Wait for Services to Initialize

```bash
# Check service health
docker compose ps

# View router logs
docker compose logs -f router

# View sidecar logs
docker compose logs -f duckdb-sidecar
```

### 4. Initialize Data (Optional)

```bash
# Initialize PostgreSQL with sample data
python init_db.py

# Or use the dashboard to create tables and insert data
```

## 🎮 Usage

### API Endpoints

#### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "alive"
}
```

#### Query Execution

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT * FROM users WHERE id = 1"
  }'
```

Response:
```json
{
  "data": [{"id": 1, "name": "Alice", "role": "Engineer"}],
  "engine": "postgres",
  "duration": 0.0234
}
```

#### Force Specific Engine

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT COUNT(*) FROM users",
    "force_engine": "clickhouse"
  }'
```

### DuckDB S3 Sidecar - Data Ingestion 🆕

The DuckDB sidecar provides a simple API for pushing data directly to S3 with automatic date-based partitioning.

#### Why Use the Sidecar?

- **Easy S3 Integration**: No need to configure S3 in your application
- **Automatic Partitioning**: Data is organized by date (year/month/day)
- **Direct to Iceberg**: Data flows directly to your data lake
- **Flexible Ingestion**: Batch or streaming modes
- **Format Handling**: Automatic conversion to Parquet

#### Quick Start

```bash
# Check sidecar health
curl http://localhost:8001/health

# Ingest batch data
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

Response:
```json
{
  "status": "success",
  "s3_path": "s3://lake-data/data/events/year=2025/month=12/day=20/data_100530.parquet",
  "record_count": 2,
  "partition_date": "2025-12-20"
}
```

#### Ingestion Patterns

**1. Batch Ingestion (Best for bulk transfers)**

```python
import requests

data = {
    "table_name": "sales",
    "records": [
        {"id": 1, "product": "Widget", "amount": 100},
        {"id": 2, "product": "Gadget", "amount": 200}
    ],
    "partition_date": "2025-12-20"  # Optional
}

response = requests.post("http://localhost:8001/ingest", json=data)
print(response.json())
```

**2. Streaming Ingestion (Best for real-time data)**

```python
import requests

# Stream individual records
for record in event_stream:
    requests.post(
        "http://localhost:8001/ingest/stream?table_name=events",
        json={"data": record}
    )

# Flush buffered records to S3
requests.post("http://localhost:8001/flush?table_name=events")
```

**3. From Application Pod to Sidecar**

In your application (running in the same Docker network):

```python
import requests

# Use the service name from docker-compose
SIDECAR_URL = "http://duckdb-sidecar:8001"

def send_to_data_lake(data):
    """Push data from your app to the data lake"""
    response = requests.post(
        f"{SIDECAR_URL}/ingest",
        json={
            "table_name": "app_data",
            "records": data
        }
    )
    return response.json()

# In your application logic
events = fetch_app_events()
result = send_to_data_lake(events)
print(f"Sent {result['record_count']} records to S3")
```

#### Data Flow Pattern

```
Your App → POST /ingest → DuckDB Sidecar → S3/Iceberg
   │              │              │              │
   │              │              │              └→ Parquet files
   │              │              └→ Date partitioning
   │              └→ JSON data
   └→ Any pod in cluster

Result: s3://lake-data/data/{table}/year=YYYY/month=MM/day=DD/data_*.parquet
```

#### Run the Examples

```bash
# Run comprehensive examples
python example_sidecar_usage.py
```

This demonstrates:
- Batch ingestion with date partitioning
- Streaming with manual flush
- Historical data loading
- Multi-table management

#### API Documentation

Access interactive API docs at: http://localhost:8001/docs

Available endpoints:
- `GET /health` - Health check
- `POST /ingest` - Batch data ingestion
- `POST /ingest/stream` - Stream single records
- `POST /flush` - Flush buffered data to S3
- `GET /tables` - List all temporary tables
- `GET /table/{name}/count` - Get buffered record count

### Dashboard UI

The Streamlit dashboard provides an interactive interface:

```bash
# Install dependencies
pip install streamlit requests pandas plotly

# Run dashboard
streamlit run dashboard.py
```

Access at: http://localhost:8501

Features:
- Live data feed from PostgreSQL
- Intelligent routing demonstration
- Performance comparison between engines
- Catalog benchmark comparison

## 🧠 Routing Logic

The router analyzes SQL queries and applies these rules:

### 1. **PostgreSQL** (OLTP Engine)
- Point lookups: `WHERE id = X`
- Write operations: INSERT, UPDATE, DELETE, CREATE
- Transactional consistency required

**Example:**
```sql
SELECT * FROM users WHERE id = 1
INSERT INTO users (name, role) VALUES ('Charlie', 'Analyst')
```

### 2. **ClickHouse** (Speed Engine)
- Aggregation queries without JOINs
- COUNT, SUM, AVG, MIN, MAX operations
- Single-table analytics

**Example:**
```sql
SELECT COUNT(*) FROM users
SELECT role, COUNT(*) FROM users GROUP BY role
```

### 3. **Trino** (Join Engine)
- Queries with JOIN operations
- Multi-table queries
- Complex analytical workloads

**Example:**
```sql
SELECT a.name, b.role 
FROM users a 
JOIN users b ON a.id = b.id
```

### 4. **DuckDB** (Fallback/Ad-hoc Engine)
- Simple SELECT queries
- Ad-hoc analysis
- Iceberg table scanning
- Queries that don't match other patterns

**Example:**
```sql
SELECT * FROM users
SELECT name FROM users LIMIT 10
```

## 🔌 Environment Variables

Configure the router using these environment variables:

```bash
POSTGRES_HOST=postgres_app      # PostgreSQL hostname
CLICKHOUSE_HOST=clickhouse      # ClickHouse hostname
TRINO_HOST=trino                # Trino hostname
MINIO_HOST=minio                # MinIO hostname
MINIO_PORT=9000                 # MinIO port
NESSIE_URL=http://nessie:19120/api/v1  # Nessie catalog URL
S3_ENDPOINT=http://minio:9000   # S3 endpoint
```

## 🧪 Testing

### Connection Testing

```bash
python test_connections.py
```

This tests:
- Router health endpoint
- Individual engine connectivity
- ETL simulation (Postgres → Iceberg)
- Data verification

### Validation Suite

```bash
python validation.py
```

Performs:
- Router connectivity check
- Engine connectivity for all databases
- Data existence verification
- Comprehensive health report

### Data Verification

```bash
python verify_data.py
```

Checks:
- Nessie catalog accessibility
- Iceberg table data
- Snapshot information

## 📊 Performance Characteristics

| Engine     | Best For                  | Latency  | Scalability |
|-----------|---------------------------|----------|-------------|
| PostgreSQL | Point lookups, writes     | Low      | Medium      |
| ClickHouse | Aggregations             | Very Low | Very High   |
| Trino      | Complex joins            | Medium   | High        |
| DuckDB     | Ad-hoc queries           | Low      | Medium      |

## 🛠️ Development

### Local Development Setup

```bash
# Install Python dependencies
pip install fastapi uvicorn duckdb trino clickhouse-connect \
    psycopg2-binary sqlglot requests streamlit pandas plotly

# Run router locally (ensure Docker services are up)
uvicorn router:app --reload --host 0.0.0.0 --port 8000
```

### Project Structure

```
query-router/
├── router.py              # Main FastAPI application
├── dashboard.py           # Streamlit dashboard
├── init_db.py            # Database initialization
├── test_connections.py    # Connection tests
├── validation.py         # Health checks
├── verify_data.py        # Data verification
├── docker-compose.yml    # Service orchestration
├── Dockerfile            # Router container image
├── trino/
│   └── catalog/
│       └── iceberg.properties  # Trino Iceberg config
└── README.md             # This file
```

## 🐛 Troubleshooting

### Common Issues

1. **Services not starting**
   ```bash
   docker compose down -v
   docker compose up -d
   ```

2. **Connection refused errors**
   - Wait for services to fully initialize (30-60 seconds)
   - Check logs: `docker compose logs <service-name>`

3. **ClickHouse queries failing**
   - Ensure MinIO is accessible
   - Check S3 endpoint configuration
   - Verify data exists in S3 bucket

4. **Trino Iceberg errors**
   - Verify Nessie is running: `curl http://localhost:19120/api/v1/config`
   - Check Iceberg catalog configuration in `trino/catalog/iceberg.properties`

5. **DuckDB S3 access failed**
   - Router falls back to local in-memory table automatically
   - Check MinIO credentials and endpoint

## 🔒 Security Notes

- Default credentials are for development only
- Change all passwords in production
- Implement proper authentication/authorization
- Use secrets management for credentials
- Enable TLS/SSL for production deployments

## 📚 Additional Resources

- [DuckDB Documentation](https://duckdb.org/docs/)
- [Trino Documentation](https://trino.io/docs/current/)
- [ClickHouse Documentation](https://clickhouse.com/docs/)
- [Apache Iceberg](https://iceberg.apache.org/)
- [Project Nessie](https://projectnessie.org/)

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

[Add your license information here]

## 👥 Authors

[Add author information here]

## 🙏 Acknowledgments

This project integrates multiple open-source technologies:
- FastAPI for the API framework
- SQLGlot for SQL parsing
- DuckDB for embedded analytics
- Trino for federated queries
- ClickHouse for fast analytics
- PostgreSQL for OLTP workloads
- Apache Iceberg for table format
- Project Nessie for catalog management
- MinIO for object storage
