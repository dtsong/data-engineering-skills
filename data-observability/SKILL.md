---
name: data-observability
description: "Use this skill when implementing monitoring, alerting, and incident response for data pipelines. Covers freshness monitoring, volume anomaly detection, schema change detection, alerting patterns, and incident response workflows. Common phrases: \"data freshness\", \"pipeline monitoring\", \"data anomaly\", \"schema drift\", \"data alerting\", \"incident response\", \"data observability\", \"stale data\". Do NOT use for writing dbt models (use dbt-transforms), pipeline scheduling (use data-pipelines), or data quality testing as deliverables (use data-testing)."
model:
  preferred: sonnet
  acceptable: [sonnet, opus]
  minimum: sonnet
  allow_downgrade: false
  reasoning_demand: medium
version: 0.1.0
---

# Data Observability Skill

Generates monitoring configurations, alerting rules, and incident response workflows for data pipelines. Silent failures are failed engagements — this skill makes them loud.

## When to Use This Skill

**Activate when:** Setting up freshness monitoring for data sources, detecting volume anomalies in pipeline loads, implementing schema change detection, configuring alerting (Slack, PagerDuty, email), building incident response runbooks, or establishing SLA-driven observability for data pipelines.

**Don't use for:**
- Writing dbt models or transformations -> use `dbt-transforms`
- Scheduling or orchestrating pipelines -> use `data-pipelines`
- Data quality testing as deliverables -> use `data-testing`
- Loading raw files into DuckDB without monitoring intent -> use `duckdb`

## Scope Constraints

- Generates monitoring configurations, SQL queries, and alerting rules — does not deploy infrastructure or provision cloud resources.
- Local-first: generated configs target the user's existing orchestrator and tools; no SaaS vendor lock-in unless explicitly requested.
- Security tier default: Tier 1 (metadata only). User must explicitly elevate to Tier 2 (sample data) or Tier 3 (full data access).
- Reference files loaded one at a time — never pre-load multiple references simultaneously.
- No cross-references to other specialist skills; use handoff protocol for adjacent work.

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| medium | Sonnet | Sonnet, Opus | Sonnet |

## Core Principles

1. **Silent failures are unacceptable** — Every data pipeline must have at least freshness and volume monitoring. Unmonitored pipelines are ticking time bombs.
2. **Five pillars** — Observability covers freshness, volume, schema, distribution, and lineage. Address each pillar proportional to the pipeline's criticality.
3. **Alert on actionable signals only** — Every alert must have a clear owner, severity level, and runbook. Noisy alerts erode trust faster than no alerts.
4. **Observability as code** — Monitoring configs, alert rules, and SLA definitions live in version control alongside pipeline code. No click-ops.
5. **SLA-driven** — Define freshness and volume SLAs first, then derive monitoring thresholds. Work backwards from business requirements, not forward from technical defaults.

## Five Pillars

| Pillar | What It Monitors | Tool Support | Default Severity |
|--------|-----------------|--------------|-----------------|
| Freshness | Time since last successful load | dbt source freshness, Dagster freshness policies, custom SQL | P1 (error) |
| Volume | Row counts vs. historical baselines | Custom SQL, dbt tests, Great Expectations | P1 (error) |
| Schema | Column additions, removals, type changes | dbt contracts, DLT schema contracts, schema snapshots | P2 (warning) |
| Distribution | Statistical drift in column values | Great Expectations, custom SQL, Monte Carlo | P3 (info) |
| Lineage | Upstream/downstream dependency tracking | dbt docs, Dagster asset graph, DataHub | P3 (info) |

**Load reference files** for implementation details on each pillar.

## Procedure

> **Progress checklist** (tick off as you complete each step):
> - [ ] 1. Classify observability need
> - [ ] 2. Assess current monitoring
> - [ ] 3. Generate monitoring configuration
> - [ ] 4. Set up alerting
> - [ ] 5. Create incident runbook (if requested)

> **Compaction recovery:** If context is compressed mid-procedure, re-read this SKILL.md to restore context. Check which checklist items are complete, then resume from the next unchecked step.

### Step 1 -- Classify observability need

Determine which mode applies before generating any configuration:

- **Pillar-specific mode**: User wants monitoring for one specific pillar (freshness, volume, schema). Load the corresponding reference file.
- **Full-stack mode**: User wants end-to-end observability setup. Work through pillars sequentially by priority: freshness -> volume -> schema -> alerting.
- **Incident mode**: User wants incident response workflow. Skip to Step 5 and load incident-response.md.
- **Alerting mode**: User wants alerting configuration only. Skip to Step 4 and load alerting-patterns.md.

