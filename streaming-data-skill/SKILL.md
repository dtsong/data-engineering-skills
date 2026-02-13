---
name: streaming-data-skill
description: "Use when building real-time or near-real-time data pipelines — Kafka, Flink, Spark Streaming, Snowpipe, BigQuery streaming, materialized views, or choosing between batch and streaming"
license: Apache-2.0
metadata:
  author: Daniel Song
  version: 1.0.0
---

# Streaming Data Skill for Claude

This skill provides expert guidance for building real-time and near-real-time data pipelines. Use it when you need to process continuous data streams, implement event-driven architectures, or choose between batch and streaming approaches for your data infrastructure.

## When to Use This Skill

Activate this skill when:

- Building or troubleshooting Kafka pipelines (producers, consumers, Kafka Connect)
- Implementing stream processing with Apache Flink, Spark Streaming, or Kafka Streams
- Designing event-driven architectures or real-time analytics platforms
- Configuring warehouse streaming ingestion (Snowpipe, BigQuery Storage Write API)
- Creating materialized views or dynamic tables for real-time aggregations
- Evaluating latency requirements and choosing between batch vs streaming
- Handling schema evolution in streaming data systems
- Processing time-series data, IoT events, or clickstream analytics
- Implementing exactly-once semantics or idempotent processing
- Debugging consumer lag, backpressure, or checkpoint failures

Don't use this skill for:

- Basic batch ETL workflows (use `dbt-skill` or core data engineering patterns)
- Static data modeling or dimensional design (use data modeling tools)
- SQL optimization for analytical queries (use warehouse-specific optimization guides)
- Data quality checks on static datasets (use dbt tests or Great Expectations)
- One-time data migrations or backfills (use batch processing patterns)

## Core Principles

### Event Time vs Processing Time

Always design for event time when building streaming pipelines. Event time reflects when an event actually occurred, while processing time reflects when your system processed it. Use event time for accurate windowing and aggregations, especially when dealing with late-arriving data or system delays.

```sql
-- Flink SQL: Always specify event time
CREATE TABLE events (
  user_id STRING,
  event_type STRING,
  event_timestamp TIMESTAMP(3),
  WATERMARK FOR event_timestamp AS event_timestamp - INTERVAL '5' SECOND
) WITH (...);
```

### Exactly-Once vs At-Least-Once

Understand delivery guarantees and their tradeoffs. Exactly-once semantics prevent duplicate processing but add complexity and latency. At-least-once is simpler and faster but requires idempotent consumers. Choose based on your use case: financial transactions need exactly-once, while analytics dashboards often tolerate at-least-once with idempotent writes.

### Backpressure Awareness

Detect and handle slow consumers before they crash your pipeline. Monitor consumer lag, implement rate limiting, and design systems to gracefully degrade under load. Use buffering strategies like Kafka's buffering or Flink's backpressure mechanisms to smooth traffic spikes.

### Watermarks and Late Data

Configure watermarks to balance latency and completeness. Watermarks tell your system when to finalize windows and emit results. Set watermark delays based on expected lateness: shorter delays reduce latency but may drop late data, longer delays increase completeness but delay results. Always handle late arrivals with side outputs or allowed lateness windows.

### Schema Evolution

Plan for schema changes from day one. Use schema registries (Confluent Schema Registry, AWS Glue Schema Registry) to enforce compatibility rules. Design consumers to handle missing fields gracefully. Test backward and forward compatibility before deploying schema changes to production.

### Idempotent Consumers

Design consumers to be safe for replay. Every streaming system will replay data at some point (failures, rebalancing, backfills). Store offsets transactionally with your output, use unique keys for upserts, and avoid operations that accumulate state incorrectly on replay.

## Architecture Decision Matrix

| Architecture | Latency | Complexity | Cost | Best For |
|-------------|---------|------------|------|----------|
| Traditional Batch | Hours to days | Low | Low | Historical reporting, data lakes, large aggregations |
| Micro-Batch (Spark Streaming) | Seconds to minutes | Medium | Medium | Near-real-time analytics, unified batch/stream code |
| True Streaming (Flink, Kafka Streams) | Milliseconds to seconds | High | Medium-High | Real-time dashboards, fraud detection, alerting |
| Lambda Architecture | Mixed | Very High | High | Transitional hybrid, accuracy + speed layers |
| Kappa Architecture | Milliseconds to seconds | Medium | Medium | Stream-first, immutable event log, reprocessing |
| Warehouse-Native Streaming | Seconds to minutes | Low | Medium | SQL-first teams, simple ingestion, BI integration |

