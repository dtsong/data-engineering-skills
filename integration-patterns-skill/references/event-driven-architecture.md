# Event-Driven Architecture

> **Part of:** [integration-patterns-skill](../SKILL.md)
> **Purpose:** Deep dive into event-driven architecture patterns — Kafka, GCP Pub/Sub, AWS EventBridge, schema registry, ordering guarantees, and partitioning strategies

## Table of Contents

- [Event-Driven Architecture Fundamentals](#event-driven-architecture-fundamentals)
- [Apache Kafka Deep Architecture](#apache-kafka-deep-architecture)
- [GCP Pub/Sub](#gcp-pubsub)
- [AWS EventBridge](#aws-eventbridge)
- [Schema Registry & Evolution](#schema-registry--evolution)
- [Ordering, Partitioning & Delivery Guarantees](#ordering-partitioning--delivery-guarantees)

---

## Event-Driven Architecture Fundamentals

### Event Types

**Domain Events:**

Events that represent state changes within a bounded context.

```json
{
  "eventId": "evt_123",
  "eventType": "OrderPlaced",
  "aggregateId": "order_456",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": 1,
  "data": {
    "orderId": "order_456",
    "customerId": "cust_789",
    "totalAmount": 99.99,
    "items": [
      {"productId": "prod_001", "quantity": 2}
    ]
  }
}
```

**Integration Events:**

Events published for cross-system communication.

```json
{
  "eventId": "evt_124",
  "eventType": "CustomerCreated",
  "source": "crm-service",
  "timestamp": "2024-01-15T10:35:00Z",
  "data": {
    "customerId": "cust_789",
    "email": "customer@example.com",
    "name": "John Doe"
  },
  "metadata": {
    "correlationId": "corr_001",
    "causationId": "evt_123"
  }
}
```

**Notification Events:**

Lightweight events to notify subscribers of state changes.

```json
{
  "eventType": "InventoryLevelChanged",
  "resourceId": "prod_001",
  "timestamp": "2024-01-15T10:40:00Z",
  "changeType": "updated"
}
```

### Event Anatomy

**Standard Event Envelope:**

```json
{
  "envelope": {
    "eventId": "unique-event-id",
    "eventType": "OrderShipped",
    "source": "order-service",
    "timestamp": "2024-01-15T10:45:00Z",
    "schemaVersion": "1.0",
    "correlationId": "trace-123",
    "causationId": "evt-parent"
  },
  "payload": {
    "orderId": "order_456",
    "trackingNumber": "TRACK123",
    "carrier": "UPS"
  },
  "metadata": {
    "userId": "user_001",
    "ipAddress": "192.168.1.1",
    "userAgent": "Mozilla/5.0"
  }
}
```

### Event Sourcing vs Event Notification vs Event-Carried State Transfer

| Pattern | Purpose | State Storage | Event Content | Use Case |
|---------|---------|---------------|---------------|----------|
| Event Sourcing | Reconstruct aggregate state | Events are source of truth | Full state changes | Audit trails, temporal queries |
| Event Notification | Trigger actions | External database | Minimal (just ID) | Microservices coordination |
| Event-Carried State Transfer | Reduce coupling | Events carry state | Full entity state | Autonomous services |

### When Event-Driven vs Request/Reply

| Factor | Event-Driven | Request/Reply |
|--------|--------------|---------------|
| Coupling | Loose | Tight |
| Response needed | No | Yes |
| Multiple consumers | Yes | No |
| Temporal decoupling | Yes | No |
| Complexity | Higher | Lower |
| Scalability | Excellent | Limited |
| Debugging | Harder | Easier |
| Use when | Async workflows, fan-out | Synchronous queries, transactions |

---

## Apache Kafka Deep Architecture

### Core Concepts

**Topics and Partitions:**

```bash
# Create topic with 3 partitions and replication factor 3
kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic orders \
  --partitions 3 \
  --replication-factor 3 \
  --config retention.ms=604800000 \
  --config compression.type=lz4
```

**Consumer Groups:**

```python
from kafka import KafkaConsumer

# Multiple consumers in same group = parallel processing
consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],
    group_id='order-processors',
    auto_offset_reset='earliest',
    enable_auto_commit=False,
    max_poll_records=500,
    session_timeout_ms=30000,
    heartbeat_interval_ms=10000
)

for message in consumer:
    process_order(message.value)
    consumer.commit()  # Manual commit after processing
```

### Producer Configuration for Reliability

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],

    # Acknowledgment settings
    acks='all',  # Wait for all in-sync replicas

    # Idempotence for exactly-once semantics
    enable_idempotence=True,

    # Retry settings
    retries=2147483647,  # Max retries
    max_in_flight_requests_per_connection=5,

    # Batching for throughput
    batch_size=16384,
    linger_ms=10,

    # Compression
    compression_type='lz4',

    # Serialization
    value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    key_serializer=lambda k: k.encode('utf-8') if k else None
)

# Send with callback
def on_send_success(record_metadata):
    print(f"Topic: {record_metadata.topic}")
    print(f"Partition: {record_metadata.partition}")
    print(f"Offset: {record_metadata.offset}")

def on_send_error(excp):
    print(f"Error: {excp}")

# Async send
producer.send(
    'orders',
    key='order_123',
    value={'orderId': 'order_123', 'amount': 99.99}
).add_callback(on_send_success).add_errback(on_send_error)

# Flush to ensure delivery
producer.flush()
```

**Producer Configuration Reference:**

| Setting | Value | Purpose |
|---------|-------|---------|
| `acks` | `all` | Wait for all replicas (durability) |
| `acks` | `1` | Wait for leader only (lower latency) |
| `acks` | `0` | No acknowledgment (fire-and-forget) |
| `enable_idempotence` | `true` | Prevent duplicates |
| `retries` | `2147483647` | Retry indefinitely |
| `max_in_flight_requests_per_connection` | `5` | Max unacked requests (with idempotence) |
| `batch_size` | `16384` | Bytes per batch |
| `linger_ms` | `10` | Wait time to batch messages |
| `compression_type` | `lz4` | Compression algorithm |

### Consumer Configuration

```python
from kafka import KafkaConsumer, TopicPartition

consumer = KafkaConsumer(
    bootstrap_servers=['localhost:9092'],
    group_id='order-processors',

    # Offset behavior
    auto_offset_reset='earliest',  # or 'latest'
    enable_auto_commit=False,  # Manual commit for control

    # Polling settings
    max_poll_records=500,  # Records per poll
    max_poll_interval_ms=300000,  # 5 minutes

    # Session settings
    session_timeout_ms=30000,  # 30 seconds
    heartbeat_interval_ms=10000,  # 10 seconds

    # Deserialization
    value_deserializer=lambda m: json.loads(m.decode('utf-8')),
    key_deserializer=lambda k: k.decode('utf-8') if k else None
)

# Subscribe to topics
consumer.subscribe(['orders', 'shipments'])

# Process messages
for message in consumer:
    try:
        process_message(message.value)

        # Manual commit after successful processing
        consumer.commit()

    except Exception as e:
        print(f"Error processing message: {e}")
        # Don't commit - message will be reprocessed
```

**Manual Partition Assignment:**

```python
# Assign specific partitions (no consumer group)
partition = TopicPartition('orders', 0)
consumer.assign([partition])

# Seek to specific offset
consumer.seek(partition, 100)

# Seek to beginning
consumer.seek_to_beginning(partition)

# Seek to end
consumer.seek_to_end(partition)
```

### Exactly-Once Semantics (EOS)

```python
from kafka import KafkaProducer, KafkaConsumer

# Transactional producer
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    transactional_id='order-processor-1',  # Unique per instance
    enable_idempotence=True,
    acks='all'
)

# Initialize transactions
producer.init_transactions()

# Consumer with read_committed isolation
consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],
    group_id='processors',
    isolation_level='read_committed',  # Only read committed messages
    enable_auto_commit=False
)

# Process messages transactionally
for message in consumer:
    try:
        # Begin transaction
        producer.begin_transaction()

        # Process message
        result = process_order(message.value)

        # Produce result
        producer.send('order-results', value=result)

        # Commit consumer offsets within transaction
        producer.send_offsets_to_transaction(
            {TopicPartition('orders', message.partition): message.offset + 1},
            consumer.config['group_id']
        )

        # Commit transaction
        producer.commit_transaction()

    except Exception as e:
        # Abort transaction on error
        producer.abort_transaction()
        print(f"Transaction aborted: {e}")
```

### Kafka Connect

**Source Connector Configuration (PostgreSQL to Kafka):**

```json
{
  "name": "postgres-source",
  "config": {
    "connector.class": "io.debezium.connector.postgresql.PostgresConnector",
    "database.hostname": "localhost",
    "database.port": "5432",
    "database.user": "postgres",
    "database.password": "password",
    "database.dbname": "mydb",
    "database.server.name": "dbserver1",
    "table.include.list": "public.orders,public.customers",
    "plugin.name": "pgoutput",
    "publication.name": "dbz_publication",
    "slot.name": "debezium_slot",
    "transforms": "unwrap",
    "transforms.unwrap.type": "io.debezium.transforms.ExtractNewRecordState",
    "transforms.unwrap.drop.tombstones": "false",
    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter"
  }
}
```

**Sink Connector Configuration (Kafka to BigQuery):**

```json
{
  "name": "bigquery-sink",
  "config": {
    "connector.class": "com.wepay.kafka.connect.bigquery.BigQuerySinkConnector",
    "topics": "orders,customers",
    "project": "my-gcp-project",
    "defaultDataset": "kafka_dataset",
    "keyfile": "/path/to/keyfile.json",
    "autoCreateTables": "true",
    "allowNewBigQueryFields": "true",
    "allowBigQueryRequiredFieldRelaxation": "true",
    "key.converter": "org.apache.kafka.connect.json.JsonConverter",
    "value.converter": "org.apache.kafka.connect.json.JsonConverter"
  }
}
```

### ksqlDB for Stream Processing

```sql
-- Create stream from topic
CREATE STREAM orders_stream (
    orderId VARCHAR KEY,
    customerId VARCHAR,
    amount DOUBLE,
    orderTime BIGINT
) WITH (
    KAFKA_TOPIC='orders',
    VALUE_FORMAT='JSON',
    TIMESTAMP='orderTime'
);

-- Aggregate stream
CREATE TABLE order_totals_by_customer AS
SELECT
    customerId,
    COUNT(*) as orderCount,
    SUM(amount) as totalAmount,
    MAX(orderTime) as lastOrderTime
FROM orders_stream
GROUP BY customerId
EMIT CHANGES;

-- Join streams
CREATE STREAM enriched_orders AS
SELECT
    o.orderId,
    o.amount,
    c.name as customerName,
    c.email as customerEmail
FROM orders_stream o
LEFT JOIN customers_table c ON o.customerId = c.customerId
EMIT CHANGES;

-- Filter and transform
CREATE STREAM high_value_orders AS
SELECT
    orderId,
    customerId,
    amount,
    'HIGH_VALUE' as orderType
FROM orders_stream
WHERE amount > 1000
EMIT CHANGES;
```

### Schema Registry with Avro

**Define Avro Schema:**

```json
{
  "type": "record",
  "name": "Order",
  "namespace": "com.example.orders",
  "fields": [
    {"name": "orderId", "type": "string"},
    {"name": "customerId", "type": "string"},
    {"name": "amount", "type": "double"},
    {"name": "orderTime", "type": "long", "logicalType": "timestamp-millis"},
    {"name": "items", "type": {
      "type": "array",
      "items": {
        "type": "record",
        "name": "OrderItem",
        "fields": [
          {"name": "productId", "type": "string"},
          {"name": "quantity", "type": "int"},
          {"name": "price", "type": "double"}
        ]
      }
    }}
  ]
}
```

**Producer with Schema Registry:**

```python
from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer

# Schema Registry configuration
schema_registry_conf = {
    'url': 'http://localhost:8081'
}

# Avro schema
value_schema_str = """
{
  "type": "record",
  "name": "Order",
  "fields": [
    {"name": "orderId", "type": "string"},
    {"name": "customerId", "type": "string"},
    {"name": "amount", "type": "double"}
  ]
}
"""

key_schema_str = """
{"type": "string"}
"""

value_schema = avro.loads(value_schema_str)
key_schema = avro.loads(key_schema_str)

# Create producer
producer = AvroProducer({
    'bootstrap.servers': 'localhost:9092',
    'schema.registry.url': 'http://localhost:8081'
}, default_key_schema=key_schema, default_value_schema=value_schema)

# Send message
producer.produce(
    topic='orders',
    key='order_123',
    value={
        'orderId': 'order_123',
        'customerId': 'cust_456',
        'amount': 99.99
    }
)

producer.flush()
```

**Consumer with Schema Registry:**

```python
from confluent_kafka.avro import AvroConsumer

consumer = AvroConsumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'order-processors',
    'schema.registry.url': 'http://localhost:8081'
})

