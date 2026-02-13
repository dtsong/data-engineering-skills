# CDC Patterns

> **Part of:** [integration-patterns-skill](../SKILL.md)
> **Purpose:** Deep dive into Change Data Capture approaches, tools, and implementation patterns

## Table of Contents

- [CDC Fundamentals](#cdc-fundamentals)
- [Debezium](#debezium)
- [Snowflake Streams](#snowflake-streams)
- [BigQuery CDC Patterns](#bigquery-cdc-patterns)
- [Fivetran & Managed CDC](#fivetran--managed-cdc)
- [CDC Pipeline Architecture](#cdc-pipeline-architecture)

---

## CDC Fundamentals

### What is CDC and Why It Matters

Change Data Capture (CDC) is a design pattern that identifies and captures changes made to data in a database. Instead of periodically reading entire tables, CDC tracks only inserts, updates, and deletes.

**Benefits:**
- **Reduced load** on source systems (no full table scans)
- **Lower latency** (near real-time vs hourly/daily batch)
- **Smaller data transfers** (only changes, not full snapshots)
- **Maintains history** (before/after values for auditing)
- **Enables event-driven architectures** (react to changes immediately)

**Use Cases:**
- Real-time analytics dashboards
- Cache invalidation in applications
- Data synchronization across systems
- Audit trails and compliance
- Event-driven microservices

### Comparison: Log-Based vs Timestamp-Based vs Trigger-Based

| Aspect | Log-Based CDC | Timestamp-Based | Trigger-Based |
|--------|---------------|-----------------|---------------|
| **Mechanism** | Read database transaction logs | Query by timestamp column | Database triggers fire on changes |
| **Performance Impact** | Minimal (async log reading) | Medium (periodic queries) | High (triggers execute inline) |
| **Captures Deletes** | Yes | No (unless soft deletes) | Yes |
| **Schema Changes** | Handled automatically | Manual intervention needed | Trigger code must be updated |
| **Latency** | Near real-time (< 1 second) | Polling interval (1-15 min) | Real-time (< 1 second) |
| **Implementation** | Complex (Debezium, GoldenGate) | Simple (SQL queries) | Medium (trigger DDL) |
| **Database Support** | PostgreSQL, MySQL, SQL Server, Oracle | Any database | Most databases |
| **Ordering Guarantees** | Strong (log sequence) | Weak (relies on timestamp) | Strong (transaction order) |
| **Operational Overhead** | Log retention management | Index on timestamp column | Trigger maintenance, storage |
| **Failure Recovery** | Resume from log position | Risk of missing changes | Complex recovery |

### When CDC vs Full Refresh

**Decision Matrix:**

| Factor | CDC | Full Refresh |
|--------|-----|--------------|
| **Table Size** | Large (> 1M rows) | Small (< 100k rows) |
| **Change Rate** | Low (< 10% daily) | High (> 50% daily) |
| **Update Frequency** | Hourly or more | Daily or less |
| **Delete Detection** | Required | Not required |
| **Source Load** | Must be minimized | Acceptable |
| **Implementation Time** | Weeks | Days |
| **Latency Requirement** | Minutes | Hours/days |
| **History Tracking** | Required | Not required |

**Example Calculation:**

```python
# CDC vs Full Refresh cost-benefit analysis

table_size = 10_000_000  # 10M rows
change_rate = 0.02  # 2% of rows change daily
row_size = 1024  # 1 KB per row
extraction_frequency = 24  # times per day

# Full refresh cost
full_refresh_data = table_size * row_size * extraction_frequency
full_refresh_gb_per_day = full_refresh_data / 1024 / 1024 / 1024
# = 10M * 1KB * 24 / 1GB = 228 GB/day

# CDC cost
cdc_data = (table_size * change_rate * row_size * extraction_frequency) + (table_size * row_size * 1)  # Initial snapshot
cdc_gb_per_day = cdc_data / 1024 / 1024 / 1024
# = (10M * 0.02 * 1KB * 24) + (10M * 1KB * 1) / 1GB = 14.3 GB/day

savings_percent = ((full_refresh_gb_per_day - cdc_gb_per_day) / full_refresh_gb_per_day) * 100
# = 93.7% reduction in data transfer
```

### CDC Event Anatomy

**Typical CDC Event Structure:**

```json
{
  "metadata": {
    "operation": "UPDATE",
    "source": {
      "database": "production",
      "schema": "public",
      "table": "customers",
      "transaction_id": "583748592",
      "lsn": "0/A7C3D8",
      "timestamp": "2026-02-13T10:45:32.123Z"
    },
    "primary_key": {
      "customer_id": 12345
    }
  },
  "before": {
    "customer_id": 12345,
    "email": "old@example.com",
    "tier": "standard",
    "last_updated": "2026-02-10T08:00:00Z"
  },
  "after": {
    "customer_id": 12345,
    "email": "new@example.com",
    "tier": "premium",
    "last_updated": "2026-02-13T10:45:32Z"
  }
}
```

**Operation Types:**
- **CREATE (c):** New record inserted
- **UPDATE (u):** Existing record modified
- **DELETE (d):** Record removed
- **READ (r):** Initial snapshot read
- **TRUNCATE (t):** Table truncated (rare in CDC)

**Key Metadata Fields:**
- **LSN/SCN:** Log Sequence Number (ordering)
- **Transaction ID:** Groups related changes
- **Timestamp:** When change occurred
- **Before/After:** Full row state for updates

---

## Debezium

### Architecture

Debezium is an open-source distributed platform for CDC built on top of Apache Kafka Connect.

**Components:**
- **Source Connectors:** Capture changes from databases
- **Kafka:** Stores change events in topics
- **Kafka Connect:** Runtime framework for connectors
- **Debezium Server:** Standalone mode without Kafka

**Flow:**

```
[PostgreSQL WAL] → [Debezium Connector] → [Kafka Topic: customers]
                                            ↓
                    [Consumer 1: Data Warehouse]
                    [Consumer 2: Cache Invalidator]
                    [Consumer 3: Search Index Updater]
```

### Supported Databases

| Database | Connector Maturity | CDC Method | Notes |
|----------|-------------------|------------|-------|
| PostgreSQL | Stable | Logical replication (pgoutput) | Best support |
| MySQL | Stable | Binlog replication | Requires binlog_format=ROW |
| SQL Server | Stable | SQL Server CDC | Requires CDC enabled |
| Oracle | Stable | LogMiner or XStream | Requires licensing |
| MongoDB | Stable | Replica set oplog | Requires replica set |
| Db2 | Incubating | ASN capture | Limited support |
| Cassandra | Incubating | CommitLog | Experimental |

### Deployment: Kafka Connect Cluster

**Docker Compose Setup:**

```yaml
# docker-compose.yml
version: '3.8'

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.4.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181
      ZOOKEEPER_TICK_TIME: 2000

  kafka:
    image: confluentinc/cp-kafka:7.4.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  connect:
    image: debezium/connect:2.4
    depends_on:
      - kafka
    ports:
      - "8083:8083"
    environment:
      BOOTSTRAP_SERVERS: kafka:29092
      GROUP_ID: 1
      CONFIG_STORAGE_TOPIC: connect_configs
      OFFSET_STORAGE_TOPIC: connect_offsets
      STATUS_STORAGE_TOPIC: connect_status
      KEY_CONVERTER: org.apache.kafka.connect.json.JsonConverter
      VALUE_CONVERTER: org.apache.kafka.connect.json.JsonConverter
      ENABLE_DEBEZIUM_SCRIPTING: "true"

  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: inventory
    command:
      - "postgres"
      - "-c"
      - "wal_level=logical"
      - "-c"
      - "max_replication_slots=4"
      - "-c"
      - "max_wal_senders=4"
```

**Start Services:**

```bash
docker-compose up -d

# Wait for services to be ready
sleep 30

# Verify Kafka Connect is running
curl http://localhost:8083/
# {"version":"3.5.0","commit":"c97b88d5db4de28d"}
```

### Configuration Example

**PostgreSQL Connector Configuration:**

```json
{
  "name": "inventory-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "tasks.max": "1",

    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "postgres",
    "database.dbname": "inventory",
    "database.server.name": "dbserver1",

    "plugin.name": "pgoutput",

    "table.include.list": "public.customers,public.orders",

    "publication.autocreate.mode": "filtered",

    "slot.name": "debezium_inventory",
    "slot.drop.on.stop": "false",

    "heartbeat.interval.ms": "10000",

    "snapshot.mode": "initial",

    "transforms": "route",
    "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
    "transforms.route.regex": "([^.]+)\\.([^.]+)\\.([^.]+)",
    "transforms.route.replacement": "$3"
  }
}
```

**Deploy Connector:**

```bash
curl -X POST http://localhost:8083/connectors \
  -H "Content-Type: application/json" \
  -d @inventory-connector.json

# Check status
curl http://localhost:8083/connectors/inventory-connector/status

# Response:
{
  "name": "inventory-connector",
  "connector": {
    "state": "RUNNING",
    "worker_id": "connect:8083"
  },
  "tasks": [
    {
      "id": 0,
      "state": "RUNNING",
      "worker_id": "connect:8083"
    }
  ]
}
```

### Snapshot Modes

| Mode | Description | When to Use |
|------|-------------|-------------|
| **initial** | Take full snapshot, then stream changes | First time setup, or after data loss |
| **initial_only** | Snapshot and stop (no streaming) | One-time bulk load |
| **schema_only** | Don't snapshot data, only schema | Data already loaded, need CDC only |
| **schema_only_recovery** | Resume from known offset | Connector restart without re-snapshot |
| **never** | Never snapshot, stream only | Table is empty or snapshot not needed |
| **when_needed** | Snapshot if no offset exists | Safe default for production |
| **exported** | Use external snapshot via pg_dump | Minimize lock on source database |
| **custom** | Pluggable snapshot logic | Advanced use cases |

**Configuration:**

```json
{
  "snapshot.mode": "initial",
  "snapshot.max.threads": 4,
  "snapshot.fetch.size": 10000,
  "snapshot.select.statement.overrides": "public.customers=SELECT * FROM public.customers WHERE active = true"
}
```

### Schema Evolution Handling

Debezium automatically handles schema changes:

**Supported Changes:**
- Adding columns (new fields appear in events)
- Dropping columns (fields disappear from events)
- Renaming columns (appears as drop + add)
- Changing column types (captured in schema)

**Example: Column Addition:**

```sql
-- In PostgreSQL
ALTER TABLE customers ADD COLUMN loyalty_points INTEGER DEFAULT 0;
```

**CDC Event After Schema Change:**

```json
{
  "schema": {
    "type": "struct",
    "fields": [
      {"field": "customer_id", "type": "int32"},
      {"field": "email", "type": "string"},
      {"field": "loyalty_points", "type": "int32", "optional": true}
    ],
    "version": 2
  },
  "payload": {
    "after": {
      "customer_id": 12345,
      "email": "user@example.com",
      "loyalty_points": 0
    }
  }
}
```

**Handling in Consumer:**

```python
from confluent_kafka import Consumer

consumer = Consumer({'group.id': 'warehouse-loader'})
consumer.subscribe(['customers'])

def handle_message(msg):
    event = json.loads(msg.value())
    schema_version = event['schema']['version']

    # Handle versioned schemas
    if schema_version == 1:
        # Old schema without loyalty_points
        insert_to_warehouse_v1(event['payload']['after'])
    elif schema_version == 2:
        # New schema with loyalty_points
        insert_to_warehouse_v2(event['payload']['after'])
    else:
        raise ValueError(f"Unknown schema version: {schema_version}")
```

### Transforms: SMT (Single Message Transforms)

**Common Transforms:**

**1. Route Messages to Different Topics:**

```json
{
  "transforms": "route",
  "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
  "transforms.route.regex": "([^.]+)\\.([^.]+)\\.([^.]+)",
  "transforms.route.replacement": "$3"
}
```

Result: `dbserver1.public.customers` → `customers`

**2. Filter Events:**

```json
{
  "transforms": "filter",
  "transforms.filter.type": "io.debezium.transforms.Filter",
  "transforms.filter.language": "jsr223.groovy",
  "transforms.filter.condition": "value.after.active == true"
}
```

**3. Extract New Record State (Flatten):**

```json
{
  "transforms": "unwrap",
  "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
  "transforms.unwrap.drop.tombstones": "false",
  "transforms.unwrap.delete.handling.mode": "rewrite",
  "transforms.unwrap.add.fields": "op,source.ts_ms"
}
```

Before:
```json
{
  "before": {...},
  "after": {"id": 1, "name": "Alice"},
  "op": "u"
}
```

After:
```json
{
  "id": 1,
  "name": "Alice",
  "__op": "u",
  "__source_ts_ms": 1676301832123
}
```

**4. Add Headers:**

```json
{
  "transforms": "addHeader",
  "transforms.addHeader.type": "org.apache.kafka.connect.transforms.InsertHeader",
  "transforms.addHeader.header": "source-database",
  "transforms.addHeader.value.literal": "production"
}
```

### Monitoring: JMX Metrics

**Enable JMX in Kafka Connect:**

```yaml
# docker-compose.yml
connect:
  environment:
    KAFKA_JMX_PORT: 9999
    KAFKA_JMX_HOSTNAME: localhost
```

**Key Metrics:**

```
# Connector metrics
debezium.metrics:type=connector-metrics,context=snapshot,server=dbserver1
  - SnapshotCompleted (boolean)
  - TotalNumberOfEventsSeen (counter)
  - NumberOfEventsFiltered (counter)
  - NumberOfErroneousEvents (counter)

debezium.metrics:type=connector-metrics,context=streaming,server=dbserver1
  - Connected (boolean)
  - MilliSecondsSinceLastEvent (gauge)
  - NumberOfCommittedTransactions (counter)
  - SourceEventPosition (gauge)

# Task metrics
kafka.connect:type=connector-task-metrics,connector=inventory-connector,task=0
  - status (gauge: 0=UNASSIGNED, 1=RUNNING, 2=PAUSED, 3=FAILED)
  - offset-commit-avg-time-ms
  - offset-commit-max-time-ms
```

**Prometheus Exporter:**

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'kafka-connect'
    static_configs:
      - targets: ['localhost:9999']
    metrics_path: /metrics
```

**Grafana Dashboard Query:**

```promql
# Event processing rate
rate(debezium_metrics_TotalNumberOfEventsSeen[5m])

# Lag from database
debezium_metrics_MilliSecondsSinceLastEvent / 1000

# Error rate
rate(debezium_metrics_NumberOfErroneousEvents[5m])
```

### Common Issues

**1. PostgreSQL WAL Retention:**

```sql
-- Check replication slots
SELECT slot_name, active, restart_lsn, confirmed_flush_lsn
FROM pg_replication_slots;

-- Problem: Slot not advancing (connector down)
-- WAL disk fills up → database stops accepting writes

-- Solution 1: Increase WAL retention
ALTER SYSTEM SET wal_keep_size = '10GB';
SELECT pg_reload_conf();

-- Solution 2: Drop inactive slot (if connector permanently gone)
SELECT pg_drop_replication_slot('debezium_inventory');
```

**2. MySQL Binlog Expiration:**

```sql
-- Check binlog retention
SHOW VARIABLES LIKE 'binlog_expire_logs_seconds';
-- Default: 2592000 (30 days)

-- Problem: Connector down longer than retention → data loss

-- Solution: Increase retention
SET GLOBAL binlog_expire_logs_seconds = 604800;  -- 7 days

-- Or set in my.cnf
[mysqld]
binlog_expire_logs_seconds = 604800
```

**3. Connector Stuck in Snapshot:**

```bash
# Check connector status
curl http://localhost:8083/connectors/inventory-connector/status

# Problem: Large table snapshot taking hours/days

# Solution: Split into chunks with custom snapshot
{
  "snapshot.mode": "custom",
  "snapshot.custom.class": "io.debezium.connector.postgresql.snapshot.ExportedSnapshotter",
  "snapshot.max.threads": 8
}

# Or use initial_only mode + separate snapshot process
```

**4. Schema Mismatch:**

```
ERROR: Column 'new_column' does not exist in target schema

# Solution 1: Use schema registry (Avro)
{
  "key.converter": "io.confluent.connect.avro.AvroConverter",
  "key.converter.schema.registry.url": "http://schema-registry:8081",
  "value.converter": "io.confluent.connect.avro.AvroConverter",
  "value.converter.schema.registry.url": "http://schema-registry:8081"
}

# Solution 2: Handle schema evolution in consumer
# (see Schema Evolution Handling section)
```

### Production Checklist

```markdown
## Pre-Production Checklist

### Database Configuration
- [ ] WAL/binlog enabled with correct format
- [ ] Replication user created with minimal privileges
- [ ] Replication slots configured (PostgreSQL)
- [ ] WAL retention set to 3x expected downtime (PostgreSQL)
- [ ] Binlog retention set to 3x expected downtime (MySQL)
- [ ] CDC enabled on required tables (SQL Server)

### Debezium Configuration
- [ ] snapshot.mode set appropriately (initial_only for first run)
- [ ] table.include.list or table.exclude.list configured
- [ ] heartbeat.interval.ms set (recommended: 10000)
- [ ] max.batch.size tuned for throughput
- [ ] max.queue.size tuned for memory
- [ ] slot.drop.on.stop = false (PostgreSQL)
- [ ] tombstones.on.delete = true (for compacted topics)

### Kafka Configuration
- [ ] Topics created with appropriate partitions and replication
- [ ] Retention policy set (time or size-based)
- [ ] Cleanup policy: delete or compact (choose based on use case)
- [ ] min.insync.replicas set for durability

### Monitoring & Alerting
- [ ] JMX metrics exported to monitoring system
- [ ] Alerts on connector failure
- [ ] Alerts on high lag (MilliSecondsSinceLastEvent > threshold)
- [ ] Alerts on error rate spike
- [ ] Dashboard created for key metrics

### Disaster Recovery
- [ ] Connector configuration backed up
- [ ] Offset topics backed up (for point-in-time recovery)
- [ ] Snapshot restoration procedure documented
- [ ] Failover procedure tested

### Testing
- [ ] Full snapshot tested on copy of production data
- [ ] Insert/update/delete operations tested
- [ ] Schema change handled correctly
- [ ] Connector restart recovery tested
- [ ] Data validation: source row count = destination row count
- [ ] Performance tested at peak load
```

---

## Snowflake Streams

### Stream Types

**Standard Stream:**
- Tracks inserts, updates, deletes
- Includes both old and new values for updates
- Most common use case

**Append-Only Stream:**
- Tracks inserts only (ignores updates/deletes)
- More efficient for insert-heavy workloads
- Use when updates/deletes don't matter

**Comparison:**

```sql
-- Standard stream
CREATE OR REPLACE STREAM customers_stream ON TABLE customers;

-- Append-only stream
CREATE OR REPLACE STREAM orders_stream ON TABLE orders
  APPEND_ONLY = TRUE;
```

### METADATA Columns

Snowflake streams provide metadata columns to identify change type:

| Column | Type | Description |
|--------|------|-------------|
| **METADATA$ACTION** | VARCHAR | INSERT, DELETE |
| **METADATA$ISUPDATE** | BOOLEAN | TRUE if row is part of an UPDATE |
| **METADATA$ROW_ID** | VARCHAR | Unique row identifier |

**Understanding Update Representation:**

```sql
-- Original table
SELECT * FROM customers WHERE customer_id = 123;
-- customer_id | name  | email
-- 123         | Alice | alice@old.com

-- Update occurs
UPDATE customers SET email = 'alice@new.com' WHERE customer_id = 123;

-- Stream contains TWO rows for this update:
SELECT *, METADATA$ACTION, METADATA$ISUPDATE
FROM customers_stream
WHERE customer_id = 123;

-- customer_id | name  | email          | METADATA$ACTION | METADATA$ISUPDATE
-- 123         | Alice | alice@old.com  | DELETE          | TRUE
-- 123         | Alice | alice@new.com  | INSERT          | TRUE
```

### Stream + Task Pattern

**Create Stream:**

```sql
CREATE OR REPLACE STREAM raw.sales.orders_stream
ON TABLE raw.sales.orders;
```

**Create Target Table:**

```sql
CREATE OR REPLACE TABLE analytics.sales.orders_fact (
  order_id INT,
  customer_id INT,
  order_date DATE,
  total_amount DECIMAL(10,2),
  status VARCHAR(50),
  loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
  PRIMARY KEY (order_id)
);
```

**Create Processing Task:**

```sql
CREATE OR REPLACE TASK raw.sales.process_orders_task
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '5 MINUTE'
WHEN
  SYSTEM$STREAM_HAS_DATA('raw.sales.orders_stream')
AS
  MERGE INTO analytics.sales.orders_fact AS target
  USING (
    SELECT
      order_id,
      customer_id,
      order_date,
      total_amount,
      status,
      METADATA$ACTION,
      METADATA$ISUPDATE
    FROM raw.sales.orders_stream
  ) AS source
  ON target.order_id = source.order_id
  WHEN MATCHED AND source.METADATA$ACTION = 'DELETE' AND source.METADATA$ISUPDATE = FALSE THEN
    DELETE
  WHEN MATCHED AND source.METADATA$ACTION = 'INSERT' AND source.METADATA$ISUPDATE = TRUE THEN
    UPDATE SET
      customer_id = source.customer_id,
      order_date = source.order_date,
      total_amount = source.total_amount,
      status = source.status,
      loaded_at = CURRENT_TIMESTAMP()
  WHEN NOT MATCHED AND source.METADATA$ACTION = 'INSERT' THEN
    INSERT (order_id, customer_id, order_date, total_amount, status)
    VALUES (source.order_id, source.customer_id, source.order_date,
            source.total_amount, source.status);

-- Enable task
ALTER TASK raw.sales.process_orders_task RESUME;
```

**Verify Task Execution:**

```sql
-- Check task history
SELECT *
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
  TASK_NAME => 'PROCESS_ORDERS_TASK',
  SCHEDULED_TIME_RANGE_START => DATEADD('hour', -1, CURRENT_TIMESTAMP())
))
ORDER BY SCHEDULED_TIME DESC;

-- Check stream offset
SELECT SYSTEM$STREAM_HAS_DATA('raw.sales.orders_stream');
-- Returns TRUE if data available, FALSE if processed

-- Check row count in stream
SELECT COUNT(*) FROM raw.sales.orders_stream;
```

### Stale Stream Handling and Retention

**Stream Staleness:**

Streams become "stale" if the underlying table's data retention period is exceeded before the stream is consumed.

```sql
-- Check data retention period
SHOW TABLES LIKE 'orders';
-- DATA_RETENTION_TIME_IN_DAYS = 1 (default for Standard Edition)

-- Check stream staleness
SHOW STREAMS LIKE 'orders_stream';
-- STALE = FALSE (stream is current)
-- STALE = TRUE (stream is stale and must be recreated)
```

**Handling Stale Streams:**

```sql
-- If stream is stale, recreate it
CREATE OR REPLACE STREAM orders_stream ON TABLE orders;
-- WARNING: This resets the stream, requiring a full reprocess

-- Prevent staleness: consume stream frequently
-- Ensure tasks run at least daily (or within retention period)

-- Increase retention for critical tables
ALTER TABLE orders SET DATA_RETENTION_TIME_IN_DAYS = 7;
-- Requires Enterprise Edition
```

### Multi-Consumer Patterns

Multiple consumers can read from the same stream using stream clones:

```sql
-- Create base stream
CREATE OR REPLACE STREAM orders_stream ON TABLE orders;

-- Consumer 1: Analytics warehouse
CREATE TASK load_to_warehouse
  SCHEDULE = '5 MINUTE'
WHEN SYSTEM$STREAM_HAS_DATA('orders_stream')
AS
  INSERT INTO analytics.orders
  SELECT * FROM orders_stream
  WHERE METADATA$ACTION = 'INSERT';

-- Consumer 2: Real-time cache updater
-- Problem: Both tasks consume from same stream
-- Solution: Clone stream for each consumer

CREATE STREAM orders_stream_analytics CLONE orders_stream;
CREATE STREAM orders_stream_cache CLONE orders_stream;

-- Now each consumer reads from its own stream clone
```

**Better Pattern: Use Multiple Streams:**

```sql
-- Create separate streams on same source table
CREATE STREAM orders_stream_warehouse ON TABLE orders;
CREATE STREAM orders_stream_cache ON TABLE orders;
CREATE STREAM orders_stream_audit ON TABLE orders;

-- Each consumer uses its own stream
-- Streams advance independently
```

### Limitations and Gotchas

**1. No Stream on External Tables:**
```sql
-- This fails:
CREATE STREAM external_data_stream ON TABLE external_data;
-- Error: Streams not supported on external tables

-- Workaround: Copy to native table first
CREATE TASK load_external
  SCHEDULE = '1 HOUR'
AS
  CREATE OR REPLACE TABLE staged_data AS
  SELECT * FROM external_data;

CREATE STREAM staged_data_stream ON TABLE staged_data;
```

**2. No Stream on Views:**
```sql
-- This fails:
CREATE STREAM view_stream ON VIEW customer_view;

-- Workaround: Stream on base table(s)
```

**3. Table Truncate Handling:**
```sql
-- When source table is truncated:
TRUNCATE TABLE orders;

-- Stream shows DELETE for all rows
SELECT COUNT(*) FROM orders_stream WHERE METADATA$ACTION = 'DELETE';
-- Could be millions of rows

-- Optimize: Clear target table directly if full truncate
IF (SELECT COUNT(*) FROM orders = 0) THEN
  TRUNCATE TABLE analytics.orders;
  SELECT * FROM orders_stream;  -- Advance stream without processing
END IF;
```

**4. Time Travel Interaction:**
```sql
-- Stream offset is tied to table's time travel
-- If table is restored to earlier point:
CREATE OR REPLACE TABLE orders AS
  SELECT * FROM orders AT(TIMESTAMP => '2026-02-10 12:00:00'::TIMESTAMP);

-- Stream becomes stale (recreate required)
```

---

## BigQuery CDC Patterns

### BigQuery Change History

BigQuery doesn't have built-in CDC like Snowflake Streams, but provides change tracking for streaming inserts:

**Change History Table:**

```sql
-- When using streaming inserts, BigQuery automatically creates:
-- [table_name]$[20260213]  -- Date-suffixed table for each day

-- Query recent changes
SELECT *
FROM `project.dataset.table$__CHANGES__`
WHERE _CHANGE_TIMESTAMP >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR);
```

**Note:** This feature is limited and not as robust as dedicated CDC solutions.

### Using MAX(BY) or QUALIFY for Latest Record

**Pattern: Deduplicate to Latest Record**

```sql
-- Using MAX(BY) (BigQuery SQL)
SELECT
  customer_id,
  MAX(email BY updated_at) AS latest_email,
  MAX(tier BY updated_at) AS latest_tier,
  MAX(updated_at) AS last_updated
FROM raw_customers
GROUP BY customer_id;
```

```sql
-- Using QUALIFY with ROW_NUMBER
SELECT
  customer_id,
  email,
  tier,
  updated_at
FROM raw_customers
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) = 1;
```

**Incremental Processing Pattern:**

```sql
-- Create staging table with all updates
CREATE OR REPLACE TABLE staging.customers_daily AS
SELECT *
FROM raw.customers
WHERE DATE(updated_at) = CURRENT_DATE();

-- Upsert into production table
MERGE INTO prod.customers AS target
USING (
  SELECT
    customer_id,
    email,
    tier,
    updated_at
  FROM staging.customers_daily
  QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) = 1
) AS source
ON target.customer_id = source.customer_id
WHEN MATCHED AND source.updated_at > target.updated_at THEN
  UPDATE SET
    email = source.email,
    tier = source.tier,
    updated_at = source.updated_at
WHEN NOT MATCHED THEN
  INSERT (customer_id, email, tier, updated_at)
  VALUES (source.customer_id, source.email, source.tier, source.updated_at);
```

### Streaming Buffer Considerations

**Streaming Insert Behavior:**

```python
from google.cloud import bigquery

client = bigquery.Client()

# Stream insert (available immediately for queries)
table_id = "project.dataset.customers"
rows_to_insert = [
    {"customer_id": 1, "email": "alice@example.com", "tier": "premium"},
    {"customer_id": 2, "email": "bob@example.com", "tier": "standard"}
]

errors = client.insert_rows_json(table_id, rows_to_insert)
if not errors:
    print("Rows inserted successfully")
```

**Streaming Buffer Limitations:**

1. **Data not immediately in storage:**
   - Queries against streaming buffer have no time-travel
   - Table decorators ($20260213) don't include streaming buffer
   - EXPORT DATA doesn't include streaming buffer

2. **Querying streaming data:**
```sql
-- This includes streaming buffer
SELECT COUNT(*) FROM `project.dataset.customers`;

-- This does NOT include streaming buffer (uses storage API)
SELECT COUNT(*) FROM `project.dataset.customers`
FOR SYSTEM_TIME AS OF TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR);
```

3. **DML on streamed tables:**
```sql
-- UPDATE/DELETE/MERGE blocked until streaming buffer cleared
-- Error: UPDATE/DELETE DML statements are not yet supported over table project.dataset.customers