**Lambda Architecture**: Run both batch and streaming pipelines, merge results. Use when migrating from batch to streaming or when streaming SLAs are too expensive for all data.

**Kappa Architecture**: Stream-only, reprocess by replaying Kafka. Use when all data can be modeled as streams and you want to avoid maintaining two codebases.

**Warehouse-Native Streaming**: Snowpipe, BigQuery streaming, Databricks Delta Live Tables. Use when your team primarily works in SQL and needs simple real-time ingestion without managing infrastructure.

## Stream Processing Frameworks

| Framework | Latency | State Mgmt | SQL Support | Cloud Managed | Best For |
|-----------|---------|------------|-------------|---------------|----------|
| Kafka Streams | Low (ms) | RocksDB embedded | No (KSQL separate) | No | Microservices, lightweight, JVM apps |
| Apache Flink | Very Low (ms) | RocksDB, heap | Yes (Flink SQL) | Yes (AWS KDA, Confluent) | Complex event processing, large state |
| Spark Structured Streaming | Medium (sec) | Memory, checkpoint | Yes (Spark SQL) | Yes (Databricks, EMR) | Unified batch/stream, existing Spark |
| ksqlDB | Low (ms) | RocksDB | Yes (streaming SQL) | Yes (Confluent Cloud) | SQL-first, simple transforms |
| Apache Beam/Dataflow | Medium (sec) | Managed | Limited | Yes (GCP Dataflow) | Multi-cloud portability, GCP native |
| Materialize | Low (ms) | Postgres-like | Yes (Postgres SQL) | Yes (Materialize Cloud) | Incremental views, SQL analysts |

### Kafka Streams Example (Python with Faust)

```python
import faust

app = faust.App('order_processor', broker='kafka://localhost:9092')

class Order(faust.Record):
    order_id: str
    user_id: str
    amount: float
    timestamp: int

orders_topic = app.topic('orders', value_type=Order)

@app.agent(orders_topic)
async def process_order(orders):
    async for order in orders:
        if order.amount > 1000:
            print(f'High value order: {order.order_id} - ${order.amount}')
            # Send to high-value topic or trigger alert
```

### Flink SQL Example

```sql
-- Create source table
CREATE TABLE orders (
    order_id STRING,
    user_id STRING,
    amount DECIMAL(10, 2),
    order_time TIMESTAMP(3),
    WATERMARK FOR order_time AS order_time - INTERVAL '10' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'orders',
    'properties.bootstrap.servers' = 'localhost:9092',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'json'
);

-- Windowed aggregation
SELECT
    user_id,
    TUMBLE_START(order_time, INTERVAL '1' HOUR) as window_start,
    COUNT(*) as order_count,
    SUM(amount) as total_amount
FROM orders
GROUP BY user_id, TUMBLE(order_time, INTERVAL '1' HOUR);
```

### Spark Structured Streaming Example

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import window, col, sum, count

spark = SparkSession.builder.appName("OrderProcessor").getOrCreate()

# Read from Kafka
orders = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "orders") \
    .load() \
    .selectExpr("CAST(value AS STRING)")

# Parse JSON and aggregate
from pyspark.sql.functions import from_json
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

schema = StructType([
    StructField("order_id", StringType()),
    StructField("user_id", StringType()),
    StructField("amount", DoubleType()),
    StructField("order_time", TimestampType())
])

parsed_orders = orders.select(from_json(col("value"), schema).alias("data")).select("data.*")

windowed_agg = parsed_orders \
    .withWatermark("order_time", "10 minutes") \
    .groupBy(
        col("user_id"),
        window(col("order_time"), "1 hour")
    ) \
    .agg(
        count("order_id").alias("order_count"),
        sum("amount").alias("total_amount")
    )

query = windowed_agg \
    .writeStream \
    .outputMode("update") \
    .format("console") \
    .start()

query.awaitTermination()
```

## Windowing Patterns

### Tumbling Windows (Fixed, Non-Overlapping)

```
Time:    0    5    10   15   20   25   30
         |----|----|----|----|----|----|
Window:  [W1 ][W2 ][W3 ][W4 ][W5 ][W6 ]
```

Fixed-size windows with no overlap. Each event belongs to exactly one window. Use for hourly aggregations, daily summaries, or regular reporting intervals.

### Sliding Windows (Fixed, Overlapping)

```
Time:    0    5    10   15   20   25   30
         |----|----|----|----|----|----|
Window:  [----W1----]
              [----W2----]
                   [----W3----]
                        [----W4----]
