---
name: data-orchestration-skill
description: "Use this skill when scheduling, orchestrating, or monitoring data pipelines. Covers Dagster assets, Airflow DAGs, Prefect flows, sensors, retries, alerting, and cross-tool integrations (dagster-dbt, dagster-dlt). Common phrases: \"schedule this pipeline\", \"Dagster vs Airflow\", \"add retry logic\", \"pipeline alerting\". Do NOT use for building transformations (use dbt-skill or python-data-engineering-skill) or designing integration patterns (use integration-patterns-skill)."
license: Apache-2.0
metadata:
  author: Daniel Song
  version: 1.0.0
---

# Data Orchestration Skill for Claude

Expert guidance for orchestrating data pipelines. Dagster-first for greenfield projects, Airflow for brownfield. Covers scheduling, dependencies, monitoring, retries, alerting, and dbt/DLT integration.

## When to Use This Skill

**Activate when:**
- Choosing between orchestration tools (Dagster vs Airflow vs Prefect vs embedded)
- Building Dagster assets, resources, sensors, schedules, or partitions
- Writing Airflow DAGs, operators, TaskFlow tasks, or connections
- Integrating orchestrators with dbt or DLT
- Implementing retry logic, alerting, failure handling, or partitioned backfills
- Deciding whether you need an orchestrator at all

**Don't use for:** dbt model writing (use `dbt-skill`), DLT source/destination config (use `integration-patterns-skill`), Kafka/Flink streaming (use `streaming-data-skill`), IaC provisioning, or CI/CD pipelines.

## Scope Constraints

- Generate orchestration code, DAG definitions, asset configs, and scheduling logic only.
- Credential management: reference environment variables and secrets managers. Never hardcode secrets. See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md).
- Limit scope to orchestration concerns. Hand off transformation logic to dbt-skill and ingestion logic to integration-patterns-skill.

## Core Principles

1. **Assets over tasks** — Define persistent data artifacts (tables, views, models), not computation steps. Asset lineage is visible, dependencies declarative, backfills targeted, freshness observable.
2. **Idempotent runs** — Use MERGE/upsert, partition by date/key, track state externally. Every run must be safe to re-execute.
3. **Declarative dependencies** — Declare dependencies; the framework resolves execution order.
4. **Observable pipelines** — Log metadata (row counts, schema changes, execution times). Monitor freshness SLAs. Trace lineage from source to dashboard. Alert with actionable context.
5. **Graceful failure** — Retry with backoff for transient failures. Re-run only failed assets. Capture failed records via dead letter patterns. Group alerts to prevent fatigue.

---

## Orchestrator Decision Matrix

| Factor | Dagster | Airflow | Prefect | Embedded |
|--------|---------|---------|---------|----------|
| **Philosophy** | Asset-oriented | Task-oriented | Flow-oriented | Tool-native |
| **Best for** | Greenfield platforms | Brownfield, large DAGs | Python-native, event-driven | Single-tool workflows |
| **dbt integration** | `dagster-dbt` (first-class) | `cosmos` (good) | CLI wrapper | Native (dbt Cloud) |
| **DLT integration** | `dagster-dlt` (first-class) | Task wrapper | Task wrapper | N/A |
| **Asset lineage** | Built-in, UI-native | Via plugins (limited) | Via artifacts | Tool-specific |
| **Partitioning** | First-class | Dynamic task mapping | Map/reduce | Tool-specific |
| **Local dev** | `dagster dev` (full UI) | Local executor (limited) | `prefect server start` | N/A |
| **Managed offering** | Dagster Cloud | MWAA, Composer, Astronomer | Prefect Cloud | Built into platform |

See [Embedded Orchestration Reference](references/embedded-orchestration.md) for dbt Cloud, Databricks Workflows, Snowflake Tasks, and Prefect patterns.

---

## The Trifecta: Dagster + DLT + dbt

Each tool handles one concern:

| Layer | Tool | Responsibility |
|-------|------|----------------|
| **Orchestration** | Dagster | Scheduling, dependency resolution, monitoring, alerting |
| **Ingestion** | DLT | Extract from sources, load to warehouse (raw layer) |
| **Transformation** | dbt | SQL transformations (staging, intermediate, marts) |

