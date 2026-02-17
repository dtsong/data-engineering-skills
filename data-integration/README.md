# Integration Patterns Skill

[![Claude Skill](https://img.shields.io/badge/Claude-Skill-8A2BE2)](https://github.com/dtsong/data-engineering-skills)

Expert guidance for designing enterprise integrations with iPaaS platforms, CDC patterns, event-driven architectures, and Reverse ETL.

## What This Skill Provides

### Integration Pattern Selection
- Decision matrix comparing REST, gRPC, Pub/Sub, CDC, webhooks, batch, and Reverse ETL
- Latency, volume, and complexity tradeoffs for each pattern
- Production-ready code examples for every pattern type
- Error handling strategies with retry logic and circuit breakers

### iPaaS Platform Guidance
- Workato, MuleSoft, Boomi, Zapier, Tray.io comparison matrix
- When to choose iPaaS vs custom code
- Pricing models and total cost of ownership analysis
- Recipe examples and best practices for each platform

### Enterprise System Connectors
- Salesforce, NetSuite, Stripe, Workday, ServiceNow integration patterns
- Auth strategies, rate limits, and pagination approaches
- API selection guidance (REST vs SOAP vs Bulk)
- Field mapping and data synchronization patterns

### Reverse ETL & Data Activation
- Hightouch and Census feature comparison
- Custom Reverse ETL implementation patterns
- Warehouse → operational system sync strategies
- Use cases for customer data activation

### Event-Driven Architectures
- Kafka, Google Pub/Sub, AWS EventBridge setup examples
- Schema registry and event versioning patterns
- Dead letter queues and error handling
- Producer/consumer code with deduplication logic

## Installation

```bash
git clone https://github.com/dtsong/data-engineering-skills ~/.claude/skills/data-engineering-skills
```

The data-integration will be automatically available in Claude Code.

## Quick Start Examples

```bash
# Design integration between Salesforce and data warehouse
"I need to sync Salesforce Accounts to Snowflake in near-real-time. Should I use CDC, webhooks, or API polling?"

# Evaluate iPaaS platforms
"Compare Workato vs MuleSoft for integrating NetSuite with 15 other SaaS apps. We need 50k transactions per day."

# Implement Reverse ETL
"Build a custom Reverse ETL pipeline from BigQuery to HubSpot to sync customer LTV scores hourly."

# Setup Change Data Capture
"Configure Debezium to stream PostgreSQL changes to Kafka, then load into Snowflake for analytics."

# Design webhook receiver
"Create a FastAPI webhook endpoint for Stripe events with signature verification and idempotency handling."
```

## Skill Structure

```
data-integration/
├── SKILL.md                              # Main skill prompt
└── references/
    ├── enterprise-connectors.md          # Salesforce, NetSuite, Stripe, Workday, ServiceNow
    ├── event-driven-architecture.md      # Kafka, Pub/Sub, EventBridge patterns
    ├── ipaas-platforms.md                # Workato, MuleSoft, Boomi deep dive
    ├── cdc-patterns.md                   # Debezium, Snowflake Streams, BigQuery CDC
    └── data-mapping-crosswalks.md        # Canonical models, crosswalk tables
```

## Learning Path

Follow this progression to master integration patterns:

1. **Start with SKILL.md** — Review the integration pattern decision matrix and core principles
2. **Choose Your Pattern** — Based on requirements, dive into the relevant reference file:
   - Building SaaS integrations? → `enterprise-connectors.md`
   - Need real-time data sync? → `cdc-patterns.md` or `event-driven-architecture.md`
   - Evaluating build vs buy? → `ipaas-platforms.md`
   - Moving warehouse data to operational systems? → Review Reverse ETL section in SKILL.md
3. **Master Data Consistency** — Read `data-mapping-crosswalks.md` for canonical model design
4. **Implement Error Handling** — Study retry strategies, circuit breakers, and DLQ patterns in SKILL.md

## Requirements

- **Claude Code** — This skill is designed for Claude Code's skill system
- **Integration Tools** (as needed):
  - Kafka, Debezium for CDC and event streaming
  - Snowflake, BigQuery, or Redshift for data warehousing
  - Docker for local testing of integration components
  - Python 3.9+ with requests, tenacity, kafka-python libraries

## Contributing

Contributions are welcome! If you have:
- Additional integration patterns or platform examples
- Real-world case studies and lessons learned
- Improved error handling or retry strategies
- New enterprise connector patterns

Please submit a pull request or open an issue.

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