```

Fixed-size windows that slide at regular intervals. Events can belong to multiple windows. Use for moving averages, trend detection, or smoothing metrics over time.

### Session Windows (Gap-Based)

```
Time:    0    5    10   15   20   25   30
Events:  *  * *         *         * **
         |--S1--|       |S2|      |-S3-|
         (gap=3) (gap>3)(gap<3)  (gap=3)
```

Variable-size windows based on inactivity gaps. Window closes after a period of inactivity. Use for user sessions, conversation threads, or activity bursts.

### Global Windows (Custom Triggers)

All events in a single window, controlled by custom triggers. Use when you need complete control over when to emit results, such as accumulating until a specific condition is met.

### Flink SQL Windowed Aggregation

```sql
-- Tumbling window: 5-minute fixed intervals
SELECT
    user_id,
    TUMBLE_START(event_time, INTERVAL '5' MINUTE) as window_start,
    TUMBLE_END(event_time, INTERVAL '5' MINUTE) as window_end,
    COUNT(*) as event_count
FROM events
GROUP BY user_id, TUMBLE(event_time, INTERVAL '5' MINUTE);

-- Sliding window: 10-minute window, sliding every 5 minutes
SELECT
    user_id,
    HOP_START(event_time, INTERVAL '5' MINUTE, INTERVAL '10' MINUTE) as window_start,
    HOP_END(event_time, INTERVAL '5' MINUTE, INTERVAL '10' MINUTE) as window_end,
    AVG(value) as avg_value
FROM events
GROUP BY user_id, HOP(event_time, INTERVAL '5' MINUTE, INTERVAL '10' MINUTE);

-- Session window: 30-minute inactivity gap
SELECT
    user_id,
    SESSION_START(event_time, INTERVAL '30' MINUTE) as session_start,
    SESSION_END(event_time, INTERVAL '30' MINUTE) as session_end,
    COUNT(*) as events_in_session
FROM events
GROUP BY user_id, SESSION(event_time, INTERVAL '30' MINUTE);
```

## State Management & Checkpointing

Stream processing frameworks maintain state (running aggregations, windows, joins) that must survive failures. Configure state backends and checkpointing to balance performance and fault tolerance.

**State Backends**:
- **RocksDB**: Disk-based, supports large state (GB to TB), slower than memory
- **In-Memory**: Fast but limited by heap size, loses state on crash without checkpoints
- **Managed** (cloud): Fully managed by platform (AWS KDA, Confluent Cloud)

**Checkpointing**: Periodic snapshots of state and stream positions. Configure checkpoint intervals based on recovery time objectives (RTO). Shorter intervals (30s-1min) enable faster recovery but add overhead. Longer intervals (5-10min) reduce overhead but increase recovery time.

**Savepoints**: Manual checkpoints for planned downtime (upgrades, config changes). Always take a savepoint before deploying changes to production.

**State TTL**: Expire old state to prevent unbounded growth. Set TTL based on business logic (user sessions expire after 1 hour, daily aggregations expire after 7 days).

```python
# Flink Python: Configure checkpointing
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.checkpointing_mode import CheckpointingMode

env = StreamExecutionEnvironment.get_execution_environment()

# Checkpoint every 60 seconds
env.enable_checkpointing(60000)

# Exactly-once semantics
env.get_checkpoint_config().set_checkpointing_mode(CheckpointingMode.EXACTLY_ONCE)

# Keep 3 checkpoints
env.get_checkpoint_config().set_max_concurrent_checkpoints(1)
env.get_checkpoint_config().set_min_pause_between_checkpoints(500)
```

## Schema Evolution in Streams

Use schema registries to manage schema changes safely across producers and consumers. Test compatibility before deploying changes.

### Avro with Schema Registry

```python
from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer

# Define schema
value_schema_str = """
{
   "namespace": "com.example",
   "name": "Order",
   "type": "record",
   "fields" : [
     {"name": "order_id", "type": "string"},
     {"name": "user_id", "type": "string"},
     {"name": "amount", "type": "double"},
     {"name": "timestamp", "type": "long"}
   ]
}
"""

value_schema = avro.loads(value_schema_str)

avroProducer = AvroProducer({
    'bootstrap.servers': 'localhost:9092',
    'schema.registry.url': 'http://localhost:8081'
}, default_value_schema=value_schema)

value = {
    "order_id": "order-123",
    "user_id": "user-456",
    "amount": 99.99,
    "timestamp": 1640000000000
}

