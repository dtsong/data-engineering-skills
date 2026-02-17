# Streaming Data Skill

![Claude Skill](https://img.shields.io/badge/Claude-Skill-8A63D2?logo=anthropic)
![Kafka](https://img.shields.io/badge/Apache%20Kafka-231F20?logo=apachekafka&logoColor=white)
![Flink](https://img.shields.io/badge/Apache%20Flink-E6526F?logo=apacheflink&logoColor=white)
![Snowflake](https://img.shields.io/badge/Snowflake-29B5E8?logo=snowflake&logoColor=white)
![BigQuery](https://img.shields.io/badge/BigQuery-669DF6?logo=googlebigquery&logoColor=white)

Expert guidance for building real-time and near-real-time data pipelines with Kafka, Flink, Spark Streaming, and warehouse streaming ingestion.

## What This Skill Provides

### Architecture Selection
- Batch vs micro-batch vs true streaming decision framework
- Lambda vs Kappa architecture tradeoffs
- Warehouse-native streaming (Snowpipe, BigQuery Storage Write API) evaluation
- Latency, complexity, and cost analysis for each approach

### Stream Processing
- Kafka setup, exactly-once semantics, and schema evolution patterns
- Apache Flink DataStream API and Flink SQL for complex event processing
- Spark Structured Streaming for unified batch/stream workloads
- Windowing patterns: tumbling, sliding, session, and global windows
- State management, checkpointing, and fault tolerance strategies

### Warehouse Streaming
- Snowpipe Streaming with Snowflake Ingest SDK for sub-second latency
- BigQuery Storage Write API with exactly-once guarantees
- Dynamic Tables (Snowflake) and Materialized Views for incremental updates
- Choosing between stream processing frameworks vs warehouse-native streaming

### Testing & Monitoring
- Stream testing with embedded Kafka and testcontainers
- Consumer lag monitoring and alerting thresholds
- Backpressure detection and handling
- Schema Registry integration and compatibility testing

## Installation

```bash
git clone https://github.com/dtsong/data-engineering-skills ~/.claude/skills/data-engineering-skills
```

The skill will be auto-discovered by Claude Code when you work on streaming data projects.

## Quick Start Examples

### Should I use batch or streaming?

```
Should I use batch or streaming for my real-time dashboard that updates every 5 minutes with hourly sales aggregations?
```

Claude will analyze your latency requirements, complexity constraints, and team capabilities to recommend between traditional batch, micro-batch (Spark Streaming), or true streaming (Flink/Kafka Streams).

### Set up Kafka with exactly-once semantics

```
Set up Kafka with exactly-once semantics for our payment events. We need producers, consumers, and schema evolution support.
```

Claude will configure Kafka producers with idempotent writes and transactional IDs, set up consumers with isolation.level=read_committed, integrate Schema Registry with Avro, and provide monitoring for exactly-once violations.

### Configure Snowpipe Streaming

```
Configure Snowpipe Streaming to ingest from our Kafka topic into Snowflake with sub-second latency. We have 10 Kafka partitions.
```

Claude will set up Snowflake Ingest SDK with channels mapped to Kafka partitions, implement offset tracking for exactly-once delivery, handle backpressure and retries, and add monitoring for ingestion lag.

### Choose between Flink and Spark Streaming

```
Help me choose between Flink and Spark Streaming for our use case: processing clickstream events with sessionization, 1-second latency requirement, and 10TB daily volume.
```

Claude will compare state management capabilities, latency characteristics, SQL support, operational complexity, and provide a recommendation with code examples for your specific requirements.

### Add monitoring to Kafka pipeline

```
Add monitoring and alerting to our Kafka consumer pipeline. We need to track lag, throughput, and error rates.
```

Claude will configure Prometheus exporters for Kafka metrics, create Grafana dashboards for consumer lag and throughput, set up alerts for critical thresholds (lag > 1M messages, error rate > 0.1%), and implement dead letter queue patterns.

## Skill Structure

```
event-streaming/
├── SKILL.md                           # Main skill file (this document)
├── README.md                          # This file
└── references/
    ├── kafka-deep-dive.md             # Kafka architecture, exactly-once, Connect, ksqlDB
    ├── flink-spark-streaming.md       # Flink DataStream, SQL, watermarks, state
    ├── warehouse-streaming-ingestion.md # Snowpipe, Dynamic Tables, BQ Storage Write API
    └── stream-testing-patterns.md     # Embedded Kafka, testcontainers, replay, backfill
```

## Learning Path

1. **Start with SKILL.md** — Read the architecture decision matrix and core principles to understand when to use streaming vs batch, and which streaming approach fits your requirements.

2. **Explore Kafka Deep Dive** — If you're building Kafka pipelines, dive into `references/kafka-deep-dive.md` for producer/consumer configuration, exactly-once semantics, Kafka Connect, and ksqlDB patterns.

3. **Study Stream Processing Frameworks** — Read `references/flink-spark-streaming.md` to compare Flink and Spark Streaming, learn windowing patterns, and implement stateful stream processing.

4. **Learn Warehouse Streaming** — If your team is SQL-first or you want simpler infrastructure, explore `references/warehouse-streaming-ingestion.md` for Snowpipe Streaming, Dynamic Tables, and BigQuery Storage Write API.

5. **Master Testing Patterns** — Use `references/stream-testing-patterns.md` to learn how to unit test streaming applications, run integration tests with testcontainers, and safely replay streams for backfills.

## Requirements

- **Claude Code** — This skill is designed for use with Claude Code CLI
- **Streaming Platform Knowledge** — Basic understanding of Kafka, event-driven architectures, or real-time data processing
- **Data Engineering Fundamentals** — Familiarity with ETL concepts, data modeling, and SQL

## Contributing

Contributions are welcome! Please follow the [Contributing Guidelines](../CONTRIBUTING.md) in the main repository.

If you encounter issues or have suggestions for improving the event-streaming, please open an issue at https://github.com/dtsong/data-engineering-skills/issues.

## License

Copyright 2026 Daniel Song

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