consumer.subscribe(['orders'])

while True:
    msg = consumer.poll(1.0)

    if msg is None:
        continue

    if msg.error():
        print(f"Error: {msg.error()}")
        continue

    # Avro deserialized automatically
    order = msg.value()
    print(f"Order: {order['orderId']}, Amount: {order['amount']}")
```

### Security Configuration

```python
# SASL/SSL configuration
producer = KafkaProducer(
    bootstrap_servers=['kafka.example.com:9093'],

    # SSL settings
    security_protocol='SASL_SSL',
    ssl_cafile='/path/to/ca-cert',
    ssl_certfile='/path/to/client-cert',
    ssl_keyfile='/path/to/client-key',

    # SASL settings
    sasl_mechanism='PLAIN',
    sasl_plain_username='kafka-user',
    sasl_plain_password='password'
)
```

### Performance Tuning

| Parameter | Recommended | Impact |
|-----------|-------------|--------|
| `batch.size` | 16384-65536 | Larger = higher throughput, more latency |
| `linger.ms` | 10-100 | Wait time to batch messages |
| `compression.type` | `lz4` or `snappy` | Reduce network/storage usage |
| `buffer.memory` | 67108864 (64MB) | Producer buffer size |
| `max.request.size` | 1048576 (1MB) | Max message size |
| `fetch.min.bytes` | 1024 | Min data to fetch (consumer) |
| `fetch.max.wait.ms` | 500 | Max wait for min bytes (consumer) |

---

## GCP Pub/Sub

### Topics and Subscriptions

```python
from google.cloud import pubsub_v1