```
┌─────────────────────────────────────────────────────┐
│                  Dagster (Orchestrator)              │
│  ┌───────────┐     ┌────────────┐     ┌──────────┐ │
│  │ DLT Assets│ ──→ │ dbt Assets │ ──→ │ Quality  │ │
│  │ (ingest)  │     │ (transform)│     │ (assert) │ │
│  └───────────┘     └────────────┘     └──────────┘ │
│       ▼                  ▼                  ▼       │
│  ┌──────────────────────────────────────────────┐   │
│  │         Snowflake / BigQuery                 │   │
│  │  raw.* → staging.* → intermediate.* → marts.*│  │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Key benefits:** DLT assets auto-depend on source availability. dbt assets auto-depend on raw tables DLT creates. Dagster shows complete lineage from API to marts. Backfills target specific date ranges across both DLT and dbt. Failures in DLT prevent dbt from running on stale data.

For full trifecta code example, see [Dagster Integrations Reference](references/dagster-integrations.md).

---

## Dagster Quickstart

```bash
pip install dagster dagster-webserver
dagster dev -f my_pipeline.py        # Full UI at http://localhost:3000
```

For asset examples (basic, resources, schedules, sensors), see [Dagster Patterns Reference](references/dagster-patterns.md).
For dbt and DLT integrations, see [Dagster Integrations Reference](references/dagster-integrations.md).

---

## Airflow Quickstart

Airflow stores credentials in **Connections** — never in DAG code. Configure via Airflow UI, environment variables (`AIRFLOW_CONN_*`), or secrets backends (Vault, AWS SM, GCP SM).

For TaskFlow API, classic operator pattern, dynamic task mapping, `cosmos` dbt integration, and managed Airflow (MWAA/Composer/Astronomer), see [Airflow Patterns Reference](references/airflow-patterns.md).

---

## Common Patterns

### Retry Strategy

```python
# Dagster
@asset(retry_policy=RetryPolicy(max_retries=3, delay=30, backoff=Backoff.EXPONENTIAL))
def flaky_api_asset():
    return call_external_api()

# Airflow
default_args = {"retries": 3, "retry_delay": timedelta(minutes=5),
                "retry_exponential_backoff": True, "max_retry_delay": timedelta(minutes=30)}
```

### Alerting

```python
# Dagster: freshness policies
@asset(freshness_policy=FreshnessPolicy(maximum_lag_minutes=120))
def fct_orders(stg_orders): ...
# Configure Slack/PagerDuty alerts in Dagster Cloud or via dagster-slack

# Airflow: failure callbacks
def on_failure_callback(context):
    send_slack_alert(channel="#data-alerts",
        message=f"Task {context['dag'].dag_id}.{context['task'].task_id} failed on {context['ds']}")
```

### Partitioned Backfills

```python
# Dagster: daily partitions
daily_partitions = DailyPartitionsDefinition(start_date="2024-01-01")

@asset(partitions_def=daily_partitions)
def daily_orders(context):
    date = context.partition_key
    orders = fetch_orders(date=date)
    load_to_warehouse(orders, partition=date)
# Backfill via UI (select range → Materialize) or CLI:
# dagster asset materialize --partition "2024-01-01...2024-01-31"
```

---

## Security Posture

This skill generates orchestration code including DAG definitions, asset configurations, and scheduling logic.
See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for the full security framework.

**Credentials required**: Warehouse connections, API keys, secrets manager access, alerting webhooks
**Where to configure**: Dagster EnvVar resources, Airflow Connections, environment variables
**Minimum role/permissions**: Orchestrator service account with scoped warehouse access

| Capability | Tier 1 (Cloud-Native) | Tier 2 (Regulated) | Tier 3 (Air-Gapped) |
|------------|----------------------|--------------------|--------------------|
| Execute pipelines | Against dev/staging | Generate code for review | Generate code only |
| Configure schedules | Deploy to dev | Generate configs for review | Generate configs only |
| Manage connections | Configure dev connections | Generate templates | Document requirements |
| Backfill data | Execute against dev | Generate plans for review | Generate plans only |

---

## Reference Files

- [Dagster Patterns](references/dagster-patterns.md) — Assets, resources, sensors, schedules, partitions, backfills, I/O managers, asset checks
- [Dagster Integrations](references/dagster-integrations.md) — `dagster-dbt`, `dagster-dlt`, trifecta example, dagster-k8s, dagster-cloud
- [Airflow Patterns](references/airflow-patterns.md) — TaskFlow API, operators, connections, dynamic task mapping, `cosmos`, MWAA/Composer
- [Embedded Orchestration](references/embedded-orchestration.md) — When NOT to add an orchestrator: dbt Cloud, Databricks Workflows, Snowflake Tasks, Prefect
