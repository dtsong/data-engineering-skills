# Event-Driven Architecture

## Fundamentals

**Event types:** Domain events (state changes in bounded context), Integration events (cross-system communication with correlation/causation IDs), Notification events (lightweight change signals).

**When event-driven vs request/reply:** Use events for loose coupling, multiple consumers, async workflows, fan-out. Use request/reply for synchronous queries, immediate responses, simpler debugging.

| Pattern | State Storage | Event Content | Use Case |
|---------|---------------|---------------|----------|
| Event Sourcing | Events are source of truth | Full state changes | Audit trails, temporal queries |
| Event Notification | External database | Minimal (just ID) | Microservice coordination |
| Event-Carried State Transfer | Events carry state | Full entity state | Autonomous services |

## Apache Kafka

### Producer Config for Reliability

```python
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    acks='all',                    # Wait for all replicas
    enable_idempotence=True,       # Prevent duplicates
    retries=2147483647,            # Retry indefinitely
    compression_type='lz4',
    batch_size=16384, linger_ms=10,
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
)
```

| Setting | Value | Purpose |
|---------|-------|---------|
| `acks=all` | Durability | Wait for all replicas |
| `acks=1` | Lower latency | Leader only |
| `enable_idempotence=True` | Exactly-once | Prevent duplicates |
| `compression_type=lz4` | Throughput | Smaller payloads |

### Consumer Config

```python
consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],
    group_id='processors',
    auto_offset_reset='earliest',
    enable_auto_commit=False,      # Manual commit for control
    max_poll_records=500,
    session_timeout_ms=30000,
)
for message in consumer:
    process_message(message.value)
    consumer.commit()  # Only after successful processing
```

### Exactly-Once Semantics

Use transactional producer (`transactional_id` + `init_transactions()`) with `read_committed` consumer isolation. Wrap produce + offset commit in single transaction; abort on error.

### Kafka Connect

Source connectors (e.g., Debezium PostgreSQL -> Kafka) and sink connectors (e.g., Kafka -> BigQuery). Configure via JSON POST to Connect REST API.

### ksqlDB

```sql
CREATE STREAM orders_stream (orderId VARCHAR KEY, customerId VARCHAR, amount DOUBLE)
  WITH (KAFKA_TOPIC='orders', VALUE_FORMAT='JSON');

CREATE TABLE order_totals AS
  SELECT customerId, COUNT(*) as cnt, SUM(amount) as total
  FROM orders_stream GROUP BY customerId EMIT CHANGES;
```

## GCP Pub/Sub

**Pull vs Push:** Pull gives consumer rate control, good for batch/high-throughput. Push delivers instantly to HTTPS endpoint, good for real-time.

### Ordered Delivery

```python
publisher = pubsub_v1.PublisherClient(
    publisher_options=pubsub_v1.types.PublisherOptions(enable_message_ordering=True))
publisher.publish(topic_path, data, ordering_key=customer_id)
```

Create subscription with `enable_message_ordering=True`. Messages with same ordering_key delivered in order.

**Dead letter topics:** Set `max_delivery_attempts=5` on subscription; failed messages route to dead letter topic.

**Exactly-once:** `enable_exactly_once_delivery=True` on subscription.

**BigQuery subscription:** Write Pub/Sub messages directly to BigQuery table (no consumer code needed).

**Dataflow integration:** Apache Beam pipeline reads from Pub/Sub, transforms, writes to BigQuery.

## AWS EventBridge

**Event buses + rules:** Create custom event bus, define rules with event patterns (source, detail-type, detail filters), attach targets (Lambda, SQS, Step Functions).

**Content-based filtering:**
```json
{"source": ["order-service"], "detail": {"amount": [{"numeric": [">", 1000]}]}}
```

**Archive and replay:** Archive events with retention policy. Replay specific time ranges to a destination bus for reprocessing.

**Cross-account:** Grant `events:PutEvents` permission to target account. Target account creates rule matching source account ID.

## Schema Registry & Evolution

**Why:** Contract enforcement, documentation, compatibility checking, version management, serialization efficiency.

**Compatibility modes:**

| Mode | Allowed Changes | Use Case |
|------|-----------------|----------|
| BACKWARD | Delete fields, add optional | Consumer upgrades first |
| FORWARD | Add fields, delete optional | Producer upgrades first |
| FULL | Add/delete optional only | Both upgrade anytime |
| NONE | Any change | Development only |

**Avro vs Protobuf vs JSON Schema:** Avro = best schema evolution + fast + binary. Protobuf = smallest + fastest. JSON Schema = human readable but larger.

**Non-breaking changes:** Add optional fields with defaults, deprecate (don't remove) fields, add new message types.
**Breaking changes (avoid):** Remove required fields, change field types, rename without aliases.

## Delivery Guarantees

| Guarantee | Implementation | Use Case |
|-----------|----------------|----------|
| At-most-once | acks=0, fire-and-forget | Metrics, logs |
| At-least-once | acks=all + manual commit | Most use cases |
| Exactly-once | Idempotence + transactions | Financial transactions |

**Deduplication strategies:** Message ID tracking (Redis/set), content hash comparison. Use TTL to bound storage.

**Partition key strategies:** By entity ID (ordered processing), by hash (load balancing), by time (time-series).

Ordering guaranteed within partition only. For cross-partition coordination, use saga pattern with compensating transactions.