# Publisher client
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path('my-project', 'orders')

# Create topic
topic = publisher.create_topic(request={'name': topic_path})

# Subscriber client
subscriber = pubsub_v1.SubscriberClient()
subscription_path = subscriber.subscription_path('my-project', 'order-processor')

# Create subscription
subscription = subscriber.create_subscription(
    request={
        'name': subscription_path,
        'topic': topic_path,
        'ack_deadline_seconds': 60,
        'message_retention_duration': {'seconds': 604800},  # 7 days
        'retry_policy': {
            'minimum_backoff': {'seconds': 10},
            'maximum_backoff': {'seconds': 600}
        }
    }
)
```

### Push vs Pull Subscriptions

**Decision Criteria:**

| Factor | Pull | Push |
|--------|------|------|
| Control | High (consumer controls rate) | Low (Pub/Sub controls rate) |
| Scaling | Manual | Automatic (autoscaling endpoint) |
| Latency | Higher (polling) | Lower (instant delivery) |
| Endpoint required | No | Yes (HTTPS) |
| Use when | Batch processing, high throughput | Real-time, low latency |

**Pull Subscription:**

```python
from concurrent.futures import TimeoutError

def pull_messages(subscription_path, timeout=5.0):
    """Pull messages from subscription."""
    subscriber = pubsub_v1.SubscriberClient()

    def callback(message):
        print(f"Received message: {message.data.decode('utf-8')}")
        print(f"Attributes: {message.attributes}")

        # Process message
        try:
            process_order(message.data)
            message.ack()  # Acknowledge successful processing
        except Exception as e:
            print(f"Error: {e}")
            message.nack()  # Negative acknowledge - redelivery

    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

    print(f"Listening for messages on {subscription_path}...")

    try:
        streaming_pull_future.result(timeout=timeout)
    except TimeoutError:
        streaming_pull_future.cancel()
        streaming_pull_future.result()
