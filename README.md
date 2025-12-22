# 🏎️ SQL Query Router

An intelligent SQL query router that automatically directs queries to the optimal database engine based on query characteristics and workload patterns. **Now with streaming ingestion support via Kafka + Flink!**

## 🎯 Overview

The Query Router is a FastAPI-based application that implements intelligent query routing across multiple database engines:

- **PostgreSQL** - OLTP workloads and transactional queries
- **ClickHouse** - Fast analytical aggregations
- **Trino** - Complex joins and federated queries
- **DuckDB** - Ad-hoc analytics and Iceberg table access

Additionally, the platform supports **streaming data ingestion**:

- **Kafka** - Distributed message streaming platform
- **Flink** - Real-time stream processing engine
- **Iceberg + Nessie** - Data lake tables with Git-like versioning

The router automatically analyzes incoming SQL queries and routes them to the most appropriate engine based on query patterns, optimizing for performance and resource utilization.

## 🏗️ Architecture

### Batch + OLAP Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Client Application                    │
│                   (Dashboard/API)                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Query Router (FastAPI)                  │
│  - SQL Parsing (SQLGlot)                                │
│  - Routing Logic                                        │
│  - DuckDB Integration                                   │
└─────┬───────┬──────────┬────────────┬──────────────────┘
      │       │          │            │
      ▼       ▼          ▼            ▼
  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐
  │Postgres│ │ClickH. │ │ Trino  │ │  DuckDB    │
  │ (OLTP) │ │ (Speed)│ │ (Join) │ │ (Ad-hoc)   │
  └────────┘ └───┬────┘ └───┬────┘ └─────┬──────┘
                 │          │            │
                 └──────────┴────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  MinIO (S3 Storage)  │
                 │  + Nessie Catalog    │
                 │  (Iceberg Tables)    │
                 └─────────────────────┘
```

### Streaming Ingestion Architecture

```
┌──────────────────────────────────────────────────────────┐
│                   Data Sources                            │
│          (Applications, IoT, Logs, Events)               │
└────────────────────┬─────────────────────────────────────┘
                     │
                     ▼
              ┌─────────────┐
              │    Kafka    │  ← Message Streaming
              │  (Topics)   │     • High throughput
              └──────┬──────┘     • Distributed
                     │
                     ▼
              ┌─────────────┐
              │    Flink    │  ← Stream Processing
              │(Job/Task Mgr)│    • Real-time ETL
              └──────┬──────┘     • Stateful ops
                     │
                     ▼
              ┌─────────────┐
              │   Iceberg   │  ← Table Format
              │ (via Nessie)│     • ACID txns
              └──────┬──────┘     • Versioning
                     │
                     ▼
              ┌─────────────┐
              │    MinIO    │  ← Storage Layer
              └──────┬──────┘
                     │
         ┌───────────┴───────────┐
         ▼                       ▼
    ┌────────┐              ┌────────┐
    │ Trino  │              │ DuckDB │  ← Query Layer
    └────────┘              └────────┘
```

**Complete Flow:** 
`Events → Kafka → Flink → Iceberg/Nessie → MinIO → Query Engines`

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

### Streaming Components

8. **Apache Kafka**
   - Distributed message streaming platform
   - High-throughput event ingestion
   - Pub-sub messaging for real-time data
   - Topic-based data organization

9. **Apache Flink**
   - Stream processing engine
   - Real-time ETL and transformations
   - Stateful stream processing
   - Exactly-once semantics
   - Direct integration with Iceberg

10. **Zookeeper**
    - Coordination service for Kafka
    - Manages Kafka cluster metadata
    - Leader election and configuration

### Supporting Components

- **Dashboard (`dashboard.py`)** - Streamlit web UI for interactive testing
- **Validation (`validation.py`)** - Health checks and connectivity tests
- **Test Utilities** - Connection testing and data verification scripts
- **Streaming Example (`examples/streaming_ingestion.py`)** - Kafka producer/consumer demo

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
- **Zookeeper (port 2181)** - Kafka coordination
- **Kafka (port 9092, 29092)** - Message streaming
- **Flink JobManager (port 8081)** - Stream processing UI
- **Flink TaskManager** - Stream processing workers

### 3. Wait for Services to Initialize

```bash
# Check service health
docker compose ps

