## Contents

- [Flink vs Spark Decision](#flink-vs-spark-decision)
- [Apache Flink](#apache-flink)
  - [DataStream API](#datastream-api)
  - [Flink SQL](#flink-sql)
- [Spark Structured Streaming](#spark-structured-streaming)
- [Watermarks and Late Data](#watermarks-and-late-data)
- [State Management](#state-management)
  - [Flink State](#flink-state)
  - [Spark State](#spark-state)

---

# Flink and Spark Structured Streaming

> **Part of:** [event-streaming](../SKILL.md)
> **Purpose:** Framework comparison, DataStream API, Flink SQL, Spark Structured Streaming, watermarks, state management

## Flink vs Spark Decision

| Criterion | Choose Flink | Choose Spark |
|---|---|---|
| Latency | Sub-second required | Seconds acceptable |
| State | Large (GB+), incremental checkpoints | Small-medium |
| ML integration | Not needed | MLlib/MLflow needed |
| Existing infra | Greenfield or streaming-first | Existing Spark/Databricks |
| Processing model | True event-by-event | Micro-batch unified with batch |

| Use Case | Latency | Recommendation |
|---|---|---|
| Real-time fraud | < 100ms | Flink |
| Clickstream analytics | 5-30s | Spark |
| IoT aggregation | < 1s | Flink |
| ETL pipelines | 1-5 min | Spark |
| Log aggregation | 1 min | Spark |

## Apache Flink

### DataStream API

```java
// Kafka source with watermarks
KafkaSource<String> source = KafkaSource.<String>builder()
    .setBootstrapServers("localhost:9092")
    .setTopics("user-events")
    .setGroupId("flink-consumer")
    .setValueOnlyDeserializer(new SimpleStringSchema())
    .build();

WatermarkStrategy<String> wm = WatermarkStrategy
    .<String>forBoundedOutOfOrderness(Duration.ofSeconds(5))
    .withTimestampAssigner((event, ts) -> parseTimestamp(event));

DataStream<String> stream = env.fromSource(source, wm, "Kafka Source");

// Transform -> window -> sink
stream.map(json -> parseEvent(json))
    .filter(e -> e.getEventType().equals("pageview"))
    .keyBy(Event::getUserId)
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .aggregate(new CountAggregator())
    .sinkTo(kafkaSink);
```

**Side outputs** route late/error events to separate streams via `OutputTag`. **Async I/O** enables non-blocking external lookups with `AsyncDataStream.unorderedWait()`.

### Flink SQL

```sql
CREATE TABLE user_events (
    user_id STRING,
    event_type STRING,
    event_time AS TO_TIMESTAMP_LTZ(event_timestamp, 3),
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH ('connector'='kafka', 'topic'='user-events', 'format'='json');

-- Tumbling window aggregation
SELECT user_id,
    TUMBLE_START(event_time, INTERVAL '5' MINUTE) AS window_start,
    COUNT(*) AS event_count
FROM user_events
GROUP BY user_id, TUMBLE(event_time, INTERVAL '5' MINUTE);
```

**Window types in SQL**: `TUMBLE`, `HOP` (sliding), `SESSION`. **Temporal joins**: `LEFT JOIN dim FOR SYSTEM_TIME AS OF e.event_time AS d ON e.key = d.key` for processing-time lookups against versioned tables.

**UDFs**: Register scalar (`ScalarFunction`), table (`TableFunction`), or aggregate (`AggregateFunction`) UDFs with `tableEnv.createTemporarySystemFunction()`.

## Spark Structured Streaming

```python
# Kafka -> windowed aggregation -> Delta Lake
raw = spark.readStream.format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "user-events").load()

events = raw.select(from_json(col("value").cast("string"), schema).alias("d")).select("d.*") \
    .withColumn("event_time", (col("timestamp") / 1000).cast("timestamp"))

windowed = events.withWatermark("event_time", "10 seconds") \
    .groupBy(window(col("event_time"), "5 minutes"), col("user_id")) \
    .agg(count("*").alias("count"))

query = windowed.writeStream.format("delta") \
    .outputMode("append") \
    .option("checkpointLocation", "/checkpoint") \
    .start("/delta/stats")
```

**Output modes**: `append` (new rows only), `complete` (full table), `update` (changed rows). **Triggers**: `processingTime`, `once` (one-time batch), `availableNow` (Spark 3.3+), `continuous` (experimental).

**foreachBatch**: Execute custom logic per micro-batch — write to multiple sinks, run business logic, merge into Delta.

**Session windows** (Spark 3.2+): `session_window(col("event_time"), "30 minutes")`.

## Watermarks and Late Data

**Watermark** = max(event_time) - allowed_lateness. Events older than watermark are considered late.

| Scenario | Late Data % | Recommended Watermark |
|---|---|---|
| IoT (stable network) | < 1% | 5-10 seconds |
| Mobile app events | 5-10% | 5-10 minutes |
| CDC from databases | < 0.1% | 10-30 seconds |
| Log aggregation | 10-20% | 30-60 minutes |

**Flink late data**: Default drops. Use `.sideOutputLateData(tag)` to capture. Use `.allowedLateness(Time.minutes(1))` to keep window state for updates.

**Spark late data**: Dropped after watermark by default. Use `update` or `complete` output mode to receive late updates within watermark threshold.

Handle idle sources with `.withIdleness(Duration.ofMinutes(1))` in Flink to prevent watermark stalls.

## State Management

### Flink State

**Types**: ValueState (single value/key), ListState, MapState, ReducingState. Access via `getRuntimeContext().getState(descriptor)` in `KeyedProcessFunction`.

**Backends**: HashMapStateBackend (heap, fast, limited) vs EmbeddedRocksDBStateBackend (disk, large state, incremental checkpoints).

**Checkpointing**:
```java
env.enableCheckpointing(60000); // 60s interval
env.getCheckpointConfig().setCheckpointingMode(CheckpointingMode.EXACTLY_ONCE);
env.getCheckpointConfig().setCheckpointStorage("s3://bucket/checkpoints");
```

**State TTL**: `StateTtlConfig.newBuilder(Time.hours(24)).setUpdateType(OnCreateAndWrite).build()` — apply to state descriptors. Cleanup strategies: full snapshot, incremental, RocksDB compaction filter.

**Savepoints**: `flink savepoint <jobId> <path>`. Restore: `flink run -s <savepoint-path> job.jar`.

### Spark State

**State store backends**: HDFSBackedStateStore (default, in-memory + HDFS) or RocksDBStateStore (Spark 3.2+, disk-based for large state).

Use `mapGroupsWithState` / `flatMapGroupsWithState` for arbitrary stateful operations with timeout support.

---

Back to [main skill](../SKILL.md)