```

**Push Subscription:**

```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/pubsub/push', methods=['POST'])
def pubsub_push():
    """Handle push notification from Pub/Sub."""
    envelope = request.get_json()

    if not envelope:
        return 'Bad Request: no Pub/Sub message', 400

    pubsub_message = envelope.get('message')

    if not pubsub_message:
        return 'Bad Request: invalid Pub/Sub message', 400

    # Decode message
    import base64
    data = base64.b64decode(pubsub_message['data']).decode('utf-8')
    attributes = pubsub_message.get('attributes', {})

    print(f"Received: {data}")

    # Process message
    try:
        process_order(data)
        return '', 204  # Success
    except Exception as e:
        print(f"Error: {e}")
        return '', 500  # Retry

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

### Ordering Keys for Ordered Delivery

```python
import json

def publish_with_ordering(topic_path, messages):
    """Publish messages with ordering."""
    publisher = pubsub_v1.PublisherClient()

    # Enable message ordering
    publisher_options = pubsub_v1.types.PublisherOptions(
        enable_message_ordering=True
    )
    publisher = pubsub_v1.PublisherClient(publisher_options=publisher_options)

    for message in messages:
        # Messages with same ordering_key are delivered in order
        data = json.dumps(message).encode('utf-8')

        future = publisher.publish(
            topic_path,
            data,
            ordering_key=message['customerId']  # Order by customer
        )

        print(f"Published message ID: {future.result()}")

# Example messages
messages = [
    {'orderId': 'order_1', 'customerId': 'cust_123', 'amount': 50.0},
    {'orderId': 'order_2', 'customerId': 'cust_123', 'amount': 75.0},
    {'orderId': 'order_3', 'customerId': 'cust_456', 'amount': 100.0}
]

publish_with_ordering(topic_path, messages)
```

**Create Subscription with Ordering:**

```python
subscription = subscriber.create_subscription(
    request={
        'name': subscription_path,
        'topic': topic_path,
        'enable_message_ordering': True
    }
)
```

### Dead Letter Topics

```python
# Create dead letter topic
dead_letter_topic = publisher.topic_path('my-project', 'orders-dead-letter')
publisher.create_topic(request={'name': dead_letter_topic})

# Create subscription with dead letter policy
subscription = subscriber.create_subscription(
    request={
        'name': subscription_path,
        'topic': topic_path,
        'dead_letter_policy': {
            'dead_letter_topic': dead_letter_topic,
            'max_delivery_attempts': 5
        }
    }
)
```

### Exactly-Once Delivery

```python
# Enable exactly-once delivery with ordering
subscription = subscriber.create_subscription(
    request={
        'name': subscription_path,
        'topic': topic_path,
        'enable_exactly_once_delivery': True,
        'enable_message_ordering': True
    }
)

# Consumer automatically handles deduplication
def callback(message):
    # Message will be delivered exactly once
    # even if ack is delayed or fails
    process_order(message.data)
    message.ack()

streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)
```

### BigQuery Subscriptions

```python
# Create BigQuery table
from google.cloud import bigquery

bq_client = bigquery.Client()
table_id = 'my-project.orders_dataset.orders_table'

schema = [
    bigquery.SchemaField('orderId', 'STRING', mode='REQUIRED'),
    bigquery.SchemaField('customerId', 'STRING', mode='REQUIRED'),
    bigquery.SchemaField('amount', 'FLOAT64', mode='REQUIRED'),
    bigquery.SchemaField('timestamp', 'TIMESTAMP', mode='REQUIRED')
]

table = bigquery.Table(table_id, schema=schema)
bq_client.create_table(table)

# Create BigQuery subscription
from google.cloud.pubsub_v1.types import BigQueryConfig

bigquery_config = BigQueryConfig(
    table=table_id,
    write_metadata=True,
    use_topic_schema=True
)

subscription = subscriber.create_subscription(
    request={
        'name': subscription_path,
        'topic': topic_path,
        'bigquery_config': bigquery_config
    }
)
```

