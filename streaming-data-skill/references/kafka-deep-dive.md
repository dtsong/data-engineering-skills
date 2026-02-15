## Contents

- [Kafka Architecture](#kafka-architecture)
- [Producer Configuration](#producer-configuration)
- [Consumer Configuration](#consumer-configuration)
- [Exactly-Once Semantics](#exactly-once-semantics)
- [Kafka Connect](#kafka-connect)
- [ksqlDB](#ksqldb)
- [Security](#security)
- [Production Tuning](#production-tuning)

---

# Kafka Deep Dive

> **Part of:** [streaming-data-skill](../SKILL.md)
> **Purpose:** Kafka architecture, producer/consumer configuration, exactly-once semantics, Kafka Connect, ksqlDB, security, and production tuning

## Kafka Architecture

**Brokers** store data and handle client requests. **Topics** are divided into **partitions** for parallelism. Each partition has a leader (handles reads/writes) and follower replicas (fault tolerance). Replication factor of 3 is standard.

**KRaft vs ZooKeeper**: KRaft (Kafka 3.3+) is production-ready, self-managed metadata quorum. ZooKeeper deprecated in Kafka 4.0+. Use KRaft for new deployments.

**ISR (In-Sync Replicas)**: Replicas caught up within `replica.lag.time.max.ms`. On leader failure, controller selects new leader from ISR.

**Log retention**: Time-based (`log.retention.hours=168`) or size-based (`log.retention.bytes`). **Log compaction** (`cleanup.policy=compact`) retains latest value per key — use for CDC changelogs and config topics.

**Partition count**: `max(throughput_required / partition_throughput, max_concurrent_consumers)`. Start with 2-3x expected consumer count.

## Producer Configuration

| Parameter | Recommendation |
|---|---|
| `acks` | `all` for durability |
| `enable.idempotence` | `true` (prevents duplicates) |
| `compression.type` | `lz4` (fast) or `zstd` (best ratio) |
| `batch.size` / `linger.ms` | 16-32KB / 10-100ms for throughput |

```python
# Idempotent producer (Python confluent-kafka)
producer = Producer({
    'bootstrap.servers': 'localhost:9092',
    'enable.idempotence': True,
    'acks': 'all',
    'compression.type': 'lz4'
})
producer.produce('topic', key='key1', value='data', callback=delivery_report)
producer.flush()
```

**Transactional producer**: Set `transactional.id` for atomic writes across partitions. Call `init_transactions()`, `begin_transaction()`, `commit_transaction()`.

## Consumer Configuration

| Parameter | Recommendation |
|---|---|
| `enable.auto.commit` | `false` for manual control |
| `auto.offset.reset` | `latest` for new data |
| `partition.assignment.strategy` | `cooperative-sticky` (Kafka 2.4+) |
| `session.timeout.ms` | 10000-45000 |
| `group.instance.id` | Set for static membership (avoids rebalance on restart) |

Commit offsets after successful processing. Use batch commit pattern for throughput. On deserialization errors, log to dead-letter queue and commit to skip poison pills.

## Exactly-Once Semantics

| Level | Implementation | Use Case |
|---|---|---|
| At-Most-Once | `acks=0`, no retries | Lossy metrics/logs |
| At-Least-Once | `acks=all`, idempotent consumer | Most pipelines |
| Exactly-Once | Transactional producer + `read_committed` consumer | Financial, billing |

**EOS pipeline**: Transactional producer wraps consume-transform-produce in a transaction, committing consumer offsets atomically with output via `send_offsets_to_transaction()`.

**Kafka Streams EOS**: Set `processing.guarantee=exactly_once_v2`.

Skip EOS when sinks are idempotent (upserts), metrics are approximate, or downstream deduplicates.

## Kafka Connect

**Source connectors** (external -> Kafka): Debezium (CDC), JDBC (incremental). **Sink connectors** (Kafka -> external): S3 Parquet, BigQuery, Snowflake, Elasticsearch.

Use distributed mode for production (`connect-distributed`). Configure dead-letter queues:

```json
{
  "errors.tolerance": "all",
  "errors.deadletterqueue.topic.name": "dlq-connector-errors",
  "errors.deadletterqueue.topic.replication.factor": "3",
  "errors.deadletterqueue.context.headers.enable": "true"
}
```

**SMTs**: RegexRouter (routing), MaskField (PII), InsertField (timestamps). **Converters**: Avro (schema registry), JSON, Protobuf.

Monitor via REST API: `GET /connectors/{name}/status`, `POST /connectors/{name}/restart`.

## ksqlDB

**Streams** = unbounded append-only events. **Tables** = current state with upserts. Create from Kafka topics with `CREATE STREAM/TABLE ... WITH (KAFKA_TOPIC=..., VALUE_FORMAT='JSON')`.

Supports tumbling, hopping, session windows. Pull queries for point lookups on materialized state; push queries for continuous results.

Use ksqlDB for SQL-first simple transforms. Use Kafka Streams for complex Java logic. Use Flink SQL for complex streaming + batch.

## Security

| Mechanism | Use Case |
|---|---|
| SASL/SCRAM-SHA-512 | Production (recommended) |
| mTLS | High-security environments |
| OAUTHBEARER | Cloud-native, token-based |
| PLAIN | Development only |

Configure ACLs per topic and consumer group: `kafka-acls --add --allow-principal User:alice --operation Read --topic user-events`. Use prefixed ACLs for namespaced topics.

## Production Tuning

**JVM**: 4-8GB heap (`-Xms6g -Xmx6g`), G1GC, remainder to OS page cache.

**OS**: File descriptors 100K+, `vm.swappiness=1`, deadline/noop disk scheduler for SSDs.

**Capacity planning**: `total_storage = daily_throughput x retention_days x replication_factor`. Single broker effective throughput = `min(disk_bw, network_bw) / replication_factor`.

**Key alerts**: Under-replicated partitions > 0 (5min), offline partitions > 0, consumer lag > 1M, disk > 80%, producer errors > 1%, frequent rebalancing (> 5/hour).

---

Back to [main skill](../SKILL.md)
