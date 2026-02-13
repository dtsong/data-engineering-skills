# Kafka Deep Dive

> **Part of:** [streaming-data-skill](../SKILL.md)
> **Purpose:** Comprehensive Apache Kafka reference covering architecture, configuration, exactly-once semantics, Kafka Connect, ksqlDB, security, and production tuning

## Table of Contents

- [Kafka Architecture](#kafka-architecture)
- [Producer Configuration](#producer-configuration)
- [Consumer Configuration](#consumer-configuration)
- [Exactly-Once Semantics (EOS)](#exactly-once-semantics-eos)
- [Kafka Connect](#kafka-connect)
- [ksqlDB](#ksqldb)
- [Security](#security)
- [Production Tuning](#production-tuning)

---

## Kafka Architecture

### Cluster Topology

Kafka operates as a distributed system of brokers that store and serve data in topics.

```
┌─────────────────────────────────────────────────────────────┐
│                     Kafka Cluster                            │
│                                                               │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐          │
│  │ Broker 1 │      │ Broker 2 │      │ Broker 3 │          │
│  │  Leader  │◄────►│ Follower │◄────►│ Follower │          │
│  │  P0, P2  │      │  P1, P0  │      │  P2, P1  │          │
│  └──────────┘      └──────────┘      └──────────┘          │
│       ▲                 ▲                 ▲                  │
│       │                 │                 │                  │
└───────┼─────────────────┼─────────────────┼──────────────────┘
        │                 │                 │
        └─────────────────┴─────────────────┘
                          │
              ┌───────────┴────────────┐
              │  ZooKeeper / KRaft     │
              │  (Metadata & Leader    │
              │   Election)            │
              └────────────────────────┘
```

### Brokers, Topics, Partitions, Replication

**Brokers** are individual Kafka servers that store data and handle client requests.

**Topics** are logical channels for organizing messages. Each topic is divided into **partitions** for parallelism and scalability.

**Partitions** are ordered, immutable sequences of records. Each partition has:
- A leader broker (handles all reads/writes)
- Zero or more follower replicas (passive copies for fault tolerance)

**Replication factor** determines how many copies of each partition exist across brokers. Common value: 3.

```bash
# Create topic with 6 partitions and replication factor 3
kafka-topics --create \
  --topic user-events \
  --partitions 6 \
  --replication-factor 3 \
  --bootstrap-server localhost:9092
```

### ZooKeeper vs KRaft

| Feature | ZooKeeper | KRaft (Kafka Raft) |
|---------|-----------|-------------------|
| **Architecture** | External dependency | Self-managed metadata quorum |
| **Complexity** | Higher (separate cluster) | Lower (built-in) |
| **Scalability** | Limited (metadata bottleneck) | Higher (up to millions of partitions) |
| **Availability** | GA since 0.8 | Production-ready in Kafka 3.3+ |
| **Migration** | Manual migration required | Native mode |

**Migration Path:**
1. Kafka 3.0-3.2: ZooKeeper required
2. Kafka 3.3+: KRaft production-ready, ZooKeeper optional
3. Kafka 4.0+: ZooKeeper deprecated

Enable KRaft mode:
```properties
# server.properties
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@localhost:9093
listeners=PLAINTEXT://localhost:9092,CONTROLLER://localhost:9093
```

### Partition Leadership and ISR

**In-Sync Replicas (ISR)**: Set of replicas that are fully caught up with the leader.

A replica is in ISR if:
- It has fetched messages within `replica.lag.time.max.ms` (default: 30s)
- It is not more than `replica.lag.max.messages` behind (removed in Kafka 0.9+)

When a leader fails:
1. Controller selects new leader from ISR
2. Followers sync with new leader
3. Client requests automatically routed to new leader

```bash
# Check ISR status
kafka-topics --describe \
  --topic user-events \
  --bootstrap-server localhost:9092

# Output shows Leader and Replicas (ISR)
# Topic: user-events  Partition: 0  Leader: 1  Replicas: 1,2,3  Isr: 1,2,3
```

### Log Segments, Retention, Compaction

Kafka stores partition data as **log segments** on disk.

**Log Segment Structure:**
```
/var/kafka-logs/user-events-0/
  00000000000000000000.log       # Data file
  00000000000000000000.index     # Offset index
  00000000000000000000.timeindex # Timestamp index
  00000000000005000000.log       # Next segment
  00000000000005000000.index
```

**Retention Policies:**
```properties
# Time-based retention (delete logs older than 7 days)
log.retention.hours=168

# Size-based retention (delete when partition exceeds 1GB)
log.retention.bytes=1073741824

# Segment size (roll to new segment after 1GB)
log.segment.bytes=1073741824
```

**Log Compaction** retains only the latest value for each key:

```properties
# Enable compaction
cleanup.policy=compact

# Compaction settings
min.cleanable.dirty.ratio=0.5
segment.ms=604800000
```

Use compaction for:
- Changelog topics (database CDC)
- Configuration/metadata topics
- Key-value snapshots

### Partition Count Selection

**Formula:**
```
partition_count = max(
  throughput_required / partition_throughput,
  max_concurrent_consumers
)
```

**Partition throughput** depends on:
- Producer batch size and compression
- Consumer processing time
- Broker disk I/O

**Example:**
- Required throughput: 100 MB/s
- Single partition throughput: 20 MB/s
- Minimum partitions: 100 / 20 = 5

**Considerations:**
- Too few partitions: Limited parallelism, throughput bottleneck
- Too many partitions: Higher metadata overhead, slower leader election, more file handles

**Recommendation:** Start with 2-3x expected consumer count, monitor, and adjust.

---

## Producer Configuration

### Critical Configuration Parameters

| Parameter | Values | Purpose | Recommendation |
|-----------|--------|---------|----------------|
| `acks` | 0, 1, all | Acknowledgment level | `all` for durability |
| `retries` | 0-MAX_INT | Number of retry attempts | `Integer.MAX_VALUE` |
| `retry.backoff.ms` | milliseconds | Wait between retries | 100 (default) |
| `enable.idempotence` | true/false | Prevent duplicates | `true` for exactly-once |
| `max.in.flight.requests.per.connection` | 1-5 | Pipelined requests | 5 with idempotence |
| `compression.type` | none, gzip, snappy, lz4, zstd | Compression algorithm | `lz4` or `zstd` |
| `batch.size` | bytes | Max batch size | 16384-32768 |
| `linger.ms` | milliseconds | Wait before send | 10-100 for throughput |

### Idempotent Producer Setup

Idempotent producers prevent duplicate messages even with retries.

**Python (confluent-kafka):**
```python
from confluent_kafka import Producer

config = {
    'bootstrap.servers': 'localhost:9092',
    'enable.idempotence': True,  # Enables idempotence
    'acks': 'all',                # Required for idempotence
    'retries': 2147483647,        # Max retries
    'max.in.flight.requests.per.connection': 5
}

producer = Producer(config)

def delivery_report(err, msg):
    if err is not None:
        print(f'Delivery failed: {err}')
    else:
        print(f'Message delivered to {msg.topic()} [{msg.partition()}]')

# Produce with idempotence
producer.produce(
    'user-events',
    key='user-123',
    value='{"action": "login"}',
    callback=delivery_report
)

producer.flush()
```

**Java:**
```java
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("enable.idempotence", true);
props.put("acks", "all");
props.put("retries", Integer.MAX_VALUE);

KafkaProducer<String, String> producer = new KafkaProducer<>(props);

ProducerRecord<String, String> record =
    new ProducerRecord<>("user-events", "user-123", "{\"action\":\"login\"}");

producer.send(record, (metadata, exception) -> {
    if (exception != null) {
        exception.printStackTrace();
    } else {
        System.out.printf("Sent to partition %d offset %d%n",
            metadata.partition(), metadata.offset());
    }
});

producer.close();
```

### Transactional Producer (Exactly-Once)

Transactional producers enable atomic writes across multiple partitions.

```python
from confluent_kafka import Producer

config = {
    'bootstrap.servers': 'localhost:9092',
    'transactional.id': 'user-service-producer-1',  # Unique per instance
    'enable.idempotence': True,
    'acks': 'all'
}

producer = Producer(config)
producer.init_transactions()

try:
    producer.begin_transaction()

    # Produce multiple messages atomically
    producer.produce('user-events', key='user-123', value='{"action": "signup"}')
    producer.produce('user-events', key='user-123', value='{"action": "login"}')
    producer.produce('analytics', key='user-123', value='{"metric": "new_user"}')

    # Commit transaction (all-or-nothing)
    producer.commit_transaction()

except Exception as e:
    producer.abort_transaction()
    raise e
```

**Java:**
```java
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("transactional.id", "user-service-producer-1");
props.put("enable.idempotence", true);

KafkaProducer<String, String> producer = new KafkaProducer<>(props);
producer.initTransactions();

try {
    producer.beginTransaction();
    producer.send(new ProducerRecord<>("user-events", "user-123", "{\"action\":\"signup\"}"));
    producer.send(new ProducerRecord<>("user-events", "user-123", "{\"action\":\"login\"}"));
    producer.commitTransaction();
} catch (Exception e) {
    producer.abortTransaction();
    throw e;
}
```

### Serialization with Avro and Schema Registry

**Avro Schema:**
```json
{
  "type": "record",
  "name": "UserEvent",
  "namespace": "com.example",
  "fields": [
    {"name": "user_id", "type": "string"},
    {"name": "event_type", "type": "string"},
    {"name": "timestamp", "type": "long"}
  ]
}
```

**Python Producer with Avro:**
```python
from confluent_kafka import Producer
from confluent_kafka.serialization import SerializationContext, MessageField
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer

schema_registry_conf = {'url': 'http://localhost:8081'}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

avro_schema = """
{
  "type": "record",
  "name": "UserEvent",
  "fields": [
    {"name": "user_id", "type": "string"},
    {"name": "event_type", "type": "string"},
    {"name": "timestamp", "type": "long"}
  ]
}
"""

avro_serializer = AvroSerializer(
    schema_registry_client,
    avro_schema
)

producer_conf = {'bootstrap.servers': 'localhost:9092'}
producer = Producer(producer_conf)

event = {
    'user_id': 'user-123',
    'event_type': 'login',
    'timestamp': 1643723400000
}

producer.produce(
    topic='user-events',
    key='user-123',
    value=avro_serializer(event, SerializationContext('user-events', MessageField.VALUE))
)

producer.flush()
```

### Batching and Compression

**Compression Comparison:**

| Algorithm | Compression Ratio | CPU Usage | Speed | Use Case |
|-----------|------------------|-----------|-------|----------|
| none | 1.0x | Minimal | Fastest | Low latency, high CPU cost |
| gzip | 3.5x | High | Slow | Storage-optimized |
| snappy | 2.0x | Medium | Fast | Balanced (legacy) |
| lz4 | 2.2x | Low | Very fast | **Recommended default** |
| zstd | 3.0x | Medium | Fast | **Best ratio/speed** |

**Configuration:**
```properties
# Batch multiple records together
batch.size=32768          # 32KB batches
linger.ms=10              # Wait 10ms for batching

# Compress batches
compression.type=lz4      # Fast compression

# Buffer memory
buffer.memory=67108864    # 64MB total buffer
```

**Impact:**
- Higher `batch.size`: Better compression, higher throughput, more latency
- Higher `linger.ms`: More batching, higher throughput, more latency
- Lower values: Lower latency, lower throughput

### Partitioner Strategies

**Default Partitioner (Murmur2):**
```python
# With key: hash(key) % num_partitions
producer.produce('topic', key='user-123', value='data')

# Without key: round-robin or sticky partitioning
producer.produce('topic', value='data')
```

**Custom Partitioner (Java):**
```java
public class RegionPartitioner implements Partitioner {
    @Override
    public int partition(String topic, Object key, byte[] keyBytes,
                        Object value, byte[] valueBytes, Cluster cluster) {
        String region = extractRegion(key.toString());
        int numPartitions = cluster.partitionCountForTopic(topic);

        // Route by region
        switch (region) {
            case "us-east": return 0 % numPartitions;
            case "us-west": return 1 % numPartitions;
            case "eu": return 2 % numPartitions;
            default: return Math.abs(key.hashCode()) % numPartitions;
        }
    }
}

// Configure producer
props.put("partitioner.class", "com.example.RegionPartitioner");
```

### Error Handling

**Delivery Callbacks:**
```python
def delivery_callback(err, msg):
    if err:
        # Retriable errors (handled by producer retries)
        if err.code() == KafkaError._MSG_TIMED_OUT:
            print(f"Timeout, will retry: {err}")

        # Non-retriable errors
        elif err.code() == KafkaError.MSG_SIZE_TOO_LARGE:
            print(f"Message too large: {err}")
            # Log to dead-letter queue

        elif err.code() == KafkaError.UNKNOWN_TOPIC_OR_PART:
            print(f"Topic doesn't exist: {err}")
    else:
        print(f"Success: partition={msg.partition()}, offset={msg.offset()}")

producer.produce('topic', value='data', callback=delivery_callback)
```

---

## Consumer Configuration

### Consumer Groups and Partition Assignment

Consumer groups enable parallel processing with automatic load balancing.

```
Topic: user-events (6 partitions)

Consumer Group: analytics-group
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Consumer 1  │  │ Consumer 2  │  │ Consumer 3  │
│  P0, P1     │  │  P2, P3     │  │  P4, P5     │
└─────────────┘  └─────────────┘  └─────────────┘

Each partition assigned to exactly one consumer in the group.
```

**Assignment Strategies:**
- **RangeAssignor** (default): Assigns partitions by topic range
- **RoundRobinAssignor**: Distributes partitions evenly across consumers
- **StickyAssignor**: Minimizes partition movement during rebalance
- **CooperativeStickyAssignor**: Incremental rebalancing (Kafka 2.4+)

### Critical Configuration Parameters

| Parameter | Values | Purpose | Recommendation |
|-----------|--------|---------|----------------|
| `group.id` | string | Consumer group identifier | Required for coordination |
| `auto.offset.reset` | earliest, latest, none | Starting position for new group | `latest` for new data |
| `enable.auto.commit` | true/false | Automatic offset commit | `false` for manual control |
| `auto.commit.interval.ms` | milliseconds | Auto-commit frequency | 5000 (default) |
| `max.poll.records` | 1-10000 | Records per poll | 500 (default) |
| `max.poll.interval.ms` | milliseconds | Max time between polls | 300000 (5 min) |
| `session.timeout.ms` | milliseconds | Failure detection timeout | 10000-45000 |
| `heartbeat.interval.ms` | milliseconds | Heartbeat frequency | 3000 (1/3 session) |

### Manual Commit Patterns

**Synchronous Commit (Python):**
```python
from confluent_kafka import Consumer, KafkaError

config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'analytics-group',
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False  # Manual commits
}

consumer = Consumer(config)
consumer.subscribe(['user-events'])

try:
    while True:
        msg = consumer.poll(timeout=1.0)

        if msg is None:
            continue
        if msg.error():
            print(f"Error: {msg.error()}")
            continue

        # Process message
        print(f"Received: {msg.value().decode('utf-8')}")
        process_message(msg.value())

        # Commit offset synchronously
        consumer.commit(asynchronous=False)

except KeyboardInterrupt:
    pass
finally:
    consumer.close()
```

**Asynchronous Commit (Java):**
```java
Properties props = new Properties();
props.put("bootstrap.servers", "localhost:9092");
props.put("group.id", "analytics-group");
props.put("enable.auto.commit", "false");

KafkaConsumer<String, String> consumer = new KafkaConsumer<>(props);
consumer.subscribe(Arrays.asList("user-events"));

try {
    while (true) {
        ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(1000));

        for (ConsumerRecord<String, String> record : records) {
            processMessage(record.value());
        }

        // Async commit with callback
        consumer.commitAsync((offsets, exception) -> {
            if (exception != null) {
                System.err.println("Commit failed: " + exception.getMessage());
            }
        });
    }
} finally {
    // Sync commit on shutdown for reliability
    consumer.commitSync();
    consumer.close();
}
```

**Batch Commit Pattern:**
```python
batch_size = 100
messages = []

while True:
    msg = consumer.poll(timeout=1.0)

    if msg and not msg.error():
        messages.append(msg)

        if len(messages) >= batch_size:
            # Process batch
            process_batch(messages)

            # Commit after successful batch processing
            consumer.commit(asynchronous=False)
            messages = []
```

### Rebalancing Strategies

**Eager Rebalancing** (default until Kafka 2.3):
1. Stop all consumers
2. Revoke all partitions
3. Reassign partitions
4. Resume consumption

**Cooperative (Incremental) Rebalancing** (Kafka 2.4+):
1. Identify partitions to move
2. Revoke only those partitions
3. Other partitions continue processing
4. Assign revoked partitions to new consumers

```python
config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'analytics-group',
    'partition.assignment.strategy': 'cooperative-sticky'  # Incremental rebalancing
}
```

### Static Membership

Static membership prevents unnecessary rebalances during brief consumer restarts.

```python
config = {
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'analytics-group',
    'group.instance.id': 'consumer-1',  # Static member ID
    'session.timeout.ms': 45000         # Longer timeout for restarts
}

# Consumer restarts within session.timeout.ms keep their partitions
```

**Benefits:**
- No rebalance on planned restarts (deployments)
- Faster recovery
- Reduced partition movement

**Use when:**
- Frequent rolling deployments
- Stateful consumers with local caches

### Consumer Lag Monitoring

**Consumer lag** = latest offset - committed offset

```bash
# Check lag with kafka-consumer-groups
kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group analytics-group \
  --describe

# Output:
# GROUP           TOPIC       PARTITION  CURRENT-OFFSET  LOG-END-OFFSET  LAG
# analytics-group user-events 0          1000            1500            500
# analytics-group user-events 1          2000            2100            100
```

**Programmatic Monitoring (Python):**
```python
from confluent_kafka.admin import AdminClient

admin = AdminClient({'bootstrap.servers': 'localhost:9092'})

# Get consumer group offsets
group_offsets = admin.list_consumer_group_offsets('analytics-group')

# Compare with high water marks
for partition, offset in group_offsets.result().items():
    high_water_mark = consumer.get_watermark_offsets(partition)[1]
    lag = high_water_mark - offset.offset
    print(f"Partition {partition.partition}: lag={lag}")
```

### Graceful Shutdown

```python
import signal
import sys

running = True

def signal_handler(sig, frame):
    global running
    print("Shutting down gracefully...")
    running = False

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

consumer = Consumer(config)
consumer.subscribe(['user-events'])

try:
    while running:
        msg = consumer.poll(timeout=1.0)
        if msg and not msg.error():
            process_message(msg.value())
            consumer.commit(asynchronous=False)
finally:
    # Final commit before closing
    consumer.commit()
    consumer.close()
    sys.exit(0)
```

### Error Handling

**Deserialization Errors:**
```python
from confluent_kafka import Consumer, KafkaError
import json

def consume_with_error_handling():
    consumer = Consumer(config)
    consumer.subscribe(['user-events'])

    while True:
        msg = consumer.poll(timeout=1.0)

        if msg is None:
            continue

        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue  # End of partition
            else:
                print(f"Consumer error: {msg.error()}")
                continue

        try:
            # Attempt deserialization
            data = json.loads(msg.value().decode('utf-8'))
            process_message(data)
            consumer.commit()

        except json.JSONDecodeError as e:
            # Poison pill - log and skip
            print(f"Invalid JSON at offset {msg.offset()}: {e}")
            send_to_dead_letter_queue(msg)
            consumer.commit()  # Commit to move past bad message

        except Exception as e:
            # Processing error - may want to retry
            print(f"Processing error: {e}")
            # Don't commit - will retry on next poll
```

---

## Exactly-Once Semantics (EOS)

### Three Guarantee Levels

| Level | Description | Implementation | Use Cases |
|-------|-------------|----------------|-----------|
| **At-Most-Once** | Messages may be lost, never duplicated | `acks=0`, no retries | Metrics, logs (lossy OK) |
| **At-Least-Once** | Messages never lost, may duplicate | `acks=all`, retries, idempotent consumer | Most streaming pipelines |
| **Exactly-Once** | Messages neither lost nor duplicated | Transactional producer + consumer | Financial transactions, billing |

### Idempotent Producer

Prevents duplicate messages from producer retries using Producer ID (PID) and sequence numbers.

**How it works:**
1. Broker assigns unique PID to each producer
2. Producer attaches sequence number to each message
3. Broker detects and drops duplicate sequence numbers

```python
config = {
    'bootstrap.servers': 'localhost:9092',
    'enable.idempotence': True,  # Automatically sets:
                                  # - acks=all
                                  # - max.in.flight.requests.per.connection=5
                                  # - retries=Integer.MAX_VALUE
}

producer = Producer(config)

# Duplicates automatically prevented on retry
for i in range(1000):
    producer.produce('topic', value=f'message-{i}')

producer.flush()
```

**Guarantees:**
- No duplicates within a single producer session
- Ordering preserved per partition
- Duplicates possible after producer restart (new PID)

### Transactional Producer + Consumer

End-to-end exactly-once requires transactional semantics.

**Producer Side:**
```python
config = {
    'bootstrap.servers': 'localhost:9092',
    'transactional.id': 'transformer-service-1',  # Must be unique and stable
    'enable.idempotence': True
}

producer = Producer(config)
producer.init_transactions()

consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'transformer-group',
    'enable.auto.commit': False,
    'isolation.level': 'read_committed'  # Only read committed transactions
})

consumer.subscribe(['input-topic'])

while True:
    msg = consumer.poll(timeout=1.0)
    if msg and not msg.error():
        try:
            producer.begin_transaction()

            # Transform and produce
            transformed = transform(msg.value())
            producer.produce('output-topic', value=transformed)

            # Include consumer offset in transaction
            producer.send_offsets_to_transaction(
                consumer.position(consumer.assignment()),
                consumer.consumer_group_metadata()
            )

            producer.commit_transaction()

        except Exception as e:
            producer.abort_transaction()
            raise e
```

**Java Example:**
```java
Properties producerProps = new Properties();
producerProps.put("bootstrap.servers", "localhost:9092");
producerProps.put("transactional.id", "transformer-service-1");

KafkaProducer<String, String> producer = new KafkaProducer<>(producerProps);
producer.initTransactions();

Properties consumerProps = new Properties();
consumerProps.put("bootstrap.servers", "localhost:9092");
consumerProps.put("group.id", "transformer-group");
consumerProps.put("isolation.level", "read_committed");
consumerProps.put("enable.auto.commit", "false");

KafkaConsumer<String, String> consumer = new KafkaConsumer<>(consumerProps);
consumer.subscribe(Arrays.asList("input-topic"));

while (true) {
    ConsumerRecords<String, String> records = consumer.poll(Duration.ofMillis(1000));

    if (!records.isEmpty()) {
        producer.beginTransaction();

        try {
            for (ConsumerRecord<String, String> record : records) {
                String transformed = transform(record.value());
                producer.send(new ProducerRecord<>("output-topic", transformed));
            }

            // Commit offsets as part of transaction
            producer.sendOffsetsToTransaction(
                getOffsets(records),
                consumer.groupMetadata()
            );

            producer.commitTransaction();
        } catch (Exception e) {
            producer.abortTransaction();
            throw e;
        }
    }
}
```

### Exactly-Once in Kafka Streams

```java
Properties props = new Properties();
props.put(StreamsConfig.APPLICATION_ID_CONFIG, "word-count-app");
props.put(StreamsConfig.BOOTSTRAP_SERVERS_CONFIG, "localhost:9092");
props.put(StreamsConfig.PROCESSING_GUARANTEE_CONFIG, "exactly_once_v2");  // EOS

StreamsBuilder builder = new StreamsBuilder();

builder.stream("input-topic")
    .flatMapValues(value -> Arrays.asList(value.toLowerCase().split("\\W+")))
    .groupBy((key, word) -> word)
    .count()
    .toStream()
    .to("output-topic");

KafkaStreams streams = new KafkaStreams(builder.build(), props);
streams.start();
```

**Processing guarantee options:**
- `at_least_once` (default): Duplicates possible
- `exactly_once_v2` (Kafka 2.6+): Transactional processing

### End-to-End Exactly-Once

**Complete Pipeline:**
```
Source System → Kafka Producer (transactional) →
Kafka Topic →
Kafka Consumer (read_committed) →
Processing →
Kafka Producer (transactional) →
Sink Topic →
Sink Consumer (idempotent writes) →
Target System
```

**Requirements:**
1. Idempotent producer OR transactional producer
2. Transactional consumer-producer loop
3. Idempotent sink writes (upserts, not inserts)

### When Exactly-Once is NOT Needed

Skip EOS overhead when:
- **Idempotent sinks**: Database upserts with unique keys
- **Metrics/monitoring**: Approximate counts acceptable
- **Lossy processing**: Sampling, statistics
- **External deduplication**: Downstream system handles duplicates

### Performance Impact

**Latency Impact:**
- Idempotent producer: < 5% overhead
- Transactional producer: 10-30% overhead (commit latency)

**Throughput Impact:**
- Minimal with proper batching
- Transaction commits are batched

**Tuning:**
```properties
# Reduce transaction overhead
transaction.timeout.ms=60000          # Longer transactions
linger.ms=100                         # Batch more before commit
batch.size=32768                      # Larger batches
compression.type=lz4                  # Compress batches
```

**When to use At-Least-Once instead:**
- Latency-sensitive applications (< 10ms p99)
- Very high throughput requirements (> 1M msg/s)
- Idempotent downstream processing available

---

## Kafka Connect

### Architecture Overview

Kafka Connect provides a framework for streaming data between Kafka and external systems.

**Source Connectors**: External System → Kafka
**Sink Connectors**: Kafka → External System

### Standalone vs Distributed Mode

| Feature | Standalone | Distributed |
|---------|-----------|-------------|
| **Scalability** | Single process | Multi-worker cluster |
| **Fault Tolerance** | None | Automatic failover |
| **Configuration** | File-based | REST API |
| **Use Case** | Development, testing | Production |

**Start Standalone:**
```bash
connect-standalone \
  /etc/kafka/connect-standalone.properties \
  /etc/kafka/connector1.properties
```

**Start Distributed:**
```bash
connect-distributed /etc/kafka/connect-distributed.properties
```

### Popular Connectors

#### Debezium PostgreSQL Source Connector

Captures database changes (CDC) and streams to Kafka.

```json
{
  "name": "postgres-source",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "postgres.example.com",
    "database.port": "5432",
    "database.user": "debezium",
    "database.password": "secret",
    "database.dbname": "production",
    "database.server.name": "prod-db",
    "table.include.list": "public.users,public.orders",
    "plugin.name": "pgoutput",
    "publication.name": "debezium_pub",
    "slot.name": "debezium_slot",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter",
    "tasks.max": "1"
  }
}
```

**Output Topics:**
- `prod-db.public.users`: User table changes
- `prod-db.public.orders`: Order table changes

#### JDBC Source Connector

Incrementally loads data from relational databases.

```json
{
  "name": "jdbc-source",
  "config": {
    "connector.class": "io.confluent.connect.jdbc.JdbcSourceConnector",
    "connection.url": "jdbc:postgresql://postgres:5432/production",
    "connection.user": "connect",
    "connection.password": "secret",
    "mode": "incrementing",
    "incrementing.column.name": "id",
    "topic.prefix": "jdbc-",
    "table.whitelist": "users,orders",
    "poll.interval.ms": "60000",
    "batch.max.rows": "1000",
    "tasks.max": "3"
  }
}
```

**Modes:**
- `incrementing`: Uses auto-increment ID column
- `timestamp`: Uses timestamp column
- `timestamp+incrementing`: Combines both
- `bulk`: Full table scan (not recommended)

#### S3 Sink Connector with Parquet

```json
{
  "name": "s3-sink-parquet",
  "config": {
    "connector.class": "io.confluent.connect.s3.S3SinkConnector",
    "topics": "user-events,orders",
    "s3.bucket.name": "my-data-lake",
    "s3.region": "us-east-1",
    "s3.part.size": "5242880",
    "flush.size": "10000",
    "rotate.interval.ms": "3600000",
    "storage.class": "io.confluent.connect.s3.storage.S3Storage",
    "format.class": "io.confluent.connect.s3.format.parquet.ParquetFormat",
    "parquet.codec": "snappy",
    "partitioner.class": "io.confluent.connect.storage.partitioner.TimeBasedPartitioner",
    "path.format": "'year'=YYYY/'month'=MM/'day'=dd",
    "partition.duration.ms": "3600000",
    "locale": "en-US",
    "timezone": "UTC",
    "schema.compatibility": "NONE",
    "tasks.max": "3"
  }
}
```

**Output Structure:**
```
s3://my-data-lake/topics/user-events/year=2026/month=02/day=13/
  user-events+0+0000000000+0000010000.snappy.parquet
  user-events+1+0000000000+0000010000.snappy.parquet
```

#### BigQuery Sink Connector

```json
{
  "name": "bigquery-sink",
  "config": {
    "connector.class": "com.wepay.kafka.connect.bigquery.BigQuerySinkConnector",
    "topics": "user-events",
    "project": "my-gcp-project",
    "defaultDataset": "analytics",
    "keyfile": "/path/to/service-account-key.json",
    "autoCreateTables": "true",
    "autoUpdateSchemas": "true",
    "sanitizeTopics": "true",
    "allowNewBigQueryFields": "true",
    "allowBigQueryRequiredFieldRelaxation": "true",
    "upsertEnabled": "true",
    "deleteEnabled": "false",
    "kafkaKeyFieldName": "_key",
    "tasks.max": "1"
  }
}
```

#### Snowflake Sink Connector

```json
{
  "name": "snowflake-sink",
  "config": {
    "connector.class": "com.snowflake.kafka.connector.SnowflakeSinkConnector",
    "topics": "orders",
    "snowflake.url.name": "https://xy12345.snowflakecomputing.com",
    "snowflake.user.name": "kafka_connect",
    "snowflake.private.key": "<private_key>",
    "snowflake.database.name": "ANALYTICS",
    "snowflake.schema.name": "PUBLIC",
    "buffer.count.records": "10000",
    "buffer.flush.time": "60",
    "buffer.size.bytes": "5000000",
    "snowflake.topic2table.map": "orders:ORDERS_TABLE",
    "tasks.max": "2"
  }
}
```

#### Elasticsearch Sink Connector

```json
{
  "name": "elasticsearch-sink",
  "config": {
    "connector.class": "io.confluent.connect.elasticsearch.ElasticsearchSinkConnector",
    "topics": "user-events",
    "connection.url": "https://elasticsearch:9200",
    "connection.username": "elastic",
    "connection.password": "secret",
    "type.name": "_doc",
    "key.ignore": "false",
    "schema.ignore": "true",
    "behavior.on.null.values": "delete",
    "transforms": "addTimestamp",
    "transforms.addTimestamp.type": "org.apache.kafka.connect.transforms.InsertField$Value",
    "transforms.addTimestamp.timestamp.field": "ingestion_time",
    "tasks.max": "2"
  }
}
```

### Single Message Transforms (SMTs)

**Route Messages by Header:**
```json
{
  "transforms": "route",
  "transforms.route.type": "org.apache.kafka.connect.transforms.RegexRouter",
  "transforms.route.regex": ".*",
  "transforms.route.replacement": "prefix-$0"
}
```

**Mask Sensitive Fields:**
```json
{
  "transforms": "maskPII",
  "transforms.maskPII.type": "org.apache.kafka.connect.transforms.MaskField$Value",
  "transforms.maskPII.fields": "ssn,credit_card"
}
```

**Add Timestamp:**
```json
{
  "transforms": "insertTimestamp",
  "transforms.insertTimestamp.type": "org.apache.kafka.connect.transforms.InsertField$Value",
  "transforms.insertTimestamp.timestamp.field": "processed_at"
}
```

**Filter Records:**
```json
{
  "transforms": "filter",
  "transforms.filter.type": "org.apache.kafka.connect.transforms.Filter",
  "transforms.filter.condition": "$[?(@.status == 'active')]"
}
```

### Converters

**Avro Converter:**
```json
{
  "key.converter": "io.confluent.connect.avro.AvroConverter",
  "key.converter.schema.registry.url": "http://schema-registry:8081",
  "value.converter": "io.confluent.connect.avro.AvroConverter",
  "value.converter.schema.registry.url": "http://schema-registry:8081"
}
```

**JSON Converter:**
```json
{
  "key.converter": "org.apache.kafka.connect.json.JsonConverter",
  "key.converter.schemas.enable": "false",
  "value.converter": "org.apache.kafka.connect.json.JsonConverter",
  "value.converter.schemas.enable": "true"
}
```

**Protobuf Converter:**
```json
{
  "key.converter": "io.confluent.connect.protobuf.ProtobufConverter",
  "key.converter.schema.registry.url": "http://schema-registry:8081",
  "value.converter": "io.confluent.connect.protobuf.ProtobufConverter",
  "value.converter.schema.registry.url": "http://schema-registry:8081"
}
```

### Dead Letter Queue

Handle failed records without stopping the connector.

```json
{
  "errors.tolerance": "all",
  "errors.deadletterqueue.topic.name": "dlq-connector-errors",
  "errors.deadletterqueue.topic.replication.factor": "3",
  "errors.deadletterqueue.context.headers.enable": "true",
  "errors.log.enable": "true",
  "errors.log.include.messages": "true"
}
```

**DLQ Message Headers:**
- `__connect.errors.topic`: Original topic
- `__connect.errors.partition`: Original partition
- `__connect.errors.offset`: Original offset
- `__connect.errors.exception.class.name`: Exception class
- `__connect.errors.exception.message`: Error message

### Monitoring Connect Workers

**REST API Endpoints:**
```bash
# List connectors
curl http://localhost:8083/connectors

# Connector status
curl http://localhost:8083/connectors/postgres-source/status

# Connector tasks
curl http://localhost:8083/connectors/postgres-source/tasks

# Restart connector
curl -X POST http://localhost:8083/connectors/postgres-source/restart

# Pause connector
curl -X PUT http://localhost:8083/connectors/postgres-source/pause

# Resume connector
curl -X PUT http://localhost:8083/connectors/postgres-source/resume
```

**Key Metrics:**
- `kafka.connect:type=connector-metrics,connector=<name>`: Connector-level metrics
- `kafka.connect:type=task-metrics,connector=<name>,task=<id>`: Task-level metrics
- `kafka.connect:type=connect-worker-metrics`: Worker-level metrics

---

## ksqlDB

### Streams vs Tables

**Streams**: Unbounded sequence of events (append-only log)
**Tables**: Current state (changelog with upserts)

| Feature | Stream | Table |
|---------|--------|-------|
| **Represents** | Events/facts | Current state |
| **Updates** | Append-only | Upsert (by key) |
| **Query** | Push queries | Pull + push queries |
| **Example** | Click events | User profiles |

### Creating Streams and Tables

**Create Stream from Kafka Topic:**
```sql
CREATE STREAM user_events (
  user_id VARCHAR KEY,
  event_type VARCHAR,
  page_url VARCHAR,
  timestamp BIGINT
) WITH (
  KAFKA_TOPIC='user-events',
  VALUE_FORMAT='JSON',
  TIMESTAMP='timestamp',
  PARTITIONS=6,
  REPLICAS=3
);
```

**Create Table from Kafka Topic:**
```sql
CREATE TABLE users (
  user_id VARCHAR PRIMARY KEY,
  username VARCHAR,
  email VARCHAR,
  created_at BIGINT
) WITH (
  KAFKA_TOPIC='users',
  VALUE_FORMAT='AVRO',
  PARTITIONS=6,
  REPLICAS=3
);
```

**Create Stream from Stream (Derived):**
```sql
CREATE STREAM pageviews AS
  SELECT
    user_id,
    page_url,
    TIMESTAMPTOSTRING(timestamp, 'yyyy-MM-dd HH:mm:ss') AS event_time
  FROM user_events
  WHERE event_type = 'pageview'
  EMIT CHANGES;
```

### Windowed Aggregations

**Tumbling Window (Non-overlapping):**
```sql
CREATE TABLE pageviews_per_minute AS
  SELECT
    user_id,
    COUNT(*) AS view_count,
    WINDOWSTART AS window_start,
    WINDOWEND AS window_end
  FROM user_events
  WINDOW TUMBLING (SIZE 1 MINUTE)
  GROUP BY user_id
  EMIT CHANGES;
```

**Hopping Window (Overlapping):**
```sql
CREATE TABLE pageviews_5min_1min_hop AS
  SELECT
    user_id,
    COUNT(*) AS view_count,
    WINDOWSTART,
    WINDOWEND
  FROM user_events
  WINDOW HOPPING (SIZE 5 MINUTES, ADVANCE BY 1 MINUTE)
  GROUP BY user_id
  EMIT CHANGES;
```

**Session Window (Activity-based):**
```sql
CREATE TABLE user_sessions AS
  SELECT
    user_id,
    COUNT(*) AS event_count,
    WINDOWSTART AS session_start,
    WINDOWEND AS session_end
  FROM user_events
  WINDOW SESSION (30 MINUTES)  -- Session ends after 30 min inactivity
  GROUP BY user_id
  EMIT CHANGES;
```

### Pull Queries vs Push Queries

**Pull Query** (query current state):
```sql
-- Get current count for a specific user
SELECT view_count
FROM pageviews_per_minute
WHERE user_id = 'user-123'
  AND WINDOWSTART = 1643723400000;
```

**Push Query** (continuous stream):
```sql
-- Subscribe to all updates
SELECT user_id, view_count, WINDOWSTART
FROM pageviews_per_minute
EMIT CHANGES;
```

### Materialized Views

ksqlDB automatically materializes table state for pull queries.

```sql
CREATE TABLE user_stats AS
  SELECT
    user_id,
    COUNT_DISTINCT(page_url) AS unique_pages,
    COUNT(*) AS total_events,
    MAX(timestamp) AS last_activity
  FROM user_events
  GROUP BY user_id
  EMIT CHANGES;

-- Pull query against materialized view (low latency)
SELECT unique_pages, total_events
FROM user_stats
WHERE user_id = 'user-123';
```

### JOIN Types

**Stream-Stream Join:**
```sql
CREATE STREAM enriched_events AS
  SELECT
    e.user_id,
    e.event_type,
    c.campaign_id,
    c.campaign_name
  FROM user_events e
  INNER JOIN campaign_clicks c
    WITHIN 1 HOUR
    ON e.user_id = c.user_id;
```

**Stream-Table Join (Enrichment):**
```sql
CREATE STREAM enriched_pageviews AS
  SELECT
    pv.user_id,
    pv.page_url,
    u.username,
    u.email,
    u.created_at
  FROM user_events pv
  LEFT JOIN users u
    ON pv.user_id = u.user_id;
```

**Table-Table Join:**
```sql
CREATE TABLE user_order_summary AS
  SELECT
    u.user_id,
    u.username,
    o.total_orders,
    o.total_revenue
  FROM users u
  LEFT JOIN order_summary o
    ON u.user_id = o.user_id;
```

### ksqlDB vs Kafka Streams vs Flink SQL

| Feature | ksqlDB | Kafka Streams | Flink SQL |
|---------|--------|---------------|-----------|
| **Language** | SQL | Java/Scala | SQL |
| **Deployment** | Server (separate) | Embedded library | Cluster (separate) |
| **State** | RocksDB | RocksDB | RocksDB/Heap |
| **Windowing** | Tumbling, hopping, session | All window types | All window types |
| **Joins** | Stream-stream, stream-table, table-table | All join types | All join types |
| **UDFs** | Java/JavaScript | Java/Scala | Java/Python |
| **Pull Queries** | Yes (materialized) | No (write custom) | No (batch query) |
| **Learning Curve** | Low (SQL) | Medium (Java API) | Medium (SQL + ops) |
| **Ops Complexity** | Medium (separate server) | Low (embedded) | High (cluster) |
| **Best For** | SQL analysts, simple ETL | Java developers, complex logic | Complex streaming + batch |

---

## Security

### SASL Mechanisms

| Mechanism | Security | Complexity | Use Case |
|-----------|----------|------------|----------|
| **PLAIN** | Low (plaintext) | Low | Development only |
| **SCRAM-SHA-256/512** | High | Medium | **Recommended** for production |
| **GSSAPI (Kerberos)** | High | High | Enterprise environments |
| **OAUTHBEARER** | High | Medium | Cloud-native, token-based |

### SASL/SCRAM Configuration

**Create SCRAM Credentials:**
```bash
kafka-configs --bootstrap-server localhost:9092 \
  --alter \
  --add-config 'SCRAM-SHA-512=[password=secret123]' \
  --entity-type users \
  --entity-name alice
```

**Broker Configuration (server.properties):**
```properties
listeners=SASL_SSL://0.0.0.0:9093
advertised.listeners=SASL_SSL://kafka.example.com:9093

security.inter.broker.protocol=SASL_SSL
sasl.mechanism.inter.broker.protocol=SCRAM-SHA-512
sasl.enabled.mechanisms=SCRAM-SHA-512

listener.name.sasl_ssl.scram-sha-512.sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required;
```

**Client Configuration (Python):**
```python
config = {
    'bootstrap.servers': 'kafka.example.com:9093',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanism': 'SCRAM-SHA-512',
    'sasl.username': 'alice',
    'sasl.password': 'secret123',
    'ssl.ca.location': '/path/to/ca-cert.pem'
}

producer = Producer(config)
```

**Client Configuration (Java):**
```properties
bootstrap.servers=kafka.example.com:9093
security.protocol=SASL_SSL
sasl.mechanism=SCRAM-SHA-512
sasl.jaas.config=org.apache.kafka.common.security.scram.ScramLoginModule required \
  username="alice" \
  password="secret123";
ssl.truststore.location=/path/to/truststore.jks
ssl.truststore.password=truststore-password
```

### SSL/TLS Encryption

**Generate Certificates:**
```bash
# CA certificate
openssl req -new -x509 -keyout ca-key -out ca-cert -days 365

# Broker keystore
keytool -keystore kafka.server.keystore.jks -alias localhost -validity 365 -genkey -keyalg RSA

# Certificate signing request
keytool -keystore kafka.server.keystore.jks -alias localhost -certreq -file cert-file

# Sign certificate
openssl x509 -req -CA ca-cert -CAkey ca-key -in cert-file -out cert-signed -days 365 -CAcreateserial

# Import CA and signed cert
keytool -keystore kafka.server.keystore.jks -alias CARoot -import -file ca-cert
keytool -keystore kafka.server.keystore.jks -alias localhost -import -file cert-signed

# Client truststore
keytool -keystore kafka.client.truststore.jks -alias CARoot -import -file ca-cert
```

**Broker Configuration:**
```properties
listeners=SSL://0.0.0.0:9093
ssl.keystore.location=/path/to/kafka.server.keystore.jks
ssl.keystore.password=keystore-password
ssl.key.password=key-password
ssl.truststore.location=/path/to/kafka.server.truststore.jks
ssl.truststore.password=truststore-password
ssl.client.auth=required
```

### Access Control Lists (ACLs)

**Topic-Level ACLs:**
```bash
# Grant alice READ permission on topic user-events
kafka-acls --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:alice \
  --operation Read \
  --topic user-events

# Grant bob WRITE permission
kafka-acls --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:bob \
  --operation Write \
  --topic user-events

# Grant group READ permission
kafka-acls --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:alice \
  --operation Read \
  --group analytics-group
```

**Wildcard ACLs:**
```bash
# Grant alice ALL permissions on topics prefixed with "analytics-"
kafka-acls --bootstrap-server localhost:9092 \
  --add \
  --allow-principal User:alice \
  --operation All \
  --topic analytics- \
  --resource-pattern-type prefixed
```

**List ACLs:**
```bash
kafka-acls --bootstrap-server localhost:9092 --list
```

**Remove ACLs:**
```bash
kafka-acls --bootstrap-server localhost:9092 \
  --remove \
  --allow-principal User:alice \
  --operation Read \
  --topic user-events
```

### Confluent RBAC

Role-Based Access Control (commercial Confluent Platform feature).

```bash
# Assign role to user
confluent iam rbac role-binding create \
  --principal User:alice \
  --role ResourceOwner \
  --resource Topic:user-events \
  --kafka-cluster-id lkc-12345

# Predefined roles:
# - SystemAdmin
# - ClusterAdmin
# - ResourceOwner
# - DeveloperRead
# - DeveloperWrite
```

### Audit Logging

Enable audit logging for security events.

```properties
# Broker configuration
authorizer.class.name=kafka.security.authorizer.AclAuthorizer
audit.log.enabled=true
audit.log.path=/var/log/kafka/audit.log
```

**Audit Log Events:**
- Authentication attempts
- Authorization decisions (allow/deny)
- Topic creation/deletion
- ACL modifications

---

## Production Tuning

### Hardware Sizing

**CPU:**
- 8-16 cores per broker for moderate workload
- 24+ cores for high-throughput workloads
- Multi-core benefits: parallel I/O threads, network threads, compaction

**Memory:**
- Broker JVM heap: 4-8 GB (more doesn't help significantly)
- OS page cache: Remaining RAM (Kafka relies heavily on page cache)
- Example: 64 GB total RAM = 6 GB JVM + 58 GB page cache

**Disk:**
- **SSD strongly recommended** for low-latency workloads
- HDD acceptable for high-throughput, latency-tolerant workloads
- RAID 10 for redundancy (though Kafka replication often sufficient)
- Capacity: Plan for 3x retention (accounting for replication factor 3)

**Network:**
- 10 Gbps minimum for production clusters
- 25-100 Gbps for high-throughput workloads
- Separate network for replication traffic if possible

**Example Sizing:**
- Throughput: 100 MB/s writes, 300 MB/s reads
- Retention: 7 days
- Replication factor: 3
- Disk: 100 MB/s × 86400 s/day × 7 days × 3 = 180 TB
- Brokers: 6 brokers × 30 TB each

### JVM Tuning

**Heap Size:**
```bash
# Set JVM heap (don't exceed 8 GB)
export KAFKA_HEAP_OPTS="-Xms6g -Xmx6g"
```

**Garbage Collection (G1GC recommended):**
```bash
export KAFKA_JVM_PERFORMANCE_OPTS="-XX:+UseG1GC \
  -XX:MaxGCPauseMillis=20 \
  -XX:InitiatingHeapOccupancyPercent=35 \
  -XX:G1HeapRegionSize=16M \
  -XX:MinMetaspaceSize=96m \
  -XX:MaxMetaspaceSize=256m"
```

**GC Logging:**
```bash
export KAFKA_GC_LOG_OPTS="-Xlog:gc*:file=/var/log/kafka/gc.log:time,tags:filecount=10,filesize=100M"
```

### OS Tuning

**File Descriptors:**
```bash
# Increase limits (100,000+ for production)
echo "* soft nofile 100000" >> /etc/security/limits.conf
echo "* hard nofile 100000" >> /etc/security/limits.conf

# Verify
ulimit -n
```

**Swappiness:**
```bash
# Reduce swapping (prefer page cache eviction)
sysctl vm.swappiness=1
echo "vm.swappiness=1" >> /etc/sysctl.conf
```

**Disk Scheduler:**
```bash
# Use deadline or noop scheduler for SSDs
echo deadline > /sys/block/sda/queue/scheduler

# Or for NVMe SSDs
echo none > /sys/block/nvme0n1/queue/scheduler
```

**Network Buffers:**
```bash
# Increase TCP buffers
sysctl -w net.core.rmem_max=134217728
sysctl -w net.core.wmem_max=134217728
sysctl -w net.ipv4.tcp_rmem="4096 87380 67108864"
sysctl -w net.ipv4.tcp_wmem="4096 65536 67108864"
```

### Topic Configuration

**Partitions:**
```bash
# Higher partitions = more parallelism, but more overhead
# Rule of thumb: (target throughput / single partition throughput)
kafka-topics --create \
  --topic high-throughput \
  --partitions 24 \
  --bootstrap-server localhost:9092
```

**Replication:**
```bash
# Replication factor 3 recommended for production
kafka-topics --create \
  --topic critical-data \
  --replication-factor 3 \
  --config min.insync.replicas=2 \
  --bootstrap-server localhost:9092
```

**Retention:**
```bash
# Time-based
kafka-configs --alter \
  --topic logs \
  --add-config retention.ms=604800000 \
  --bootstrap-server localhost:9092

# Size-based
kafka-configs --alter \
  --topic metrics \
  --add-config retention.bytes=107374182400 \
  --bootstrap-server localhost:9092
```

**Segment Size:**
```bash
# Smaller segments = more granular retention, more files
# Larger segments = fewer files, less overhead
kafka-configs --alter \
  --topic events \
  --add-config segment.bytes=1073741824 \
  --bootstrap-server localhost:9092
```

### Broker Configuration

**I/O Threads:**
```properties
# Number of threads for disk I/O
# Recommendation: number of disks (or 8-16 for RAID/SSD)
num.io.threads=16
```

**Network Threads:**
```properties
# Number of threads for network requests
# Recommendation: 8-16 for most workloads
num.network.threads=8

# Request queue size
queued.max.requests=500
```

**Socket Buffers:**
```properties
# Send buffer for network socket
socket.send.buffer.bytes=102400

# Receive buffer for network socket
socket.receive.buffer.bytes=102400

# Max size for socket requests
socket.request.max.bytes=104857600
```

**Log Flush:**
```properties
# Rely on OS page cache, don't force flush
log.flush.interval.messages=9223372036854775807
log.flush.interval.ms=9223372036854775807

# Replication provides durability
```

**Replication:**
```properties
# Larger replica fetch size improves throughput
replica.fetch.max.bytes=1048576
replica.fetch.response.max.bytes=10485760

# Number of fetcher threads
num.replica.fetchers=4
```

### Monitoring Key Metrics

| Component | Metric | Threshold | Alert Condition |
|-----------|--------|-----------|-----------------|
| **Broker** | Under-replicated partitions | 0 | > 0 for 5 min |
| | Offline partitions | 0 | > 0 |
| | Active controller | 1 | != 1 |
| | Request queue size | < 100 | > 100 |
| | Network processor avg idle | > 0.3 | < 0.2 |
| | Request handler avg idle | > 0.3 | < 0.2 |
| | Log flush rate | - | Spikes |
| | Bytes in/out rate | - | Capacity limits |
| **Producer** | Record send rate | - | Drops |
| | Record error rate | < 0.1% | > 1% |
| | Produce throttle time | < 10ms | > 100ms |
| | Request latency p99 | < 100ms | > 500ms |
| | Buffer available bytes | > 10MB | < 1MB |
| **Consumer** | Records lag max | < 10000 | > 100000 |
| | Records lag avg | - | Growing |
| | Fetch rate | - | Drops |
| | Commit rate | - | Drops |
| | Join rate | < 1/min | > 5/min (rebalances) |

**Prometheus Exporters:**
```bash
# JMX Exporter for Kafka metrics
java -javaagent:jmx_prometheus_javaagent.jar=7071:kafka-broker.yml \
  -jar kafka.jar
```

**Example Prometheus Queries:**
```promql
# Under-replicated partitions
kafka_server_replicamanager_underreplicatedpartitions

# Consumer lag
kafka_consumergroup_lag{topic="user-events"}

# Broker bytes in rate
rate(kafka_server_brokertopicmetrics_bytesin_total[5m])
```

### Capacity Planning Formula

**Throughput Capacity:**
```
broker_throughput = num_brokers × single_broker_throughput
single_broker_throughput = min(disk_bandwidth, network_bandwidth) / replication_factor
```

**Storage Capacity:**
```
total_storage = daily_throughput × retention_days × replication_factor
daily_throughput = avg_throughput_mb_per_sec × 86400
```

**Example:**
- Single broker disk: 200 MB/s write
- Network: 1 GB/s (125 MB/s)
- Bottleneck: 125 MB/s network
- Replication factor: 3
- Effective throughput: 125 / 3 = 41 MB/s per broker
- 10 brokers: 410 MB/s cluster throughput
- Daily data: 410 MB/s × 86400 = 35.4 TB/day
- 7-day retention × 3 replication: 35.4 × 7 × 3 = 743 TB total

### Alerting Thresholds

| Alert | Severity | Threshold | Action |
|-------|----------|-----------|--------|
| Broker down | Critical | Any broker offline | Page on-call |
| Under-replicated partitions | Critical | > 0 for 5 min | Investigate broker health |
| Offline partitions | Critical | > 0 | Immediate investigation |
| Consumer lag > 1M | Warning | Lag > 1,000,000 | Scale consumers |
| Consumer lag growing | Warning | Growing for 15 min | Investigate processing |
| Disk usage > 80% | Warning | > 80% | Plan capacity increase |
| Disk usage > 90% | Critical | > 90% | Emergency capacity add |
| Request queue > 100 | Warning | > 100 for 5 min | Investigate load |
| Producer errors > 1% | Warning | Error rate > 1% | Check network/broker |
| Rebalancing frequently | Warning | > 5/hour | Investigate consumer stability |

---

Back to [main skill](../SKILL.md)