### Dataflow Integration

```python
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions

# Beam pipeline to process Pub/Sub messages
def run_pipeline():
    options = PipelineOptions([
        '--project=my-project',
        '--runner=DataflowRunner',
        '--temp_location=gs://my-bucket/temp',
        '--region=us-central1'
    ])

    with beam.Pipeline(options=options) as pipeline:
        (pipeline
         | 'Read from Pub/Sub' >> beam.io.ReadFromPubSub(
             subscription=subscription_path
         )
         | 'Parse JSON' >> beam.Map(lambda x: json.loads(x.decode('utf-8')))
         | 'Transform' >> beam.Map(transform_order)
         | 'Write to BigQuery' >> beam.io.WriteToBigQuery(
             'my-project:orders_dataset.processed_orders',
             schema='orderId:STRING,customerId:STRING,amount:FLOAT64',
             write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND
         ))

def transform_order(order):
    """Transform order data."""
    return {
        'orderId': order['orderId'],
        'customerId': order['customerId'],
        'amount': order['amount']
    }
```

### Monitoring

```python
from google.cloud import monitoring_v3

def get_subscription_metrics(project_id, subscription_id):
    """Get subscription backlog and oldest unacked message age."""
    client = monitoring_v3.MetricServiceClient()
    project_name = f"projects/{project_id}"

    # Query backlog
    backlog_query = monitoring_v3.Query(
        client,
        project_name,
        'pubsub.googleapis.com/subscription/num_undelivered_messages',
        minutes=60
    )

    backlog_query = backlog_query.select_resources(
        subscription_id=subscription_id
    )

    for time_series in backlog_query:
        print(f"Backlog: {time_series.points[0].value.int64_value} messages")

    # Query oldest unacked message age
    age_query = monitoring_v3.Query(
        client,
        project_name,
        'pubsub.googleapis.com/subscription/oldest_unacked_message_age',
        minutes=60
    )

    age_query = age_query.select_resources(
        subscription_id=subscription_id
    )

    for time_series in age_query:
        print(f"Oldest unacked: {time_series.points[0].value.double_value} seconds")
```

---

## AWS EventBridge

### Event Buses and Rules

```python
import boto3
import json

eventbridge = boto3.client('events', region_name='us-east-1')

# Create custom event bus
response = eventbridge.create_event_bus(
    Name='orders-event-bus'
)

# Create rule
rule_response = eventbridge.put_rule(
    Name='high-value-orders',
    EventBusName='orders-event-bus',
    EventPattern=json.dumps({
        'source': ['order-service'],
        'detail-type': ['OrderPlaced'],
        'detail': {
            'amount': [{'numeric': ['>', 1000]}]
        }
    }),
    State='ENABLED'
)

# Add target (Lambda function)
eventbridge.put_targets(
    Rule='high-value-orders',
    EventBusName='orders-event-bus',
    Targets=[
        {
            'Id': '1',
            'Arn': 'arn:aws:lambda:us-east-1:123456789012:function:ProcessHighValueOrder',
            'RetryPolicy': {
                'MaximumRetryAttempts': 2,
                'MaximumEventAge': 3600
            },
            'DeadLetterConfig': {
                'Arn': 'arn:aws:sqs:us-east-1:123456789012:high-value-orders-dlq'
            }
        }
    ]
)
```

### Schema Registry

```python
# Create schema
schemas = boto3.client('schemas', region_name='us-east-1')

schema_content = {
    "openapi": "3.0.0",
    "info": {
        "version": "1.0.0",
        "title": "OrderPlaced"
    },
    "paths": {},
    "components": {
        "schemas": {
            "OrderPlaced": {
                "type": "object",
                "required": ["orderId", "customerId", "amount"],
                "properties": {
                    "orderId": {"type": "string"},
                    "customerId": {"type": "string"},
                    "amount": {"type": "number"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "productId": {"type": "string"},
                                "quantity": {"type": "integer"}
                            }
                        }
                    }
                }
            }
        }
    }
}

response = schemas.create_schema(
    RegistryName='order-schemas',
    SchemaName='OrderPlaced',
    Type='OpenApi3',
    Content=json.dumps(schema_content)
)
```

### Content-Based Filtering

```json
{
  "source": ["order-service"],
  "detail-type": ["OrderPlaced"],
  "detail": {
    "amount": [{"numeric": [">", 1000]}],
    "customerId": [{"prefix": "VIP-"}],
    "region": ["us-east-1", "us-west-2"],
    "items": {
      "productId": [{"exists": true}]
    }
  }
}
```

**Advanced Pattern Matching:**

```json
{
  "detail": {
    "$or": [
      {"amount": [{"numeric": [">", 1000]}]},
      {"customerId": [{"prefix": "VIP-"}]}
    ]
  }
}
```

### Cross-Account Event Routing