-- Workaround: Wait for buffer to flush (90 minutes typical)
-- Or use batch loads instead of streaming inserts
```

### MERGE Statement Patterns

**Basic Upsert:**

```sql
MERGE INTO prod.customers AS target
USING staging.customers_incremental AS source
ON target.customer_id = source.customer_id
WHEN MATCHED THEN
  UPDATE SET
    email = source.email,
    tier = source.tier,
    updated_at = source.updated_at
WHEN NOT MATCHED THEN
  INSERT (customer_id, email, tier, updated_at)
  VALUES (source.customer_id, source.email, source.tier, source.updated_at);
```

**Conditional Update (Only if Newer):**

```sql
MERGE INTO prod.customers AS target
USING staging.customers_incremental AS source
ON target.customer_id = source.customer_id
WHEN MATCHED AND source.updated_at > target.updated_at THEN
  UPDATE SET
    email = source.email,
    tier = source.tier,
    updated_at = source.updated_at
WHEN NOT MATCHED THEN
  INSERT (customer_id, email, tier, updated_at)
  VALUES (source.customer_id, source.email, source.tier, source.updated_at);
```

**Handle Deletes (Soft Delete):**

```sql
MERGE INTO prod.customers AS target
USING (
  SELECT
    customer_id,
    email,
    tier,
    updated_at,
    is_deleted
  FROM staging.customers_incremental
) AS source
ON target.customer_id = source.customer_id
WHEN MATCHED AND source.is_deleted = TRUE THEN
  UPDATE SET
    is_deleted = TRUE,
    deleted_at = CURRENT_TIMESTAMP()