avroProducer.produce(topic='orders', value=value)
avroProducer.flush()
```

### Schema Compatibility Modes

| Mode | Allowed Changes | Use When |
|------|----------------|----------|
| BACKWARD | Delete fields, add optional fields | Consumers upgrade before producers (most common) |
| FORWARD | Add fields, delete optional fields | Producers upgrade before consumers |
| FULL | Backward + Forward compatible changes only | Upgrade order is unpredictable |
| NONE | No compatibility checks | Development only, never production |

**Best Practice**: Use BACKWARD compatibility for most production systems. Add new fields with defaults, never remove required fields without a multi-phase migration.

[Deep dive →](references/kafka-deep-dive.md#schema-registry)

## Warehouse Streaming Ingestion

Modern data warehouses offer native streaming ingestion APIs that bypass traditional batch loading. Use these for low-latency ingestion without managing separate stream processing infrastructure.

### Snowpipe Streaming (Snowflake Ingest SDK)

Snowpipe Streaming enables sub-second latency ingestion using the Snowflake Ingest SDK. Unlike Snowpipe (S3-based), Snowpipe Streaming pushes data directly to Snowflake tables using channels and offsets.

```python
from snowflake.ingest import SimpleIngestManager
from snowflake.ingest import StagedFile
from snowflake.ingest.utils.uris import DEFAULT_SCHEME
import time

# Initialize Snowpipe Streaming client
ingest_manager = SimpleIngestManager(
    account='your_account',
    host='your_account.snowflakecomputing.com',
    user='your_user',
    pipe='your_db.your_schema.your_pipe',
    private_key='path/to/private_key.pem'
)

# Open channel
channel_name = 'kafka_channel_1'

# Push data
rows = [
    {"order_id": "order-123", "user_id": "user-456", "amount": 99.99},
    {"order_id": "order-124", "user_id": "user-457", "amount": 149.99}
]

# Insert rows with offset tracking
offset_token = ingest_manager.insert_rows(rows, offset_token=None)

# Commit offset
ingest_manager.commit_channel(channel_name, offset_token)
```

**Key Concepts**:
- **Channels**: Logical partitions for parallel writes (map to Kafka partitions)
- **Offsets**: Track progress for exactly-once delivery
- **Latency**: Sub-second to few seconds (vs minutes for S3-based Snowpipe)

### BigQuery Storage Write API

BigQuery Storage Write API provides exactly-once streaming with lower cost than legacy streaming API. Use default streams for simple ingestion or committed streams for exactly-once semantics.

```python
from google.cloud import bigquery_storage_v1
from google.cloud.bigquery_storage_v1 import types
from google.cloud.bigquery_storage_v1 import writer
from google.protobuf import descriptor_pb2
import json

client = bigquery_storage_v1.BigQueryWriteClient()

# Create write stream
project_id = "your-project"
dataset_id = "your_dataset"
table_id = "your_table"
parent = client.table_path(project_id, dataset_id, table_id)

write_stream = types.WriteStream()
write_stream.type_ = types.WriteStream.Type.COMMITTED  # Exactly-once

write_stream = client.create_write_stream(
    parent=parent, write_stream=write_stream
)

# Append rows
request_template = types.AppendRowsRequest()
request_template.write_stream = write_stream.name

proto_rows = types.ProtoRows()
# Add serialized rows to proto_rows...

request = types.AppendRowsRequest()
request.write_stream = write_stream.name
proto_data = types.AppendRowsRequest.ProtoData()
proto_data.rows = proto_rows
request.proto_rows = proto_data

response = client.append_rows(request)
print(f"Appended {len(proto_rows.serialized_rows)} rows")
```

**Stream Types**:
- **Default**: Simple, at-least-once, no commit needed
- **Committed**: Exactly-once, requires explicit commit
- **Pending**: For transactions, commit multiple streams atomically

### Dynamic Tables (Snowflake) / Materialized Views

Define transformations declaratively, let the warehouse manage incremental updates.

```sql
-- Snowflake Dynamic Table
CREATE DYNAMIC TABLE hourly_order_summary
  TARGET_LAG = '1 minute'
  WAREHOUSE = compute_wh
AS
SELECT
    DATE_TRUNC('hour', order_time) as hour,
    user_id,
    COUNT(*) as order_count,
    SUM(amount) as total_amount
FROM raw_orders
GROUP BY 1, 2;

-- BigQuery Materialized View
CREATE MATERIALIZED VIEW hourly_order_summary
AS
SELECT
    TIMESTAMP_TRUNC(order_time, HOUR) as hour,
    user_id,
    COUNT(*) as order_count,
    SUM(amount) as total_amount
