# 🌊 Streaming Data Architecture

## Overview

This document describes the streaming data ingestion architecture using **Kafka** (streaming), **Flink** (processing), **Iceberg** (tables), and **Nessie** (catalog). This architecture provides a robust, scalable solution for real-time data processing in an Iceberg-native environment.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Data Sources                                  │
│                 (Applications, APIs, IoT, etc.)                     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
                    ┌────────────────┐
                    │     Kafka      │  ← Message Streaming Platform
                    │   (Topics)     │     • High throughput
                    └────────┬───────┘     • Distributed
                             │             • Fault-tolerant
                             ▼
                    ┌────────────────┐
                    │     Flink      │  ← Stream Processing Engine
                    │  (JobManager)  │     • Stateful processing
                    │ (TaskManagers) │     • Exactly-once semantics
                    └────────┬───────┘     • Event time processing
                             │
                             ▼
                    ┌────────────────┐
                    │    Iceberg     │  ← Open Table Format
                    │   (via Nessie) │     • ACID transactions
                    │                │     • Schema evolution
                    └────────┬───────┘     • Time travel
                             │
                             ▼
                    ┌────────────────┐
                    │     MinIO      │  ← S3-Compatible Storage
                    │   (S3 Bucket)  │     • Object storage
                    └────────┬───────┘     • Data lake
                             │
                             ▼
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
        ┌──────────┐                 ┌──────────┐
        │  Trino   │                 │  DuckDB  │  ← Query Engines
        │          │                 │          │     • SQL analytics
        └──────────┘                 └──────────┘     • Ad-hoc queries
```

## 🎯 Key Components

### 1. Apache Kafka
**Role:** Message streaming platform

**Features:**
- High-throughput publish-subscribe messaging
- Distributed, partitioned, replicated commit log
- Horizontal scalability
- Fault tolerance with replication

**Use Cases:**
- Real-time event streaming
- Log aggregation
- Data integration
- Stream processing input

**Configuration:**
```yaml
kafka:
  bootstrap_servers: localhost:29092
  topics:
    - user_events
    - transaction_logs
    - sensor_data
```

### 2. Apache Flink
**Role:** Stream processing engine

**Features:**
- True streaming (not micro-batching)
- Exactly-once state consistency
- Event time processing with watermarks
- Stateful stream processing
- Rich APIs (DataStream, Table, SQL)

**Use Cases:**
- Real-time ETL
- Stream analytics
- Complex event processing
- Fraud detection
- Real-time recommendations

**Key Capabilities:**
```java
// Flink DataStream API example
DataStream<Event> events = env
    .addSource(new FlinkKafkaConsumer<>("user_events", ...))
    .keyBy(event -> event.getUserId())
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .aggregate(new EventAggregator());

// Write to Iceberg
FlinkSink.forRowData(events)
    .tableLoader(TableLoader.fromCatalog(...))
    .build();
```

### 3. Apache Iceberg
**Role:** Open table format for data lakes

**Features:**
- ACID transactions
- Schema evolution
- Hidden partitioning
- Time travel and rollback
- Partition evolution
- Snapshot isolation

**Benefits for Streaming:**
- Consistent reads during writes
- Atomic commits for micro-batches
- Efficient incremental updates
- Metadata-based operations

**Table Properties:**
```sql
CREATE TABLE iceberg.public.user_events (
    user_id BIGINT,
    event_time TIMESTAMP,
    event_type VARCHAR,
    properties MAP<VARCHAR, VARCHAR>
)
WITH (
    format = 'PARQUET',
    partitioning = ARRAY['day(event_time)']
);
```

### 4. Project Nessie
**Role:** Git-like catalog for Iceberg tables

**Features:**
- Branching and tagging for data
- Atomic multi-table commits
- Time travel across tables
- Audit trail
- Data versioning

**Benefits:**
- Safe CI/CD for data pipelines
- A/B testing on data
- Easy rollback
- Schema evolution tracking

**API Example:**
```python
# Create a branch for testing
nessie.create_branch("test-pipeline", from_ref="main")