WHEN MATCHED AND source.is_deleted = FALSE THEN
  UPDATE SET
    email = source.email,
    tier = source.tier,
    updated_at = source.updated_at,
    is_deleted = FALSE
WHEN NOT MATCHED AND source.is_deleted = FALSE THEN
  INSERT (customer_id, email, tier, updated_at, is_deleted)
  VALUES (source.customer_id, source.email, source.tier, source.updated_at, FALSE);
```

### CDC with Cloud Datastream

**Cloud Datastream:** Managed CDC service from Google Cloud

**Setup:**

```bash
# 1. Enable Datastream API
gcloud services enable datastream.googleapis.com

# 2. Create connection profile for source (PostgreSQL)
gcloud datastream connection-profiles create source-postgres \
  --location=us-central1 \
  --type=POSTGRESQL \
  --postgresql-hostname=10.0.0.5 \
  --postgresql-port=5432 \
  --postgresql-username=datastream \
  --postgresql-password=secret \
  --postgresql-database=production \
  --display-name="Production PostgreSQL"

# 3. Create connection profile for destination (BigQuery)
gcloud datastream connection-profiles create dest-bigquery \
  --location=us-central1 \
  --type=BIGQUERY \
  --bigquery-project-id=my-project \
  --display-name="BigQuery Destination"

