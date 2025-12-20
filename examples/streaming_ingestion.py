"""
Streaming Ingestion Example: Kafka → Flink → Iceberg (via Nessie)

This script demonstrates a complete streaming data pipeline:
1. Producer: Generates sample user events and publishes to Kafka
2. Consumer: Flink processes the stream and writes to Iceberg tables via Nessie catalog
3. Query: Router can query the streamed data via Trino/DuckDB

Architecture:
  Kafka (Stream) → Flink (Processing) → Iceberg/Nessie (Storage) → Query Engines (Analytics)
"""

import json
import time
import os
import random
from datetime import datetime, timezone
from typing import Dict, Any

try:
    from kafka import KafkaProducer, KafkaConsumer
    KAFKA_AVAILABLE = True
except ImportError:
    KAFKA_AVAILABLE = False
    print("⚠️  kafka-python not installed. Install with: pip install kafka-python")

import requests

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
KAFKA_TOPIC = "user_events"
ROUTER_URL = os.getenv("ROUTER_URL", "http://localhost:8000")
NESSIE_URL = os.getenv("NESSIE_URL", "http://localhost:19120/api/v1")


def generate_sample_event(user_id: int) -> Dict[str, Any]:
    """Generate a sample user event."""
    events = [
        {"action": "login", "page": "/home"},
        {"action": "view", "page": "/products"},
        {"action": "click", "page": "/product/123"},
        {"action": "add_to_cart", "page": "/cart"},
        {"action": "checkout", "page": "/checkout"},
    ]
    
    event = random.choice(events)
    
    return {
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": event["action"],
        "page": event["page"],
        "session_id": f"session_{user_id % 10}",
    }


class StreamingProducer:
    """Kafka producer for streaming events."""
    
    def __init__(self):
        if not KAFKA_AVAILABLE:
            raise ImportError("kafka-python is required")
        
        self.producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: str(k).encode('utf-8')
        )
        print(f"✅ Kafka Producer connected to {KAFKA_BOOTSTRAP_SERVERS}")
    
    def send_event(self, event: Dict[str, Any]):
        """Send an event to Kafka."""
        user_id = event["user_id"]
        future = self.producer.send(KAFKA_TOPIC, key=user_id, value=event)
        
        try:
            record_metadata = future.get(timeout=10)
            print(f"📤 Sent: {event['action']} for user {user_id} to partition {record_metadata.partition}")
            return True
        except Exception as e:
            print(f"❌ Failed to send event: {e}")
            return False
    
    def produce_stream(self, num_events: int = 100, delay: float = 0.5):
        """Produce a stream of events."""
        print(f"\n🚀 Starting to produce {num_events} events to Kafka topic '{KAFKA_TOPIC}'...")
        
        for i in range(num_events):
            user_id = (i % 20) + 1  # Cycle through 20 users
            event = generate_sample_event(user_id)
            self.send_event(event)
            time.sleep(delay)
        
        print(f"\n✅ Produced {num_events} events successfully!")
        self.producer.close()


class StreamingConsumer:
    """Simple Kafka consumer for demonstration (in production, use Flink)."""
    
    def __init__(self):
        if not KAFKA_AVAILABLE:
            raise ImportError("kafka-python is required")
        
        self.consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='streaming-demo-consumer',
            value_deserializer=lambda v: json.loads(v.decode('utf-8'))
        )
        print(f"✅ Kafka Consumer connected to {KAFKA_BOOTSTRAP_SERVERS}")
    
    def consume_and_display(self, max_messages: int = 10):
        """Consume and display messages."""
        print(f"\n👂 Consuming messages from topic '{KAFKA_TOPIC}'...")
        count = 0
        
        for message in self.consumer:
            event = message.value
            print(f"📥 Received: user_id={event['user_id']}, action={event['action']}, page={event['page']}")
            count += 1
            
            if count >= max_messages:
                break
        
        print(f"\n✅ Consumed {count} messages")
        self.consumer.close()