### Step 2 -- Assess current monitoring

Ask these questions if not already provided:
- What orchestrator? (Dagster, Airflow, dbt Cloud, none)
- What data warehouse / lakehouse? (Snowflake, BigQuery, DuckDB, Postgres)
- What notification channels exist? (Slack, PagerDuty, email)
- What are the business-critical SLAs? (e.g., "dashboard must refresh by 8am EST")

### Step 3 -- Generate monitoring configuration

Based on classification, load the appropriate reference file and generate configs:

- Freshness monitoring -> Load **[freshness-monitoring.md](references/freshness-monitoring.md)**
- Volume anomaly detection -> Load **[volume-anomaly-detection.md](references/volume-anomaly-detection.md)**
- Schema change detection -> Load **[schema-change-detection.md](references/schema-change-detection.md)**

Generate SQL queries, dbt YAML configs, or orchestrator-native monitoring rules. Unload reference file after generating configuration before loading the next.

### Step 4 -- Set up alerting

Load **[alerting-patterns.md](references/alerting-patterns.md)** and generate:

1. Severity classification for each monitor (P0-P3)
2. Notification routing (which channel for which severity)
3. Alert deduplication and cooldown rules
4. Runbook link for each alert type

Unload alerting-patterns.md after generating configuration.

### Step 5 -- Create incident runbook (incident mode or when requested)

Load **[incident-response.md](references/incident-response.md)** and generate:

1. Incident classification criteria
2. Triage workflow steps
3. Communication templates
4. Recovery and verification procedures

## Security Posture

# SECURITY: This skill generates monitoring configurations and SQL queries for local execution only. No network calls, credential access, or data file reads are performed by Claude. Generated configs reference local infrastructure — validate connection strings before deployment.

See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for the full framework.
See [Consulting Security Tier Model](../shared-references/data-engineering/security-tier-model.md) for tier definitions.

| Capability | Tier 1 (Default) | Tier 2 (Sampled) | Tier 3 (Full Access) |
|------------|-----------------|-------------------|---------------------|
| Monitoring config | Schema/metadata only | Stats on sample data | Full data profiling |
| Alert rules | Template with placeholders | Populated from samples | Fully configured |
| Freshness queries | Generate SQL only | Execute on samples | Execute on full data |
| Incident runbooks | Generic templates | Customized to pipeline | Fully populated |

### Input Sanitization

When user provides connection strings, table names, or file paths for monitoring configs:
- Validate table/schema names contain only alphanumeric characters, underscores, and dots.
- Reject paths containing `..`, `~`, environment variables, or shell metacharacters.
- Never interpolate user-provided strings directly into shell commands.
- Sanitize Slack webhook URLs — never log or echo them in generated configs.

## Reference Files

Reference files loaded on demand — one at a time:

- **[freshness-monitoring.md](references/freshness-monitoring.md)** — dbt source freshness config, custom freshness queries, SLA thresholds, stale data patterns, DuckDB freshness checks. Load at Step 3 for freshness monitoring.
- **[volume-anomaly-detection.md](references/volume-anomaly-detection.md)** — Row count baselines, spike/drop detection, zero-row detection, dbt volume tests, seasonal adjustment. Load at Step 3 for volume monitoring.
- **[schema-change-detection.md](references/schema-change-detection.md)** — dbt contracts, DLT schema contracts, schema snapshots, diffing patterns, migration docs. Load at Step 3 for schema monitoring.
- **[alerting-patterns.md](references/alerting-patterns.md)** — Dagster/Airflow alerting, Slack webhooks, PagerDuty, severity levels, alert fatigue prevention. Load at Step 4.
- **[incident-response.md](references/incident-response.md)** — Incident classification, triage workflow, impact assessment, communication templates, postmortem template, backfill patterns. Load at Step 5 (incident mode or when requested).

## Handoffs

- **Orchestrator-native monitoring** -> [data-pipelines](../data-pipelines/SKILL.md) (Dagster freshness policies, Airflow SLA misses as part of DAG definition)
- **dbt source freshness and test alerting** -> [dbt-transforms](../dbt-transforms/SKILL.md) (source freshness YAML, custom test severity)
- **Packaging observability as deliverable** -> [client-delivery](../client-delivery/SKILL.md) (engagement scaffolding, client handoff of monitoring setup)
- **Data quality validation** -> [data-testing](../data-testing/SKILL.md) (quality checks that feed into observability monitors)