# Write data to test branch
# ...test processing...

# Merge to main if tests pass
nessie.merge_branch("test-pipeline", into="main")
```

## 📊 Data Flow

### Streaming Ingestion Pipeline

1. **Data Production**
   ```python
   # Application produces events to Kafka
   producer.send('user_events', {
       'user_id': 123,
       'event_type': 'page_view',
       'timestamp': '2025-12-20T12:00:00Z',
       'page': '/products'
   })
   ```

2. **Stream Processing (Flink)**
   ```sql
   -- Flink SQL processes stream
   CREATE TABLE user_events_kafka (
       user_id BIGINT,
       event_type STRING,
       event_time TIMESTAMP(3),
       WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
   ) WITH (
       'connector' = 'kafka',
       'topic' = 'user_events',
       'properties.bootstrap.servers' = 'kafka:9092'
   );
   
   -- Aggregate and write to Iceberg
   INSERT INTO iceberg_catalog.db.user_activity
   SELECT 
       user_id,
       event_type,
       TUMBLE_END(event_time, INTERVAL '1' MINUTE) as window_end,
       COUNT(*) as event_count
   FROM user_events_kafka
   GROUP BY user_id, event_type, TUMBLE(event_time, INTERVAL '1' MINUTE);
   ```

3. **Storage (Iceberg + MinIO)**
   - Flink writes to Iceberg tables
   - Iceberg manages data files in MinIO (S3)
   - Nessie tracks metadata versions
   - ACID guarantees maintained

4. **Query (Trino/DuckDB)**
   ```sql
   -- Query real-time data via Query Router
   SELECT event_type, COUNT(*) as count
   FROM iceberg.public.user_events
   WHERE event_time > NOW() - INTERVAL '1' HOUR
   GROUP BY event_type;
   ```

## 🚀 Getting Started

### Prerequisites

```bash
# Ensure all services are running
docker compose up -d

# Verify services
docker compose ps
```

Expected services:
- ✅ Zookeeper (port 2181)
- ✅ Kafka (port 9092/29092)
- ✅ Flink JobManager (port 8081)
- ✅ Flink TaskManager
- ✅ MinIO (port 9000)
- ✅ Nessie (port 19120)
- ✅ Router (port 8000)

### Installation

```bash
# Install Python dependencies
pip install kafka-python requests

# Or using requirements file
pip install -r examples/requirements.txt
```

### Quick Start: Streaming Demo

```bash
# Run the complete streaming demo
python examples/streaming_ingestion.py

# Or run individual steps:

# 1. Setup Iceberg table
python examples/streaming_ingestion.py setup

# 2. Produce events to Kafka
python examples/streaming_ingestion.py produce 100

# 3. Consume events from Kafka
python examples/streaming_ingestion.py consume 10

# 4. Query streaming data
python examples/streaming_ingestion.py query
```

## 🧪 Example Use Cases

### Use Case 1: Real-Time User Analytics

**Scenario:** Track user behavior in real-time for personalization

```python
# Producer: Web application logs events
def log_user_event(user_id, page, action):
    producer.send('user_events', {
        'user_id': user_id,
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'page': page
    })

# Flink: Aggregate events in 5-minute windows
# SQL: Query aggregated data
SELECT 
    user_id,
    action,
    COUNT(*) as frequency,
    MAX(timestamp) as last_seen
FROM iceberg.public.user_events
WHERE timestamp > NOW() - INTERVAL '1' HOUR
GROUP BY user_id, action
ORDER BY frequency DESC;
```

### Use Case 2: IoT Sensor Data Processing

**Scenario:** Process millions of sensor readings per second

```python
# Producer: IoT devices send sensor data
def send_sensor_reading(device_id, reading):
    producer.send('sensor_data', {
        'device_id': device_id,
        'timestamp': datetime.utcnow().isoformat(),
        'temperature': reading['temp'],
        'humidity': reading['humidity'],
        'location': reading['location']
    })

