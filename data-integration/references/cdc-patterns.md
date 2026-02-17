## Contents

- [CDC Fundamentals](#cdc-fundamentals)
  - [Log-Based vs Timestamp-Based vs Trigger-Based](#log-based-vs-timestamp-based-vs-trigger-based)
  - [CDC vs Full Refresh Decision](#cdc-vs-full-refresh-decision)
- [Debezium](#debezium)
  - [Deployment](#deployment)
  - [Connector Config (PostgreSQL)](#connector-config-postgresql)
  - [Snapshot Modes](#snapshot-modes)
  - [Key SMTs (Single Message Transforms)](#key-smts-single-message-transforms)
  - [Common Issues](#common-issues)
- [Snowflake Streams](#snowflake-streams)
  - [Stream + Task Pattern](#stream--task-pattern)
- [BigQuery CDC](#bigquery-cdc)
- [Fivetran & Managed CDC](#fivetran--managed-cdc)
- [CDC Pipeline Architecture](#cdc-pipeline-architecture)

---

# CDC Patterns

## CDC Fundamentals

CDC tracks inserts, updates, and deletes instead of full table scans. Benefits: reduced source load, lower latency, smaller transfers, maintains before/after history.

### Log-Based vs Timestamp-Based vs Trigger-Based

| Aspect | Log-Based | Timestamp-Based | Trigger-Based |
|--------|-----------|-----------------|---------------|
| Mechanism | Read transaction logs | Query by timestamp | DB triggers |
| Performance impact | Minimal (async) | Medium (queries) | High (inline) |
| Captures deletes | Yes | No (unless soft) | Yes |
| Latency | < 1 second | 1-15 min polling | < 1 second |
| Ordering | Strong (log sequence) | Weak (timestamp) | Strong |

### CDC vs Full Refresh Decision

Use CDC when: table > 1M rows, change rate < 10% daily, need minute-level latency, delete detection required, must minimize source load. Use full refresh when: table < 100k rows, change rate > 50%, daily latency acceptable.

**CDC savings example:** 10M rows at 2% daily change rate, 24x/day extraction: full refresh = ~228 GB/day, CDC = ~14 GB/day (93.7% reduction).

## Debezium

Open-source log-based CDC on Kafka Connect. Supports PostgreSQL (pgoutput), MySQL (binlog), SQL Server (CDC), Oracle (LogMiner), MongoDB (oplog).

### Deployment

```yaml
# Key docker-compose services: zookeeper, kafka, debezium/connect, postgres
# PostgreSQL requires: wal_level=logical, max_replication_slots=4, max_wal_senders=4
```

### Connector Config (PostgreSQL)

```json
{
  "name": "inventory-connector",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres",
    "database.port": "5432",
    "database.user": "postgres",
    "database.dbname": "inventory",
    "table.include.list": "public.customers,public.orders",
    "plugin.name": "pgoutput",
    "slot.name": "debezium_inventory",
    "slot.drop.on.stop": "false",
    "heartbeat.interval.ms": "10000",
    "snapshot.mode": "initial",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState"
  }
}
```

### Snapshot Modes

| Mode | Use When |
|------|----------|
| `initial` | First setup or after data loss |
| `schema_only` | Data already loaded, need CDC only |
| `when_needed` | Safe default for production |
| `never` | Table empty or snapshot unnecessary |

### Key SMTs (Single Message Transforms)

- **RegexRouter** — Route topics: `dbserver1.public.customers` -> `customers`
- **ExtractNewRecordState** — Flatten before/after envelope to just the new record
- **Filter** — Drop events based on conditions (e.g., `value.after.active == true`)

### Common Issues

1. **WAL disk fills up** — Replication slot not advancing while connector is down. Fix: monitor slots, set `wal_keep_size`, drop inactive slots if permanently gone.
2. **Binlog expired** — Connector down longer than retention. Fix: increase `binlog_expire_logs_seconds`.
3. **Stuck in snapshot** — Large table. Fix: increase `snapshot.max.threads`, use `exported` mode.
4. **Schema mismatch** — Use Avro + schema registry, or handle evolution in consumer.

## Snowflake Streams

**Standard stream:** Tracks inserts, updates, deletes. **Append-only:** Inserts only (more efficient).

Updates appear as two rows: DELETE (old) + INSERT (new), both with `METADATA$ISUPDATE = TRUE`.

### Stream + Task Pattern

```sql
CREATE STREAM orders_stream ON TABLE raw.sales.orders;

CREATE TASK process_orders_task
  WAREHOUSE = COMPUTE_WH
  SCHEDULE = '5 MINUTE'
WHEN SYSTEM$STREAM_HAS_DATA('raw.sales.orders_stream')
AS
  MERGE INTO analytics.orders_fact AS target
  USING (SELECT *, METADATA$ACTION, METADATA$ISUPDATE FROM orders_stream) AS source
  ON target.order_id = source.order_id
  WHEN MATCHED AND source.METADATA$ACTION = 'DELETE' AND NOT source.METADATA$ISUPDATE THEN DELETE
  WHEN MATCHED AND source.METADATA$ACTION = 'INSERT' AND source.METADATA$ISUPDATE THEN
    UPDATE SET customer_id = source.customer_id, total_amount = source.total_amount
  WHEN NOT MATCHED AND source.METADATA$ACTION = 'INSERT' THEN
    INSERT (order_id, customer_id, total_amount) VALUES (source.order_id, source.customer_id, source.total_amount);

ALTER TASK process_orders_task RESUME;
```

**Staleness:** Stream becomes stale if table retention period elapses before consumption. Fix: consume frequently, increase `DATA_RETENTION_TIME_IN_DAYS`.

**Multi-consumer:** Create separate streams on same table for each consumer (streams advance independently).

**Limitations:** No streams on external tables or views. Truncate generates DELETE for all rows. Time travel restore makes stream stale.

## BigQuery CDC

No native CDC like Snowflake Streams. Use QUALIFY + ROW_NUMBER for latest-record deduplication:

```sql
SELECT * FROM raw_customers
QUALIFY ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) = 1;
```

MERGE for incremental upsert with conditional update (only if newer). Handle soft deletes via `is_deleted` flag.

**Cloud Datastream:** Managed CDC service. PostgreSQL/MySQL -> BigQuery with auto-added `_metadata_timestamp`, `_metadata_deleted`, `_metadata_change_type` columns.

## Fivetran & Managed CDC

Log-based CDC for PostgreSQL, MySQL, SQL Server, Oracle, MongoDB. Setup: enable WAL/binlog, create replication user, configure in UI.

**Sync modes:** Log-Based CDC (real-time, captures deletes), Key-Based Append (by incrementing key), Key-Based Update (by updated_at), Full Refresh.

**History mode:** SCD Type 2 with `_fivetran_start`, `_fivetran_end`, `_fivetran_active`. **Soft deletes:** `_fivetran_deleted = TRUE` instead of row removal.

**Fivetran vs Airbyte:** Fivetran = zero maintenance, per-MAR pricing. Airbyte = customizable, free OSS or cheaper cloud.

## CDC Pipeline Architecture

Typical: Source DB -> CDC Tool -> Kafka -> Warehouse + real-time consumers.

**Ordering:** Preserved within partition only. Partition by entity ID to keep related events ordered. Use saga pattern for cross-partition coordination.

**Backfill strategies:** (1) Debezium `snapshot.mode=initial` (automatic), (2) Manual bulk load + schema_only CDC for recent changes, (3) Partitioned parallel backfill by date ranges.

**Monitoring:** Track lag (alert if > 5 min), validate source vs destination row counts, log schema version changes.