class IcebergWriter:
    """Write streaming data to Iceberg tables via Trino."""
    
    def __init__(self):
        print(f"✅ Iceberg Writer initialized (Router: {ROUTER_URL})")
    
    def create_streaming_table(self):
        """Create Iceberg table for streaming events."""
        sql = """
        CREATE TABLE IF NOT EXISTS iceberg.public.user_events (
            user_id INTEGER,
            timestamp VARCHAR,
            action VARCHAR,
            page VARCHAR,
            session_id VARCHAR
        )
        """
        
        try:
            response = requests.post(
                f"{ROUTER_URL}/query",
                json={"sql": sql, "force_engine": "trino"}
            )
            result = response.json()
            
            if "error" in result:
                print(f"⚠️  Table creation warning: {result['error']}")
            else:
                print("✅ Iceberg table 'user_events' created/verified")
            
            return True
        except Exception as e:
            print(f"❌ Failed to create table: {e}")
            return False
    
    def batch_insert_events(self, events: list):
        """Insert a batch of events into Iceberg table.
        
        Note: This example uses SQL string construction with escaping because it interfaces
        with a REST API that accepts SQL strings. In production, consider:
        1. Using the native Iceberg writer API for direct writes
        2. Using Flink's Iceberg connector for streaming writes
        3. Validating/sanitizing input data before insertion
        4. Implementing rate limiting and input validation at the API level
        
        For this demo, we:
        - Validate user_id as integer
        - Escape single quotes using SQL standard (doubling them)
        - Control the input data source (generated events only)
        """
        if not events:
            return
        
        # Build VALUES clause with proper escaping and validation
        values = []
        for event in events:
            # Validate and escape values to prevent SQL injection
            user_id = int(event['user_id'])  # Ensure integer (raises ValueError if invalid)
            
            # Escape single quotes by doubling them (SQL standard)
            # This prevents SQL injection from malicious input
            timestamp = str(event['timestamp']).replace("'", "''")
            action = str(event['action']).replace("'", "''")
            page = str(event['page']).replace("'", "''")
            session_id = str(event['session_id']).replace("'", "''")
            
            values.append(
                f"({user_id}, '{timestamp}', '{action}', '{page}', '{session_id}')"
            )
        
        sql = f"INSERT INTO iceberg.public.user_events VALUES {', '.join(values)}"
        
        try:
            response = requests.post(
                f"{ROUTER_URL}/query",
                json={"sql": sql, "force_engine": "trino"}
            )
            result = response.json()
            
            if "error" in result:
                print(f"❌ Insert failed: {result['error']}")
            else:
                print(f"✅ Inserted {len(events)} events into Iceberg table")
            
            return True
        except Exception as e:
            print(f"❌ Failed to insert events: {e}")
            return False


def verify_nessie_connection():
    """Verify Nessie catalog is accessible."""
    try:
        response = requests.get(f"{NESSIE_URL}/config", timeout=5)
        if response.status_code == 200:
            print("✅ Nessie catalog is accessible")
            return True
        else:
            print(f"⚠️  Nessie returned status code: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Nessie is not accessible: {e}")
        return False


def query_streaming_data():
    """Query the streaming data from Iceberg table."""
    print("\n📊 Querying streaming data from Iceberg table...")
    
    queries = [
        ("Total events", "SELECT COUNT(*) as total_events FROM iceberg.public.user_events"),
        ("Events by action", "SELECT action, COUNT(*) as count FROM iceberg.public.user_events GROUP BY action"),
        ("Recent events", "SELECT * FROM iceberg.public.user_events LIMIT 5"),
    ]
    
    for name, sql in queries:
        print(f"\n🔍 {name}:")
        try:
            response = requests.post(
                f"{ROUTER_URL}/query",
                json={"sql": sql, "force_engine": "trino"}
            )
            result = response.json()
            
            if "error" in result:
                print(f"  ❌ Query failed: {result['error']}")
            else:
                print(f"  ✅ Results: {result.get('data', [])}")
        except Exception as e:
            print(f"  ❌ Query error: {e}")