# Flink: Detect anomalies and calculate moving averages
# Query: Analyze sensor trends
SELECT 
    device_id,
    AVG(temperature) as avg_temp,
    MAX(temperature) as max_temp,
    COUNT(*) as reading_count
FROM iceberg.public.sensor_readings
WHERE timestamp > NOW() - INTERVAL '15' MINUTE
GROUP BY device_id
HAVING MAX(temperature) > 80; -- Alert threshold
```

### Use Case 3: Financial Transaction Monitoring

**Scenario:** Real-time fraud detection on transactions

```python
# Producer: Payment system publishes transactions
def record_transaction(txn):
    producer.send('transactions', {
        'txn_id': txn['id'],
        'user_id': txn['user_id'],
        'amount': txn['amount'],
        'timestamp': txn['timestamp'],
        'merchant': txn['merchant'],
        'location': txn['location']
    })

# Flink: Pattern detection for fraud
# Query: Suspicious transaction analysis
SELECT 
    user_id,
    COUNT(*) as txn_count,
    SUM(amount) as total_amount,
    COUNT(DISTINCT merchant) as merchant_count
FROM iceberg.public.transactions
WHERE timestamp > NOW() - INTERVAL '5' MINUTE
GROUP BY user_id
HAVING COUNT(*) > 10 OR SUM(amount) > 10000;
```

## 🔧 Configuration

### Kafka Configuration

```yaml
# docker-compose.yml
kafka:
  image: confluentinc/cp-kafka:7.5.0
  environment:
    KAFKA_BROKER_ID: 1
    KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
    KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1
    KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
```

### Flink Configuration

```yaml
# flink-conf.yaml (custom config)
jobmanager.rpc.address: flink-jobmanager
taskmanager.numberOfTaskSlots: 4
parallelism.default: 2

# State backend (for fault tolerance)
state.backend: rocksdb
state.checkpoints.dir: s3://lake-data/flink-checkpoints
state.savepoints.dir: s3://lake-data/flink-savepoints

# Iceberg connector
execution.checkpointing.interval: 60s
execution.checkpointing.mode: EXACTLY_ONCE
```

### Iceberg + Nessie Configuration

```properties
# Flink Iceberg Catalog
catalog-impl=org.apache.iceberg.nessie.NessieCatalog
uri=http://nessie:19120/api/v1
ref=main
warehouse=s3://lake-data

# S3 Configuration
s3.endpoint=http://minio:9000
s3.access-key-id=admin
s3.secret-access-key=password
s3.path-style-access=true
```

## 📈 Performance Optimization

### Kafka Tuning

```properties
# Producer settings
acks=all                          # Wait for all replicas
compression.type=lz4              # Compress messages
batch.size=16384                  # Batch size in bytes
linger.ms=10                      # Wait time for batching

# Consumer settings
fetch.min.bytes=1024              # Minimum data per fetch
fetch.max.wait.ms=500             # Max wait time
max.poll.records=500              # Records per poll
```

### Flink Tuning

```yaml
# Parallelism
taskmanager.numberOfTaskSlots: 8
parallelism.default: 4

# Memory
taskmanager.memory.process.size: 4096m
taskmanager.memory.managed.fraction: 0.4

# Checkpointing
execution.checkpointing.interval: 60000
execution.checkpointing.min-pause: 30000
```

### Iceberg Tuning

```sql
-- Table properties
ALTER TABLE iceberg.public.user_events 
SET TBLPROPERTIES (
    'write.format.default' = 'parquet',
    'write.target-file-size-bytes' = '536870912', -- 512 MB
    'commit.manifest.min-count-to-merge' = '5',
    'commit.manifest-merge.enabled' = 'true'
);
```

## 🔍 Monitoring

### Kafka Monitoring

```bash
# Check topics
docker compose exec kafka kafka-topics --list --bootstrap-server localhost:9092