```python
# Source account: Grant permission
eventbridge.put_permission(
    EventBusName='orders-event-bus',
    StatementId='AllowAccountB',
    Action='events:PutEvents',
    Principal='123456789012'  # Target account ID
)

# Target account: Create rule to receive events
eventbridge.put_rule(
    Name='cross-account-orders',
    EventPattern=json.dumps({
        'account': ['987654321098']  # Source account ID
    }),
    State='ENABLED'
)
```

### Archive and Replay

```python
# Create archive
archive_response = eventbridge.create_archive(
    ArchiveName='orders-archive',
    EventSourceArn='arn:aws:events:us-east-1:123456789012:event-bus/orders-event-bus',
    EventPattern=json.dumps({
        'source': ['order-service']
    }),
    RetentionDays=30
)

# Replay events
replay_response = eventbridge.start_replay(
    ReplayName='orders-replay-2024-01-15',
    EventSourceArn='arn:aws:events:us-east-1:123456789012:event-bus/orders-event-bus',
    EventStartTime='2024-01-15T00:00:00Z',
    EventEndTime='2024-01-15T23:59:59Z',
    Destination={
        'Arn': 'arn:aws:events:us-east-1:123456789012:event-bus/replay-bus'
    }
)
```

### Integration with AWS Services

**Lambda Target:**

```python
eventbridge.put_targets(
    Rule='order-processing',
    Targets=[
        {
            'Id': '1',
            'Arn': 'arn:aws:lambda:us-east-1:123456789012:function:ProcessOrder',
            'RetryPolicy': {
                'MaximumRetryAttempts': 2
            }
        }
    ]
)
```

**SQS Target:**

```python
eventbridge.put_targets(
    Rule='order-processing',
    Targets=[
        {
            'Id': '1',
            'Arn': 'arn:aws:sqs:us-east-1:123456789012:order-queue',
            'SqsParameters': {
                'MessageGroupId': 'orders'
            }
        }
    ]
)
```

**Step Functions Target:**

```python
eventbridge.put_targets(
    Rule='order-workflow',
    Targets=[
        {
            'Id': '1',
            'Arn': 'arn:aws:states:us-east-1:123456789012:stateMachine:OrderWorkflow',
            'RoleArn': 'arn:aws:iam::123456789012:role/EventBridgeStepFunctionsRole'
        }
    ]
)
```

### Terraform Example

```hcl
resource "aws_cloudwatch_event_bus" "orders" {
  name = "orders-event-bus"
}

resource "aws_cloudwatch_event_rule" "high_value_orders" {
  name           = "high-value-orders"
  event_bus_name = aws_cloudwatch_event_bus.orders.name

  event_pattern = jsonencode({
    source      = ["order-service"]
    detail-type = ["OrderPlaced"]
    detail = {
      amount = [{
        numeric = [">", 1000]
      }]
    }
  })
}

resource "aws_cloudwatch_event_target" "lambda" {
  rule           = aws_cloudwatch_event_rule.high_value_orders.name
  event_bus_name = aws_cloudwatch_event_bus.orders.name
  arn            = aws_lambda_function.process_order.arn

  retry_policy {
    maximum_retry_attempts = 2
    maximum_event_age      = 3600
  }

  dead_letter_config {
    arn = aws_sqs_queue.dlq.arn
  }
}
```

---

## Schema Registry & Evolution

### Why Schema Registry Matters

Schema registry provides:

1. **Contract enforcement** - Producers and consumers agree on message format
2. **Documentation** - Self-documenting message formats
3. **Compatibility checking** - Prevent breaking changes
4. **Version management** - Track schema evolution over time
5. **Serialization efficiency** - Smaller message payloads

### Confluent Schema Registry Setup

```bash
# Start Schema Registry (Docker)
docker run -d \
  --name schema-registry \
  -p 8081:8081 \
  -e SCHEMA_REGISTRY_HOST_NAME=schema-registry \
  -e SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS=kafka:9092 \
  confluentinc/cp-schema-registry:latest
```

**Register Schema:**

```python
import requests
import json

schema_registry_url = 'http://localhost:8081'

# Avro schema
order_schema = {
    "type": "record",
    "name": "Order",
    "namespace": "com.example.orders",
    "fields": [
        {"name": "orderId", "type": "string"},
        {"name": "customerId", "type": "string"},
        {"name": "amount", "type": "double"}
    ]
}

# Register schema
response = requests.post(
    f'{schema_registry_url}/subjects/orders-value/versions',
    headers={'Content-Type': 'application/vnd.schemaregistry.v1+json'},
    json={'schema': json.dumps(order_schema)}
)

schema_id = response.json()['id']
print(f"Schema registered with ID: {schema_id}")
```

### Compatibility Modes

| Mode | Changes Allowed | Checked Against | Use Case |
|------|-----------------|-----------------|----------|
| **BACKWARD** | Delete fields, add optional fields | Last version | Consumer upgrade first |
| **FORWARD** | Add fields, delete optional fields | Last version | Producer upgrade first |
| **FULL** | Add/delete optional fields only | Last version | Both can upgrade anytime |
| **NONE** | Any change allowed | Not checked | Development only |
| **BACKWARD_TRANSITIVE** | BACKWARD rules | All versions | Strict consumer-first |
| **FORWARD_TRANSITIVE** | FORWARD rules | All versions | Strict producer-first |
| **FULL_TRANSITIVE** | FULL rules | All versions | Maximum compatibility |