# 4. Create stream
gcloud datastream streams create postgres-to-bigquery \
  --location=us-central1 \
  --display-name="PostgreSQL to BigQuery CDC" \
  --source=source-postgres \
  --destination=dest-bigquery \
  --postgresql-source-config=postgresql-source-config.json \
  --bigquery-destination-config=bigquery-destination-config.json
```

**postgresql-source-config.json:**

```json
{
  "includeObjects": {
    "postgresqlSchemas": [
      {
        "schema": "public",
        "postgresqlTables": [
          {"table": "customers"},
          {"table": "orders"}
        ]
      }
    ]
  },
  "replicationSlot": "datastream_slot",
  "publication": "datastream_publication"
}
```

**BigQuery Destination Structure:**

```
project.dataset.customers
  - customer_id (from source)
  - email (from source)
  - tier (from source)
  - _metadata_timestamp (Datastream added)
  - _metadata_deleted (Datastream added)
  - _metadata_change_type (Datastream added)
```

**Process CDC Changes:**

```sql
-- Materialize latest state from CDC stream
CREATE OR REPLACE TABLE analytics.customers AS
SELECT
  customer_id,
  email,
  tier
FROM (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY customer_id
      ORDER BY _metadata_timestamp DESC
    ) AS rn
  FROM raw_cdc.customers
  WHERE _metadata_deleted = FALSE
)
WHERE rn = 1;
```

---

## Fivetran & Managed CDC

### Fivetran's CDC Connectors

Fivetran provides managed CDC for major databases using log-based replication:

**Supported Databases:**
- PostgreSQL (logical replication)
- MySQL (binlog replication)
- SQL Server (CDC)
- Oracle (LogMiner)
- MongoDB (change streams)

**Setup Process:**

```bash
# 1. Configure source database (PostgreSQL example)
# On source database:
ALTER SYSTEM SET wal_level = 'logical';
ALTER SYSTEM SET max_replication_slots = 10;
SELECT pg_reload_conf();

