# Stream Testing Patterns

> **Part of:** [streaming-data-skill](../SKILL.md)
> **Purpose:** Deep dive into testing streaming data pipelines — embedded Kafka, testcontainers, integration testing, property-based testing, replay, and backfill strategies

## Table of Contents

- [Testing Strategy for Streaming](#testing-strategy-for-streaming)
- [Embedded Kafka for Testing](#embedded-kafka-for-testing)
- [Testcontainers](#testcontainers)
- [Testing Flink Jobs](#testing-flink-jobs)
- [Testing Spark Streaming](#testing-spark-streaming)
- [Replay and Backfill Strategies](#replay-and-backfill-strategies)

---

## Testing Strategy for Streaming

Streaming pipelines require a layered testing approach that addresses the unique challenges of unbounded data, event time, and stateful processing.

### Testing Pyramid for Streaming

| Test Level | Scope | Tools | Execution Time |
|------------|-------|-------|----------------|
| **Unit** | Individual transformations, serializers, window logic | JUnit, pytest, ScalaTest | Milliseconds |
| **Integration** | Producer/consumer contracts, schema compatibility, connector behavior | Embedded Kafka, testcontainers | Seconds |
| **End-to-end** | Full pipeline flow, exactly-once guarantees, failure recovery | Docker Compose, cloud sandboxes | Minutes |

### What to Test at Each Level

| Test Level | What to Test | Example |
|------------|--------------|---------|
| **Unit** | Transformation logic | Input event → output event mapping |
| | Serialization/deserialization | Avro schema encode/decode |
| | Windowing logic | Window assignment for event timestamp |
| | Stateful operations | Aggregation state updates |
| | Error handling | Malformed event parsing |
| **Integration** | Producer/consumer contracts | Producer writes → consumer reads same data |
| | Schema compatibility | Schema evolution (backward/forward) |
| | Connector behavior | Kafka Connect sink writes to database |
| | Partitioning | Key-based partition assignment |
| | Consumer group rebalancing | New consumer joins group |
| **End-to-end** | Full pipeline flow | Source → transform → sink |
| | Exactly-once guarantees | No duplicates after retry |
| | Failure recovery | Pipeline restarts from checkpoint |
| | Late data handling | Events arrive after watermark |
| | Backpressure | Slow sink doesn't crash pipeline |

### Test Environment Considerations

**Embedded**: In-process broker (EmbeddedKafka, MemoryStream)
- Pros: Fast, no external dependencies, easy CI/CD
- Cons: Limited feature parity, no distributed behavior

**Containerized**: Docker containers (testcontainers, Docker Compose)
- Pros: Full feature parity, realistic behavior, isolated
- Cons: Slower, requires Docker, resource overhead

**Cloud sandbox**: Dedicated test environment (GCP project, AWS account)
- Pros: Production parity, full service integration
- Cons: Expensive, slow, cleanup complexity

Choose embedded for unit tests, containerized for integration tests, and cloud sandbox for end-to-end validation.

---

## Embedded Kafka for Testing

Embedded Kafka runs an in-process Kafka broker for fast, isolated testing. Ideal for unit and integration tests without external dependencies.

### Spring Kafka Test (Java)

```java
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.kafka.test.utils.KafkaTestUtils;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.core.DefaultKafkaProducerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.junit.jupiter.api.Test;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;

import java.util.Map;
import java.util.Collections;
import static org.assertj.core.api.Assertions.assertThat;

@EmbeddedKafka(
    partitions = 1,
    topics = {"test-topic"},
    brokerProperties = {
        "auto.create.topics.enable=true",
        "log.dir=/tmp/kafka-test"
    }
)
public class KafkaIntegrationTest {

    @Test
    public void testProducerConsumer() {
        // Get embedded broker address
        String bootstrapServers = embeddedKafkaBroker.getBrokersAsString();

        // Create producer
        Map<String, Object> producerProps = KafkaTestUtils.producerProps(bootstrapServers);
        DefaultKafkaProducerFactory<String, String> pf =
            new DefaultKafkaProducerFactory<>(producerProps);
        KafkaTemplate<String, String> template = new KafkaTemplate<>(pf);

        // Send test message
        template.send("test-topic", "key1", "value1");

        // Create consumer
        Map<String, Object> consumerProps = KafkaTestUtils.consumerProps(
            bootstrapServers,
            "test-group",
            "true"
        );
        DefaultKafkaConsumerFactory<String, String> cf =
            new DefaultKafkaConsumerFactory<>(consumerProps);
        KafkaConsumer<String, String> consumer = cf.createConsumer();

        // Subscribe and consume
        consumer.subscribe(Collections.singletonList("test-topic"));
        ConsumerRecord<String, String> record =
            KafkaTestUtils.getSingleRecord(consumer, "test-topic");

        // Verify
        assertThat(record.key()).isEqualTo("key1");
        assertThat(record.value()).isEqualTo("value1");

        consumer.close();
    }
}
```

### Confluent Kafka Python Testing

```python
import pytest
from confluent_kafka import Producer, Consumer
from confluent_kafka.admin import AdminClient, NewTopic
import time

class TestEmbeddedKafka:
    """Test Kafka producers and consumers with embedded broker"""

    @pytest.fixture
    def kafka_broker(self):
        """
        Fixture for embedded Kafka (requires kafka-python-testing)
        Alternative: use testcontainers (see next section)
        """
        from kafka_testing import EmbeddedKafkaCluster

        cluster = EmbeddedKafkaCluster(
            num_brokers=1,
            topics=['test-topic']
        )
        cluster.start()

        yield cluster.bootstrap_servers

        cluster.stop()

    def test_produce_consume(self, kafka_broker):
        """Test basic produce and consume flow"""
        topic = 'test-topic'

        # Producer configuration
        producer_config = {
            'bootstrap.servers': kafka_broker,
            'client.id': 'test-producer'
        }

        producer = Producer(producer_config)

        # Produce test message
        test_key = 'key1'
        test_value = 'value1'

        producer.produce(
            topic,
            key=test_key.encode('utf-8'),
            value=test_value.encode('utf-8'),
            callback=lambda err, msg: print(f"Produced: {msg.value()}")
        )

        producer.flush(timeout=5)

        # Consumer configuration
        consumer_config = {
            'bootstrap.servers': kafka_broker,
            'group.id': 'test-group',
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': False
        }

        consumer = Consumer(consumer_config)
        consumer.subscribe([topic])

        # Consume message
        msg = consumer.poll(timeout=5.0)

        assert msg is not None, "No message received"
        assert msg.error() is None, f"Consumer error: {msg.error()}"
        assert msg.key().decode('utf-8') == test_key
        assert msg.value().decode('utf-8') == test_value

        consumer.close()
```

### TestTopicFactory Pattern

Encapsulate topic creation and cleanup for reusable test fixtures:

```python
class TestTopicFactory:
    """Factory for creating and managing test topics"""

    def __init__(self, bootstrap_servers):
        self.bootstrap_servers = bootstrap_servers
        self.admin_client = AdminClient({'bootstrap.servers': bootstrap_servers})
        self.created_topics = []

    def create_topic(self, name, num_partitions=1, replication_factor=1):
        """Create a test topic"""
        topic = NewTopic(
            topic=name,
            num_partitions=num_partitions,
            replication_factor=replication_factor
        )

        fs = self.admin_client.create_topics([topic])

        # Wait for creation
        for topic_name, f in fs.items():
            try:
                f.result()
                self.created_topics.append(topic_name)
                print(f"Created topic: {topic_name}")
            except Exception as e:
                print(f"Failed to create topic {topic_name}: {e}")
                raise

    def cleanup(self):
        """Delete all created topics"""
        if self.created_topics:
            fs = self.admin_client.delete_topics(self.created_topics)

            for topic_name, f in fs.items():
                try:
                    f.result()
                    print(f"Deleted topic: {topic_name}")
                except Exception as e:
                    print(f"Failed to delete topic {topic_name}: {e}")

        self.created_topics = []


# Usage in pytest
@pytest.fixture
def topic_factory(kafka_broker):
    factory = TestTopicFactory(kafka_broker)
    yield factory
    factory.cleanup()


def test_with_dynamic_topic(topic_factory):
    topic_name = "dynamic-test-topic"
    topic_factory.create_topic(topic_name, num_partitions=3)

    # Run test with topic...
```

### Limitations of Embedded Kafka

**Feature gaps**: Missing some broker features (log compaction edge cases, quota enforcement)
**Single node**: No distributed behavior testing (rebalancing, replication)
**Performance**: Not representative of production throughput
**State**: In-memory state lost between tests (no persistent logs)

For comprehensive integration testing, use Testcontainers with real Kafka containers.

---

## Testcontainers

Testcontainers provides Docker-based test dependencies with full feature parity. Spin up Kafka, Schema Registry, and connectors for realistic integration tests.

### Why Testcontainers for Streaming Tests

**Full feature parity**: Real Kafka broker with all features enabled
**Service composition**: Multi-container setups (Kafka + Schema Registry + Connect)
**Isolation**: Each test gets clean containers, no cross-test pollution
**Production parity**: Same Docker images as production deployments
**Language support**: Java, Python, Go, .NET libraries available

### KafkaContainer Setup (Python)

```python
import pytest
from testcontainers.kafka import KafkaContainer
from confluent_kafka import Producer, Consumer
from confluent_kafka.admin import AdminClient, NewTopic

@pytest.fixture(scope="module")
def kafka_container():
    """Start Kafka container for all tests in module"""
    with KafkaContainer() as kafka:
        # Container is running, get bootstrap servers
        bootstrap_servers = kafka.get_bootstrap_server()
        print(f"Kafka running at: {bootstrap_servers}")
        yield bootstrap_servers
    # Container automatically stopped and removed


def test_kafka_produce_consume(kafka_container):
    """Test produce and consume with containerized Kafka"""
    topic = 'test-events'

    # Create topic
    admin_client = AdminClient({'bootstrap.servers': kafka_container})
    topic_obj = NewTopic(topic, num_partitions=3, replication_factor=1)
    admin_client.create_topics([topic_obj])

    # Produce messages
    producer = Producer({'bootstrap.servers': kafka_container})

    for i in range(10):
        producer.produce(
            topic,
            key=f"key-{i}".encode('utf-8'),
            value=f"value-{i}".encode('utf-8')
        )

    producer.flush()

    # Consume messages
    consumer = Consumer({
        'bootstrap.servers': kafka_container,
        'group.id': 'test-group',
        'auto.offset.reset': 'earliest'
    })

    consumer.subscribe([topic])

    messages = []
    for _ in range(10):
        msg = consumer.poll(timeout=5.0)
        if msg and not msg.error():
            messages.append(msg.value().decode('utf-8'))

    consumer.close()

    # Verify
    assert len(messages) == 10
    assert 'value-0' in messages
    assert 'value-9' in messages
```

### KafkaContainer Setup (Java)

```java
import org.testcontainers.containers.KafkaContainer;
import org.testcontainers.utility.DockerImageName;
import org.junit.jupiter.api.Test;
import org.apache.kafka.clients.producer.KafkaProducer;
import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.consumer.KafkaConsumer;
import org.apache.kafka.clients.consumer.ConsumerRecords;

import java.time.Duration;
import java.util.Collections;
import java.util.Properties;

public class KafkaContainerTest {

    @Test
    public void testKafkaContainer() {
        // Start Kafka container
        try (KafkaContainer kafka = new KafkaContainer(
                DockerImageName.parse("confluentinc/cp-kafka:7.5.0"))) {

            kafka.start();

            String bootstrapServers = kafka.getBootstrapServers();

            // Producer
            Properties producerProps = new Properties();
            producerProps.put("bootstrap.servers", bootstrapServers);
            producerProps.put("key.serializer",
                "org.apache.kafka.common.serialization.StringSerializer");
            producerProps.put("value.serializer",
                "org.apache.kafka.common.serialization.StringSerializer");

            KafkaProducer<String, String> producer =
                new KafkaProducer<>(producerProps);

            producer.send(new ProducerRecord<>("test-topic", "key1", "value1"));
            producer.flush();
            producer.close();

            // Consumer
            Properties consumerProps = new Properties();
            consumerProps.put("bootstrap.servers", bootstrapServers);
            consumerProps.put("group.id", "test-group");
            consumerProps.put("auto.offset.reset", "earliest");
            consumerProps.put("key.deserializer",
                "org.apache.kafka.common.serialization.StringDeserializer");
            consumerProps.put("value.deserializer",
                "org.apache.kafka.common.serialization.StringDeserializer");

            KafkaConsumer<String, String> consumer =
                new KafkaConsumer<>(consumerProps);

            consumer.subscribe(Collections.singletonList("test-topic"));

            ConsumerRecords<String, String> records =
                consumer.poll(Duration.ofSeconds(10));

            assertThat(records.count()).isEqualTo(1);
            assertThat(records.iterator().next().value()).isEqualTo("value1");

            consumer.close();
        }
    }
}
```

### SchemaRegistryContainer for Avro Testing

```python
from testcontainers.kafka import KafkaContainer
from testcontainers.compose import DockerCompose
from confluent_kafka import avro
from confluent_kafka.avro import AvroProducer, AvroConsumer
import pytest

@pytest.fixture(scope="module")
def kafka_with_schema_registry():
    """Start Kafka and Schema Registry containers"""
    # Use Docker Compose for multi-container setup
    compose = DockerCompose(
        filepath=".",
        compose_file_name="docker-compose.test.yml"
    )

    compose.start()

    # Wait for services to be ready
    compose.wait_for("http://localhost:8081")  # Schema Registry

    yield {
        'bootstrap_servers': 'localhost:9092',
        'schema_registry_url': 'http://localhost:8081'
    }

    compose.stop()


# docker-compose.test.yml content:
"""
version: '3.8'
services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on:
      - zookeeper
    ports:
      - "9092:9092"
    environment:
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

  schema-registry:
    image: confluentinc/cp-schema-registry:7.5.0
    depends_on:
      - kafka
    ports:
      - "8081:8081"
    environment:
      SCHEMA_REGISTRY_HOST_NAME: schema-registry
      SCHEMA_REGISTRY_KAFKASTORE_BOOTSTRAP_SERVERS: kafka:9092
"""


def test_avro_produce_consume(kafka_with_schema_registry):
    """Test Avro serialization with Schema Registry"""

    # Define Avro schema
    value_schema = avro.loads('''
    {
        "type": "record",
        "name": "User",
        "fields": [
            {"name": "name", "type": "string"},
            {"name": "age", "type": "int"}
        ]
    }
    ''')

    key_schema = avro.loads('{"type": "string"}')

    # Producer
    producer_config = {
        'bootstrap.servers': kafka_with_schema_registry['bootstrap_servers'],
        'schema.registry.url': kafka_with_schema_registry['schema_registry_url']
    }

    producer = AvroProducer(
        producer_config,
        default_key_schema=key_schema,
        default_value_schema=value_schema
    )

    # Produce Avro message
    producer.produce(
        topic='users',
        key='user1',
        value={'name': 'Alice', 'age': 30}
    )

    producer.flush()

    # Consumer
    consumer_config = {
        'bootstrap.servers': kafka_with_schema_registry['bootstrap_servers'],
        'schema.registry.url': kafka_with_schema_registry['schema_registry_url'],
        'group.id': 'test-group',
        'auto.offset.reset': 'earliest'
    }

    consumer = AvroConsumer(consumer_config)
    consumer.subscribe(['users'])

    msg = consumer.poll(timeout=5.0)

    assert msg is not None
    assert msg.value()['name'] == 'Alice'
    assert msg.value()['age'] == 30

    consumer.close()
```

### Multi-Container Compose: Kafka + Schema Registry + Connect

```python
# Full stack integration test
@pytest.fixture(scope="module")
def kafka_stack():
    """Start full Kafka stack (broker + schema registry + connect)"""
    compose = DockerCompose(
        filepath="tests",
        compose_file_name="docker-compose.kafka-stack.yml"
    )

    compose.start()

    # Wait for all services
    import time
    time.sleep(10)  # Or implement proper health checks

    yield {
        'kafka': 'localhost:9092',
        'schema_registry': 'http://localhost:8081',
        'connect': 'http://localhost:8083'
    }

    compose.stop()


def test_kafka_connect_sink(kafka_stack):
    """Test Kafka Connect sink connector"""
    import requests

    # Create connector
    connector_config = {
        "name": "test-sink",
        "config": {
            "connector.class": "io.confluent.connect.jdbc.JdbcSinkConnector",
            "tasks.max": "1",
            "topics": "test-topic",
            "connection.url": "jdbc:postgresql://postgres:5432/testdb",
            "auto.create": "true"
        }
    }

    response = requests.post(
        f"{kafka_stack['connect']}/connectors",
        json=connector_config
    )

    assert response.status_code == 201

    # Produce message to topic (connector should sink to database)
    # ... producer code ...

    # Verify data in database
    # ... database check ...
```

### pytest Fixtures with testcontainers-kafka

```python
import pytest
from testcontainers.kafka import KafkaContainer
from confluent_kafka.admin import AdminClient, NewTopic

@pytest.fixture(scope="session")
def kafka_bootstrap_servers():
    """Session-scoped Kafka container (shared across all tests)"""
    with KafkaContainer() as kafka:
        yield kafka.get_bootstrap_server()


@pytest.fixture
def kafka_topic(kafka_bootstrap_servers):
    """Function-scoped topic (new topic per test)"""
    import uuid

    topic_name = f"test-topic-{uuid.uuid4()}"

    admin = AdminClient({'bootstrap.servers': kafka_bootstrap_servers})
    topic = NewTopic(topic_name, num_partitions=1, replication_factor=1)
    admin.create_topics([topic])

    yield topic_name

    # Cleanup (optional, container is ephemeral)
    admin.delete_topics([topic_name])


@pytest.fixture
def kafka_producer(kafka_bootstrap_servers):
    """Reusable producer fixture"""
    from confluent_kafka import Producer

    producer = Producer({'bootstrap.servers': kafka_bootstrap_servers})
    yield producer
    producer.flush()


@pytest.fixture
def kafka_consumer(kafka_bootstrap_servers):
    """Reusable consumer fixture"""
    from confluent_kafka import Consumer

    consumer = Consumer({
        'bootstrap.servers': kafka_bootstrap_servers,
        'group.id': 'test-group',
        'auto.offset.reset': 'earliest'
    })

    yield consumer
    consumer.close()


# Usage in tests
def test_end_to_end(kafka_topic, kafka_producer, kafka_consumer):
    """End-to-end test with fixtures"""
    # Produce
    kafka_producer.produce(kafka_topic, value=b'test-message')
    kafka_producer.flush()

    # Consume
    kafka_consumer.subscribe([kafka_topic])
    msg = kafka_consumer.poll(timeout=5.0)

    assert msg is not None
    assert msg.value() == b'test-message'
```

### Network Configuration for Container-to-Container Communication

```python
from testcontainers.core.network import Network

@pytest.fixture(scope="module")
def kafka_network():
    """Custom Docker network for inter-container communication"""
    network = Network()
    yield network
    network.remove()


@pytest.fixture(scope="module")
def kafka_with_network(kafka_network):
    """Kafka container on custom network"""
    kafka = KafkaContainer(network=kafka_network.name)
    kafka.start()

    yield kafka

    kafka.stop()


@pytest.fixture(scope="module")
def app_container(kafka_network, kafka_with_network):
    """Application container that connects to Kafka"""
    from testcontainers.core.container import DockerContainer

    # Get Kafka hostname within Docker network
    kafka_hostname = kafka_with_network.get_container_host_ip()

    app = DockerContainer("my-app:latest")
    app.with_network(kafka_network)
    app.with_env("KAFKA_BOOTSTRAP_SERVERS", f"{kafka_hostname}:9092")
    app.start()

    yield app

    app.stop()
```

### CI/CD Considerations

**Docker-in-Docker**: CI runners need Docker socket access or DinD mode
**Resource limits**: Set container memory/CPU limits to avoid CI runner exhaustion
**Parallel execution**: Avoid port conflicts with dynamic port allocation
**Cleanup**: Ensure containers stop even on test failure (use context managers/fixtures)

```yaml
# GitHub Actions example
name: Integration Tests

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install pytest testcontainers-kafka confluent-kafka

      - name: Run tests
        run: |
          pytest tests/integration --tb=short -v
```

### Resource Management and Cleanup

```python
import pytest
import logging

@pytest.fixture(autouse=True, scope="session")
def docker_cleanup():
    """Ensure Docker cleanup even on test failure"""
    yield

    # Force cleanup of any dangling containers
    import docker
    client = docker.from_env()

    containers = client.containers.list(
        all=True,
        filters={'label': 'org.testcontainers=true'}
    )

    for container in containers:
        logging.info(f"Cleaning up container: {container.id}")
        container.remove(force=True)
```

---

## Testing Flink Jobs

Apache Flink provides test harnesses for unit testing streaming operators and transformations.

### MiniCluster for Local Testing

```java
import org.apache.flink.runtime.testutils.MiniClusterResourceConfiguration;
import org.apache.flink.test.util.MiniClusterWithClientResource;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.junit.ClassRule;
import org.junit.Test;

public class FlinkJobTest {

    @ClassRule
    public static MiniClusterWithClientResource flinkCluster =
        new MiniClusterWithClientResource(
            new MiniClusterResourceConfiguration.Builder()
                .setNumberSlotsPerTaskManager(2)
                .setNumberTaskManagers(1)
                .build()
        );

    @Test
    public void testStreamingJob() throws Exception {
        StreamExecutionEnvironment env =
            StreamExecutionEnvironment.getExecutionEnvironment();

        env.setParallelism(1);

        // Define test pipeline
        DataStream<String> input = env.fromElements("event1", "event2", "event3");

        DataStream<String> result = input
            .map(event -> event.toUpperCase())
            .filter(event -> event.startsWith("EVENT"));

        // Collect results
        List<String> output = new ArrayList<>();
        result.addSink(new CollectSink(output));

        // Execute
        env.execute("Test Job");

        // Verify
        assertThat(output).containsExactlyInAnyOrder("EVENT1", "EVENT2", "EVENT3");
    }

    // Helper sink for collecting results
    private static class CollectSink implements SinkFunction<String> {
        private final List<String> output;

        public CollectSink(List<String> output) {
            this.output = output;
        }

        @Override
        public void invoke(String value, Context context) {
            output.add(value);
        }
    }
}
```

### Flink TestHarness for Operators

```java
import org.apache.flink.streaming.api.operators.StreamMap;
import org.apache.flink.streaming.util.OneInputStreamOperatorTestHarness;
import org.apache.flink.api.common.functions.MapFunction;
import org.junit.Test;

public class MapOperatorTest {

    @Test
    public void testMapOperator() throws Exception {
        // Create test harness for map operator
        StreamMap<String, Integer> operator = new StreamMap<>(
            new MapFunction<String, Integer>() {
                @Override
                public Integer map(String value) {
                    return value.length();
                }
            }
        );

        OneInputStreamOperatorTestHarness<String, Integer> testHarness =
            new OneInputStreamOperatorTestHarness<>(operator);

        testHarness.open();

        // Process test records
        testHarness.processElement("hello", 10L);
        testHarness.processElement("world", 20L);
        testHarness.processElement("flink", 30L);

        // Get output
        List<Integer> output = testHarness.extractOutputValues();

        // Verify
        assertThat(output).containsExactly(5, 5, 5);

        testHarness.close();
    }
}
```

### Testing Windowed Aggregation

```java
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;
import org.apache.flink.streaming.api.watermark.Watermark;
import org.apache.flink.streaming.runtime.streamrecord.StreamRecord;
import org.junit.Test;

public class WindowOperatorTest {

    @Test
    public void testTumblingWindow() throws Exception {
        // Create windowed aggregation operator
        // (simplified example - actual implementation more complex)

        KeyedOneInputStreamOperatorTestHarness<String, Event, Long> testHarness =
            createWindowTestHarness();

        testHarness.open();

        // Process events with timestamps
        testHarness.processElement(new Event("user1", 100), 1000L);
        testHarness.processElement(new Event("user1", 200), 2000L);
        testHarness.processElement(new Event("user1", 300), 3000L);

        // Advance watermark to trigger window
        testHarness.processWatermark(new Watermark(5000L));

        // Verify window result
        List<StreamRecord<Long>> output = testHarness.extractOutputStreamRecords();
        assertThat(output).hasSize(1);
        assertThat(output.get(0).getValue()).isEqualTo(600L);  // Sum of values

        testHarness.close();
    }
}
```

### Testing State and Timers

```java
import org.apache.flink.streaming.api.functions.KeyedProcessFunction;
import org.apache.flink.streaming.api.operators.KeyedProcessOperator;
import org.apache.flink.streaming.util.KeyedOneInputStreamOperatorTestHarness;
import org.apache.flink.util.Collector;
import org.junit.Test;

public class StatefulOperatorTest {

    // Stateful function with timer
    private static class SessionAggregator
            extends KeyedProcessFunction<String, Event, SessionResult> {

        private static final long SESSION_TIMEOUT = 5000L;

        @Override
        public void processElement(Event event, Context ctx, Collector<SessionResult> out) {
            // Update state and set timer
            long currentTime = ctx.timestamp();
            ctx.timerService().registerEventTimeTimer(currentTime + SESSION_TIMEOUT);
        }

        @Override
        public void onTimer(long timestamp, OnTimerContext ctx, Collector<SessionResult> out) {
            // Emit session result on timeout
            out.collect(new SessionResult(ctx.getCurrentKey(), timestamp));
        }
    }

    @Test
    public void testSessionAggregation() throws Exception {
        KeyedProcessOperator<String, Event, SessionResult> operator =
            new KeyedProcessOperator<>(new SessionAggregator());

        KeyedOneInputStreamOperatorTestHarness<String, Event, SessionResult> testHarness =
            new KeyedOneInputStreamOperatorTestHarness<>(
                operator,
                event -> event.getUserId(),  // Key selector
                Types.STRING
            );

        testHarness.open();

        // Process event
        testHarness.processElement(new Event("user1", 100), 1000L);

        // Advance time to trigger timer
        testHarness.setProcessingTime(7000L);

        // Verify timer fired and result emitted
        List<SessionResult> output = testHarness.extractOutputValues();
        assertThat(output).hasSize(1);
        assertThat(output.get(0).getUserId()).isEqualTo("user1");

        testHarness.close();
    }
}
```

---

## Testing Spark Streaming

Spark Structured Streaming provides test utilities for unit testing streaming queries.

### MemoryStream for Unit Testing

```python
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, window
import pytest

@pytest.fixture(scope="module")
def spark():
    """Create Spark session for testing"""
    spark = SparkSession.builder \
        .master("local[2]") \
        .appName("StreamingTest") \
        .getOrCreate()

    yield spark

    spark.stop()


def test_streaming_aggregation(spark):
    """Test streaming aggregation with MemoryStream"""
    from pyspark.sql.streaming import DataStreamWriter

    # Create MemoryStream (for testing only)
    # Note: MemoryStream requires Scala, use rate source as alternative

    # Alternative: use rate source for testing
    input_df = spark.readStream \
        .format("rate") \
        .option("rowsPerSecond", 10) \
        .load()

    # Transform
    result_df = input_df \
        .withWatermark("timestamp", "10 seconds") \
        .groupBy(
            window("timestamp", "5 seconds"),
            col("value") % 10  # Group by value mod 10
        ) \
        .agg(count("*").alias("event_count"))

    # Write to memory sink for testing
    query = result_df.writeStream \
        .format("memory") \
        .queryName("test_output") \
        .outputMode("update") \
        .start()

    # Wait for some data
    query.processAllAvailable()

    # Read from memory sink
    output_df = spark.sql("SELECT * FROM test_output")

    # Verify
    assert output_df.count() > 0
    assert "event_count" in output_df.columns

    query.stop()
```

### PySpark Example: Test Streaming Aggregation

```python
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField, StringType, TimestampType
from pyspark.sql.functions import col, window, count
import pytest
from datetime import datetime

@pytest.fixture
def spark():
    spark = SparkSession.builder \
        .master("local[2]") \
        .appName("StreamTest") \
        .config("spark.sql.shuffle.partitions", "2") \
        .getOrCreate()

    spark.sparkContext.setLogLevel("WARN")

    yield spark
    spark.stop()


def test_windowed_count(spark, tmp_path):
    """Test windowed aggregation with file source/sink"""

    # Schema
    schema = StructType([
        StructField("user_id", StringType(), False),
        StructField("action", StringType(), False),
        StructField("timestamp", TimestampType(), False)
    ])

    # Create test data
    test_data = [
        ("user1", "click", datetime(2026, 1, 1, 10, 0, 0)),
        ("user2", "view", datetime(2026, 1, 1, 10, 0, 5)),
        ("user1", "click", datetime(2026, 1, 1, 10, 0, 10)),
        ("user1", "purchase", datetime(2026, 1, 1, 10, 1, 0))
    ]

    # Write test data to JSON files
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    test_df = spark.createDataFrame(test_data, schema)
    test_df.write.json(str(input_dir))

    # Read as stream
    input_stream = spark.readStream \
        .schema(schema) \
        .json(str(input_dir))

    # Windowed aggregation
    windowed_counts = input_stream \
        .withWatermark("timestamp", "1 minute") \
        .groupBy(
            window("timestamp", "1 minute"),
            "action"
        ) \
        .agg(count("*").alias("count"))

    # Write to memory sink
    output_dir = tmp_path / "output"

    query = windowed_counts.writeStream \
        .format("memory") \
        .queryName("windowed_counts") \
        .outputMode("complete") \
        .start()

    # Process all available data
    query.processAllAvailable()

    # Read results
    result_df = spark.sql("SELECT * FROM windowed_counts")

    # Verify
    result_list = result_df.collect()
    assert len(result_list) > 0

    click_count = [r for r in result_list if r.action == "click"][0]
    assert click_count["count"] == 2

    query.stop()
```

### StreamingQueryListener for Assertions

```python
from pyspark.sql.streaming import StreamingQueryListener

class TestQueryListener(StreamingQueryListener):
    """Custom listener for test assertions"""

    def __init__(self):
        self.query_progress = []
        self.errors = []

    def onQueryStarted(self, event):
        print(f"Query started: {event.id}")

    def onQueryProgress(self, event):
        self.query_progress.append(event.progress)
        print(f"Progress: {event.progress.numInputRows} rows processed")

    def onQueryTerminated(self, event):
        if event.exception:
            self.errors.append(event.exception)
            print(f"Query failed: {event.exception}")


def test_with_listener(spark):
    """Test streaming query with custom listener"""

    listener = TestQueryListener()
    spark.streams.addListener(listener)

    # Create and run streaming query
    query = spark.readStream \
        .format("rate") \
        .option("rowsPerSecond", 5) \
        .load() \
        .writeStream \
        .format("memory") \
        .queryName("test_query") \
        .start()

    # Wait for some progress
    query.processAllAvailable()

    # Assertions on listener state
    assert len(listener.query_progress) > 0, "No progress reported"
    assert len(listener.errors) == 0, "Errors occurred"

    total_rows = sum(p.numInputRows for p in listener.query_progress)
    assert total_rows > 0, "No rows processed"

    query.stop()
    spark.streams.removeListener(listener)
```

### Testing foreachBatch Sinks

```python
from pyspark.sql.functions import col

def test_foreach_batch_sink(spark, tmp_path):
    """Test custom foreachBatch sink logic"""

    output_batches = []

    def process_batch(batch_df, batch_id):
        """Custom batch processing logic"""
        # Collect batch for verification
        output_batches.append({
            'batch_id': batch_id,
            'count': batch_df.count(),
            'data': batch_df.collect()
        })

        # Write to storage
        batch_df.write.mode("append").parquet(str(tmp_path / "output"))

    # Create streaming source
    input_stream = spark.readStream \
        .format("rate") \
        .option("rowsPerSecond", 10) \
        .load()

    # Use foreachBatch
    query = input_stream \
        .writeStream \
        .foreachBatch(process_batch) \
        .start()

    # Process some batches
    import time
    time.sleep(3)

    query.stop()

    # Verify
    assert len(output_batches) > 0, "No batches processed"
    assert all(b['count'] > 0 for b in output_batches), "Empty batches"

    # Verify output files
    output_df = spark.read.parquet(str(tmp_path / "output"))
    assert output_df.count() > 0
```

### Delta Lake Test Utilities

```python
from delta import DeltaTable
from pyspark.sql.functions import expr

def test_delta_streaming_merge(spark, tmp_path):
    """Test streaming merge into Delta table"""

    delta_path = str(tmp_path / "delta_table")

    # Initial Delta table
    initial_data = [
        ("user1", 100),
        ("user2", 200)
    ]

    spark.createDataFrame(initial_data, ["user_id", "balance"]) \
        .write.format("delta").save(delta_path)

    # Streaming updates
    updates_path = str(tmp_path / "updates")
    updates_data = [
        ("user1", 50),   # Update existing
        ("user3", 300)   # Insert new
    ]

    spark.createDataFrame(updates_data, ["user_id", "amount"]) \
        .write.json(updates_path)

    # Read updates as stream
    updates_stream = spark.readStream \
        .schema("user_id STRING, amount INT") \
        .json(updates_path)

    # Merge function for foreachBatch
    def merge_updates(batch_df, batch_id):
        delta_table = DeltaTable.forPath(spark, delta_path)

        delta_table.alias("target").merge(
            batch_df.alias("updates"),
            "target.user_id = updates.user_id"
        ).whenMatchedUpdate(
            set={"balance": expr("target.balance + updates.amount")}
        ).whenNotMatchedInsert(
            values={
                "user_id": "updates.user_id",
                "balance": "updates.amount"
            }
        ).execute()

    # Run streaming merge
    query = updates_stream.writeStream \
        .foreachBatch(merge_updates) \
        .start()

    query.processAllAvailable()
    query.stop()

    # Verify final state
    result_df = spark.read.format("delta").load(delta_path)
    result_list = result_df.collect()

    # Check updates
    user1 = [r for r in result_list if r.user_id == "user1"][0]
    assert user1.balance == 150  # 100 + 50

    user3 = [r for r in result_list if r.user_id == "user3"][0]
    assert user3.balance == 300  # New insert
```

---

## Replay and Backfill Strategies

Streaming pipelines must handle replay scenarios: reprocessing historical data after bug fixes, schema changes, or data quality issues.

### Why Replay Matters

**Bug fixes**: Reprocess data after correcting transformation logic
**Schema changes**: Migrate data to new schema format
**Data quality**: Reprocess after fixing upstream data issues
**Feature backfill**: Compute new metrics on historical data
**Disaster recovery**: Rebuild state after data loss

### Kafka Offset Reset Strategies

```python
from confluent_kafka import Consumer, TopicPartition

def reset_to_earliest(consumer, topic):
    """Reset consumer to beginning of topic"""
    consumer.subscribe([topic])

    # Get assigned partitions (requires at least one poll)
    consumer.poll(timeout=1.0)
    partitions = consumer.assignment()

    # Seek to beginning
    for partition in partitions:
        partition.offset = 0  # OFFSET_BEGINNING
        consumer.seek(partition)

    print(f"Reset {topic} to earliest offset")


def reset_to_timestamp(consumer, topic, timestamp_ms):
    """Reset consumer to specific timestamp"""
    consumer.subscribe([topic])
    consumer.poll(timeout=1.0)

    partitions = consumer.assignment()

    # Set timestamp for offset lookup
    partitions_with_ts = [
        TopicPartition(p.topic, p.partition, timestamp_ms)
        for p in partitions
    ]

    # Lookup offsets for timestamp
    offset_partitions = consumer.offsets_for_times(partitions_with_ts)

    # Seek to timestamp offsets
    for partition in offset_partitions:
        if partition.offset >= 0:
            consumer.seek(partition)
            print(f"Reset partition {partition.partition} to offset {partition.offset}")


def reset_to_offset(consumer, topic, partition, offset):
    """Reset consumer to specific offset"""
    tp = TopicPartition(topic, partition, offset)
    consumer.assign([tp])
    consumer.seek(tp)

    print(f"Reset {topic}:{partition} to offset {offset}")


# Usage
consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'replay-group',
    'enable.auto.commit': False
})

# Replay from beginning
reset_to_earliest(consumer, 'user-events')

# Replay from specific timestamp (24 hours ago)
import time
yesterday_ms = int((time.time() - 86400) * 1000)
reset_to_timestamp(consumer, 'user-events', yesterday_ms)

# Replay from specific offset
reset_to_offset(consumer, 'user-events', partition=0, offset=12345)
```

### Consumer Group Management for Replay

```bash
# Kafka CLI tools for consumer group management

# List consumer groups
kafka-consumer-groups.sh --bootstrap-server localhost:9092 --list

# Describe consumer group (see current offsets)
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group my-app-group \
  --describe

# Reset offsets to earliest (dry run)
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group my-app-group \
  --topic user-events \
  --reset-offsets --to-earliest \
  --dry-run

# Reset offsets to earliest (execute)
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group my-app-group \
  --topic user-events \
  --reset-offsets --to-earliest \
  --execute

# Reset to specific offset
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group my-app-group \
  --topic user-events:0 \
  --reset-offsets --to-offset 50000 \
  --execute

# Reset to timestamp (ISO 8601)
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group my-app-group \
  --topic user-events \
  --reset-offsets --to-datetime 2026-01-01T00:00:00.000 \
  --execute
```

### Idempotent Replay Requirements

Design pipelines for idempotent replay: reprocessing produces same results.

**Deterministic transformations**: Same input always produces same output
**No external state dependencies**: Don't rely on external APIs that change over time
**Upsert semantics**: Writes should be idempotent (INSERT OR UPDATE, not INSERT)
**Versioned schemas**: Include schema version in data for migration replay
**Offset tracking**: Store processing offsets for exactly-once replay

```python
# Idempotent sink pattern
def write_idempotent(record):
    """Upsert to database (idempotent)"""
    query = """
        INSERT INTO events (event_id, user_id, action, timestamp)
        VALUES (?, ?, ?, ?)
        ON CONFLICT (event_id)
        DO UPDATE SET
            user_id = EXCLUDED.user_id,
            action = EXCLUDED.action,
            timestamp = EXCLUDED.timestamp
    """

    db.execute(query, (
        record['event_id'],
        record['user_id'],
        record['action'],
        record['timestamp']
    ))
```

### Backfill Patterns

#### Pattern 1: Replay from Kafka

Best when Kafka retention allows (data still in topic).

```python
def replay_from_kafka(topic, start_offset, end_offset):
    """Replay specific offset range from Kafka"""
    consumer = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'backfill-group',
        'enable.auto.commit': False
    })

    # Assign specific partition and offset
    tp = TopicPartition(topic, partition=0, offset=start_offset)
    consumer.assign([tp])
    consumer.seek(tp)

    processed = 0

    while True:
        msg = consumer.poll(timeout=1.0)

        if msg is None:
            continue

        if msg.error():
            raise Exception(f"Consumer error: {msg.error()}")

        # Stop at end offset
        if msg.offset() >= end_offset:
            break

        # Process message
        process_event(msg.value())
        processed += 1

        if processed % 1000 == 0:
            print(f"Processed {processed} events")

    consumer.close()
    print(f"Backfill complete: {processed} events")
```

#### Pattern 2: Batch Backfill + Resume Streaming

When Kafka retention expired, backfill from data lake then resume streaming.

```python
from pyspark.sql import SparkSession
from datetime import datetime

def batch_backfill(spark, start_date, end_date, output_table):
    """Batch backfill from data lake"""

    # Read historical data from S3/GCS
    df = spark.read.parquet("s3://data-lake/events/") \
        .filter(f"date >= '{start_date}' AND date < '{end_date}'")

    # Apply same transformations as streaming pipeline
    transformed = transform_events(df)

    # Write to same sink as streaming
    transformed.write \
        .format("delta") \
        .mode("overwrite") \
        .option("replaceWhere", f"date >= '{start_date}' AND date < '{end_date}'") \
        .save(output_table)

    print(f"Backfilled {transformed.count()} events")


def resume_streaming(spark, checkpoint_path, output_table, start_timestamp):
    """Resume streaming from specific timestamp"""

    # Read from Kafka starting at timestamp
    stream = spark.readStream \
        .format("kafka") \
        .option("kafka.bootstrap.servers", "localhost:9092") \
        .option("subscribe", "user-events") \
        .option("startingOffsetsByTimestamp",
                f'{{"user-events":{{"0":{start_timestamp}}}}}') \
        .load()

    # Apply transformations
    transformed = transform_events(stream)

    # Write to Delta with checkpointing
    query = transformed.writeStream \
        .format("delta") \
        .option("checkpointLocation", checkpoint_path) \
        .outputMode("append") \
        .start(output_table)

    return query


# Orchestrate backfill + streaming
spark = SparkSession.builder.appName("Backfill").getOrCreate()

# Step 1: Batch backfill historical data
batch_backfill(
    spark,
    start_date="2026-01-01",
    end_date="2026-02-01",
    output_table="/delta/events"
)

# Step 2: Resume streaming from end of backfill
backfill_end_ts = int(datetime(2026, 2, 1).timestamp() * 1000)
query = resume_streaming(
    spark,
    checkpoint_path="/checkpoints/events",
    output_table="/delta/events",
    start_timestamp=backfill_end_ts
)

query.awaitTermination()
```

#### Pattern 3: Time-Travel Replay

Kafka supports offset-by-timestamp lookup for time-travel replay.

```python
def time_travel_replay(topic, start_datetime, end_datetime):
    """Replay events within time range"""
    from datetime import datetime

    consumer = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'time-travel-group',
        'enable.auto.commit': False
    })

    # Convert datetime to milliseconds
    start_ts = int(start_datetime.timestamp() * 1000)
    end_ts = int(end_datetime.timestamp() * 1000)

    # Get partitions
    consumer.subscribe([topic])
    consumer.poll(timeout=1.0)
    partitions = consumer.assignment()

    # Lookup start offsets by timestamp
    start_partitions = [
        TopicPartition(p.topic, p.partition, start_ts)
        for p in partitions
    ]

    start_offsets = consumer.offsets_for_times(start_partitions)

    # Lookup end offsets by timestamp
    end_partitions = [
        TopicPartition(p.topic, p.partition, end_ts)
        for p in partitions
    ]

    end_offsets = consumer.offsets_for_times(end_partitions)

    # Seek to start offsets
    for partition in start_offsets:
        if partition.offset >= 0:
            consumer.seek(partition)

    # Process until end offsets
    processed = 0

    while True:
        msg = consumer.poll(timeout=1.0)

        if msg is None:
            continue

        if msg.error():
            raise Exception(f"Error: {msg.error()}")

        # Check if reached end offset for this partition
        partition_end = next(
            (p.offset for p in end_offsets
             if p.partition == msg.partition()),
            None
        )

        if partition_end and msg.offset() >= partition_end:
            print(f"Reached end for partition {msg.partition()}")
            # Remove this partition from assignment
            # (simplified - production needs proper handling)
            continue

        # Process message
        process_event(msg.value())
        processed += 1

    consumer.close()
    print(f"Time-travel replay complete: {processed} events")


# Usage
from datetime import datetime

time_travel_replay(
    topic='user-events',
    start_datetime=datetime(2026, 2, 1, 0, 0, 0),
    end_datetime=datetime(2026, 2, 2, 0, 0, 0)
)
```

### Testing Replay in Staging Environments

Create dedicated consumer groups for replay testing without affecting production.

```python
def test_replay_staging():
    """Test replay in staging environment"""

    # Staging consumer group (separate from prod)
    consumer = Consumer({
        'bootstrap.servers': 'staging-kafka:9092',
        'group.id': 'staging-replay-test',
        'enable.auto.commit': False
    })

    # Reset to known good state
    reset_to_timestamp(consumer, 'events', timestamp_ms=known_good_timestamp)

    # Process and verify
    results = []
    for _ in range(100):
        msg = consumer.poll(timeout=1.0)
        if msg and not msg.error():
            result = process_and_validate(msg)
            results.append(result)

    # Assertions
    assert len(results) == 100
    assert all(r['valid'] for r in results)

    consumer.close()
```

### Monitoring Backfill Progress

```python
import time
from confluent_kafka import Consumer, TopicPartition

def monitor_backfill_progress(topic, target_offset):
    """Monitor backfill progress to target offset"""

    admin_consumer = Consumer({
        'bootstrap.servers': 'localhost:9092',
        'group.id': 'backfill-progress-monitor'
    })

    # Get current offset
    admin_consumer.subscribe([topic])
    admin_consumer.poll(timeout=1.0)

    while True:
        positions = admin_consumer.position(admin_consumer.assignment())

        current_offset = sum(p.offset for p in positions)
        progress_pct = (current_offset / target_offset) * 100

        print(f"Progress: {current_offset}/{target_offset} ({progress_pct:.1f}%)")

        if current_offset >= target_offset:
            print("Backfill complete!")
            break

        time.sleep(10)  # Check every 10 seconds

    admin_consumer.close()
```

---

Back to [main skill](../SKILL.md)