# View logs
docker compose logs -f router
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
KAFKA_BOOTSTRAP_SERVERS=kafka:9092  # Kafka brokers
```

## 🌊 Streaming Data Ingestion

The platform supports real-time streaming data ingestion using **Kafka** and **Flink**, perfectly integrated with the **Iceberg-native** environment.

### Quick Start: Streaming Demo

```bash
# Install streaming dependencies
pip install -r examples/requirements.txt

# Run the complete streaming demo
python examples/streaming_ingestion.py
```

This demo:
1. ✅ Verifies Nessie and Kafka connectivity
2. ✅ Creates Iceberg table for streaming events
3. ✅ Produces sample events to Kafka
4. ✅ Consumes events and writes to Iceberg (simulating Flink)
5. ✅ Queries the streamed data via Trino

### Streaming Architecture Benefits

**Why Kafka + Flink + Iceberg + Nessie?**

- **Kafka**: High-throughput distributed streaming platform
  - Handles millions of events per second
  - Durable, fault-tolerant message storage
  - Decouples producers from consumers

- **Flink**: True streaming with exactly-once semantics
  - Real-time ETL and transformations
  - Stateful stream processing
  - Native Iceberg connector for atomic writes

- **Iceberg**: ACID transactions for streaming writes
  - Consistent reads during writes
  - Schema evolution without downtime
  - Time travel for historical analysis

- **Nessie**: Git-like versioning for data
  - Branching for testing stream processing jobs
  - Rollback capability for bad data
  - Audit trail for all data changes

### Use Cases

1. **Real-time Analytics**: User behavior tracking, clickstream analysis
2. **IoT Data Processing**: Sensor data ingestion and aggregation
3. **Financial Transactions**: Fraud detection, risk monitoring
4. **Log Aggregation**: Application logs, system metrics
5. **Change Data Capture (CDC)**: Database replication, event sourcing

### Access Streaming UIs

- **Flink Dashboard**: http://localhost:8081
- **Kafka Console**: Use CLI tools in the Kafka container
- **MinIO Console**: http://localhost:9001 (view data files)
- **Nessie API**: http://localhost:19120/api/v1 (catalog versioning)

For detailed streaming documentation, examples, and configuration, see **[STREAMING.md](STREAMING.md)**.

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
├── docker-compose.yml    # Service orchestration (batch + streaming)
├── Dockerfile            # Router container image
├── trino/
│   └── catalog/
│       └── iceberg.properties  # Trino Iceberg config
├── examples/
│   ├── streaming_ingestion.py  # Kafka/Flink streaming demo
│   └── requirements.txt        # Streaming dependencies
├── README.md             # This file
├── STREAMING.md          # Streaming architecture documentation
└── BENCHMARK.md          # Performance benchmarks
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

6. **Kafka connection issues**
   - Verify Kafka is running: `docker compose ps kafka`
   - Check logs: `docker compose logs kafka`
   - Test connectivity: `docker compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092`

7. **Flink job issues**
   - Access Flink UI: http://localhost:8081
   - Check logs: `docker compose logs flink-jobmanager`

## 🔒 Security Notes

- Default credentials are for development only
- Change all passwords in production
- Implement proper authentication/authorization
- Use secrets management for credentials
- Enable TLS/SSL for production deployments
- Secure Kafka with SASL/SSL for production
- Use IAM roles for S3 access in cloud deployments

## 📚 Additional Resources

### Core Technologies
- [DuckDB Documentation](https://duckdb.org/docs/)
- [Trino Documentation](https://trino.io/docs/current/)
- [ClickHouse Documentation](https://clickhouse.com/docs/)
- [Apache Iceberg](https://iceberg.apache.org/)
- [Project Nessie](https://projectnessie.org/)

### Streaming Technologies
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Apache Flink Documentation](https://nightlies.apache.org/flink/flink-docs-release-1.18/)
- [Flink + Iceberg Integration](https://iceberg.apache.org/docs/latest/flink/)
- [Kafka Streams](https://kafka.apache.org/documentation/streams/)

### Architecture Patterns
- [Streaming Data Pipelines](STREAMING.md)
- [Performance Benchmarks](BENCHMARK.md)
- [Lakehouse Architecture](https://www.databricks.com/glossary/data-lakehouse)

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
- Apache Kafka for message streaming
- Apache Flink for stream processing