CREATE PUBLICATION fivetran_publication FOR ALL TABLES;

CREATE USER fivetran_user WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO fivetran_user;
GRANT USAGE ON SCHEMA public TO fivetran_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO fivetran_user;

# 2. Create connector in Fivetran UI
# - Connector: PostgreSQL
# - Host: database.example.com
# - Port: 5432
# - User: fivetran_user
# - Password: secure_password
# - Update Method: LOG-BASED (CDC)
# - Destination: Snowflake / BigQuery / Redshift
```

**Fivetran Configuration:**

```json
{
  "schema": "public",
  "connection": {
    "host": "database.example.com",
    "port": 5432,
    "database": "production",
    "user": "fivetran_user",
    "password": "********"
  },
  "update_method": "LOG_BASED",
  "sync_frequency": 5,
  "schemas": {
    "public": {
      "customers": {
        "enabled": true,
        "sync_mode": "SOFT_DELETE"
      },
      "orders": {
        "enabled": true,
        "sync_mode": "SOFT_DELETE"
      }
    }
  }
}
```

### HVA (High Volume Agent) for On-Prem Databases

**Use Case:** On-premises databases that can't expose ports to internet

**Architecture:**

```
[On-Prem Database] → [HVA Agent (on-prem)] → [Fivetran Cloud] → [Destination]
```

**Installation:**

```bash
# Download HVA agent
wget https://fivetran.com/downloads/hva/hva-linux-x64.tar.gz
tar -xzf hva-linux-x64.tar.gz
cd hva

