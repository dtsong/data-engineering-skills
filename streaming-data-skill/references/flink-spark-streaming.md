# Flink and Spark Structured Streaming

> **Part of:** [streaming-data-skill](../SKILL.md)
> **Purpose:** Deep dive into Apache Flink and Spark Structured Streaming covering DataStream API, Flink SQL, watermarks, state management, and framework comparison

## Table of Contents

- [Flink vs Spark Streaming Decision](#flink-vs-spark-streaming-decision)
- [Apache Flink DataStream API](#apache-flink-datastream-api)
- [Flink SQL & Table API](#flink-sql--table-api)
- [Spark Structured Streaming](#spark-structured-streaming)
- [Watermarks and Late Data](#watermarks-and-late-data)
- [State Management](#state-management)

---

## Flink vs Spark Streaming Decision

### Comprehensive Comparison

| Feature | Apache Flink | Spark Structured Streaming |
|---------|--------------|---------------------------|
| **Processing Model** | True streaming (event-by-event) | Micro-batch (small batches) |
| **Latency** | Sub-second (milliseconds) | Seconds (batch interval) |
| **Throughput** | Very high | Very high |
| **State Management** | RocksDB, incremental checkpoints | In-memory, HDFS-backed |
| **State Backend** | Heap, RocksDB (embedded) | Heap, RocksDB (Spark 3.2+) |
| **Checkpointing** | Incremental, asynchronous | Batch-based |
| **SQL Support** | Flink SQL (mature) | Spark SQL (mature) |
| **Window Types** | Tumbling, sliding, session, global, custom | Tumbling, sliding, session |
| **Watermarks** | Native, per-partition watermarks | Per-partition watermarks |
| **Late Data** | Side outputs, allowed lateness | Drop or late updates |
| **Exactly-Once** | Yes (transactions, 2PC) | Yes (idempotent sinks) |
| **ML Integration** | FlinkML (limited) | MLlib, MLflow (extensive) |
| **Batch-Stream Unification** | Yes (DataStream + Table API) | Yes (same DataFrame API) |
| **Managed Services** | AWS Kinesis Data Analytics, Confluent Cloud | Databricks, AWS EMR, GCP Dataproc |
| **Deployment** | Standalone, YARN, Kubernetes, Mesos | Standalone, YARN, Kubernetes, Mesos |
| **Community** | Large, streaming-focused | Very large, broader ecosystem |
| **Learning Curve** | Moderate (streaming concepts) | Easy (if familiar with Spark) |
| **Language Support** | Java, Scala, Python (PyFlink) | Scala, Python, Java, R |
| **Ecosystem** | Kafka, Pulsar, JDBC, Elasticsearch | Kafka, Delta Lake, Iceberg, Unity Catalog |

### Decision Criteria

**Choose Flink when:**
- Sub-second latency required (real-time alerts, fraud detection)
- Complex event processing with sophisticated state
- Very high message rates (millions of events/sec)
- Pure streaming workloads
- Need incremental checkpointing for large state
- Building streaming-first applications

**Choose Spark Structured Streaming when:**
- Batch and streaming workloads share code
- Integration with Spark ML pipelines
- Existing Spark/Databricks infrastructure
- Easier learning curve for Spark users
- Need unified analytics (batch + streaming + ML)
- Second-level latency acceptable

**Example Decision Matrix:**

| Use Case | Latency Req | State Size | Recommendation | Reason |
|----------|-------------|------------|----------------|--------|
| Real-time fraud detection | < 100ms | Large (GB) | **Flink** | Low latency, complex state |
| Clickstream analytics | 5-30s | Medium | **Spark** | Batch integration, ML |
| IoT sensor aggregation | < 1s | Large | **Flink** | High throughput, low latency |
| ETL pipelines | 1-5 min | Small | **Spark** | Batch/stream unification |
| Financial trading | < 50ms | Medium | **Flink** | Ultra-low latency |
| Log aggregation | 1 min | Small | **Spark** | Simple, existing infra |

---

## Apache Flink DataStream API

### Execution Environment Setup

**Java:**
```java
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.datastream.DataStream;

public class FlinkJob {
    public static void main(String[] args) throws Exception {
        // Create execution environment
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();

        // Configure checkpointing
        env.enableCheckpointing(60000); // Checkpoint every 60s
        env.getCheckpointConfig().setMinPauseBetweenCheckpoints(30000);
        env.getCheckpointConfig().setCheckpointTimeout(300000);

        // Set parallelism
        env.setParallelism(4);

        // Job logic here...

        // Trigger execution
        env.execute("Flink Streaming Job");
    }
}
```

**Python (PyFlink):**
```python
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.checkpointing_mode import CheckpointingMode

env = StreamExecutionEnvironment.get_execution_environment()

# Enable checkpointing
env.enable_checkpointing(60000)  # 60 seconds
env.get_checkpoint_config().set_checkpointing_mode(CheckpointingMode.EXACTLY_ONCE)

# Set parallelism
env.set_parallelism(4)

# Job logic here...

env.execute("Flink Python Job")
```

### Sources

**Kafka Source (Java):**
```java
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.api.common.serialization.SimpleStringSchema;

KafkaSource<String> source = KafkaSource.<String>builder()
    .setBootstrapServers("localhost:9092")
    .setTopics("user-events")
    .setGroupId("flink-consumer-group")
    .setStartingOffsets(OffsetsInitializer.earliest())
    .setValueOnlyDeserializer(new SimpleStringSchema())
    .build();

DataStream<String> stream = env.fromSource(
    source,
    WatermarkStrategy.noWatermarks(),
    "Kafka Source"
);
```

**File Source:**
```java
import org.apache.flink.connector.file.src.FileSource;
import org.apache.flink.core.fs.Path;
import org.apache.flink.api.common.serialization.SimpleStringEncoder;

FileSource<String> fileSource = FileSource
    .forRecordStreamFormat(new TextLineFormat(), new Path("/data/input"))
    .build();

DataStream<String> stream = env.fromSource(
    fileSource,
    WatermarkStrategy.noWatermarks(),
    "File Source"
);
```

**Custom Source (Python):**
```python
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import SourceFunction
import random
import time

class CustomSource(SourceFunction):
    def __init__(self):
        self.running = True

    def run(self, ctx):
        while self.running:
            event = {"user_id": f"user-{random.randint(1, 100)}",
                    "event_type": "click",
                    "timestamp": int(time.time() * 1000)}
            ctx.collect(str(event))
            time.sleep(0.1)

    def cancel(self):
        self.running = False

env = StreamExecutionEnvironment.get_execution_environment()
stream = env.add_source(CustomSource())
```

### Transformations

**Map, FlatMap, Filter:**
```java
DataStream<Event> events = stream
    .map(json -> parseEvent(json))  // 1-to-1 transformation
    .filter(event -> event.getEventType().equals("click"))  // Filter events
    .flatMap((event, out) -> {  // 1-to-N transformation
        for (String tag : event.getTags()) {
            out.collect(new TaggedEvent(event, tag));
        }
    });
```

**KeyBy (Partitioning):**
```java
// Partition by user_id
KeyedStream<Event, String> keyedStream = events
    .keyBy(event -> event.getUserId());
```

**Reduce (Aggregation):**
```java
DataStream<UserStats> stats = keyedStream
    .reduce((stats1, stats2) -> {
        stats1.setCount(stats1.getCount() + stats2.getCount());
        return stats1;
    });
```

**Window Aggregation:**
```java
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;

DataStream<WindowResult> windowedStats = keyedStream
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .aggregate(new EventCountAggregator());
```

### Complete Flink Job Example

**Kafka → Process → Kafka (Java):**
```java
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.sink.KafkaSink;
import org.apache.flink.connector.kafka.sink.KafkaRecordSerializationSchema;
import org.apache.flink.api.common.serialization.SimpleStringSchema;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import java.time.Duration;

public class UserEventProcessor {
    public static void main(String[] args) throws Exception {
        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.enableCheckpointing(60000);

        // Kafka source
        KafkaSource<String> source = KafkaSource.<String>builder()
            .setBootstrapServers("localhost:9092")
            .setTopics("user-events")
            .setGroupId("flink-processor")
            .setStartingOffsets(OffsetsInitializer.latest())
            .setValueOnlyDeserializer(new SimpleStringSchema())
            .build();

        // Watermark strategy (5 seconds out-of-orderness)
        WatermarkStrategy<String> watermarkStrategy = WatermarkStrategy
            .<String>forBoundedOutOfOrderness(Duration.ofSeconds(5))
            .withTimestampAssigner((event, timestamp) -> parseTimestamp(event));

        // Read from Kafka
        DataStream<String> rawEvents = env.fromSource(source, watermarkStrategy, "Kafka Source");

        // Parse and transform
        DataStream<UserEvent> events = rawEvents
            .map(json -> UserEvent.fromJson(json))
            .filter(event -> event.getEventType().equals("pageview"));

        // Windowed aggregation
        DataStream<String> aggregated = events
            .keyBy(UserEvent::getUserId)
            .window(TumblingEventTimeWindows.of(Time.minutes(5)))
            .aggregate(new PageViewAggregator())
            .map(result -> result.toJson());

        // Kafka sink
        KafkaSink<String> sink = KafkaSink.<String>builder()
            .setBootstrapServers("localhost:9092")
            .setRecordSerializer(KafkaRecordSerializationSchema.builder()
                .setTopic("user-stats")
                .setValueSerializationSchema(new SimpleStringSchema())
                .build())
            .build();

        aggregated.sinkTo(sink);

        env.execute("User Event Processor");
    }

    private static long parseTimestamp(String json) {
        // Extract timestamp from JSON
        return System.currentTimeMillis();
    }
}

// Helper classes
class UserEvent {
    private String userId;
    private String eventType;
    private long timestamp;

    public static UserEvent fromJson(String json) {
        // Parse JSON
        return new UserEvent();
    }

    public String getUserId() { return userId; }
    public String getEventType() { return eventType; }
    public long getTimestamp() { return timestamp; }
}

class PageViewAggregator implements AggregateFunction<UserEvent, UserStats, UserStats> {
    @Override
    public UserStats createAccumulator() {
        return new UserStats();
    }

    @Override
    public UserStats add(UserEvent event, UserStats acc) {
        acc.incrementCount();
        acc.setUserId(event.getUserId());
        return acc;
    }

    @Override
    public UserStats getResult(UserStats acc) {
        return acc;
    }

    @Override
    public UserStats merge(UserStats a, UserStats b) {
        a.setCount(a.getCount() + b.getCount());
        return a;
    }
}

class UserStats {
    private String userId;
    private int count;

    public void incrementCount() { count++; }
    public void setUserId(String userId) { this.userId = userId; }
    public void setCount(int count) { this.count = count; }
    public int getCount() { return count; }

    public String toJson() {
        return String.format("{\"user_id\":\"%s\",\"count\":%d}", userId, count);
    }
}
```

### Keyed vs Non-Keyed Streams

**Keyed Stream** (partitioned by key):
```java
DataStream<Event> stream = ...;

// Partition by key - enables stateful operations
KeyedStream<Event, String> keyed = stream.keyBy(Event::getUserId);

// Stateful operations available
keyed.reduce((e1, e2) -> merge(e1, e2));
keyed.window(TumblingEventTimeWindows.of(Time.minutes(5)));
```

**Non-Keyed Stream** (global parallelism):
```java
// Non-keyed - operations applied globally
DataStream<Event> stream = ...;
stream.windowAll(TumblingEventTimeWindows.of(Time.minutes(5)));
```

### Side Outputs

Route different types of events to different streams.

```java
import org.apache.flink.streaming.api.functions.ProcessFunction;
import org.apache.flink.util.Collector;
import org.apache.flink.util.OutputTag;

// Define output tags
final OutputTag<Event> lateDataTag = new OutputTag<Event>("late-data"){};
final OutputTag<Event> errorTag = new OutputTag<Event>("errors"){};

// Process function with side outputs
DataStream<Event> mainStream = stream
    .process(new ProcessFunction<Event, Event>() {
        @Override
        public void processElement(Event event, Context ctx, Collector<Event> out) {
            try {
                if (event.getTimestamp() < ctx.timerService().currentWatermark()) {
                    // Late data - send to side output
                    ctx.output(lateDataTag, event);
                } else if (event.isValid()) {
                    // Normal processing
                    out.collect(event);
                } else {
                    // Invalid event
                    ctx.output(errorTag, event);
                }
            } catch (Exception e) {
                ctx.output(errorTag, event);
            }
        }
    });

// Access side outputs
DataStream<Event> lateData = mainStream.getSideOutput(lateDataTag);
DataStream<Event> errors = mainStream.getSideOutput(errorTag);

// Process side outputs separately
lateData.sinkTo(lateSink);
errors.sinkTo(errorSink);
```

### Async I/O for External Lookups

Enrich streaming data with external database lookups without blocking.

```java
import org.apache.flink.streaming.api.functions.async.AsyncFunction;
import org.apache.flink.streaming.api.functions.async.ResultFuture;
import org.apache.flink.streaming.api.datastream.AsyncDataStream;
import java.util.concurrent.TimeUnit;

class AsyncDatabaseLookup extends RichAsyncFunction<Event, EnrichedEvent> {
    private transient DatabaseClient client;

    @Override
    public void open(Configuration parameters) {
        client = new DatabaseClient();
    }

    @Override
    public void asyncInvoke(Event event, ResultFuture<EnrichedEvent> resultFuture) {
        // Async lookup
        client.asyncGet(event.getUserId(), new Callback() {
            @Override
            public void onSuccess(UserProfile profile) {
                resultFuture.complete(Collections.singleton(
                    new EnrichedEvent(event, profile)
                ));
            }

            @Override
            public void onFailure(Throwable throwable) {
                resultFuture.completeExceptionally(throwable);
            }
        });
    }

    @Override
    public void close() {
        client.close();
    }
}

// Use async I/O
DataStream<EnrichedEvent> enriched = AsyncDataStream.unorderedWait(
    events,
    new AsyncDatabaseLookup(),
    1000,  // Timeout (ms)
    TimeUnit.MILLISECONDS,
    100    // Max concurrent requests
);
```

---

## Flink SQL & Table API

### Table Environment Setup

**Java:**
```java
import org.apache.flink.table.api.EnvironmentSettings;
import org.apache.flink.table.api.TableEnvironment;
import org.apache.flink.table.api.bridge.java.StreamTableEnvironment;

// Streaming mode
EnvironmentSettings settings = EnvironmentSettings
    .newInstance()
    .inStreamingMode()
    .build();

TableEnvironment tableEnv = TableEnvironment.create(settings);

// Or from StreamExecutionEnvironment
StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
StreamTableEnvironment tableEnv = StreamTableEnvironment.create(env);
```

**Python:**
```python
from pyflink.table import EnvironmentSettings, TableEnvironment

settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
table_env = TableEnvironment.create(settings)
```

### DDL: Create Tables with Connectors

**Kafka Source Table:**
```sql
CREATE TABLE user_events (
    user_id STRING,
    event_type STRING,
    page_url STRING,
    event_timestamp BIGINT,
    event_time AS TO_TIMESTAMP_LTZ(event_timestamp, 3),
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'user-events',
    'properties.bootstrap.servers' = 'localhost:9092',
    'properties.group.id' = 'flink-sql-consumer',
    'scan.startup.mode' = 'latest-offset',
    'format' = 'json',
    'json.fail-on-missing-field' = 'false',
    'json.ignore-parse-errors' = 'true'
);
```

**Filesystem Sink Table (Parquet):**
```sql
CREATE TABLE user_stats_parquet (
    user_id STRING,
    event_count BIGINT,
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3)
) PARTITIONED BY (user_id) WITH (
    'connector' = 'filesystem',
    'path' = 's3://my-bucket/user-stats/',
    'format' = 'parquet',
    'sink.partition-commit.policy.kind' = 'success-file',
    'sink.partition-commit.delay' = '1 min'
);
```

**JDBC Table (PostgreSQL):**
```sql
CREATE TABLE user_profiles (
    user_id STRING,
    username STRING,
    email STRING,
    created_at TIMESTAMP(3),
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'jdbc',
    'url' = 'jdbc:postgresql://localhost:5432/mydb',
    'table-name' = 'users',
    'username' = 'flink',
    'password' = 'secret',
    'driver' = 'org.postgresql.Driver'
);
```

### Windowed Aggregations

**Tumbling Window:**
```sql
-- Count events per user per 5-minute window
INSERT INTO user_stats_parquet
SELECT
    user_id,
    COUNT(*) AS event_count,
    TUMBLE_START(event_time, INTERVAL '5' MINUTE) AS window_start,
    TUMBLE_END(event_time, INTERVAL '5' MINUTE) AS window_end
FROM user_events
GROUP BY
    user_id,
    TUMBLE(event_time, INTERVAL '5' MINUTE);
```

**Hopping Window:**
```sql
-- 10-minute window, advancing every 5 minutes
SELECT
    user_id,
    COUNT(*) AS event_count,
    HOP_START(event_time, INTERVAL '5' MINUTE, INTERVAL '10' MINUTE) AS window_start,
    HOP_END(event_time, INTERVAL '5' MINUTE, INTERVAL '10' MINUTE) AS window_end
FROM user_events
GROUP BY
    user_id,
    HOP(event_time, INTERVAL '5' MINUTE, INTERVAL '10' MINUTE);
```

**Session Window:**
```sql
-- Session window with 30-minute inactivity gap
SELECT
    user_id,
    COUNT(*) AS event_count,
    SESSION_START(event_time, INTERVAL '30' MINUTE) AS session_start,
    SESSION_END(event_time, INTERVAL '30' MINUTE) AS session_end
FROM user_events
GROUP BY
    user_id,
    SESSION(event_time, INTERVAL '30' MINUTE);
```

### Temporal Joins (Lookup Joins)

Join streaming events with versioned dimension tables.

**For Processing-Time Lookup:**
```sql
-- Enrich events with latest user profile
SELECT
    e.user_id,
    e.event_type,
    u.username,
    u.email,
    e.event_time
FROM user_events AS e
LEFT JOIN user_profiles FOR SYSTEM_TIME AS OF e.event_time AS u
    ON e.user_id = u.user_id;
```

**Versioned Table (Temporal Table):**
```sql
-- Create versioned dimension table
CREATE TABLE user_profiles_versioned (
    user_id STRING,
    username STRING,
    email STRING,
    updated_at TIMESTAMP(3),
    WATERMARK FOR updated_at AS updated_at - INTERVAL '1' SECOND,
    PRIMARY KEY (user_id) NOT ENFORCED
) WITH (
    'connector' = 'kafka',
    'topic' = 'user-profiles-cdc',
    'properties.bootstrap.servers' = 'localhost:9092',
    'scan.startup.mode' = 'earliest-offset',
    'format' = 'debezium-json'
);

-- Temporal join with versioned table
SELECT
    e.user_id,
    e.event_type,
    u.username,
    e.event_time
FROM user_events AS e
LEFT JOIN user_profiles_versioned FOR SYSTEM_TIME AS OF e.event_time AS u
    ON e.user_id = u.user_id;
```

### User-Defined Functions (UDFs)

**Scalar UDF (Java):**
```java
import org.apache.flink.table.functions.ScalarFunction;

public class HashFunction extends ScalarFunction {
    public String eval(String input) {
        return Integer.toHexString(input.hashCode());
    }
}

// Register UDF
tableEnv.createTemporarySystemFunction("hash", HashFunction.class);

// Use in SQL
tableEnv.executeSql("SELECT user_id, hash(user_id) AS user_hash FROM user_events");
```

**Table UDF (UDTF):**
```java
import org.apache.flink.table.functions.TableFunction;
import org.apache.flink.types.Row;

public class SplitFunction extends TableFunction<Row> {
    public void eval(String str) {
        for (String s : str.split(",")) {
            collect(Row.of(s));
        }
    }
}

// Register and use
tableEnv.createTemporarySystemFunction("split", SplitFunction.class);

tableEnv.executeSql(
    "SELECT user_id, tag " +
    "FROM user_events, LATERAL TABLE(split(tags)) AS T(tag)"
);
```

**Aggregate UDF:**
```java
import org.apache.flink.table.functions.AggregateFunction;

public class WeightedAvgFunction extends AggregateFunction<Double, WeightedAvgAccumulator> {
    @Override
    public WeightedAvgAccumulator createAccumulator() {
        return new WeightedAvgAccumulator();
    }

    public void accumulate(WeightedAvgAccumulator acc, Double value, Double weight) {
        acc.sum += value * weight;
        acc.weightSum += weight;
    }

    @Override
    public Double getValue(WeightedAvgAccumulator acc) {
        return acc.weightSum == 0 ? null : acc.sum / acc.weightSum;
    }
}

class WeightedAvgAccumulator {
    public double sum = 0;
    public double weightSum = 0;
}
```

### Catalogs (Hive, JDBC)

**Hive Catalog:**
```java
import org.apache.flink.table.catalog.hive.HiveCatalog;

HiveCatalog hive = new HiveCatalog(
    "myhive",                              // Catalog name
    "default",                             // Default database
    "/opt/hive-conf",                      // Hive conf directory
    "3.1.2"                                // Hive version
);

tableEnv.registerCatalog("myhive", hive);
tableEnv.useCatalog("myhive");

// Query Hive tables
tableEnv.executeSql("SELECT * FROM hive_table");
```

**JDBC Catalog:**
```sql
CREATE CATALOG jdbc_catalog WITH (
    'type' = 'jdbc',
    'base-url' = 'jdbc:postgresql://localhost:5432/',
    'default-database' = 'mydb',
    'username' = 'flink',
    'password' = 'secret'
);

USE CATALOG jdbc_catalog;
SHOW TABLES;
```

---

## Spark Structured Streaming

### SparkSession and ReadStream API

**Python (PySpark):**
```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, window, count, from_json
from pyspark.sql.types import StructType, StructField, StringType, LongType

# Create SparkSession
spark = SparkSession.builder \
    .appName("Streaming Job") \
    .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoints") \
    .getOrCreate()

# Define schema
schema = StructType([
    StructField("user_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("page_url", StringType(), True),
    StructField("timestamp", LongType(), True)
])

# Read from Kafka
raw_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "user-events") \
    .option("startingOffsets", "latest") \
    .load()

# Parse JSON
events = raw_stream.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")
```

**Scala:**
```scala
import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._
import org.apache.spark.sql.types._

val spark = SparkSession.builder()
  .appName("Streaming Job")
  .config("spark.sql.streaming.checkpointLocation", "/tmp/checkpoints")
  .getOrCreate()

val schema = StructType(Seq(
  StructField("user_id", StringType, true),
  StructField("event_type", StringType, true),
  StructField("timestamp", LongType, true)
))

val rawStream = spark.readStream
  .format("kafka")
  .option("kafka.bootstrap.servers", "localhost:9092")
  .option("subscribe", "user-events")
  .option("startingOffsets", "latest")
  .load()

val events = rawStream
  .select(from_json(col("value").cast("string"), schema).as("data"))
  .select("data.*")
```

### Sources

**Kafka Source:**
```python
df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "topic1,topic2") \
    .option("startingOffsets", "earliest") \
    .option("failOnDataLoss", "false") \
    .load()
```

**File Source (CSV):**
```python
df = spark.readStream \
    .schema(schema) \
    .option("maxFilesPerTrigger", 100) \
    .csv("/data/input/")
```

**Rate Source (Testing):**
```python
# Generate test data
df = spark.readStream \
    .format("rate") \
    .option("rowsPerSecond", 1000) \
    .load()
```

**Socket Source (Development only):**
```python
df = spark.readStream \
    .format("socket") \
    .option("host", "localhost") \
    .option("port", 9999) \
    .load()
```

### Transformations and Windowing

**Windowed Aggregation with Watermark:**
```python
from pyspark.sql.functions import window, col, count, avg

# Define event time column
events_with_time = events.withColumn(
    "event_time",
    (col("timestamp") / 1000).cast("timestamp")
)

# Watermark for late data (5 seconds)
windowed = events_with_time \
    .withWatermark("event_time", "5 seconds") \
    .groupBy(
        window(col("event_time"), "5 minutes"),
        col("user_id")
    ) \
    .agg(
        count("*").alias("event_count"),
        avg("page_load_time").alias("avg_load_time")
    )
```

**Sliding Window:**
```python
# 10-minute window, sliding every 5 minutes
windowed = events_with_time \
    .withWatermark("event_time", "10 seconds") \
    .groupBy(
        window(col("event_time"), "10 minutes", "5 minutes"),
        col("user_id")
    ) \
    .count()
```

**Session Window (Spark 3.2+):**
```python
from pyspark.sql.functions import session_window

# Session window with 30-minute gap
sessions = events_with_time \
    .withWatermark("event_time", "10 seconds") \
    .groupBy(
        session_window(col("event_time"), "30 minutes"),
        col("user_id")
    ) \
    .count()
```

### Output Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **append** | Only new rows added to result table | Immutable events, time-based aggregations |
| **complete** | Entire result table output | Small result sets, dashboards |
| **update** | Only changed rows output | Large result sets, incremental updates |

```python
# Append mode (only new data)
query = windowed.writeStream \
    .outputMode("append") \
    .format("console") \
    .start()

# Complete mode (entire table)
query = windowed.writeStream \
    .outputMode("complete") \
    .format("console") \
    .start()

# Update mode (changed rows)
query = windowed.writeStream \
    .outputMode("update") \
    .format("console") \
    .start()
```

### Sinks

**Kafka Sink:**
```python
query = windowed \
    .selectExpr("CAST(user_id AS STRING) AS key", "to_json(struct(*)) AS value") \
    .writeStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("topic", "user-stats") \
    .option("checkpointLocation", "/tmp/checkpoint") \
    .start()
```

**Console Sink (Development):**
```python
query = windowed.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", False) \
    .start()
```

**File Sink (Parquet):**
```python
query = windowed.writeStream \
    .format("parquet") \
    .option("path", "/data/output/") \
    .option("checkpointLocation", "/tmp/checkpoint") \
    .partitionBy("user_id") \
    .start()
```

**Delta Lake Sink:**
```python
query = windowed.writeStream \
    .format("delta") \
    .option("path", "/data/delta/user_stats") \
    .option("checkpointLocation", "/tmp/checkpoint") \
    .outputMode("append") \
    .start()
```

**Memory Sink (Testing):**
```python
query = windowed.writeStream \
    .format("memory") \
    .queryName("user_stats_table") \
    .outputMode("complete") \
    .start()

# Query in-memory table
spark.sql("SELECT * FROM user_stats_table").show()
```

### Complete Streaming Job: Kafka → Windowed Aggregation → Delta Lake

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, window, count, avg, from_json, to_json, struct
from pyspark.sql.types import StructType, StructField, StringType, LongType, DoubleType

# Initialize Spark
spark = SparkSession.builder \
    .appName("User Analytics Pipeline") \
    .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
    .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
    .getOrCreate()

# Schema
schema = StructType([
    StructField("user_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("page_url", StringType(), True),
    StructField("page_load_time", DoubleType(), True),
    StructField("timestamp", LongType(), True)
])

# Read from Kafka
raw_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", "localhost:9092") \
    .option("subscribe", "user-events") \
    .option("startingOffsets", "latest") \
    .option("failOnDataLoss", "false") \
    .load()

# Parse and transform
events = raw_stream \
    .select(from_json(col("value").cast("string"), schema).alias("data")) \
    .select("data.*") \
    .withColumn("event_time", (col("timestamp") / 1000).cast("timestamp")) \
    .filter(col("event_type") == "pageview")

# Windowed aggregation
windowed_stats = events \
    .withWatermark("event_time", "10 seconds") \
    .groupBy(
        window(col("event_time"), "5 minutes"),
        col("user_id")
    ) \
    .agg(
        count("*").alias("pageview_count"),
        avg("page_load_time").alias("avg_load_time"),
        count(col("page_url").distinct()).alias("unique_pages")
    ) \
    .select(
        col("user_id"),
        col("window.start").alias("window_start"),
        col("window.end").alias("window_end"),
        col("pageview_count"),
        col("avg_load_time"),
        col("unique_pages")
    )

# Write to Delta Lake
query = windowed_stats.writeStream \
    .format("delta") \
    .outputMode("append") \
    .option("path", "/data/delta/user_pageview_stats") \
    .option("checkpointLocation", "/tmp/checkpoint/user_stats") \
    .start()

# Await termination
query.awaitTermination()
```

### Trigger Types

**Processing Time Trigger:**
```python
# Trigger every 10 seconds
query = df.writeStream \
    .trigger(processingTime="10 seconds") \
    .format("console") \
    .start()
```

**Once Trigger (One-time micro-batch):**
```python
# Process available data once and stop
query = df.writeStream \
    .trigger(once=True) \
    .format("console") \
    .start()
```

**Available-Now Trigger (Spark 3.3+):**
```python
# Process all available data in multiple batches
query = df.writeStream \
    .trigger(availableNow=True) \
    .format("console") \
    .start()
```

**Continuous Trigger (Experimental):**
```python
# Continuous processing with 1-second checkpoint
query = df.writeStream \
    .trigger(continuous="1 second") \
    .format("console") \
    .start()
```

### foreachBatch for Custom Sinks

Execute arbitrary logic on each micro-batch.

```python
def process_batch(batch_df, batch_id):
    print(f"Processing batch {batch_id}")

    # Write to multiple destinations
    batch_df.write \
        .format("delta") \
        .mode("append") \
        .save("/data/delta/events")

    # Write aggregates to PostgreSQL
    aggregates = batch_df.groupBy("user_id").count()
    aggregates.write \
        .format("jdbc") \
        .option("url", "jdbc:postgresql://localhost:5432/mydb") \
        .option("dbtable", "user_event_counts") \
        .option("user", "spark") \
        .option("password", "secret") \
        .mode("append") \
        .save()

    # Custom business logic
    if batch_df.filter(col("event_type") == "purchase").count() > 0:
        send_notification("New purchases detected")

query = events.writeStream \
    .foreachBatch(process_batch) \
    .start()
```

---

## Watermarks and Late Data

### Understanding Watermarks

Watermarks track progress of event time in streaming systems.

**Concept:**
```
Event Time vs Processing Time with Watermark

Processing Time ────────────────────────────────────────►
                │
                │  Events arrive (potentially out of order)
                │
                │  o  o    o        o    o  o
                │  │  │    │        │    │  │
Event Time      │  5  3    7        2    9  6
                │
Watermark ──────┼──────────────────────5────────────►
                │           ▲
                │           │
                │      Current watermark
                │      (events older than 5 considered late)
```

**Watermark = max(event_time) - allowed_lateness**

### Flink Watermark Strategies

**Bounded Out-of-Orderness:**
```java
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.common.eventtime.SerializableTimestampAssigner;
import java.time.Duration;

WatermarkStrategy<Event> watermarkStrategy = WatermarkStrategy
    .<Event>forBoundedOutOfOrderness(Duration.ofSeconds(5))
    .withTimestampAssigner(new SerializableTimestampAssigner<Event>() {
        @Override
        public long extractTimestamp(Event event, long recordTimestamp) {
            return event.getTimestamp();
        }
    });

DataStream<Event> stream = env
    .fromSource(kafkaSource, watermarkStrategy, "Kafka Source");
```

**Custom Watermark Strategy:**
```java
import org.apache.flink.api.common.eventtime.Watermark;
import org.apache.flink.api.common.eventtime.WatermarkGenerator;
import org.apache.flink.api.common.eventtime.WatermarkOutput;

public class CustomWatermarkGenerator implements WatermarkGenerator<Event> {
    private long maxTimestamp = Long.MIN_VALUE;
    private final long outOfOrdernessMs = 5000;

    @Override
    public void onEvent(Event event, long eventTimestamp, WatermarkOutput output) {
        maxTimestamp = Math.max(maxTimestamp, event.getTimestamp());
    }

    @Override
    public void onPeriodicEmit(WatermarkOutput output) {
        // Emit watermark every interval
        output.emitWatermark(new Watermark(maxTimestamp - outOfOrdernessMs));
    }
}

WatermarkStrategy<Event> strategy = WatermarkStrategy
    .forGenerator((ctx) -> new CustomWatermarkGenerator())
    .withTimestampAssigner((event, timestamp) -> event.getTimestamp());
```

**Idle Source Handling:**
```java
WatermarkStrategy<Event> strategy = WatermarkStrategy
    .<Event>forBoundedOutOfOrderness(Duration.ofSeconds(5))
    .withIdleness(Duration.ofMinutes(1))  // Mark idle after 1 min
    .withTimestampAssigner((event, timestamp) -> event.getTimestamp());
```

### Spark withWatermark

```python
from pyspark.sql.functions import col, window

# Define watermark (allow 10 seconds late data)
windowed = events \
    .withWatermark("event_time", "10 seconds") \
    .groupBy(
        window(col("event_time"), "5 minutes"),
        col("user_id")
    ) \
    .count()
```

**Watermark Behavior:**
- Spark tracks max event time seen
- Watermark = max_event_time - threshold
- Windows close when watermark passes window end
- Late data (older than watermark) dropped by default

### Late Data Handling

**Flink: Drop Late Data (Default):**
```java
// Late data automatically dropped after window closes
DataStream<Result> windowed = stream
    .keyBy(Event::getUserId)
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .aggregate(new CountAggregator());
```

**Flink: Side Output for Late Data:**
```java
import org.apache.flink.util.OutputTag;

final OutputTag<Event> lateDataTag = new OutputTag<Event>("late-data"){};

// Collect late data in side output
DataStream<Result> windowed = stream
    .keyBy(Event::getUserId)
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .sideOutputLateData(lateDataTag)  // Capture late data
    .aggregate(new CountAggregator());

// Access late data
DataStream<Event> lateData = windowed.getSideOutput(lateDataTag);

// Process late data separately
lateData.map(event -> {
    System.out.println("Late event: " + event);
    return event;
}).sinkTo(lateSink);
```

**Flink: Allowed Lateness:**
```java
// Allow 1 minute of lateness (update windows for late data)
DataStream<Result> windowed = stream
    .keyBy(Event::getUserId)
    .window(TumblingEventTimeWindows.of(Time.minutes(5)))
    .allowedLateness(Time.minutes(1))  // Keep window state for 1 min after watermark
    .aggregate(new CountAggregator());

// Results may update as late data arrives within allowed lateness period
```

**Spark: Late Data Updates:**
```python
# Spark updates previous windows for late data within watermark threshold
windowed = events \
    .withWatermark("event_time", "10 minutes") \
    .groupBy(
        window(col("event_time"), "5 minutes"),
        col("user_id")
    ) \
    .count()

# Late data within 10 minutes updates previous windows
# Requires "update" or "complete" output mode for updates
```

### Choosing Watermark Bounds

**Tradeoff: Completeness vs Latency**

| Watermark Delay | Completeness | Latency | Use Case |
|-----------------|--------------|---------|----------|
| 1 second | Low (miss late data) | Low (fast results) | Real-time dashboards |
| 1 minute | Medium | Medium | Typical analytics |
| 1 hour | High (most data) | High (delayed results) | Batch-like processing |
| Infinite | 100% (never close) | Infinite | Not practical |

**Decision Matrix:**

| Scenario | Late Data % | Latency Requirement | Recommended Watermark |
|----------|-------------|---------------------|----------------------|
| IoT sensors (stable network) | < 1% | < 5 seconds | 5-10 seconds |
| Mobile app events | 5-10% | 1-5 minutes | 5-10 minutes |
| CDC from databases | < 0.1% | Seconds | 10-30 seconds |
| Log aggregation | 10-20% | Minutes-hours | 30-60 minutes |
| Financial transactions | 0% (must be complete) | Seconds | 5-10 seconds + alerts |

**Example Configuration:**
```python
# Mobile analytics (tolerate some late data for low latency)
windowed = events \
    .withWatermark("event_time", "5 minutes") \
    .groupBy(window(col("event_time"), "10 minutes")) \
    .count()

# Financial reporting (capture all data, higher latency OK)
windowed = events \
    .withWatermark("event_time", "1 hour") \
    .groupBy(window(col("event_time"), "1 hour")) \
    .sum("transaction_amount")
```

---

## State Management

### Flink State Types

**ValueState** (single value per key):
```java
import org.apache.flink.api.common.state.ValueState;
import org.apache.flink.api.common.state.ValueStateDescriptor;
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.util.Collector;

public class CountFunction extends KeyedProcessFunction<String, Event, String> {
    private ValueState<Long> countState;

    @Override
    public void open(Configuration parameters) {
        ValueStateDescriptor<Long> descriptor =
            new ValueStateDescriptor<>("count", Long.class);
        countState = getRuntimeContext().getState(descriptor);
    }

    @Override
    public void processElement(Event event, Context ctx, Collector<String> out) throws Exception {
        Long count = countState.value();
        if (count == null) {
            count = 0L;
        }
        count++;
        countState.update(count);

        out.collect(event.getUserId() + " has " + count + " events");
    }
}
```

**ListState** (list of values per key):
```java
import org.apache.flink.api.common.state.ListState;
import org.apache.flink.api.common.state.ListStateDescriptor;

public class RecentEventsFunction extends KeyedProcessFunction<String, Event, String> {
    private ListState<Event> recentEvents;

    @Override
    public void open(Configuration parameters) {
        ListStateDescriptor<Event> descriptor =
            new ListStateDescriptor<>("recent-events", Event.class);
        recentEvents = getRuntimeContext().getListState(descriptor);
    }

    @Override
    public void processElement(Event event, Context ctx, Collector<String> out) throws Exception {
        // Add to list
        recentEvents.add(event);

        // Iterate over list
        List<Event> events = new ArrayList<>();
        for (Event e : recentEvents.get()) {
            events.add(e);
        }

        // Keep only last 10 events
        if (events.size() > 10) {
            recentEvents.clear();
            for (int i = events.size() - 10; i < events.size(); i++) {
                recentEvents.add(events.get(i));
            }
        }

        out.collect(event.getUserId() + " recent events: " + events.size());
    }
}
```

**MapState** (key-value map per key):
```java
import org.apache.flink.api.common.state.MapState;
import org.apache.flink.api.common.state.MapStateDescriptor;

public class PageViewCountFunction extends KeyedProcessFunction<String, Event, String> {
    private MapState<String, Long> pageViewCounts;

    @Override
    public void open(Configuration parameters) {
        MapStateDescriptor<String, Long> descriptor =
            new MapStateDescriptor<>("page-counts", String.class, Long.class);
        pageViewCounts = getRuntimeContext().getMapState(descriptor);
    }

    @Override
    public void processElement(Event event, Context ctx, Collector<String> out) throws Exception {
        String page = event.getPageUrl();

        Long count = pageViewCounts.get(page);
        if (count == null) {
            count = 0L;
        }
        count++;
        pageViewCounts.put(page, count);

        // Output all page counts
        StringBuilder sb = new StringBuilder();
        for (Map.Entry<String, Long> entry : pageViewCounts.entries()) {
            sb.append(entry.getKey()).append(": ").append(entry.getValue()).append(", ");
        }
        out.collect(event.getUserId() + " page views: " + sb.toString());
    }
}
```

**ReducingState** (aggregated value):
```java
import org.apache.flink.api.common.state.ReducingState;
import org.apache.flink.api.common.state.ReducingStateDescriptor;
import org.apache.flink.api.common.functions.ReduceFunction;

public class SumFunction extends KeyedProcessFunction<String, Event, String> {
    private ReducingState<Long> sumState;

    @Override
    public void open(Configuration parameters) {
        ReducingStateDescriptor<Long> descriptor = new ReducingStateDescriptor<>(
            "sum",
            new ReduceFunction<Long>() {
                @Override
                public Long reduce(Long a, Long b) {
                    return a + b;
                }
            },
            Long.class
        );
        sumState = getRuntimeContext().getReducingState(descriptor);
    }

    @Override
    public void processElement(Event event, Context ctx, Collector<String> out) throws Exception {
        sumState.add(event.getValue());
        out.collect(event.getUserId() + " sum: " + sumState.get());
    }
}
```

### State Backends

**HashMapStateBackend** (heap-based, fast):
```java
import org.apache.flink.runtime.state.hashmap.HashMapStateBackend;

env.setStateBackend(new HashMapStateBackend());

// Checkpoints stored in distributed filesystem
env.getCheckpointConfig().setCheckpointStorage("hdfs:///checkpoints");
```

**EmbeddedRocksDBStateBackend** (disk-based, large state):
```java
import org.apache.flink.contrib.streaming.state.EmbeddedRocksDBStateBackend;

EmbeddedRocksDBStateBackend backend = new EmbeddedRocksDBStateBackend(true);  // Incremental checkpoints
env.setStateBackend(backend);
env.getCheckpointConfig().setCheckpointStorage("s3://my-bucket/checkpoints");
```

**Comparison:**

| Feature | HashMapStateBackend | EmbeddedRocksDBStateBackend |
|---------|-------------------|---------------------------|
| **Storage** | JVM heap | RocksDB (disk) |
| **State Size** | Limited by heap | Limited by disk |
| **Performance** | Faster | Slower (disk I/O) |
| **Checkpoints** | Full snapshots | Incremental available |
| **Use Case** | Small-medium state | Large state (GB-TB) |

### Checkpointing

**Enable Checkpointing:**
```java
import org.apache.flink.streaming.api.CheckpointingMode;

// Checkpoint every 60 seconds
env.enableCheckpointing(60000);

// Exactly-once semantics
env.getCheckpointConfig().setCheckpointingMode(CheckpointingMode.EXACTLY_ONCE);

// Minimum pause between checkpoints
env.getCheckpointConfig().setMinPauseBetweenCheckpoints(30000);

// Checkpoint timeout
env.getCheckpointConfig().setCheckpointTimeout(300000);

// Allow 1 concurrent checkpoint
env.getCheckpointConfig().setMaxConcurrentCheckpoints(1);

// Retain checkpoint on job cancellation
env.getCheckpointConfig().setExternalizedCheckpointCleanup(
    CheckpointConfig.ExternalizedCheckpointCleanup.RETAIN_ON_CANCELLATION
);
```

**Checkpoint Storage:**
```java
// HDFS
env.getCheckpointConfig().setCheckpointStorage("hdfs:///flink-checkpoints");

// S3
env.getCheckpointConfig().setCheckpointStorage("s3://my-bucket/checkpoints");

// Local filesystem (development only)
env.getCheckpointConfig().setCheckpointStorage("file:///tmp/checkpoints");
```

### Savepoints

Savepoints are manual checkpoints for job upgrades/migrations.

**Trigger Savepoint:**
```bash
# Trigger savepoint
flink savepoint <jobId> hdfs:///savepoints

# Output: Savepoint stored in hdfs:///savepoints/savepoint-abc123
```

**Restore from Savepoint:**
```bash
# Start job from savepoint
flink run -s hdfs:///savepoints/savepoint-abc123 my-job.jar

# Allow non-restored state (for job upgrades)
flink run -s hdfs:///savepoints/savepoint-abc123 --allowNonRestoredState my-job.jar
```

**Use Cases:**
- Application upgrades (code changes)
- Cluster migration
- Scaling parallelism
- Bug fixes requiring job restart

### State TTL

Automatically clean up old state.

```java
import org.apache.flink.api.common.state.StateTtlConfig;
import org.apache.flink.api.common.time.Time;

StateTtlConfig ttlConfig = StateTtlConfig
    .newBuilder(Time.hours(24))  // 24-hour TTL
    .setUpdateType(StateTtlConfig.UpdateType.OnCreateAndWrite)  // Update on write
    .setStateVisibility(StateTtlConfig.StateVisibility.NeverReturnExpired)  // Never return expired
    .cleanupFullSnapshot()  // Cleanup on full snapshot
    .build();

ValueStateDescriptor<String> descriptor = new ValueStateDescriptor<>("my-state", String.class);
descriptor.enableTimeToLive(ttlConfig);

ValueState<String> state = getRuntimeContext().getState(descriptor);
```

**TTL Cleanup Strategies:**
- `cleanupFullSnapshot()`: Cleanup during full checkpoint
- `cleanupIncrementally(cleanupSize, runCleanupForEveryRecord)`: Incremental cleanup
- `cleanupInRocksdbCompactFilter()`: RocksDB compaction filter (RocksDB only)

### Incremental Checkpoints with RocksDB

```java
EmbeddedRocksDBStateBackend backend = new EmbeddedRocksDBStateBackend(true);  // Enable incremental
env.setStateBackend(backend);
env.enableCheckpointing(60000);
```

**Benefits:**
- Faster checkpoints (only changed state)
- Lower checkpoint overhead for large state
- Reduced network and storage I/O

**Tradeoff:**
- Slightly more complex recovery
- Requires RocksDB backend

### Spark State Management

**GroupState / GroupStateTimeout:**
```python
from pyspark.sql.streaming import GroupState, GroupStateTimeout
from pyspark.sql.types import StructType, StructField, StringType, LongType

def update_state(key, values, state):
    """
    Update state for each key (user).
    """
    # Get current state
    if state.exists:
        count = state.get
    else:
        count = 0

    # Update state
    for value in values:
        count += 1

    # Update and return
    state.update(count)
    return (key, count)

# Apply stateful operation
stateful_counts = events \
    .groupByKey(lambda event: event["user_id"]) \
    .mapGroupsWithState(
        update_state,
        outputStructType=StructType([
            StructField("user_id", StringType()),
            StructField("count", LongType())
        ]),
        stateStructType=LongType(),
        timeoutConf=GroupStateTimeout.NoTimeout
    )
```

**Arbitrary Stateful Operation (Scala):**
```scala
import org.apache.spark.sql.streaming.{GroupState, GroupStateTimeout}

case class UserEvent(userId: String, eventType: String)
case class UserState(count: Long, lastSeen: Long)
case class UserStats(userId: String, count: Long)

def updateUserState(
    userId: String,
    events: Iterator[UserEvent],
    state: GroupState[UserState]
): UserStats = {

  // Get or create state
  val currentState = if (state.exists) state.get else UserState(0, 0)

  // Update state
  val newCount = currentState.count + events.size
  val newState = UserState(newCount, System.currentTimeMillis())

  // Update state
  state.update(newState)

  // Set timeout (optional)
  state.setTimeoutDuration("1 hour")

  UserStats(userId, newCount)
}

val statefulStream = events
  .groupByKey(_.userId)
  .mapGroupsWithState(GroupStateTimeout.ProcessingTimeTimeout)(updateUserState)
```

**State Store Configuration:**
```python
spark = SparkSession.builder \
    .config("spark.sql.streaming.stateStore.providerClass",
            "org.apache.spark.sql.execution.streaming.state.RocksDBStateStoreProvider") \
    .config("spark.sql.streaming.stateStore.rocksdb.compactOnCommit", "true") \
    .getOrCreate()
```

**State Store Backends:**
- **HDFSBackedStateStore** (default): In-memory with HDFS backup
- **RocksDBStateStore** (Spark 3.2+): Disk-based for large state

---

Back to [main skill](../SKILL.md)
