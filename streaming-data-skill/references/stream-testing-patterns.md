# Stream Testing Patterns

> **Part of:** [streaming-data-skill](../SKILL.md)
> **Purpose:** Testing streaming pipelines — embedded Kafka, testcontainers, Flink/Spark test harnesses, replay and backfill strategies

## Testing Strategy

### Testing Pyramid

| Level | Scope | Tools | Time |
|---|---|---|---|
| Unit | Transforms, serializers, window logic | JUnit, pytest | ms |
| Integration | Producer/consumer contracts, schema compat, connectors | Embedded Kafka, testcontainers | seconds |
| End-to-end | Full pipeline, EOS guarantees, failure recovery | Docker Compose, cloud sandboxes | minutes |

### Environment Selection

**Embedded** (in-process broker): Fast, no deps, easy CI. Limited feature parity, no distributed behavior. Use for unit tests.

**Containerized** (testcontainers/Docker Compose): Full parity, realistic, isolated. Slower, requires Docker. Use for integration tests.

**Cloud sandbox**: Production parity. Expensive, slow. Use for E2E validation.

## Embedded Kafka

```python
# testcontainers-based Kafka for Python (recommended over embedded)
@pytest.fixture(scope="module")
def kafka_container():
    with KafkaContainer() as kafka:
        yield kafka.get_bootstrap_server()

def test_produce_consume(kafka_container):
    producer = Producer({'bootstrap.servers': kafka_container})
    producer.produce('test-topic', key=b'k1', value=b'v1')
    producer.flush()

    consumer = Consumer({
        'bootstrap.servers': kafka_container,
        'group.id': 'test', 'auto.offset.reset': 'earliest'})
    consumer.subscribe(['test-topic'])
    msg = consumer.poll(timeout=5.0)
    assert msg.value() == b'v1'
    consumer.close()
```

Use `TestTopicFactory` pattern: encapsulate topic creation/cleanup in a fixture that tracks and deletes created topics.

**Limitations**: Missing log compaction edge cases, no distributed behavior testing, non-representative performance. Use testcontainers for full parity.

## Testcontainers

Full Docker-based dependencies with production parity. Each test gets clean containers.

**Multi-container**: Use Docker Compose for Kafka + Schema Registry + Connect stacks. **Avro testing**: Produce/consume with AvroProducer/AvroConsumer against containerized Schema Registry.

```python
# Reusable pytest fixtures
@pytest.fixture(scope="session")
def kafka_bootstrap(self):
    with KafkaContainer() as kafka:
        yield kafka.get_bootstrap_server()

@pytest.fixture
def unique_topic(kafka_bootstrap):
    name = f"test-{uuid.uuid4()}"
    admin = AdminClient({'bootstrap.servers': kafka_bootstrap})
    admin.create_topics([NewTopic(name, 1, 1)])
    yield name
    admin.delete_topics([name])
```

**CI/CD**: Ensure Docker socket access, set container resource limits, use dynamic port allocation, clean up via context managers.

## Testing Flink Jobs

**MiniCluster**: Local Flink cluster for integration tests. Set `setNumberSlotsPerTaskManager(2)`.

**TestHarness**: Unit test operators with `OneInputStreamOperatorTestHarness`. Process elements, advance watermarks, verify output.

```java
// Test windowed aggregation
testHarness.processElement(new Event("user1", 100), 1000L);
testHarness.processElement(new Event("user1", 200), 2000L);
testHarness.processWatermark(new Watermark(5000L)); // triggers window
List<Long> output = testHarness.extractOutputValues();
assertThat(output.get(0)).isEqualTo(300L);
```

**State and timers**: Use `KeyedOneInputStreamOperatorTestHarness` with `KeyedProcessFunction`. Register timers, advance processing time, verify timer-triggered output.

## Testing Spark Streaming

```python
# Memory sink pattern for testing
query = windowed_df.writeStream \
    .format("memory").queryName("test_output") \
    .outputMode("complete").start()
query.processAllAvailable()
result = spark.sql("SELECT * FROM test_output")
assert result.count() > 0
query.stop()
```

**Rate source**: `spark.readStream.format("rate").option("rowsPerSecond", 10)` generates test data without external deps.

**foreachBatch testing**: Collect batches in a list, verify counts and data after `processAllAvailable()`.

**Delta merge testing**: Create initial Delta table, stream updates via `foreachBatch` with `DeltaTable.merge()`, verify final state.

## Replay and Backfill Strategies

### Kafka Offset Reset

```python
# Reset to timestamp (24 hours ago)
partitions = [TopicPartition(topic, p, yesterday_ms) for p in range(num_partitions)]
offsets = consumer.offsets_for_times(partitions)
for tp in offsets:
    consumer.seek(tp)
```

CLI: `kafka-consumer-groups.sh --reset-offsets --to-earliest|--to-offset N|--to-datetime ISO8601 --execute`.

### Idempotent Replay Requirements

- Deterministic transforms (same input -> same output)
- Upsert semantics (INSERT ON CONFLICT UPDATE, not INSERT)
- No external state dependencies that change over time
- Offset tracking for exactly-once replay

### Backfill Patterns

**Pattern 1 — Replay from Kafka**: Reset consumer offset when retention allows. Process specific offset range with early termination at end offset.

**Pattern 2 — Batch backfill + resume streaming**: Read historical data from data lake (S3/GCS parquet), apply same transforms, write to sink with `replaceWhere`. Resume streaming from backfill end timestamp via `startingOffsetsByTimestamp`.

**Pattern 3 — Time-travel replay**: Use `offsets_for_times()` to find start/end offsets for a time range. Process only events within that window.

### Testing Replay

Create dedicated staging consumer groups. Reset to known-good timestamp, process N events, validate output. Never share consumer groups between replay testing and production.

---

Back to [main skill](../SKILL.md)