# Configure
cat > config.json <<EOF
{
  "api_key": "YOUR_FIVETRAN_API_KEY",
  "api_secret": "YOUR_FIVETRAN_API_SECRET",
  "group_id": "YOUR_GROUP_ID",
  "local_data_directory": "/var/fivetran/data"
}
EOF

# Start HVA
./hva start

# Verify connection
./hva status
# Status: Connected to Fivetran Cloud
```

### Incremental Sync Modes

| Mode | Description | Delete Handling | Use Case |
|------|-------------|-----------------|----------|
| **Log-Based CDC** | Read database transaction logs | Captured | Real-time, high-fidelity replication |
| **Key-Based (Append)** | Query by incrementing key (ID, timestamp) | Not captured | Simple tables with append-only data |
| **Key-Based (Update)** | Query by updated_at timestamp | Not captured | Tables with updates but no deletes |
| **Full Refresh** | Copy entire table each sync | Implicit (full replace) | Small tables, no incremental key |

**Configuration:**

```sql
-- Key-based incremental (requires cursor column)
-- Fivetran automatically detects: created_at, updated_at, modified_date

-- Explicitly set cursor column if non-standard name
-- In Fivetran UI: Table Settings → customers → Cursor Column: last_modified_timestamp

-- For append-only:
-- Table Settings → customers → Primary Key: customer_id → Mode: Append
```

### History Mode and Soft Deletes

**Fivetran History Mode:**

When enabled, Fivetran maintains full change history instead of just latest state.

**Standard Mode (Latest State):**

```sql
-- Destination table: customers
SELECT * FROM customers WHERE customer_id = 123;

-- customer_id | email           | tier    | _fivetran_synced
-- 123         | alice@new.com   | premium | 2026-02-13 10:00:00

-- Only latest state visible
```

**History Mode (Full Audit Trail):**

```sql
-- Destination table: customers_history
SELECT * FROM customers_history WHERE customer_id = 123 ORDER BY _fivetran_start;

