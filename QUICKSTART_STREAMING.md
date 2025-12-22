# Quick Start Guide: Streaming Ingestion

This guide will help you get started with the streaming ingestion feature in under 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.9+ installed
- At least 8GB RAM available

## Step 1: Start All Services

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd query-router

# Start all services including streaming components
docker compose up -d

# Verify all services are running
docker compose ps
```

Expected services:
- ✅ PostgreSQL (port 5432)
- ✅ ClickHouse (port 8123)
- ✅ Trino (port 8080)
- ✅ MinIO (port 9000, 9001)
- ✅ Nessie (port 19120)
- ✅ Router (port 8000)
- ✅ **Zookeeper (port 2181)**
- ✅ **Kafka (port 9092, 29092)**
- ✅ **Flink JobManager (port 8081)**
- ✅ **Flink TaskManager**

## Step 2: Install Python Dependencies

```bash
# Install streaming example dependencies
pip install -r examples/requirements.txt
```

This installs:
- `kafka-python` - Kafka client for Python
- `requests` - HTTP library (likely already installed)

## Step 3: Run the Streaming Demo

```bash
# Run the complete streaming pipeline demo
python examples/streaming_ingestion.py
```

This will:
1. ✅ Verify Nessie and Kafka connectivity
2. ✅ Create an Iceberg table for streaming events
3. ✅ Produce 20 sample events to Kafka
4. ✅ Consume events from Kafka (simulating Flink processing)
5. ✅ Write events to Iceberg table
6. ✅ Query the streamed data via Trino

## Step 4: Explore the Results

### View Flink Dashboard
```bash
# Open Flink web UI
open http://localhost:8081
```
(or navigate to http://localhost:8081 in your browser)

### Query Streaming Data
```bash
# Query via Python script
python examples/streaming_ingestion.py query

# Or query directly via the router API
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM iceberg.public.user_events LIMIT 10", "force_engine": "trino"}'
```

### View Data in MinIO
```bash
# Open MinIO console
open http://localhost:9001
```
Login with: `admin` / `password`

Navigate to the `lake-data` bucket to see the Iceberg data files.

## Individual Commands

Once you've run the full demo, you can use individual commands:

```bash
# Create Iceberg table
python examples/streaming_ingestion.py setup

# Produce events to Kafka
python examples/streaming_ingestion.py produce 100

# Consume events from Kafka
python examples/streaming_ingestion.py consume 10

# Query streaming data
python examples/streaming_ingestion.py query

# Run full demo again
python examples/streaming_ingestion.py demo
```

## Next Steps

1. **Read the comprehensive guide**: Check out [STREAMING.md](STREAMING.md) for detailed architecture, use cases, and best practices

2. **Modify the example**: Edit `examples/streaming_ingestion.py` to:
   - Change event schema
   - Add custom transformations
   - Implement different aggregations

3. **Deploy Flink jobs**: Write actual Flink applications for:
   - Real-time ETL
   - Stream analytics
   - Complex event processing

4. **Scale the pipeline**:
   - Add more Kafka partitions
   - Increase Flink parallelism
   - Configure checkpointing for fault tolerance

5. **Production deployment**: See [STREAMING.md](STREAMING.md) for:
   - Security configurations
   - Performance tuning
   - Monitoring setup
   - High availability

## Troubleshooting

### Kafka not starting
```bash
# Check logs
docker compose logs kafka

# Restart services
docker compose restart kafka zookeeper
```

### Python dependencies not installing
```bash
# Use a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r examples/requirements.txt
```

### Services taking too long to start
```bash
# Wait 60 seconds for all services to initialize
sleep 60

# Check service health
docker compose ps
```

### Connection errors
```bash
# Ensure all services are healthy
docker compose ps

# Run validation
python validation.py
```

## Getting Help

- **Documentation**: See [STREAMING.md](STREAMING.md) for comprehensive guide
- **Architecture**: See [README.md](README.md) for overall architecture
- **Benchmarks**: See [BENCHMARK.md](BENCHMARK.md) for performance testing
- **Issues**: Check existing issues or create a new one on GitHub

## Example Output

When you run `python examples/streaming_ingestion.py`, you should see:

```
================================================================================
🌊 STREAMING INGESTION DEMO: Kafka → Flink → Iceberg (Nessie)
================================================================================

1️⃣  Verifying prerequisites...
✅ Nessie catalog is accessible

2️⃣  Setting up Iceberg table...
✅ Iceberg table 'user_events' created/verified

3️⃣  Producing events to Kafka...
📤 Sent: login for user 1 to partition 0
📤 Sent: view for user 2 to partition 0
...
✅ Produced 20 events successfully!

4️⃣  Simulating Flink stream processing...
📦 Collected 20 events from Kafka
✅ Inserted 20 events into Iceberg table

5️⃣  Querying streamed data from Iceberg...
✅ Results: [{'total_events': 20}]

================================================================================
✅ STREAMING PIPELINE DEMO COMPLETE!
================================================================================
```

## Clean Up

To stop all services:

```bash
# Stop all containers
docker compose down

# Stop and remove volumes (WARNING: deletes all data)
docker compose down -v
```

---

**Ready to build real-time data pipelines?** Start with this guide, then dive into [STREAMING.md](STREAMING.md) for advanced topics!