**Set Compatibility Mode:**

```python
# Set compatibility for subject
response = requests.put(
    f'{schema_registry_url}/config/orders-value',
    headers={'Content-Type': 'application/vnd.schemaregistry.v1+json'},
    json={'compatibility': 'BACKWARD'}
)
```

### Avro vs Protobuf vs JSON Schema

| Feature | Avro | Protobuf | JSON Schema |
|---------|------|----------|-------------|
| Binary format | Yes | Yes | No |
| Schema evolution | Excellent | Good | Limited |
| Language support | Good | Excellent | Universal |
| Message size | Small | Smallest | Large |
| Human readable | No | No | Yes |
| Schema definition | JSON | .proto file | JSON |
| Backward compat | Built-in | Manual | Manual |
| Performance | Fast | Fastest | Slow |

**Protobuf Schema:**

```protobuf
syntax = "proto3";

package com.example.orders;

message Order {
  string order_id = 1;
  string customer_id = 2;
  double amount = 3;
  int64 order_time = 4;

  repeated OrderItem items = 5;
}

message OrderItem {
  string product_id = 1;
  int32 quantity = 2;
  double price = 3;
}
```

**JSON Schema:**

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["orderId", "customerId", "amount"],
  "properties": {
    "orderId": {"type": "string"},
    "customerId": {"type": "string"},
    "amount": {"type": "number"},
    "orderTime": {"type": "integer"},
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["productId", "quantity"],
        "properties": {
          "productId": {"type": "string"},
          "quantity": {"type": "integer"},
          "price": {"type": "number"}
        }
      }
    }
  }
}
```

### Schema Evolution Best Practices

**Breaking Changes (Avoid):**

- Removing required fields
- Changing field types
- Renaming fields (without aliases in Avro)
- Changing field numbers in Protobuf

**Non-Breaking Changes:**

- Adding optional fields with defaults
- Removing optional fields
- Adding new message types
- Deprecating fields (mark but don't remove)

**Avro Evolution Example:**

```python
# Version 1
schema_v1 = {
    "type": "record",
    "name": "Order",
    "fields": [
        {"name": "orderId", "type": "string"},
        {"name": "amount", "type": "double"}
    ]
}

# Version 2 - Backward compatible (add optional field)
schema_v2 = {
    "type": "record",
    "name": "Order",
    "fields": [
        {"name": "orderId", "type": "string"},
        {"name": "amount", "type": "double"},
        {"name": "currency", "type": "string", "default": "USD"}  # Default required
    ]
}

# Version 3 - Backward compatible (rename with alias)
schema_v3 = {
    "type": "record",
    "name": "Order",
    "fields": [
        {"name": "orderId", "type": "string"},
        {"name": "totalAmount", "type": "double", "aliases": ["amount"]},  # Alias old name
        {"name": "currency", "type": "string", "default": "USD"}
    ]
}
```

---

## Ordering, Partitioning & Delivery Guarantees

### Delivery Guarantee Comparison

| Guarantee | Description | Implementation | Performance | Use Case |
|-----------|-------------|----------------|-------------|----------|
| **At-most-once** | Message may be lost, never duplicated | Fire-and-forget, acks=0 | Fastest | Metrics, logs |
| **At-least-once** | Message never lost, may duplicate | Retry, acks=1 | Fast | Most use cases |
| **Exactly-once** | Message delivered once, no duplicates | Idempotence + transactions | Slowest | Financial transactions |

### At-Least-Once Pattern

```python
# Kafka producer with retries
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    acks='all',  # Wait for all replicas
    retries=3,
    max_in_flight_requests_per_connection=1  # Preserve order
)

# Consumer with manual commit
consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],
    enable_auto_commit=False,
    group_id='processors'
)

for message in consumer:
    try:
        # Process message
        process_order(message.value)

        # Commit offset only after successful processing
        consumer.commit()

    except Exception as e:
        print(f"Processing failed: {e}")
        # Don't commit - message will be redelivered
```

### Exactly-Once Pattern

```python
# Idempotent consumer with deduplication
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def process_with_deduplication(message):
    """Process message with idempotency check."""
    message_id = message.key.decode('utf-8')

    # Check if already processed
    if redis_client.exists(f"processed:{message_id}"):
        print(f"Duplicate message {message_id}, skipping")
        return

    # Process message
    process_order(message.value)

    # Mark as processed (with TTL for cleanup)
    redis_client.setex(
        f"processed:{message_id}",
        timedelta(days=7),
        '1'
    )

# Use in consumer
for message in consumer:
    process_with_deduplication(message)
    consumer.commit()
```

### Partition Key Selection Strategies

**By Entity ID (Ordered Processing):**

```python
# All events for same customer go to same partition
producer.send(
    'orders',
    key=customer_id.encode('utf-8'),
    value=order_data
)
```

**By Hash (Load Balancing):**

```python
import hashlib