-- customer_id | email         | tier     | _fivetran_start     | _fivetran_end        | _fivetran_active
-- 123         | alice@old.com | standard | 2025-01-15 08:00:00 | 2026-02-13 10:00:00  | FALSE
-- 123         | alice@new.com | premium  | 2026-02-13 10:00:00 | NULL                 | TRUE

-- Full history with SCD Type 2 pattern
```

**Soft Deletes:**

```sql
-- When source record deleted, Fivetran marks as deleted (doesn't remove)
SELECT * FROM customers WHERE customer_id = 456;

-- customer_id | email         | tier     | _fivetran_deleted | _fivetran_synced
-- 456         | bob@test.com  | standard | TRUE              | 2026-02-13 11:00:00

-- Filter active records in views:
CREATE VIEW active_customers AS
SELECT * FROM customers
WHERE _fivetran_deleted = FALSE OR _fivetran_deleted IS NULL;
```

### Airbyte CDC Comparison

| Feature | Fivetran | Airbyte |
|---------|----------|---------|
| **Ease of Setup** | Excellent (fully managed) | Good (self-hosted or cloud) |
| **CDC Support** | PostgreSQL, MySQL, SQL Server, Oracle, MongoDB | PostgreSQL, MySQL, SQL Server, MongoDB |
| **Cost** | $1-3 per MAR (Monthly Active Row) | Free (open-source) or $250+/mo (cloud) |
| **Maintenance** | Zero (fully managed) | Medium (self-hosted) to Low (cloud) |
| **Customization** | Limited | High (open-source, extensible) |
| **Monitoring** | Built-in dashboard | Requires external setup (Prometheus/Grafana) |
| **Support** | Enterprise support available | Community or paid support |
| **Schema Drift** | Auto-handled | Auto-handled (with notifications) |

**When to Choose:**

- **Fivetran:** Enterprise, need zero maintenance, budget for per-row pricing
- **Airbyte:** Need customization, have engineering resources, cost-sensitive at scale

### Cost Implications: CDC vs Full Refresh

**Fivetran Pricing Example:**

```python
# Monthly Active Row (MAR) pricing

# Scenario 1: Full refresh daily
table_size = 10_000_000  # 10M rows
sync_frequency = 30  # days per month
mar = table_size  # All rows active each sync
cost = mar / 1_000_000 * 2  # $2 per MAR
# = 10M / 1M * $2 = $20/month for this table

# Scenario 2: CDC (only changes)
change_rate = 0.02  # 2% changed daily
daily_changes = table_size * change_rate
mar_cdc = daily_changes * sync_frequency + table_size  # Initial + changes
mar_cdc = (10_000_000 * 0.02 * 30) + 10_000_000  # Initial sync counted once
mar_cdc = 16_000_000
cost_cdc = mar_cdc / 1_000_000 * 2
# = 16M / 1M * $2 = $32/month

# Wait, CDC costs MORE in this example?
# Yes - for small tables with low change rate, full refresh can be cheaper
# CDC wins at scale (large tables, frequent syncs)

# Scenario 3: Large table, hourly syncs
table_size = 100_000_000  # 100M rows
change_rate = 0.01  # 1% changed per hour
hourly_changes = table_size * change_rate
syncs_per_month = 24 * 30

# Full refresh (hourly)
mar_full = table_size * syncs_per_month
# = 100M * 720 = 72 billion (too expensive)

# CDC (only changes)
total_changes = hourly_changes * syncs_per_month
mar_cdc = table_size + total_changes  # Initial + cumulative changes
# = 100M + (1M * 720) = 820M
cost_cdc = 820_000_000 / 1_000_000 * 2
# = 820 * $2 = $1,640/month (expensive but manageable)

# Conclusion: CDC essential for high-frequency, large-table scenarios
```

---

## CDC Pipeline Architecture

### End-to-End Architecture

**Typical Flow:**

```
[Source Database] → [CDC Tool] → [Streaming Platform] → [Warehouse/Lake]
                                         ↓
                                  [Real-time Consumers]
                                  - Cache Invalidation
                                  - Search Index Update
                                  - Event-Driven Services
```

**Example Stack:**

```
PostgreSQL → Debezium → Kafka → Snowflake (via Kafka Connect Sink)
                          ↓
                        Flink (real-time aggregations)
                          ↓
                        Redis (cache updates)
```

**Component Choices:**

| Layer | Options | Considerations |
|-------|---------|----------------|
| **CDC Tool** | Debezium, Fivetran, Datastream, Custom | Managed vs self-hosted, cost, databases |
| **Streaming** | Kafka, Kinesis, Pub/Sub, EventHub | Throughput, ordering, integrations |
| **Processing** | Kafka Streams, Flink, Spark Streaming | Complexity of transformations |
| **Destination** | Snowflake, BigQuery, S3, Redshift | Query patterns, cost, team skills |

### Ordering Guarantees in CDC

**Within a Single Partition/Shard:**

```
PostgreSQL Transaction Log:
  LSN 1000: INSERT customer_id=1
  LSN 1001: UPDATE customer_id=1 SET tier='premium'
  LSN 1002: INSERT order_id=100 FOR customer_id=1

Kafka Topic (single partition):
  Offset 0: INSERT customer_id=1
  Offset 1: UPDATE customer_id=1
  Offset 2: INSERT order_id=100

✓ Ordering preserved within partition
```

**Across Multiple Partitions:**

```
Kafka Topic (partitioned by table):
  Partition 0 (customers):
    Offset 0: INSERT customer_id=1
    Offset 1: UPDATE customer_id=1

  Partition 1 (orders):
    Offset 0: INSERT order_id=100 FOR customer_id=1

✗ No ordering guarantee between partitions
  Order might be processed before customer exists in destination
```

**Solution: Partition by Entity ID:**

```json
// Debezium SMT configuration
{
  "transforms": "extractKey",
  "transforms.extractKey.type": "org.apache.kafka.connect.transforms.ExtractField$Key",
  "transforms.extractKey.field": "customer_id"
}

// Result: All events for customer_id=1 go to same partition
// Ordering preserved for related entities
```

### Handling Schema Drift from Source

**Detection:**

```python
import json
from confluent_kafka import Consumer

schema_registry = {}

def handle_cdc_event(msg):
    event = json.loads(msg.value())
    table_name = event['source']['table']
    schema_version = event['schema']['version']

    # Check if schema changed
    if table_name not in schema_registry:
        schema_registry[table_name] = schema_version
        print(f"New table detected: {table_name}")
    elif schema_registry[table_name] != schema_version:
        old_version = schema_registry[table_name]
        schema_registry[table_name] = schema_version
        print(f"SCHEMA CHANGE: {table_name} v{old_version} → v{schema_version}")

        # Analyze changes
        old_fields = set(get_schema_fields(table_name, old_version))
        new_fields = set(event['schema']['fields'])

        added = new_fields - old_fields
        removed = old_fields - new_fields

        if added:
            print(f"  Added columns: {added}")
        if removed:
            print(f"  Removed columns: {removed}")

        # Send alert
        send_alert(f"Schema change detected in {table_name}")
```

**Handling Strategies:**

1. **Lenient Consumer (Ignore New Columns):**
```python
def insert_to_warehouse(event):
    # Only insert columns that exist in warehouse schema
    warehouse_columns = get_warehouse_schema('customers')
    filtered_data = {
        k: v for k, v in event['after'].items()
        if k in warehouse_columns
    }
    insert_row(filtered_data)
```

2. **Schema Evolution (Add Columns):**
```python
def handle_new_column(table_name, column_name, column_type):
    # Automatically add column to warehouse
    ddl = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};"
    execute_ddl(ddl)
    print(f"Added column {column_name} to {table_name}")
