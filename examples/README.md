# Examples

This directory contains example scripts demonstrating various features of the Query Router.

## Streaming Ingestion Example

**File**: `streaming_ingestion.py`

A complete demonstration of streaming data ingestion using Kafka, Flink, Iceberg, and Nessie.

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure all services are running
docker compose up -d
```

### Usage

**Run complete demo:**
```bash
python streaming_ingestion.py
```

**Individual commands:**

```bash
# Create Iceberg table
python streaming_ingestion.py setup

# Produce events to Kafka
python streaming_ingestion.py produce 100

# Consume events from Kafka
python streaming_ingestion.py consume 10

# Query streaming data
python streaming_ingestion.py query
```

### What it demonstrates

1. **Kafka Producer**: Generates sample user events and publishes to Kafka topics
2. **Kafka Consumer**: Consumes events from Kafka (simulates Flink processing)
3. **Iceberg Writer**: Writes streaming data to Iceberg tables via Trino
4. **Query Layer**: Queries the streamed data using the Query Router

### Architecture Flow

```
Events → Kafka Topic → Consumer (Flink simulation) → Iceberg/Nessie → MinIO → Query Engines
```

For more details, see [STREAMING.md](../STREAMING.md) in the root directory.