# Check consumer lag
docker compose exec kafka kafka-consumer-groups --bootstrap-server localhost:9092 --describe --group streaming-demo-consumer

# View messages
docker compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic user_events --from-beginning --max-messages 10
```

### Flink Monitoring

```bash
# Web UI
open http://localhost:8081

# Job status
curl http://localhost:8081/jobs

# Task metrics
curl http://localhost:8081/jobs/<job-id>/vertices/<vertex-id>/metrics
```

### Iceberg/Nessie Monitoring

```bash
# List branches
curl http://localhost:19120/api/v1/trees

# View commit log
curl http://localhost:19120/api/v1/trees/main/log

# Query table metadata via Trino
SELECT * FROM iceberg.public."user_events$snapshots";
```

## 🛠️ Troubleshooting

### Issue: Kafka connection refused

**Solution:**
```bash
# Check Kafka is running
docker compose ps kafka

# Check logs
docker compose logs kafka

# Test connectivity
docker compose exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092
```

### Issue: Flink job submission fails

**Solution:**
```bash
# Check Flink cluster
curl http://localhost:8081/overview

# View JobManager logs
docker compose logs flink-jobmanager

# Check TaskManager status
docker compose logs flink-taskmanager
```

### Issue: Iceberg writes failing

**Solution:**
```bash
# Verify Nessie is accessible
curl http://localhost:19120/api/v1/config

# Check MinIO connectivity
curl http://localhost:9000/minio/health/live

# Verify Iceberg catalog in Trino
docker compose exec trino trino --execute "SHOW SCHEMAS FROM iceberg;"
```

## 🔐 Security Considerations

### Production Recommendations

1. **Kafka Security**
   - Enable SSL/TLS encryption
   - Configure SASL authentication
   - Use ACLs for topic access control

2. **Flink Security**
   - Enable Kerberos authentication
   - Encrypt state backends
   - Secure REST API endpoints

3. **Iceberg/Nessie**
   - Use IAM roles for S3 access
   - Implement catalog-level authentication
   - Enable audit logging

4. **Network Security**
   - Use private networks for inter-service communication
   - Implement firewall rules
   - Enable VPC peering for cloud deployments

## 📚 Additional Resources

### Documentation
- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- [Apache Flink Documentation](https://nightlies.apache.org/flink/flink-docs-release-1.18/)
- [Apache Iceberg Documentation](https://iceberg.apache.org/docs/latest/)
- [Project Nessie Documentation](https://projectnessie.org/docs/)

### Tutorials
- [Flink + Iceberg Integration](https://iceberg.apache.org/docs/latest/flink/)
- [Kafka Streams Tutorial](https://kafka.apache.org/documentation/streams/)
- [Nessie Getting Started](https://projectnessie.org/try/)

### Community
- [Apache Iceberg Slack](https://join.slack.com/t/apache-iceberg/shared_invite/)
- [Flink User Mailing List](https://flink.apache.org/community.html)
- [Nessie GitHub](https://github.com/projectnessie/nessie)

## 🎓 Best Practices

1. **Schema Design**
   - Use Iceberg's schema evolution for backwards compatibility
   - Partition by time for time-series data
   - Use appropriate data types

2. **Stream Processing**
   - Implement watermarks for late data handling
   - Use checkpointing for fault tolerance
   - Design idempotent operations

3. **Data Versioning**
   - Use Nessie branches for development/testing
   - Tag important data snapshots
   - Implement retention policies

4. **Query Optimization**
   - Use partition pruning in queries
   - Leverage Iceberg's hidden partitioning
   - Maintain table statistics

5. **Operations**
   - Monitor consumer lag
   - Set up alerting for job failures
   - Regularly compact Iceberg tables
   - Clean up old snapshots

---

*Last Updated: 2025-12-20*