```

3. **Strict Mode (Fail Fast):**
```python
def validate_schema(event):
    expected_schema = load_expected_schema(event['source']['table'])
    actual_schema = event['schema']

    if actual_schema != expected_schema:
        raise SchemaValidationError(
            f"Schema mismatch for {event['source']['table']}"
        )
```

### Backfill Strategies

**Pattern 1: Snapshot + CDC**

```python
# 1. Take initial snapshot (with CDC capturing ongoing changes)
# Debezium automatically does this with snapshot.mode=initial

# 2. Snapshot runs (minutes to hours)
# Meanwhile, CDC captures all changes in Kafka

# 3. When snapshot completes, resume from CDC
# No data loss, no gaps
```

**Pattern 2: Manual Backfill + CDC**

```sql
-- 1. Start CDC (streaming only, no snapshot)
-- Debezium snapshot.mode=schema_only

-- 2. Perform manual bulk load (parallel, faster)
COPY (
  SELECT * FROM customers WHERE created_at < '2026-02-01'
) TO '/data/customers_historical.csv';

-- Load to warehouse via COPY/LOAD command (fast)
COPY INTO analytics.customers
FROM 's3://bucket/customers_historical.csv'
FILE_FORMAT = (TYPE = CSV);

-- 3. CDC catches up on recent changes (from 2026-02-01 onward)
-- Merge CDC events into warehouse
```

**Pattern 3: Partitioned Backfill**

```python
import concurrent.futures
from datetime import datetime, timedelta

def backfill_partition(table, start_date, end_date):
    """Backfill one date partition"""
    query = f"""
        SELECT * FROM {table}
        WHERE created_at >= '{start_date}'
          AND created_at < '{end_date}'
    """
    data = extract_from_source(query)
    load_to_warehouse(table, data)
    print(f"Loaded {table} partition {start_date}")

# Backfill in parallel
start = datetime(2024, 1, 1)
end = datetime(2026, 2, 1)
partitions = []

current = start
while current < end:
    next_date = current + timedelta(days=1)
    partitions.append((current, next_date))
    current = next_date

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [
        executor.submit(backfill_partition, 'customers', start, end)
        for start, end in partitions
    ]
    concurrent.futures.wait(futures)

print("Backfill complete, CDC now handles real-time")
```

### Monitoring: Lag, Row Counts, Schema Changes

**Lag Monitoring:**

```python
from prometheus_client import Gauge
import time

lag_gauge = Gauge('cdc_lag_seconds', 'CDC lag in seconds', ['table'])

def monitor_cdc_lag():
    # For Debezium: Check MilliSecondsSinceLastEvent metric
    # For Fivetran: Query API for last sync time

    while True:
        for table in ['customers', 'orders', 'products']:
            last_event_time = get_last_cdc_event_time(table)
            lag_seconds = (datetime.now() - last_event_time).total_seconds()

            lag_gauge.labels(table=table).set(lag_seconds)

            if lag_seconds > 300:  # 5 minutes
                send_alert(f"CDC lag for {table}: {lag_seconds}s")

        time.sleep(60)
```

**Row Count Validation:**

```sql
-- Compare source vs destination row counts

-- Source (via CDC metadata)
SELECT
  'customers' AS table_name,
  COUNT(*) AS source_count
FROM source_db.customers;

-- Destination
SELECT
  'customers' AS table_name,
  COUNT(*) AS dest_count
FROM analytics.customers
WHERE _fivetran_deleted = FALSE;

-- Reconciliation report
WITH source AS (
  SELECT 'customers' AS table_name, COUNT(*) AS cnt FROM source_db.customers
  UNION ALL
  SELECT 'orders', COUNT(*) FROM source_db.orders
),
destination AS (
  SELECT 'customers' AS table_name, COUNT(*) AS cnt FROM analytics.customers
  UNION ALL
  SELECT 'orders', COUNT(*) FROM analytics.orders
)
SELECT
  s.table_name,
  s.cnt AS source_count,
  d.cnt AS dest_count,
  s.cnt - d.cnt AS difference,
  ROUND((d.cnt::FLOAT / s.cnt) * 100, 2) AS sync_percent
FROM source s
JOIN destination d ON s.table_name = d.table_name
WHERE s.cnt != d.cnt;
```

**Schema Change Detection:**

```sql
-- Log schema versions
CREATE TABLE schema_change_log (
  log_id SERIAL PRIMARY KEY,
  table_name VARCHAR(100),
  schema_version INT,
  change_type VARCHAR(50),  -- 'COLUMN_ADDED', 'COLUMN_REMOVED', 'TYPE_CHANGED'
  column_name VARCHAR(100),
  old_value TEXT,
  new_value TEXT,
  detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Consumer inserts to this table when schema change detected
-- Dashboard queries this table for alerts
SELECT
  table_name,
  COUNT(*) AS change_count,
  MAX(detected_at) AS last_change
FROM schema_change_log
WHERE detected_at >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY table_name
ORDER BY change_count DESC;
```

---

Back to [main skill](../SKILL.md)
