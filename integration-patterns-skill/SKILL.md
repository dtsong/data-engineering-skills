---
name: integration-patterns-skill
description: "Use this skill when designing data integrations or connecting systems. Covers iPaaS platforms (Workato, MuleSoft, Boomi), dlt pipelines, API patterns, CDC, webhooks, and Reverse ETL. Common phrases: \"connect these systems\", \"build a dlt pipeline\", \"event-driven architecture\", \"change data capture\". Do NOT use for stream processing frameworks (use streaming-data-skill) or pipeline scheduling (use data-orchestration-skill)."
model_tier: analytical
version: 1.0.0
---

# Integration Patterns Skill

Expert guidance for designing, implementing, and troubleshooting enterprise data integrations.

## When to Use

Activate when:
- Designing integrations between SaaS platforms (Salesforce, NetSuite, Stripe, Workday, ServiceNow)
- Evaluating iPaaS (Workato, MuleSoft, Boomi) vs DLT vs custom code
- Implementing CDC with Debezium, Snowflake Streams, or BigQuery CDC
- Building event-driven architectures with Kafka, Pub/Sub, or EventBridge
- Designing webhook receivers, Reverse ETL, or API integrations with pagination/rate limiting
- Building data sync patterns, file-based integrations, or canonical data models

## Scope Constraints

This skill covers enterprise data integration patterns. It does NOT cover: basic SQL, BI tools, infrastructure provisioning, or database optimization.

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| medium | Sonnet | Opus, Haiku | Haiku |

## Core Principles

**Loose Coupling:** Use queues, event buses, and async patterns. Implement circuit breakers to prevent cascading failures.

**Idempotency:** Use idempotency keys, upsert patterns, and deduplication logic. Assume network failures and duplicate messages will occur.

**Contract-First Design:** Use OpenAPI for REST, Protobuf for gRPC, Avro/JSON Schema for events. Version contracts; enforce schema validation at boundaries.

**Error Isolation:** Implement dead letter queues, per-integration retry logic, and clear failure boundaries. Log errors with context for troubleshooting.

**Data Freshness Awareness:** Match pattern to SLA: webhooks give sub-second latency, CDC near-real-time, batch may be hours old. Monitor actual vs expected freshness.

**Canonical Data Models:** Map external schemas to a shared canonical model at integration boundaries. Maintain crosswalk tables for ID mapping. Version canonical models and handle schema evolution.

## Integration Pattern Decision Matrix

| Pattern | Latency | Volume | Complexity | Best For |
|---------|---------|--------|------------|----------|
| Request/Reply (REST, gRPC) | Low (ms-sec) | Low-Med | Low | User-facing, CRUD |
| Pub/Sub Events | Low-Med (sec) | High | Medium | Event notifications, fan-out |
| CDC | Low (sec) | High | Med-High | DB replication, real-time analytics |
| Batch/File-based | High (hours) | Very High | Low | Bulk transfers, daily loads |
| Webhooks | Low (sec) | Medium | Medium | SaaS notifications, alerts |
| Reverse ETL | Med (min-hours) | Medium | Medium | Data activation, warehouse to CRM |
| DLT (Python-first) | Med (min) | High | Low-Med | Code-first ingestion, auto-schema |

## iPaaS vs DLT vs Custom Code

| Factor | iPaaS (Fivetran/Airbyte) | DLT | Custom Python |
|--------|--------------------------|-----|---------------|
| Setup time | Minutes (UI) | Hours (code) | Days (full build) |
| Connectors | 300+ managed | 50+ verified + custom | Unlimited |
| Schema mgmt | Auto-evolve only | Auto-evolve + contracts + Pydantic | Manual |
| Incremental | Built-in | Built-in with cursor state | Manual |
| Cost at scale | Per-MAR ($$+) | Free + compute ($) | Compute only ($) |
| Best for | Standard SaaS, non-technical teams | Custom APIs, nested data, Python teams | Unique protocols, ultra-low-latency |

**Rule of thumb:** Start iPaaS for standard SaaS connectors. Use DLT for custom logic, complex schemas, or cost control. Fall back to custom Python for unique requirements.

## iPaaS Platform Comparison

| Platform | Best For | Pricing | Complexity |
|----------|----------|---------|------------|
| Workato | Business ops, pre-built connectors | Per-task | Low |
| MuleSoft | Enterprise API management, governance | License + runtime | High |
| Boomi | Multi-cloud, B2B/EDI, MDM | Per-connection | Med-High |
| Zapier | Simple automations, SMB | Per-task | Very Low |
| Tray.io | Advanced logic, developer-friendly | Per-task | Medium |

## Reverse ETL / Data Activation

| Tool | Sync Modes | Warehouse Support | Pricing |
|------|------------|-------------------|---------|
| Hightouch | Upsert, mirror, append | Snowflake, BigQuery, Redshift, Databricks | Per-row, ~$500/mo |
| Census | Upsert, mirror, append, delete | Snowflake, BigQuery, Redshift, Databricks | Per-row, ~$1000/mo |
| Custom | Full control | Any | Dev + infra costs |

## Error Handling Strategy

Apply these layers for resilient integrations:
1. **Retry with backoff** — Use `tenacity` with exponential backoff for transient failures
2. **Circuit breaker** — Track failure count; open circuit after threshold; auto-recover after timeout
3. **Dead letter queue** — Persist failed messages with error context for manual review or replay
4. **Idempotency check** — Track processed message IDs to prevent duplicate processing

## Security Posture

See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for full framework.

**Credentials:** API keys, OAuth tokens, DB connections, webhook secrets via environment variables. Secrets managers for production.

| Capability | Tier 1 (Cloud-Native) | Tier 2 (Regulated) | Tier 3 (Air-Gapped) |
|------------|----------------------|--------------------|--------------------|
| API calls | Execute against dev | Generate for review | Generate only |
| CDC config | Deploy to dev | Generate for review | Generate only |
| Webhooks | Deploy and test | Generate with sig verification | Generate only |
| Reverse ETL | Execute against dev | Generate sync configs | Generate only |

**Credential best practices:** Use scoped/restricted keys. Prefer OAuth 2.0 over API keys. Store webhook secrets in env vars; always verify signatures. Prefer key-pair/IAM auth over passwords. Rotate on schedule.

## Reference Files

Load the appropriate reference for deep-dive guidance:

- [DLT Pipelines](references/dlt-pipelines.md) — Sources, resources, incremental loading, schema contracts, REST API source, testing, orchestration
- [Enterprise Connectors](references/enterprise-connectors.md) — Salesforce, NetSuite, Stripe, Workday, ServiceNow patterns
- [Event-Driven Architecture](references/event-driven-architecture.md) — Kafka, Pub/Sub, EventBridge, schema registry, delivery guarantees
- [iPaaS Platforms](references/ipaas-platforms.md) — Workato, MuleSoft, Boomi comparison, recipes, governance
- [CDC Patterns](references/cdc-patterns.md) — Debezium, Snowflake Streams, BigQuery CDC, backfill strategies
- [Data Mapping & Crosswalks](references/data-mapping-crosswalks.md) — Canonical models, crosswalk tables, schema drift detection

**Related skills:**
- For file-based DLT extraction and consulting portability, see [dlt-extraction-skill](../dlt-extraction-skill/SKILL.md)
- For DLT vs managed connector comparison, see [DLT vs Managed Connectors](../shared-references/data-engineering/dlt-vs-managed-connectors.md)
