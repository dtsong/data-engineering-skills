## Contents

- [Warehouse Streaming Landscape](#warehouse-streaming-landscape)
- [Snowpipe Streaming](#snowpipe-streaming)
- [Snowflake Dynamic Tables](#snowflake-dynamic-tables)
- [BigQuery Storage Write API](#bigquery-storage-write-api)
- [BigQuery Materialized Views](#bigquery-materialized-views)
- [Dataflow / Apache Beam](#dataflow--apache-beam)

---

# Warehouse Streaming Ingestion

> **Part of:** [streaming-data-skill](../SKILL.md)
> **Purpose:** Snowpipe Streaming, Dynamic Tables, BigQuery Storage Write API, materialized views, and warehouse-native streaming patterns

## Warehouse Streaming Landscape

| Feature | Snowflake | BigQuery | Databricks |
|---|---|---|---|
| Streaming method | Snowpipe Streaming (SDK) | Storage Write API | Auto Loader + Structured Streaming |
| Latency | Sub-second to seconds | Seconds | Seconds to minutes |
| Exactly-once | Offset tokens per channel | Committed streams | idempotentWrites in Delta |

Use **warehouse-native** when: transforms are simple, consumers are SQL/BI, latency is seconds-minutes, cost favors warehouse credits.

Use **external processing** (Flink/Spark/Beam) when: complex stateful transforms, multi-sink fanout, sub-second latency, advanced windowing/late-data handling.

## Snowpipe Streaming

Low-latency, exactly-once ingestion via Snowflake Ingest SDK. Pushes rows directly (vs file-based Snowpipe which monitors cloud storage).

| Aspect | Snowpipe Streaming | File-Based Snowpipe |
|---|---|---|
| Latency | Sub-second | Minutes |
| Exactly-once | Offset token per channel | File dedup by name |
| Cost | Streaming credits | Warehouse credits |

**Key concepts**: Client (SDK instance), Channel (logical partition with offset tracking), Offset Token (exactly-once marker).

```python
# Snowpipe Streaming producer (simplified)
client = SnowflakeStreamingIngestClient(account=acct, user=usr, private_key=key)
channel = client.open_channel(OpenChannelRequest(
    channel_name="ch1", database="DB", schema="EVENTS", table="RAW"))

response = channel.insert_rows([
    {"EVENT_ID": "e1", "USER_ID": "u1", "ACTION": "click", "METADATA": "{}"}
])
offset = channel.get_latest_committed_offset_token()
```

**Error handling**: Channels can become invalid on schema changes. Implement retry with channel reopening. **Batch size**: 1000-10000 rows per call. Use multiple channels for parallel ingestion.

**Schema**: Use VARIANT columns for flexible evolving event properties. Omitted columns receive NULL.

## Snowflake Dynamic Tables

Declarative incremental materialization. Define target SQL; Snowflake manages refresh to maintain freshness within `TARGET_LAG`.

```sql
-- Bronze -> Silver -> Gold pipeline
CREATE DYNAMIC TABLE SILVER.CLEANED_EVENTS
  TARGET_LAG = '1 minute'
  WAREHOUSE = STREAMING_WH
AS
SELECT EVENT_ID, EVENT_TIME, USER_ID,
    PROPERTIES:product_id::STRING AS PRODUCT_ID,
    PROPERTIES:price::FLOAT AS PRICE
FROM BRONZE.RAW_EVENTS
WHERE EVENT_ID IS NOT NULL;

CREATE DYNAMIC TABLE GOLD.REVENUE_HOURLY
  TARGET_LAG = '5 minutes'
  WAREHOUSE = STREAMING_WH
AS
SELECT DATE_TRUNC('HOUR', EVENT_TIME) AS HOUR,
    PRODUCT_ID, SUM(PRICE) AS REVENUE, COUNT(*) AS TXN_COUNT
FROM SILVER.CLEANED_EVENTS
WHERE EVENT_TYPE = 'purchase'
GROUP BY HOUR, PRODUCT_ID;
```

**Refresh modes**: AUTO (Snowflake decides), FULL, INCREMENTAL. **DOWNSTREAM**: Inherit lag from dependent tables.

| Feature | Dynamic Tables | Streams + Tasks |
|---|---|---|
| Complexity | Single SQL | Multiple objects |
| Scheduling | Automatic (lag-based) | Manual cron |
| Flexibility | SQL only | Full procedural logic |

**Limitations**: No non-deterministic functions, no stored procedures, limited VARIANT flattening in incremental mode.

Use Dynamic Tables for declarative SQL aggregations/joins. Use Streams + Tasks for procedural logic or external integrations. Use dbt incremental for version-controlled, tested transforms.

## BigQuery Storage Write API

High-throughput streaming with exactly-once semantics. Replaces legacy `tabledata.insertAll`.

| Stream Type | Guarantee | Use Case |
|---|---|---|
| Default | At-least-once | High-throughput logs, idempotent writes |
| Committed | Exactly-once (offset tracking) | Financial transactions |
| Buffered | At-least-once (manual commit) | Batching control |

```python
# Committed stream for exactly-once
client = bigquery_storage_v1.BigQueryWriteClient()
stream = client.create_write_stream(
    parent=table_path,
    write_stream=types.WriteStream(type_=types.WriteStream.Type.COMMITTED))

request = types.AppendRowsRequest(write_stream=stream.name, offset=kafka_offset)
# Add proto_rows, then append
response = client.append_rows(iter([request]))
```

**Error handling**: Retry with exponential backoff for `ResourceExhausted`. Recreate stream on `NotFound`. Fail fast on `InvalidArgument` (schema mismatch).

**Batch size**: 1000-10000 rows. Deploy writers in same region as dataset. Reuse `BigQueryWriteClient` instances.

## BigQuery Materialized Views

Pre-computed aggregations with automatic smart refresh over streaming data.

```sql
CREATE MATERIALIZED VIEW events.hourly_actions AS
SELECT TIMESTAMP_TRUNC(timestamp, HOUR) AS hour, action,
    COUNT(*) AS count, COUNT(DISTINCT user_id) AS unique_users
FROM events.user_actions
GROUP BY hour, action;
```

**Limitations**: Aggregate functions only (SUM, COUNT, AVG, MIN, MAX), no JOINs, GROUP BY required, no non-deterministic functions.

| Feature | BQ Materialized Views | Snowflake Dynamic Tables |
|---|---|---|
| Refresh | Automatic (smart tuning) | Explicit lag config |
| JOINs | Not supported | Supported |
| Complexity | Aggregations only | Full SQL |

## Dataflow / Apache Beam

Use Dataflow for complex transforms, multi-sink pipelines, or advanced windowing over GCP sources (Pub/Sub -> BigQuery). Use direct Storage Write API for simple source-to-sink with lower operational overhead.

**Beam model**: PCollection (data), PTransform (operations), Pipeline (graph), Runner (execution engine). Auto-scales based on backlog, CPU, and throughput.

Configure windowing with triggers: `AfterWatermark(late=AfterProcessingTime(5*60))` with `allowed_lateness` for late data handling.

---

Back to [main skill](../SKILL.md)