FROM `project.dataset.raw_orders`
GROUP BY 1, 2;
```

**When to Use**:
- You primarily work in SQL and want simple streaming transformations
- Latency requirements are seconds to minutes (not milliseconds)
- You want to avoid managing Kafka, Flink, or Spark infrastructure
- Your transformations fit the warehouse's incremental update capabilities

[Deep dive →](references/warehouse-streaming-ingestion.md)

## Monitoring & Alerting

Monitor streaming pipelines continuously to detect issues before they impact downstream systems.

| Metric | What It Means | Alert Threshold |
|--------|---------------|----------------|
| Consumer Lag | How far behind real-time the consumer is (messages or time) | > 1M messages or > 5 minutes |
| Throughput | Messages/second processed | < 50% of expected baseline |
| Error Rate | Failed messages / total messages | > 0.1% for critical pipelines |
| Checkpoint Duration | Time to complete checkpoint (Flink, Spark) | > 2x checkpoint interval |
| Backpressure Ratio | % of time spent waiting for downstream | > 10% sustained |
| Partition Skew | Imbalance across partitions/consumers | Max/min ratio > 3x |
| Schema Registry Errors | Failed schema validations | > 0 for production topics |
| Watermark Lag | Event time lag behind processing time | > 1 hour (depends on SLA) |

**Monitoring Tools**:
- **Prometheus + Grafana**: Self-hosted, flexible, integrates with Kafka exporters and Flink/Spark metrics
- **Confluent Control Center**: Commercial Kafka monitoring with consumer lag, throughput, and topic dashboards
- **Cloud Monitoring**: AWS CloudWatch, GCP Cloud Monitoring, Azure Monitor for managed services
- **Datadog / New Relic**: APM platforms with streaming integrations

**Alert Strategy**:
1. **Critical alerts** (page immediately): Consumer completely stopped, error rate spike, exactly-once violations
2. **Warning alerts** (investigate within hours): Elevated lag, backpressure, slow checkpoints
3. **Info alerts** (track trends): Partition rebalancing, schema changes, throughput changes

## Security Posture

This skill generates Kafka configurations, stream processing code (Flink, Spark), and warehouse streaming ingestion pipelines.
See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for the full security framework.

**Credentials required**: Kafka broker auth (SASL/mTLS), Schema Registry auth, warehouse connections for streaming ingestion
**Where to configure**: Environment variables for all secrets. Kafka client configs reference env vars.
**Minimum role/permissions**: Producer/consumer ACLs scoped to specific topics and consumer groups

### By Security Tier

| Capability | Tier 1 (Cloud-Native) | Tier 2 (Regulated) | Tier 3 (Air-Gapped) |
|------------|----------------------|--------------------|--------------------|
| Kafka producer/consumer | Deploy to dev clusters | Generate configs for review | Generate configs only |
| Flink/Spark jobs | Submit to dev environments | Generate job code for review | Generate code only |
| Warehouse streaming (Snowpipe, BQ) | Configure dev pipelines | Generate pipeline configs | Generate configs only |
| Schema Registry | Register/evolve schemas in dev | Generate schema definitions | Generate Avro/Proto schemas only |
| Topic management | Create/configure dev topics | Generate topic configs for review | Document topic requirements |

### Credential Best Practices for Streaming

- **Kafka**: Use SASL/SCRAM or mTLS for broker auth. Never use PLAINTEXT in production.
- **Schema Registry**: Use API keys or HTTP basic auth, stored in environment variables.
- **Confluent Cloud**: Use API key/secret pairs stored in env vars, not in connector JSON configs.
- **Kafka Connect**: Use `ConfigProvider` to resolve secrets from external stores (Vault, AWS SM).
- **Stream processing**: Flink/Spark jobs should read credentials from env vars or mounted secrets, never from job code.

## Reference Files

- **[Kafka Deep Dive →](references/kafka-deep-dive.md)** — Kafka architecture, exactly-once semantics, Kafka Connect, ksqlDB, security best practices, performance tuning
- **[Flink & Spark Streaming →](references/flink-spark-streaming.md)** — DataStream API, Flink SQL, watermarks, late data handling, state backends, deployment patterns
- **[Warehouse Streaming Ingestion →](references/warehouse-streaming-ingestion.md)** — Snowpipe Streaming, Dynamic Tables, BigQuery Storage Write API, Databricks Delta Live Tables
- **[Stream Testing Patterns →](references/stream-testing-patterns.md)** — Embedded Kafka for unit tests, testcontainers for integration tests, stream replay strategies, backfill patterns