def partition_by_hash(key, num_partitions):
    """Distribute evenly across partitions."""
    hash_value = int(hashlib.md5(key.encode('utf-8')).hexdigest(), 16)
    return hash_value % num_partitions

# Custom partitioner
from kafka.partitioner import Partitioner

class HashPartitioner(Partitioner):
    def partition(self, key, all_partitions, available_partitions):
        if key is None:
            return random.choice(available_partitions)

        return partition_by_hash(key.decode('utf-8'), len(all_partitions))

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    partitioner=HashPartitioner()
)
```

**By Time (Time-Series Data):**

```python
from datetime import datetime

def partition_by_hour(timestamp, num_partitions):
    """Partition by hour of day."""
    hour = timestamp.hour
    return hour % num_partitions

# Partition current events by hour
partition = partition_by_hour(datetime.now(), 24)
```

### Ordering Guarantees Within Partitions

**Kafka Ordering:**

```python
# Ordering preserved within partition only
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    max_in_flight_requests_per_connection=1  # Critical for ordering
)

# All messages with same key go to same partition
# Ordering guaranteed for messages with same key
producer.send('orders', key=b'customer_123', value=b'order_1')
producer.send('orders', key=b'customer_123', value=b'order_2')
producer.send('orders', key=b'customer_123', value=b'order_3')
```

**Pub/Sub Ordering:**

```python
# Enable ordering on publisher
publisher_options = pubsub_v1.types.PublisherOptions(
    enable_message_ordering=True
)
publisher = pubsub_v1.PublisherClient(publisher_options=publisher_options)

# Messages with same ordering_key delivered in order
publisher.publish(topic_path, b'message_1', ordering_key='customer_123')
publisher.publish(topic_path, b'message_2', ordering_key='customer_123')
publisher.publish(topic_path, b'message_3', ordering_key='customer_123')
```

### Cross-Partition Ordering (Saga Pattern)

```python
# Saga coordinator tracks multi-step workflow
class OrderSaga:
    def __init__(self):
        self.state = 'STARTED'
        self.steps = []

    def execute(self, order):
        """Execute saga steps in order."""
        try:
            # Step 1: Reserve inventory
            inventory_result = self.reserve_inventory(order)
            self.steps.append(('reserve_inventory', inventory_result))

            # Step 2: Process payment
            payment_result = self.process_payment(order)
            self.steps.append(('process_payment', payment_result))

            # Step 3: Create shipment
            shipment_result = self.create_shipment(order)
            self.steps.append(('create_shipment', shipment_result))

            self.state = 'COMPLETED'

        except Exception as e:
            # Compensate in reverse order
            self.compensate()
            raise

    def compensate(self):
        """Rollback saga steps in reverse order."""
        for step_name, step_result in reversed(self.steps):
            if step_name == 'reserve_inventory':
                self.release_inventory(step_result)
            elif step_name == 'process_payment':
                self.refund_payment(step_result)
            elif step_name == 'create_shipment':
                self.cancel_shipment(step_result)

        self.state = 'COMPENSATED'
```

### Deduplication Strategies

**Message ID Based:**

```python
# Store processed message IDs
processed_ids = set()

def process_with_dedup(message):
    message_id = message.message_id

    if message_id in processed_ids:
        return  # Skip duplicate

    process_message(message)
    processed_ids.add(message_id)
```

**Content Hash Based:**

```python
import hashlib
import json

def compute_content_hash(message):
    """Generate deterministic hash from message content."""
    content = json.dumps(message, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()

def process_with_content_dedup(message):
    content_hash = compute_content_hash(message)

    if redis_client.exists(f"hash:{content_hash}"):
        return  # Duplicate content

    process_message(message)
    redis_client.setex(f"hash:{content_hash}", timedelta(hours=24), '1')
```

### Consumer Rebalancing Impact

```python
from kafka import KafkaConsumer
from kafka.coordinator.assignors.range import RangePartitionAssignor

consumer = KafkaConsumer(
    'orders',
    bootstrap_servers=['localhost:9092'],
    group_id='processors',

    # Rebalancing settings
    session_timeout_ms=30000,  # 30 seconds - higher = fewer rebalances
    heartbeat_interval_ms=10000,  # 10 seconds
    max_poll_interval_ms=300000,  # 5 minutes - max processing time

    # Partition assignment strategy
    partition_assignment_strategy=[RangePartitionAssignor]
)

# Handle rebalance events
def on_partitions_revoked(revoked):
    """Called when partitions are revoked during rebalance."""
    print(f"Partitions revoked: {revoked}")
    # Flush in-progress work, commit offsets

def on_partitions_assigned(assigned):
    """Called when partitions are assigned after rebalance."""
    print(f"Partitions assigned: {assigned}")
    # Initialize state for new partitions

consumer.subscribe(['orders'],
    on_assign=on_partitions_assigned,
    on_revoke=on_partitions_revoked
)
```

---

Back to [main skill](../SKILL.md)