def demo_streaming_pipeline():
    """Run a complete streaming pipeline demonstration."""
    print("=" * 80)
    print("🌊 STREAMING INGESTION DEMO: Kafka → Flink → Iceberg (Nessie)")
    print("=" * 80)
    
    # Step 1: Verify prerequisites
    print("\n1️⃣  Verifying prerequisites...")
    if not KAFKA_AVAILABLE:
        print("❌ kafka-python not available. Please install: pip install kafka-python")
        return
    
    verify_nessie_connection()
    
    # Step 2: Create Iceberg table
    print("\n2️⃣  Setting up Iceberg table...")
    writer = IcebergWriter()
    writer.create_streaming_table()
    
    # Step 3: Produce events to Kafka
    print("\n3️⃣  Producing events to Kafka...")
    try:
        producer = StreamingProducer()
        producer.produce_stream(num_events=20, delay=0.2)
    except Exception as e:
        print(f"❌ Producer failed: {e}")
        print("Note: Make sure Kafka is running (docker compose up kafka)")
        return
    
    # Step 4: Simulate Flink processing by consuming and writing to Iceberg
    print("\n4️⃣  Simulating Flink stream processing...")
    print("   (In production, Flink would consume from Kafka and write to Iceberg)")
    
    try:
        # Collect some events
        consumer = KafkaConsumer(
            KAFKA_TOPIC,
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            auto_offset_reset='earliest',
            enable_auto_commit=True,
            group_id='iceberg-writer',
            value_deserializer=lambda v: json.loads(v.decode('utf-8')),
            consumer_timeout_ms=5000  # Wait 5 seconds for messages
        )
        
        events_batch = []
        for message in consumer:
            events_batch.append(message.value)
            if len(events_batch) >= 20:
                break
        
        consumer.close()
        
        if events_batch:
            print(f"   📦 Collected {len(events_batch)} events from Kafka")
            writer.batch_insert_events(events_batch)
        else:
            print("   ⚠️  No events collected from Kafka")
    
    except Exception as e:
        print(f"❌ Consumer/Writer failed: {e}")
    
    # Step 5: Query the data
    print("\n5️⃣  Querying streamed data from Iceberg...")
    time.sleep(2)  # Give Iceberg a moment to commit
    query_streaming_data()
    
    print("\n" + "=" * 80)
    print("✅ STREAMING PIPELINE DEMO COMPLETE!")
    print("=" * 80)
    print("\nKey Components:")
    print("  • Kafka: Message streaming platform")
    print("  • Flink: Stream processing engine (simulated here)")
    print("  • Iceberg: Table format for data lake")
    print("  • Nessie: Git-like catalog with versioning")
    print("  • Trino/DuckDB: Query engines for analytics")
    print("\nNext Steps:")
    print("  • Deploy actual Flink job for continuous processing")
    print("  • Scale Kafka with more partitions")
    print("  • Enable Iceberg time travel for historical queries")
    print("  • Add data quality checks in Flink")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "produce":
            try:
                num_events = int(sys.argv[2]) if len(sys.argv) > 2 else 100
            except ValueError as e:
                provided_value = sys.argv[2] if len(sys.argv) > 2 else "unknown"
                print(f"❌ Error: Number of events must be an integer, got '{provided_value}'")
                print("Usage: python streaming_ingestion.py produce [num_events]")
                print("Example: python streaming_ingestion.py produce 100")
                sys.exit(1)
            
            producer = StreamingProducer()
            producer.produce_stream(num_events=num_events)
        
        elif command == "consume":
            try:
                max_messages = int(sys.argv[2]) if len(sys.argv) > 2 else 10
            except ValueError as e:
                provided_value = sys.argv[2] if len(sys.argv) > 2 else "unknown"
                print(f"❌ Error: Max messages must be an integer, got '{provided_value}'")
                print("Usage: python streaming_ingestion.py consume [max_messages]")
                print("Example: python streaming_ingestion.py consume 10")
                sys.exit(1)
            
            consumer = StreamingConsumer()
            consumer.consume_and_display(max_messages=max_messages)
        
        elif command == "query":
            query_streaming_data()
        
        elif command == "setup":
            writer = IcebergWriter()
            writer.create_streaming_table()
        
        elif command == "demo":
            # Explicitly handle 'demo' command
            demo_streaming_pipeline()
        
        else:
            print(f"❌ Unknown command: {command}")
            print("Usage: python streaming_ingestion.py [produce|consume|query|setup|demo]")
            print("\nCommands:")
            print("  produce [N]  - Produce N events to Kafka (default: 100)")
            print("  consume [N]  - Consume N messages from Kafka (default: 10)")
            print("  query        - Query streaming data from Iceberg")
            print("  setup        - Create Iceberg table for streaming events")
            print("  demo         - Run complete streaming pipeline demo (default)")
            sys.exit(1)
    
    else:
        # Run full demo when no arguments provided
        demo_streaming_pipeline()
