# Warehouse Streaming Ingestion

> **Part of:** [streaming-data-skill](../SKILL.md)
> **Purpose:** Deep dive into streaming data into cloud warehouses — Snowpipe Streaming, Dynamic Tables, BigQuery Storage Write API, Dataflow, and warehouse-native streaming patterns

## Table of Contents

- [Warehouse Streaming Landscape](#warehouse-streaming-landscape)
- [Snowpipe Streaming](#snowpipe-streaming)
- [Snowflake Dynamic Tables](#snowflake-dynamic-tables)
- [BigQuery Storage Write API](#bigquery-storage-write-api)
- [BigQuery Materialized Views & Streaming](#bigquery-materialized-views--streaming)
- [Dataflow / Apache Beam](#dataflow--apache-beam)

---

## Warehouse Streaming Landscape

Modern cloud warehouses provide native streaming ingestion capabilities that bypass traditional batch loading patterns. Choose warehouse-native streaming when latency requirements are seconds to minutes and you need tight integration with warehouse features.

### Feature Comparison

| Feature | Snowflake | BigQuery | Databricks |
|---------|-----------|----------|------------|
| **Streaming ingestion method** | Snowpipe Streaming (SDK-based) | Storage Write API | Auto Loader + Structured Streaming |
| **Latency** | Sub-second to seconds | Seconds | Seconds to minutes |
| **Cost model** | Streaming credits + storage | Storage Write API pricing | DBU consumption |
| **Auto-scaling** | Automatic channel scaling | Automatic slot allocation | Cluster auto-scaling |
| **Schema evolution** | Schema detection on insert | Proto descriptor updates | Schema merging/overwrite modes |
| **Exactly-once support** | Offset tokens per channel | Committed streams with offsets | idempotentWrites in Delta |

### Decision Criteria: Warehouse-Native vs External Processing

Use **warehouse-native streaming** when:
- Transformations are simple (filtering, type casting, basic enrichment)
- Primary consumers are SQL analysts and BI tools
- Latency requirements are relaxed (seconds to minutes acceptable)
- Schema evolution needs are predictable
- Cost model favors warehouse credits over separate compute

Use **external processing** (Flink, Spark Streaming, Beam) when:
- Complex stateful transformations required (sessionization, pattern matching)
- Multi-sink fanout to multiple systems (warehouse + cache + search index)
- Sub-second latency required
- Advanced windowing and triggering logic needed
- Event-time processing with late data handling critical

---

## Snowpipe Streaming

Snowpipe Streaming provides low-latency, exactly-once data ingestion using the Snowflake Ingest SDK. Unlike file-based Snowpipe (which monitors cloud storage), Snowpipe Streaming accepts row-level data directly from applications.

### Architecture Components

**Snowflake Ingest SDK**: Client library (Java, Python) that manages connections to Snowflake
**Channel**: Logical partition for data ingestion with independent offset tracking
**Client**: SDK instance managing authentication and channel lifecycle
**Offset Token**: Unique identifier for committed data, enabling exactly-once delivery

### Snowpipe Streaming vs File-Based Snowpipe

| Aspect | Snowpipe Streaming | File-Based Snowpipe |
|--------|-------------------|---------------------|
| **Data source** | Application SDK calls | Cloud storage files (S3/GCS/Azure) |
| **Latency** | Sub-second | Minutes (file landing + notification) |
| **Throughput** | High (direct write) | High (parallel file processing) |
| **Schema detection** | Automatic on first insert | COPY command inference or explicit |
| **Exactly-once** | Offset token per channel | File deduplication by name |
| **Cost model** | Streaming credits (0.0036/credit) | Warehouse credits for COPY |
| **Use case** | Real-time app events | Batch file drops from data lakes |

### Setup: Java Dependencies

```xml
<!-- Maven pom.xml -->
<dependency>
    <groupId>net.snowflake</groupId>
    <artifactId>snowflake-ingest-sdk</artifactId>
    <version>2.1.0</version>
</dependency>
```

```gradle
// Gradle build.gradle
implementation 'net.snowflake:snowflake-ingest-sdk:2.1.0'
```

### Java Code Example: Complete Producer

```java
import net.snowflake.ingest.streaming.*;
import net.snowflake.ingest.utils.SFException;
import java.util.*;

public class SnowpipeStreamingProducer {

    private SnowflakeStreamingIngestClient client;
    private SnowflakeStreamingIngestChannel channel;

    public void initialize() throws Exception {
        // Create client with private key authentication
        Properties props = new Properties();
        props.put("user", "STREAMING_USER");
        props.put("private_key", loadPrivateKey());
        props.put("account", "myorg-myaccount");
        props.put("host", "myorg-myaccount.snowflakecomputing.com");
        props.put("scheme", "https");
        props.put("port", "443");

        this.client = SnowflakeStreamingIngestClientFactory.builder("MY_CLIENT")
            .setProperties(props)
            .build();

        // Open channel to target table
        OpenChannelRequest openRequest = OpenChannelRequest.builder("MY_CHANNEL")
            .setDBName("PROD_DB")
            .setSchemaName("EVENTS")
            .setTableName("USER_ACTIONS")
            .setOnErrorOption(OpenChannelRequest.OnErrorOption.CONTINUE)
            .build();

        this.channel = client.openChannel(openRequest);
    }

    public void produceEvents(List<Map<String, Object>> events) throws Exception {
        // Build rows for insertion
        List<Map<String, Object>> rows = new ArrayList<>();
        for (Map<String, Object> event : events) {
            Map<String, Object> row = new HashMap<>();
            row.put("EVENT_ID", event.get("id"));
            row.put("USER_ID", event.get("userId"));
            row.put("ACTION", event.get("action"));
            row.put("TIMESTAMP", event.get("timestamp"));
            row.put("METADATA", event.get("metadata")); // VARIANT column
            rows.add(row);
        }

        // Insert rows with offset tracking
        InsertValidationResponse response = channel.insertRows(rows, null);

        if (response.hasErrors()) {
            // Handle row-level errors
            for (InsertValidationResponse.InsertError error : response.getInsertErrors()) {
                System.err.printf("Row %d failed: %s%n",
                    error.getRowIndex(), error.getMessage());
            }
            throw new RuntimeException("Insert failed with errors");
        }

        // Get offset token for exactly-once tracking
        String offsetToken = channel.getLatestCommittedOffsetToken();
        System.out.printf("Committed offset: %s%n", offsetToken);
    }

    public void close() throws Exception {
        if (channel != null) {
            channel.close().get(); // Wait for final flush
        }
        if (client != null) {
            client.close();
        }
    }

    private String loadPrivateKey() {
        // Load RSA private key for Snowflake authentication
        // See: https://docs.snowflake.com/en/developer-guide/sql-api/authenticating
        return "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----";
    }
}
```

### Python Code Example: Using snowflake-ingest Library

```python
from snowflake.ingest import SimpleIngestManager
from snowflake.ingest.utils.uris import DEFAULT_SCHEME
from datetime import datetime
import json

class SnowpipeStreamingProducer:

    def __init__(self, account, user, private_key_path):
        self.account = account
        self.user = user
        self.private_key_path = private_key_path
        self.client = None
        self.channel = None

    def initialize(self, database, schema, table, channel_name):
        """Initialize streaming client and open channel"""
        from snowflake.ingest.streaming.snowflake_streaming_ingest_client import (
            SnowflakeStreamingIngestClient
        )
        from snowflake.ingest.streaming.open_channel_request import (
            OpenChannelRequest
        )

        # Create client
        self.client = SnowflakeStreamingIngestClient(
            account=self.account,
            user=self.user,
            private_key=self._load_private_key(),
            role="STREAMING_ROLE"
        )

        # Open channel
        request = OpenChannelRequest(
            channel_name=channel_name,
            database=database,
            schema=schema,
            table=table,
            on_error="CONTINUE"
        )

        self.channel = self.client.open_channel(request)

    def produce_events(self, events):
        """Insert events into Snowflake with offset tracking"""
        rows = []
        for event in events:
            row = {
                "EVENT_ID": event["id"],
                "USER_ID": event["user_id"],
                "ACTION": event["action"],
                "TIMESTAMP": event["timestamp"],
                "METADATA": json.dumps(event.get("metadata", {}))
            }
            rows.append(row)

        # Insert rows
        response = self.channel.insert_rows(rows)

        if response.has_errors():
            for error in response.errors:
                print(f"Row {error.row_index} failed: {error.message}")
            raise RuntimeError("Insert failed with errors")

        # Get committed offset
        offset_token = self.channel.get_latest_committed_offset_token()
        print(f"Committed offset: {offset_token}")

        return offset_token

    def close(self):
        """Close channel and client"""
        if self.channel:
            self.channel.close()
        if self.client:
            self.client.close()

    def _load_private_key(self):
        """Load RSA private key for authentication"""
        with open(self.private_key_path, 'r') as f:
            return f.read()


# Usage example
producer = SnowpipeStreamingProducer(
    account="myorg-myaccount",
    user="STREAMING_USER",
    private_key_path="/path/to/rsa_key.p8"
)

producer.initialize(
    database="PROD_DB",
    schema="EVENTS",
    table="USER_ACTIONS",
    channel_name="app_events_channel_1"
)

events = [
    {
        "id": "evt_123",
        "user_id": "usr_456",
        "action": "page_view",
        "timestamp": datetime.utcnow().isoformat(),
        "metadata": {"page": "/home", "referrer": "google"}
    }
]

offset = producer.produce_events(events)
producer.close()
```

### Schema Detection and Evolution

Snowpipe Streaming automatically detects schema on the first insert to a new table. Schema evolution follows these rules:

**Adding columns**: Automatically detected and added to table
**Changing types**: Fails if incompatible (e.g., string to number)
**Dropping columns**: Omitted columns receive NULL values
**VARIANT columns**: Accept any JSON structure without schema enforcement

```sql
-- Create table with flexible schema for streaming
CREATE TABLE EVENTS.USER_ACTIONS (
    EVENT_ID STRING NOT NULL,
    USER_ID STRING NOT NULL,
    ACTION STRING,
    TIMESTAMP TIMESTAMP_NTZ,
    METADATA VARIANT  -- Flexible schema for evolving event properties
);
```

### Offset Management for Exactly-Once Delivery

Store offset tokens externally to resume processing after failures without duplicates.

```python
import redis

class OffsetManager:

    def __init__(self, redis_client, channel_name):
        self.redis = redis_client
        self.key = f"snowpipe:offset:{channel_name}"

    def get_last_offset(self):
        """Retrieve last committed offset"""
        offset = self.redis.get(self.key)
        return offset.decode('utf-8') if offset else None

    def save_offset(self, offset_token):
        """Save offset after successful insert"""
        self.redis.set(self.key, offset_token)

    def has_processed(self, offset_token):
        """Check if offset already processed"""
        last = self.get_last_offset()
        return last and last >= offset_token


# Usage in producer
offset_mgr = OffsetManager(redis.Redis(), "app_events_channel_1")

# Before processing
last_offset = offset_mgr.get_last_offset()
if last_offset:
    # Resume from last offset (implementation-specific)
    pass

# After successful insert
new_offset = producer.produce_events(events)
offset_mgr.save_offset(new_offset)
```

### Error Handling: Channel Invalidation and Reopening

Channels can become invalid due to table schema changes or network issues. Implement retry logic with channel reopening.

```python
from snowflake.ingest.error import SFException

def insert_with_retry(channel, rows, max_retries=3):
    """Insert rows with automatic channel recovery"""
    for attempt in range(max_retries):
        try:
            response = channel.insert_rows(rows)
            if response.has_errors():
                raise RuntimeError(f"Insert errors: {response.errors}")
            return channel.get_latest_committed_offset_token()

        except SFException as e:
            if "channel is invalid" in str(e).lower():
                print(f"Channel invalid, reopening (attempt {attempt + 1})")
                channel = reopen_channel(channel)
            else:
                raise

    raise RuntimeError(f"Failed after {max_retries} retries")


def reopen_channel(old_channel):
    """Reopen channel with same configuration"""
    # Close old channel
    old_channel.close()

    # Reopen with same settings
    request = OpenChannelRequest(
        channel_name=old_channel.name,
        database=old_channel.database,
        schema=old_channel.schema,
        table=old_channel.table,
        on_error="CONTINUE"
    )

    return client.open_channel(request)
```

### Performance Tuning

**Batch size**: Insert 1000-10000 rows per call for optimal throughput
**Flush interval**: SDK auto-flushes every few seconds; explicit flush not required
**Channel count**: Use multiple channels for parallel ingestion (one per partition/shard)
**Network**: Deploy producers in same cloud region as Snowflake account

```python
# Batching configuration
BATCH_SIZE = 5000
FLUSH_INTERVAL_SECONDS = 5

batch = []
for event in event_stream:
    batch.append(event)

    if len(batch) >= BATCH_SIZE:
        producer.produce_events(batch)
        batch = []

# Flush remaining
if batch:
    producer.produce_events(batch)
```

### Cost Model

**Streaming credits**: Charged per GB ingested (approximately 0.0036 credits per GB)
**Warehouse credits**: Not consumed during ingestion (only during queries)
**Storage**: Standard Snowflake storage pricing applies

Compare with file-based Snowpipe which uses warehouse credits for COPY operations.

### Monitoring

```sql
-- View streaming file migration history
SELECT *
FROM SNOWFLAKE.ACCOUNT_USAGE.SNOWPIPE_STREAMING_FILE_MIGRATION_HISTORY
WHERE TABLE_NAME = 'USER_ACTIONS'
ORDER BY LAST_LOAD_TIME DESC
LIMIT 100;

-- Check channel status and throughput
SELECT
    CHANNEL_NAME,
    TABLE_NAME,
    ROW_COUNT,
    BYTES,
    LAST_INSERT_TIME
FROM SNOWFLAKE.ACCOUNT_USAGE.SNOWPIPE_STREAMING_CHANNELS
WHERE TABLE_NAME = 'USER_ACTIONS';

-- Monitor streaming credits consumption
SELECT
    DATE_TRUNC('HOUR', START_TIME) AS HOUR,
    SUM(CREDITS_USED) AS STREAMING_CREDITS
FROM SNOWFLAKE.ACCOUNT_USAGE.METERING_HISTORY
WHERE SERVICE_TYPE = 'SNOWPIPE_STREAMING'
GROUP BY HOUR
ORDER BY HOUR DESC;
```

---

## Snowflake Dynamic Tables

Dynamic Tables provide declarative incremental materialization. Define the target state with SQL; Snowflake automatically manages refresh logic to maintain freshness within a specified lag.

### What Dynamic Tables Are

Traditional materialized views in Snowflake are static (manual refresh). Dynamic Tables continuously refresh based on:
- **Target lag**: Maximum acceptable staleness (e.g., 1 minute, 1 hour)
- **Automatic scheduling**: Snowflake determines optimal refresh frequency
- **Incremental refresh**: Only processes changed data when possible

### CREATE DYNAMIC TABLE Syntax

```sql
CREATE DYNAMIC TABLE <name>
  TARGET_LAG = {'<time_value>' | DOWNSTREAM}
  WAREHOUSE = <warehouse_name>
  [REFRESH_MODE = {AUTO | FULL | INCREMENTAL}]
  [INITIALIZE = {ON_CREATE | ON_SCHEDULE}]
AS
  <query>;
```

**TARGET_LAG**: Maximum staleness (e.g., '1 minute', '5 minutes', '1 hour')
**DOWNSTREAM**: Inherit lag from downstream Dynamic Tables that depend on this one
**REFRESH_MODE**: AUTO (Snowflake decides), FULL (always full refresh), INCREMENTAL (delta only)
**INITIALIZE**: ON_CREATE (populate immediately) or ON_SCHEDULE (wait for first refresh)

### Simple Aggregation Dynamic Table

```sql
-- Bronze layer: raw streaming data
CREATE TABLE EVENTS.USER_ACTIONS_RAW (
    EVENT_ID STRING,
    USER_ID STRING,
    ACTION STRING,
    TIMESTAMP TIMESTAMP_NTZ,
    METADATA VARIANT
);

-- Silver layer: real-time hourly aggregations
CREATE DYNAMIC TABLE EVENTS.USER_ACTIONS_HOURLY
  TARGET_LAG = '5 minutes'
  WAREHOUSE = STREAMING_WH
  REFRESH_MODE = AUTO
AS
SELECT
    DATE_TRUNC('HOUR', TIMESTAMP) AS EVENT_HOUR,
    ACTION,
    COUNT(*) AS ACTION_COUNT,
    COUNT(DISTINCT USER_ID) AS UNIQUE_USERS
FROM EVENTS.USER_ACTIONS_RAW
GROUP BY EVENT_HOUR, ACTION;
```

### Multi-Level Dynamic Table Pipeline (Bronze → Silver → Gold)

```sql
-- Bronze: raw ingestion (Snowpipe Streaming target)
CREATE TABLE BRONZE.RAW_EVENTS (
    EVENT_ID STRING,
    EVENT_TIME TIMESTAMP_NTZ,
    USER_ID STRING,
    EVENT_TYPE STRING,
    PROPERTIES VARIANT
);

-- Silver: cleaned and enriched
CREATE DYNAMIC TABLE SILVER.CLEANED_EVENTS
  TARGET_LAG = '1 minute'
  WAREHOUSE = STREAMING_WH
AS
SELECT
    EVENT_ID,
    EVENT_TIME,
    USER_ID,
    EVENT_TYPE,
    PROPERTIES:product_id::STRING AS PRODUCT_ID,
    PROPERTIES:price::FLOAT AS PRICE,
    PROPERTIES:currency::STRING AS CURRENCY
FROM BRONZE.RAW_EVENTS
WHERE EVENT_ID IS NOT NULL
  AND EVENT_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP());  -- 7-day retention

-- Gold: business metrics
CREATE DYNAMIC TABLE GOLD.REVENUE_BY_PRODUCT_HOUR
  TARGET_LAG = '5 minutes'
  WAREHOUSE = STREAMING_WH
AS
SELECT
    DATE_TRUNC('HOUR', EVENT_TIME) AS REVENUE_HOUR,
    PRODUCT_ID,
    SUM(PRICE) AS TOTAL_REVENUE,
    COUNT(*) AS TRANSACTION_COUNT,
    AVG(PRICE) AS AVG_TRANSACTION_VALUE
FROM SILVER.CLEANED_EVENTS
WHERE EVENT_TYPE = 'purchase'
  AND CURRENCY = 'USD'
GROUP BY REVENUE_HOUR, PRODUCT_ID;
```

### Dynamic Table with JOIN

```sql
-- Reference dimension table
CREATE TABLE DIM.PRODUCTS (
    PRODUCT_ID STRING PRIMARY KEY,
    PRODUCT_NAME STRING,
    CATEGORY STRING
);

-- Dynamic Table with dimension enrichment
CREATE DYNAMIC TABLE GOLD.REVENUE_BY_CATEGORY_HOUR
  TARGET_LAG = '5 minutes'
  WAREHOUSE = STREAMING_WH
AS
SELECT
    DATE_TRUNC('HOUR', e.EVENT_TIME) AS REVENUE_HOUR,
    p.CATEGORY,
    SUM(e.PRICE) AS TOTAL_REVENUE,
    COUNT(*) AS TRANSACTION_COUNT
FROM SILVER.CLEANED_EVENTS e
INNER JOIN DIM.PRODUCTS p
  ON e.PRODUCT_ID = p.PRODUCT_ID
WHERE e.EVENT_TYPE = 'purchase'
GROUP BY REVENUE_HOUR, p.CATEGORY;
```

### Comparison: Dynamic Tables vs Streams + Tasks

| Feature | Dynamic Tables | Streams + Tasks |
|---------|---------------|-----------------|
| **Complexity** | Single SQL statement | Multiple objects (stream, task, target table) |
| **Scheduling** | Automatic (lag-based) | Manual cron or predecessor dependency |
| **Incremental logic** | Automatic (when possible) | Manual (query stream for changes) |
| **Graph awareness** | Understands dependencies | Manual dependency via AFTER clause |
| **Monitoring** | Built-in history views | Task history + custom logging |
| **Flexibility** | Limited to SQL transforms | Full procedural logic (JavaScript, Snowpark) |
| **Cost** | Warehouse credits for refresh | Warehouse credits + task compute |
| **Use case** | Declarative aggregations/joins | Complex workflows, stored procedures |

### Monitoring

```sql
-- View refresh history
SELECT
    NAME,
    SCHEMA_NAME,
    DATABASE_NAME,
    REFRESH_START_TIME,
    REFRESH_END_TIME,
    STATE,
    ROWS_INSERTED,
    BYTES_INSERTED
FROM SNOWFLAKE.ACCOUNT_USAGE.DYNAMIC_TABLE_REFRESH_HISTORY
WHERE NAME = 'REVENUE_BY_PRODUCT_HOUR'
ORDER BY REFRESH_START_TIME DESC
LIMIT 100;

-- View Dynamic Table graph (dependencies)
SELECT
    NAME,
    SCHEDULING_STATE,
    TARGET_LAG,
    DATA_TIMESTAMP,
    REFRESH_MODE
FROM SNOWFLAKE.ACCOUNT_USAGE.DYNAMIC_TABLE_GRAPH_HISTORY
WHERE NAME = 'REVENUE_BY_PRODUCT_HOUR';

-- Check current lag
SHOW DYNAMIC TABLES LIKE 'REVENUE_BY_PRODUCT_HOUR';
-- Look at SCHEDULING_STATE and CURRENT_LAG columns
```

### Limitations

**Non-deterministic functions**: CURRENT_TIMESTAMP(), RANDOM() not allowed
**Stored procedures**: Cannot call stored procedures or UDFs with side effects
**Streams**: Cannot query Snowflake streams directly
**FLATTEN**: Limited support for VARIANT flattening in incremental mode

### When to Use Dynamic Tables vs Alternatives

Use **Dynamic Tables** when:
- Transformations are SQL-only aggregations or joins
- Incremental refresh is straightforward (append-only or simple updates)
- Declarative approach preferred (no procedural logic)
- Lag-based scheduling sufficient

Use **Streams + Tasks** when:
- Complex procedural logic required (stored procedures, Python UDFs)
- Custom error handling or retry logic needed
- Integration with external systems (REST API calls)
- Fine-grained scheduling control required

Use **dbt incremental** when:
- Version control and CI/CD for transformations required
- Testing and documentation are priorities
- Multi-warehouse deployment (dbt compiles to native SQL)
- Team familiarity with dbt ecosystem

### Cost Implications

Dynamic Tables consume warehouse credits during refresh. Cost depends on:
- **Target lag**: Lower lag = more frequent refreshes = higher cost
- **Refresh mode**: FULL refreshes more expensive than INCREMENTAL
- **Data volume**: Larger tables consume more credits per refresh
- **Warehouse size**: Larger warehouses accelerate refresh but increase credit rate

```sql
-- Estimate refresh cost
SELECT
    NAME,
    SUM(CREDITS_USED) AS TOTAL_CREDITS,
    COUNT(*) AS REFRESH_COUNT,
    AVG(CREDITS_USED) AS AVG_CREDITS_PER_REFRESH
FROM SNOWFLAKE.ACCOUNT_USAGE.DYNAMIC_TABLE_REFRESH_HISTORY
WHERE NAME = 'REVENUE_BY_PRODUCT_HOUR'
  AND REFRESH_START_TIME >= DATEADD('day', -7, CURRENT_TIMESTAMP())
GROUP BY NAME;
```

---

## BigQuery Storage Write API

The BigQuery Storage Write API enables high-throughput streaming ingestion with exactly-once semantics. It replaces the legacy streaming API (tabledata.insertAll) with better performance and lower cost.

### API Stream Types

| Stream Type | Delivery Guarantee | Latency | Cost | Use Case |
|-------------|-------------------|---------|------|----------|
| **Default stream** | At-least-once | Seconds | Lower | High-throughput logs, idempotent writes |
| **Committed stream** | Exactly-once | Seconds | Higher (offset tracking) | Financial transactions, critical events |
| **Buffered stream** | At-least-once (manual commit) | Sub-second (manual flush) | Lower | Batching before commit |

**Default stream**: Single stream per table, automatic commit, no offset tracking
**Committed stream**: Multiple streams, manual commit with offset, exactly-once guarantee
**Buffered stream**: Multiple streams, manual flush and commit, for batching control

### Python Code Example: Default Stream

```python
from google.cloud import bigquery_storage_v1
from google.cloud.bigquery_storage_v1 import types, writer
from google.protobuf import descriptor_pb2
import json

class BigQueryStreamWriter:

    def __init__(self, project_id, dataset_id, table_id):
        self.client = bigquery_storage_v1.BigQueryWriteClient()
        self.parent = f"projects/{project_id}/datasets/{dataset_id}/tables/{table_id}"
        self.write_stream = None
        self.stream_writer = None

    def initialize_default_stream(self):
        """Initialize default stream (at-least-once)"""
        # Default stream always exists, no creation needed
        stream_name = f"{self.parent}/_default"

        # Create managed writer client
        self.stream_writer = writer.AppendRowsStream(
            self.client,
            stream_name
        )

    def write_rows(self, rows):
        """
        Write rows to BigQuery using default stream
        rows: list of dicts matching table schema
        """
        # Convert rows to protocol buffer format
        proto_rows = types.ProtoRows()

        for row in rows:
            proto_data = types.ProtoData()
            # Serialize row as JSON (for simplicity; proto is more efficient)
            serialized = self._serialize_row(row)
            proto_data.writer_schema = self._get_proto_schema()
            proto_data.rows.serialized_rows.append(serialized)
            proto_rows.serialized_rows.append(serialized)

        # Create append request
        request = types.AppendRowsRequest()
        request.write_stream = f"{self.parent}/_default"
        request.proto_rows = proto_rows

        # Append rows
        response = self.client.append_rows(iter([request]))

        # Check for errors
        for result in response:
            if result.error.code != 0:
                raise RuntimeError(f"Append failed: {result.error.message}")
            print(f"Appended {len(rows)} rows at offset {result.offset}")

    def _serialize_row(self, row):
        """Serialize row dict to bytes (JSON format for example)"""
        return json.dumps(row).encode('utf-8')

    def _get_proto_schema(self):
        """Get protocol buffer schema for table"""
        # In production, generate this from table schema
        # See: https://cloud.google.com/bigquery/docs/write-api#protocol_buffers
        pass


# Usage example
writer_client = BigQueryStreamWriter(
    project_id="my-project",
    dataset_id="events",
    table_id="user_actions"
)

writer_client.initialize_default_stream()

rows = [
    {
        "event_id": "evt_123",
        "user_id": "usr_456",
        "action": "page_view",
        "timestamp": "2026-02-13T10:30:00Z",
        "metadata": {"page": "/home"}
    }
]

writer_client.write_rows(rows)
```

### Python Code Example: Committed Stream with Offset Tracking

```python
from google.cloud import bigquery_storage_v1
from google.cloud.bigquery_storage_v1 import types, writer
import uuid

class ExactlyOnceWriter:

    def __init__(self, project_id, dataset_id, table_id):
        self.client = bigquery_storage_v1.BigQueryWriteClient()
        self.parent = f"projects/{project_id}/datasets/{dataset_id}/tables/{table_id}"
        self.stream_name = None
        self.stream_writer = None

    def create_committed_stream(self):
        """Create a committed stream for exactly-once writes"""
        write_stream = types.WriteStream()
        write_stream.type_ = types.WriteStream.Type.COMMITTED

        # Create stream
        stream = self.client.create_write_stream(
            parent=self.parent,
            write_stream=write_stream
        )

        self.stream_name = stream.name
        print(f"Created committed stream: {self.stream_name}")

        return stream

    def write_with_offset(self, rows, offset):
        """
        Write rows with explicit offset for exactly-once guarantee
        offset: unique string identifier (e.g., Kafka offset, sequence number)
        """
        # Create append request with offset
        request = types.AppendRowsRequest()
        request.write_stream = self.stream_name
        request.offset = offset  # Deduplication key

        # Add rows (protocol buffer format)
        proto_rows = types.ProtoRows()
        for row in rows:
            serialized = self._serialize_row(row)
            proto_rows.serialized_rows.append(serialized)

        request.proto_rows = proto_rows

        # Append with offset tracking
        try:
            response = self.client.append_rows(iter([request]))

            for result in response:
                if result.error.code != 0:
                    if "ALREADY_EXISTS" in result.error.message:
                        print(f"Offset {offset} already committed (duplicate)")
                        return "duplicate"
                    else:
                        raise RuntimeError(f"Append failed: {result.error.message}")

                print(f"Committed offset {offset}, append offset {result.append_result.offset}")
                return result.append_result.offset

        except Exception as e:
            print(f"Error appending rows: {e}")
            raise

    def finalize_stream(self):
        """Finalize stream (make data immediately available for queries)"""
        request = types.FinalizeWriteStreamRequest()
        request.name = self.stream_name

        response = self.client.finalize_write_stream(request=request)
        print(f"Finalized stream, row count: {response.row_count}")

    def _serialize_row(self, row):
        """Serialize row to protocol buffer format"""
        import json
        return json.dumps(row).encode('utf-8')


# Usage with Kafka offset tracking
writer = ExactlyOnceWriter(
    project_id="my-project",
    dataset_id="events",
    table_id="transactions"
)

writer.create_committed_stream()

# Process Kafka messages
kafka_offset = 1234567
rows = [{"transaction_id": "txn_001", "amount": 99.99}]

# Write with offset (idempotent)
result = writer.write_with_offset(rows, offset=kafka_offset)

# Finalize when done
writer.finalize_stream()
```

### Schema Management

BigQuery Storage Write API uses Protocol Buffer descriptors for schema definition. Generate descriptors from BigQuery table schema:

```python
from google.cloud import bigquery
from google.protobuf import descriptor_pb2

def get_proto_descriptor(project_id, dataset_id, table_id):
    """Generate protocol buffer descriptor from BigQuery table schema"""
    bq_client = bigquery.Client(project=project_id)
    table = bq_client.get_table(f"{project_id}.{dataset_id}.{table_id}")

    # Create descriptor
    descriptor_proto = descriptor_pb2.DescriptorProto()
    descriptor_proto.name = table_id

    for field in table.schema:
        field_proto = descriptor_proto.field.add()
        field_proto.name = field.name
        field_proto.number = len(descriptor_proto.field)

        # Map BigQuery types to proto types
        if field.field_type == "STRING":
            field_proto.type = descriptor_pb2.FieldDescriptorProto.TYPE_STRING
        elif field.field_type == "INT64":
            field_proto.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT64
        elif field.field_type == "FLOAT64":
            field_proto.type = descriptor_pb2.FieldDescriptorProto.TYPE_DOUBLE
        elif field.field_type == "TIMESTAMP":
            field_proto.type = descriptor_pb2.FieldDescriptorProto.TYPE_INT64
        # Add more type mappings as needed

    return descriptor_proto
```

### Multiplexing: Multiple Destination Tables

Use multiple committed streams to write to different tables from a single client:

```python
class MultiplexedWriter:

    def __init__(self, project_id):
        self.client = bigquery_storage_v1.BigQueryWriteClient()
        self.streams = {}  # table_id -> stream_name

    def add_table(self, dataset_id, table_id):
        """Add a destination table"""
        parent = f"projects/{project_id}/datasets/{dataset_id}/tables/{table_id}"

        write_stream = types.WriteStream()
        write_stream.type_ = types.WriteStream.Type.COMMITTED

        stream = self.client.create_write_stream(
            parent=parent,
            write_stream=write_stream
        )

        self.streams[table_id] = stream.name
        print(f"Added stream for {table_id}")

    def route_and_write(self, table_id, rows, offset):
        """Route rows to appropriate table stream"""
        if table_id not in self.streams:
            raise ValueError(f"No stream for table {table_id}")

        request = types.AppendRowsRequest()
        request.write_stream = self.streams[table_id]
        request.offset = offset

        # Add rows...
        # (similar to previous examples)

        response = self.client.append_rows(iter([request]))
        # Handle response...
```

### Error Handling

```python
from google.api_core import exceptions
import time

def append_with_retry(client, request, max_retries=3):
    """Append rows with exponential backoff retry"""
    for attempt in range(max_retries):
        try:
            response = client.append_rows(iter([request]))
            return response

        except exceptions.ResourceExhausted as e:
            # Rate limit exceeded
            wait = 2 ** attempt
            print(f"Rate limited, waiting {wait}s (attempt {attempt + 1})")
            time.sleep(wait)

        except exceptions.InvalidArgument as e:
            # Schema mismatch or invalid data
            print(f"Invalid argument: {e}")
            raise  # Don't retry

        except exceptions.NotFound as e:
            # Stream not found (may have been garbage collected)
            print(f"Stream not found: {e}")
            raise  # Recreate stream

        except Exception as e:
            print(f"Unexpected error: {e}")
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)

    raise RuntimeError(f"Failed after {max_retries} retries")
```

### Performance: Connection Pooling and Batching

**Connection pooling**: Reuse BigQueryWriteClient instances across writes
**Batching**: Append 1000-10000 rows per request for optimal throughput
**Parallelism**: Use multiple committed streams for parallel writes
**Region**: Deploy writers in same region as BigQuery dataset

```python
# Batching configuration
BATCH_SIZE = 5000
FLUSH_INTERVAL_SECONDS = 5

batch = []
last_flush = time.time()

for event in event_stream:
    batch.append(event)

    # Flush on size or time threshold
    if len(batch) >= BATCH_SIZE or (time.time() - last_flush) >= FLUSH_INTERVAL_SECONDS:
        writer.write_with_offset(batch, offset=current_offset)
        batch = []
        last_flush = time.time()
        current_offset += 1
```

### Cost Comparison

| API | Pricing | Notes |
|-----|---------|-------|
| **Storage Write API** | $0.025 per 200 MB (first 2 TB free/month) | Recommended for all new applications |
| **Legacy streaming inserts** | $0.010 per 200 MB (first 2 TB free/month) | Deprecated, higher latency |

Storage Write API has higher throughput and lower latency despite slightly higher nominal cost.

### Monitoring

```sql
-- View streaming buffer status
SELECT
    table_schema,
    table_name,
    TIMESTAMP_MILLIS(creation_time) AS creation_time,
    estimated_bytes,
    estimated_rows
FROM `my-project`.events.__TABLES__
WHERE table_name = 'user_actions';

-- Query STREAMING_TIMELINE (requires logging)
SELECT
    timestamp,
    severity,
    json_payload.stream_name,
    json_payload.offset,
    json_payload.row_count
FROM `my-project`.events.STREAMING_TIMELINE
WHERE json_payload.table_name = 'user_actions'
ORDER BY timestamp DESC
LIMIT 100;

-- Monitor write API usage (via JOBS_BY_PROJECT)
SELECT
    DATE(creation_time) AS date,
    COUNT(*) AS write_requests,
    SUM(total_bytes_processed) AS total_bytes
FROM `my-project`.region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT
WHERE job_type = 'QUERY'
  AND statement_type = 'SCRIPT'  -- Storage Write API jobs
GROUP BY date
ORDER BY date DESC;
```

---

## BigQuery Materialized Views & Streaming

Materialized views in BigQuery can automatically stay fresh over streaming data. They provide pre-computed aggregations with automatic smart refresh.

### Materialized Views Over Streaming Buffer

Create materialized views that aggregate streaming data in real-time:

```sql
-- Base table with streaming ingestion
CREATE TABLE events.user_actions (
    event_id STRING,
    user_id STRING,
    action STRING,
    timestamp TIMESTAMP,
    metadata JSON
);

-- Materialized view for real-time dashboard
CREATE MATERIALIZED VIEW events.user_actions_hourly
AS
SELECT
    TIMESTAMP_TRUNC(timestamp, HOUR) AS event_hour,
    action,
    COUNT(*) AS action_count,
    COUNT(DISTINCT user_id) AS unique_users
FROM events.user_actions
GROUP BY event_hour, action;
```

### Auto-Refresh and Smart Tuning

BigQuery automatically refreshes materialized views when base table changes. Refresh frequency depends on:
- **Query patterns**: Frequently queried views refresh more often
- **Data freshness**: Views refresh to capture recent streaming inserts
- **Cost optimization**: BigQuery balances freshness vs. refresh cost

```sql
-- Check materialized view metadata
SELECT
    table_name,
    last_refresh_time,
    refresh_watermark
FROM `my-project`.events.INFORMATION_SCHEMA.MATERIALIZED_VIEWS
WHERE table_name = 'user_actions_hourly';

-- Force manual refresh (if needed)
CALL BQ.REFRESH_MATERIALIZED_VIEW('events.user_actions_hourly');
```

### Limitations

**Aggregate functions only**: SUM, COUNT, AVG, MIN, MAX supported
**No JOINs**: Standard SQL materialized views don't support JOINs (use BigQuery BI Engine)
**GROUP BY required**: Materialized views must aggregate data
**Non-deterministic functions**: CURRENT_TIMESTAMP() not allowed

### Comparison with Snowflake Dynamic Tables

| Feature | BigQuery Materialized Views | Snowflake Dynamic Tables |
|---------|----------------------------|-------------------------|
| **Refresh control** | Automatic (smart tuning) | Explicit lag configuration |
| **JOINs** | Not supported (standard SQL) | Fully supported |
| **Incremental refresh** | Automatic | Automatic (when possible) |
| **Cost visibility** | Included in query cost | Explicit warehouse credits |
| **Complexity** | Limited to aggregations | Full SQL support |

### Code Example: Materialized View for Real-Time Dashboard

```sql
-- Base table: streaming transaction data
CREATE TABLE finance.transactions (
    transaction_id STRING,
    user_id STRING,
    amount NUMERIC,
    currency STRING,
    transaction_time TIMESTAMP,
    status STRING
);

-- Materialized view: real-time revenue metrics
CREATE MATERIALIZED VIEW finance.revenue_metrics_hourly
AS
SELECT
    TIMESTAMP_TRUNC(transaction_time, HOUR) AS revenue_hour,
    currency,
    SUM(amount) AS total_revenue,
    COUNT(*) AS transaction_count,
    AVG(amount) AS avg_transaction_value,
    COUNT(DISTINCT user_id) AS unique_customers
FROM finance.transactions
WHERE status = 'completed'
GROUP BY revenue_hour, currency;

-- Query materialized view (uses pre-computed results)
SELECT *
FROM finance.revenue_metrics_hourly
WHERE revenue_hour >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
ORDER BY revenue_hour DESC;
```

---

## Dataflow / Apache Beam

Google Cloud Dataflow is a managed service for Apache Beam pipelines. Beam provides a unified batch and streaming model with advanced windowing, triggering, and state management.

### Beam Model Fundamentals

**PCollection**: Immutable distributed dataset (bounded or unbounded)
**PTransform**: Data transformation (ParDo, GroupByKey, Combine)
**Pipeline**: Graph of PCollections and PTransforms
**Runner**: Execution engine (DirectRunner for local, DataflowRunner for cloud)

### Google Cloud Dataflow

Managed Beam runner with:
- **Auto-scaling**: Workers scale based on pipeline backlog
- **Shuffle service**: Offloads GroupByKey operations for efficiency
- **Streaming engine**: Separates computation from state storage
- **Flex Templates**: Parameterized pipeline deployment

### Streaming from Pub/Sub to BigQuery (Python)

```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.io.gcp.bigquery import WriteToBigQuery
from apache_beam.io.gcp.pubsub import ReadFromPubSub
import json

class ParseEvent(beam.DoFn):
    """Parse JSON event from Pub/Sub"""

    def process(self, element):
        try:
            event = json.loads(element.decode('utf-8'))

            # Transform to BigQuery row
            yield {
                'event_id': event['id'],
                'user_id': event['user_id'],
                'action': event['action'],
                'timestamp': event['timestamp'],
                'metadata': json.dumps(event.get('metadata', {}))
            }
        except Exception as e:
            # Log error and skip malformed events
            print(f"Error parsing event: {e}")


def run_pipeline():
    # Pipeline options
    options = PipelineOptions(
        project='my-project',
        runner='DataflowRunner',
        region='us-central1',
        temp_location='gs://my-bucket/temp',
        staging_location='gs://my-bucket/staging',
        streaming=True,
        # Auto-scaling
        autoscaling_algorithm='THROUGHPUT_BASED',
        max_num_workers=10,
        # Streaming engine (recommended)
        enable_streaming_engine=True
    )

    # BigQuery table schema
    table_schema = {
        'fields': [
            {'name': 'event_id', 'type': 'STRING', 'mode': 'REQUIRED'},
            {'name': 'user_id', 'type': 'STRING', 'mode': 'REQUIRED'},
            {'name': 'action', 'type': 'STRING', 'mode': 'NULLABLE'},
            {'name': 'timestamp', 'type': 'TIMESTAMP', 'mode': 'NULLABLE'},
            {'name': 'metadata', 'type': 'STRING', 'mode': 'NULLABLE'}
        ]
    }

    with beam.Pipeline(options=options) as pipeline:
        (
            pipeline
            # Read from Pub/Sub
            | 'Read from Pub/Sub' >> ReadFromPubSub(
                subscription='projects/my-project/subscriptions/events-sub'
            )
            # Parse JSON
            | 'Parse Events' >> beam.ParDo(ParseEvent())
            # Write to BigQuery (streaming inserts)
            | 'Write to BigQuery' >> WriteToBigQuery(
                table='my-project:events.user_actions',
                schema=table_schema,
                write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED,
                # Use Storage Write API for better performance
                method='STORAGE_WRITE_API'
            )
        )


if __name__ == '__main__':
    run_pipeline()
```

### Windowing and Triggering in Beam

```python
from apache_beam import window
from apache_beam.transforms.trigger import AfterWatermark, AfterProcessingTime, AccumulationMode

class ComputeHourlyMetrics(beam.DoFn):
    """Compute metrics per user per window"""

    def process(self, element):
        user_id, events = element

        yield {
            'user_id': user_id,
            'window_start': events[0]['window_start'],
            'window_end': events[0]['window_end'],
            'event_count': len(events),
            'actions': [e['action'] for e in events]
        }


def windowed_pipeline():
    options = PipelineOptions(streaming=True, runner='DataflowRunner')

    with beam.Pipeline(options=options) as pipeline:
        (
            pipeline
            | 'Read' >> ReadFromPubSub(subscription='...')
            | 'Parse' >> beam.ParDo(ParseEvent())
            # Fixed 1-hour windows
            | 'Window' >> beam.WindowInto(
                window.FixedWindows(60 * 60),  # 1 hour in seconds
                trigger=AfterWatermark(
                    # Late data trigger: fire every 5 minutes
                    late=AfterProcessingTime(5 * 60)
                ),
                accumulation_mode=AccumulationMode.DISCARDING,
                allowed_lateness=60 * 60  # Allow 1 hour of late data
            )
            # Group by user
            | 'Key by User' >> beam.Map(lambda e: (e['user_id'], e))
            | 'Group' >> beam.GroupByKey()
            # Compute metrics
            | 'Compute Metrics' >> beam.ParDo(ComputeHourlyMetrics())
            | 'Write' >> WriteToBigQuery(table='...')
        )
```

### Flex Templates for Parameterized Pipelines

Flex Templates allow deploying pipelines with runtime parameters:

```python
# metadata.json
{
  "name": "Events to BigQuery",
  "description": "Stream events from Pub/Sub to BigQuery",
  "parameters": [
    {
      "name": "input_subscription",
      "label": "Pub/Sub subscription",
      "helpText": "Full subscription path",
      "regexes": ["^projects/[^/]+/subscriptions/[^/]+$"]
    },
    {
      "name": "output_table",
      "label": "BigQuery output table",
      "helpText": "Format: project:dataset.table"
    }
  ]
}
```

Deploy and run:

```bash
# Build Flex Template
gcloud dataflow flex-template build gs://my-bucket/templates/events-to-bq.json \
  --image-gcr-path gcr.io/my-project/events-to-bq:latest \
  --sdk-language PYTHON \
  --metadata-file metadata.json

# Run from template
gcloud dataflow flex-template run events-to-bq-job \
  --template-file-gcs-location gs://my-bucket/templates/events-to-bq.json \
  --region us-central1 \
  --parameters input_subscription=projects/my-project/subscriptions/events-sub \
  --parameters output_table=my-project:events.user_actions
```

### Auto-Scaling Behavior

Dataflow auto-scales based on:
- **Pipeline backlog**: Unprocessed elements in Pub/Sub or other sources
- **CPU and memory utilization**: Worker resource usage
- **Throughput**: Elements processed per second

Configure auto-scaling:

```python
options = PipelineOptions(
    autoscaling_algorithm='THROUGHPUT_BASED',  # or 'NONE' to disable
    max_num_workers=20,
    num_workers=2,  # Initial worker count
)
```

### When Dataflow vs Direct Storage Write API

Use **Dataflow** when:
- Complex transformations required (windowing, stateful processing)
- Multiple sources or sinks (Pub/Sub → BigQuery + Cloud Storage)
- Advanced triggering and watermark logic needed
- Cross-region or multi-cloud data movement

Use **Direct Storage Write API** when:
- Simple transformations (filtering, mapping)
- Single source-to-sink pipeline (e.g., Kafka → BigQuery)
- Lower operational overhead preferred (no pipeline management)
- Cost optimization important (Storage Write API is cheaper)

---

Back to [main skill](../SKILL.md)
