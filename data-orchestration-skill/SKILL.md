---
name: data-orchestration-skill
description: "Use when orchestrating data pipelines — Dagster assets, Airflow DAGs, Prefect flows, scheduling, sensors, retries, alerting, dagster-dbt integration, dagster-dlt integration, or choosing between orchestration tools"
license: Apache-2.0
metadata:
  author: Daniel Song
  version: 1.0.0
---

# Data Orchestration Skill for Claude

Expert guidance for orchestrating data pipelines across modern and legacy tools. Dagster-first for greenfield projects, Airflow secondary for brownfield environments. Covers the full lifecycle: scheduling, dependency management, monitoring, retries, alerting, and integration with dbt and DLT.

## When to Use This Skill

**Activate this skill when:**

- Choosing between orchestration tools (Dagster vs Airflow vs Prefect vs embedded)
- Building Dagster assets, resources, sensors, schedules, or partitions
- Writing Airflow DAGs, operators, TaskFlow tasks, or connections
- Integrating orchestrators with dbt (`dagster-dbt`, `cosmos`) or DLT (`dagster-dlt`)
- Designing scheduling strategies (cron, sensors, event-driven)
- Implementing retry logic, alerting, and failure handling for pipelines
- Setting up partitioned backfills or historical reprocessing
- Deciding whether you even need an orchestrator (vs embedded scheduling)

**Don't use this skill for:**

- dbt model writing or testing (use `dbt-skill`)
- DLT pipeline source/destination configuration (use `integration-patterns-skill`)
- Kafka/Flink stream processing (use `streaming-data-skill`)
- Infrastructure provisioning (use Terraform/IaC patterns)
- CI/CD pipeline configuration (use CI/CD patterns)

## Core Principles

### 1. Assets Over Tasks

Modern orchestration thinks in **assets** (data artifacts) rather than **tasks** (computation steps). An asset is a persistent object in your data platform — a table, view, ML model, or file. Define what you want to exist, not just what to run.

```
# Task-oriented (Airflow legacy pattern):
extract_task >> transform_task >> load_task

# Asset-oriented (Dagster modern pattern):
raw_orders → stg_orders → fct_orders → revenue_dashboard
```

**Why assets win:** Asset lineage is visible, dependencies are declarative, backfills target specific assets, and freshness is observable.

### 2. Idempotent Runs

Every pipeline run should produce the same result when executed multiple times with the same inputs. This means:

- Use `MERGE`/upsert instead of `INSERT` for mutable data
- Partition data by date or logical key for clean re-execution
- Track state externally (not in pipeline code) for incremental loads
- Design for "run it again" — never assume single execution

### 3. Declarative Dependencies

Dependencies between pipeline steps should be declared, not orchestrated imperatively. Let the framework resolve execution order.

```python
# Dagster: dependencies are implicit via asset references
@asset
def stg_orders(raw_orders):  # Depends on raw_orders asset
    return transform(raw_orders)

# Airflow: dependencies are explicit but declarative
extract >> transform >> load  # Not: if extract.success then transform()
```

### 4. Observable Pipelines

Every pipeline should be observable: you should know what ran, when it ran, whether it succeeded, what data it produced, and how fresh that data is.

- **Metadata logging**: Record row counts, schema changes, execution times
- **Freshness checks**: Alert when assets are stale beyond SLA
- **Lineage tracking**: Trace data from source to dashboard
- **Failure alerts**: Notify the right people with actionable context

### 5. Graceful Failure

Pipelines will fail. Design for it:

- **Retry with backoff**: Transient failures (API timeouts, rate limits) should auto-retry
- **Partial re-execution**: Only re-run failed assets, not the entire pipeline
- **Dead letter patterns**: Capture failed records for investigation, don't block the pipeline
- **Alert fatigue prevention**: Group related failures, suppress duplicates, escalate only when needed

---

## Orchestrator Decision Matrix

| Factor | Dagster | Airflow | Prefect | Embedded (dbt Cloud, Databricks) |
|--------|---------|---------|---------|----------------------------------|
| **Philosophy** | Asset-oriented | Task-oriented | Flow-oriented | Tool-native scheduling |
| **Best for** | Greenfield data platforms | Brownfield, large existing DAGs | Python-native teams, event-driven | Single-tool workflows |
| **Learning curve** | Medium (new concepts) | Medium (lots of concepts) | Low (Pythonic) | Very Low (built-in) |
| **dbt integration** | `dagster-dbt` (first-class) | `cosmos` (good) | dbt CLI wrapper | Native (dbt Cloud) |
| **DLT integration** | `dagster-dlt` (first-class) | Task wrapper | Task wrapper | N/A |
| **Asset lineage** | Built-in, UI-native | Via plugins (limited) | Via artifacts | Tool-specific |
| **Partitioning** | First-class (daily, monthly, custom) | Dynamic task mapping | Map/reduce | Tool-specific |
| **Testing** | Asset unit tests, materializations | DAG validation, task testing | Flow unit tests | Tool-specific |
| **Local dev** | `dagster dev` (full UI locally) | Local executor (limited) | `prefect server start` | N/A (cloud-only) |
| **Managed offering** | Dagster Cloud | MWAA, Composer, Astronomer | Prefect Cloud | Built into platform |
| **Community** | Growing fast (2026) | Massive, mature | Medium | Tool-specific |

### When to Choose Each

**Choose Dagster when:**
- Starting a new data platform from scratch
- You value asset lineage and observability
- You want first-class dbt + DLT integration
- Your team prefers Python-native development
- You need partitioned backfills

**Choose Airflow when:**
- You have existing Airflow DAGs to maintain
- Your team already knows Airflow well
- You need the broadest operator ecosystem
- Your cloud provider offers managed Airflow (MWAA, Composer)
- You need mature, battle-tested scheduling at scale

**Choose Prefect when:**
- You want the simplest Python-native experience
- Your workflows are primarily Python functions
- You need dynamic, event-driven orchestration
- You prefer minimal infrastructure overhead

**Choose embedded orchestration when:**
- Your entire workflow lives in one tool (dbt Cloud, Databricks)
- You don't need cross-tool dependency management
- You want zero orchestrator maintenance

See [Embedded Orchestration Reference →](references/embedded-orchestration.md) for dbt Cloud, Databricks Workflows, and Snowflake Tasks patterns.

---

## Dagster Quickstart

### Basic Asset

```python
from dagster import asset, Definitions, MaterializeResult, MetadataValue

@asset(
    description="Raw orders loaded from source database",
    group_name="ingestion",
    compute_kind="python",
)
def raw_orders() -> MaterializeResult:
    """Extract orders from source and return metadata."""
    orders_df = extract_orders_from_source()
    row_count = len(orders_df)
    load_to_warehouse(orders_df, "raw.orders")

    return MaterializeResult(
        metadata={
            "row_count": MetadataValue.int(row_count),
            "preview": MetadataValue.md(orders_df.head().to_markdown()),
        }
    )

@asset(
    description="Staged orders with cleaned types and deduplication",
    group_name="staging",
    compute_kind="sql",
)
def stg_orders(raw_orders):
    """Transform raw orders into staging model."""
    return execute_sql("""
        SELECT DISTINCT
            order_id,
            customer_id,
            order_date::DATE as order_date,
            total_amount::DECIMAL(10,2) as total_amount,
            status
        FROM raw.orders
        WHERE order_id IS NOT NULL
    """)

@asset(
    description="Revenue metrics by customer",
    group_name="marts",
    compute_kind="sql",
)
def fct_customer_revenue(stg_orders):
    """Aggregate customer revenue from staged orders."""
    return execute_sql("""
        SELECT
            customer_id,
            COUNT(*) as order_count,
            SUM(total_amount) as total_revenue,
            MIN(order_date) as first_order_date,
            MAX(order_date) as last_order_date
        FROM staging.stg_orders
        GROUP BY customer_id
    """)

defs = Definitions(assets=[raw_orders, stg_orders, fct_customer_revenue])
```

### Resources (Dependency Injection)

```python
from dagster import asset, resource, Definitions, ConfigurableResource
import os

class SnowflakeResource(ConfigurableResource):
    """Snowflake connection as a Dagster resource."""
    # ── Credential boundary ──────────────────────────────────────
    # Configure via Dagster environment variables:
    #   SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY_PATH
    # See: shared-references/data-engineering/security-compliance-patterns.md
    # ─────────────────────────────────────────────────────────────
    account: str = os.environ.get("SNOWFLAKE_ACCOUNT", "")
    user: str = os.environ.get("SNOWFLAKE_USER", "")
    private_key_path: str = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH", "")
    warehouse: str = "COMPUTE_WH"
    database: str = "ANALYTICS"

    def execute_sql(self, sql: str):
        conn = snowflake.connector.connect(
            account=self.account,
            user=self.user,
            private_key_file_path=self.private_key_path,
            warehouse=self.warehouse,
            database=self.database,
        )
        return conn.cursor().execute(sql).fetchall()

@asset
def raw_orders(snowflake: SnowflakeResource):
    """Asset using injected Snowflake resource."""
    return snowflake.execute_sql("SELECT * FROM raw.orders")

defs = Definitions(
    assets=[raw_orders],
    resources={"snowflake": SnowflakeResource()},
)
```

### Schedules

```python
from dagster import (
    asset,
    define_asset_job,
    ScheduleDefinition,
    Definitions,
)

# Define a job that materializes specific assets
daily_pipeline_job = define_asset_job(
    name="daily_pipeline",
    selection=["raw_orders", "stg_orders", "fct_customer_revenue"],
    description="Daily pipeline: ingest → stage → marts",
)

# Schedule the job
daily_schedule = ScheduleDefinition(
    job=daily_pipeline_job,
    cron_schedule="0 6 * * *",  # 6 AM daily
    default_status=DefaultScheduleStatus.RUNNING,
)

defs = Definitions(
    assets=[raw_orders, stg_orders, fct_customer_revenue],
    jobs=[daily_pipeline_job],
    schedules=[daily_schedule],
)
```

### Sensors

```python
from dagster import sensor, RunRequest, SensorEvaluationContext, asset
import boto3

@sensor(
    job=daily_pipeline_job,
    minimum_interval_seconds=60,
    description="Trigger pipeline when new files arrive in S3",
)
def s3_file_sensor(context: SensorEvaluationContext):
    """Watch for new files in S3 and trigger pipeline."""
    s3 = boto3.client("s3")
    last_key = context.cursor or ""

    response = s3.list_objects_v2(
        Bucket="data-landing",
        Prefix="orders/",
        StartAfter=last_key,
    )

    new_files = response.get("Contents", [])
    if new_files:
        latest_key = new_files[-1]["Key"]
        context.update_cursor(latest_key)

        yield RunRequest(
            run_key=latest_key,
            run_config={
                "ops": {
                    "raw_orders": {"config": {"s3_key": latest_key}}
                }
            },
        )
```

### Local Development

```bash
# Install Dagster
pip install dagster dagster-webserver

# Start local dev server (full UI at http://localhost:3000)
dagster dev -f my_pipeline.py

# Or with a Dagster project
dagster dev -m my_dagster_project
```

For advanced Dagster patterns (partitions, I/O managers, backfills, multi-asset sensors), see [Dagster Patterns Reference →](references/dagster-patterns.md)

For dbt and DLT integrations with Dagster, see [Dagster Integrations Reference →](references/dagster-integrations.md)

---

## Airflow Quickstart

### TaskFlow API (Modern Pattern)

```python
from airflow.decorators import dag, task
from datetime import datetime
import os

# ── Credential boundary ──────────────────────────────────────────────
# Airflow connections store credentials securely.
# Configure via Airflow UI: Admin → Connections → Add Connection
# Or via environment variables: AIRFLOW_CONN_SNOWFLAKE_DEFAULT="snowflake://..."
# See: shared-references/data-engineering/security-compliance-patterns.md
# ─────────────────────────────────────────────────────────────────────

@dag(
    dag_id="daily_orders_pipeline",
    schedule="0 6 * * *",          # 6 AM daily
    start_date=datetime(2024, 1, 1),
    catchup=False,                  # Don't backfill on deploy
    tags=["orders", "daily"],
    default_args={
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
    },
)
def daily_orders_pipeline():

    @task()
    def extract_orders(**context):
        """Extract orders from source API."""
        from airflow.hooks.base import BaseHook
        conn = BaseHook.get_connection("orders_api")

        execution_date = context["ds"]
        orders = fetch_orders(
            api_url=conn.host,
            api_key=conn.password,
            date=execution_date,
        )
        return orders

    @task()
    def transform_orders(raw_orders: list):
        """Clean and deduplicate orders."""
        import pandas as pd
        df = pd.DataFrame(raw_orders)
        df = df.drop_duplicates(subset=["order_id"])
        df["order_date"] = pd.to_datetime(df["order_date"])
        df["total_amount"] = df["total_amount"].astype(float)
        return df.to_dict(orient="records")

    @task()
    def load_orders(clean_orders: list):
        """Load orders to Snowflake."""
        from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook
        hook = SnowflakeHook(snowflake_conn_id="snowflake_default")
        hook.run(
            "INSERT INTO raw.orders SELECT * FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))"
        )
        return len(clean_orders)

    # TaskFlow handles XCom serialization automatically
    raw = extract_orders()
    clean = transform_orders(raw)
    load_orders(clean)

daily_orders_pipeline()
```

### Classic Operator Pattern

```python
from airflow import DAG
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
from airflow.providers.snowflake.transfers.copy_into_snowflake import CopyFromExternalStageToSnowflakeOperator
from datetime import datetime, timedelta

with DAG(
    dag_id="snowflake_elt_pipeline",
    schedule="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "snowflake_conn_id": "snowflake_default",
        "retries": 2,
    },
) as dag:

    # Stage 1: Load raw data from S3
    load_raw = CopyFromExternalStageToSnowflakeOperator(
        task_id="load_raw_orders",
        table="RAW.ORDERS",
        stage="S3_STAGE",
        file_format="(TYPE=PARQUET)",
        pattern="orders/.*\\.parquet",
    )

    # Stage 2: Run dbt transformations (via cosmos)
    # See Airflow Patterns reference for cosmos setup
    run_dbt = BashOperator(
        task_id="run_dbt",
        bash_command="cd /opt/dbt && dbt run --select staging.stg_orders+",
    )

    # Stage 3: Data quality check
    quality_check = SnowflakeOperator(
        task_id="quality_check",
        sql="""
            SELECT CASE
                WHEN COUNT(*) = 0 THEN 1/0  -- Fail if no rows loaded
                ELSE 1
            END
            FROM STAGING.STG_ORDERS
            WHERE ORDER_DATE = '{{ ds }}'
        """,
    )

    load_raw >> run_dbt >> quality_check
```

### Connections (Credential Management)

Airflow stores credentials in **Connections** — never in DAG code.

```bash
# Set connections via environment variables (preferred for CI/CD)
export AIRFLOW_CONN_SNOWFLAKE_DEFAULT="snowflake://user:pass@account/db/schema?warehouse=WH&role=ROLE"
export AIRFLOW_CONN_ORDERS_API="https://api-key:secret@api.example.com"

# Or via Airflow CLI
airflow connections add snowflake_default \
    --conn-type snowflake \
    --conn-login svc_airflow \
    --conn-password "$(vault read -field=password secret/snowflake)" \
    --conn-host account.snowflakecomputing.com \
    --conn-schema public \
    --conn-extra '{"warehouse": "COMPUTE_WH", "database": "ANALYTICS", "role": "LOADER_ROLE"}'
```

For advanced Airflow patterns (dynamic task mapping, `cosmos` dbt integration, MWAA/Composer, custom operators), see [Airflow Patterns Reference →](references/airflow-patterns.md)

---

## The Trifecta: Dagster + DLT + dbt

The "trifecta" pattern — Dagster orchestrating DLT ingestion and dbt transformations — is the fastest-growing modern data stack combination. Each tool handles one concern:

| Layer | Tool | Responsibility |
|-------|------|----------------|
| **Orchestration** | Dagster | Scheduling, dependency resolution, monitoring, alerting |
| **Ingestion** | DLT | Extract from sources, load to warehouse (raw layer) |
| **Transformation** | dbt | SQL transformations (staging → intermediate → marts) |

### Trifecta Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Dagster (Orchestrator)              │
│                                                     │
│  ┌───────────┐     ┌────────────┐     ┌──────────┐ │
│  │  DLT      │ ──→ │  dbt       │ ──→ │  Quality │ │
│  │  Assets   │     │  Assets    │     │  Checks  │ │
│  │ (ingest)  │     │ (transform)│     │ (assert) │ │
│  └───────────┘     └────────────┘     └──────────┘ │
│       │                  │                  │       │
│       ▼                  ▼                  ▼       │
│  ┌──────────────────────────────────────────────┐   │
│  │            Snowflake / BigQuery               │   │
│  │  raw.* → staging.* → intermediate.* → marts.*│   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

### Trifecta Code Example

```python
from dagster import Definitions, AssetExecutionContext, define_asset_job, ScheduleDefinition
from dagster_dbt import DbtCliResource, dbt_assets, DbtProject
from dagster_dlt import DagsterDltResource, dlt_assets
import dlt

# ── Credential boundary ──────────────────────────────────────────────
# All credentials come from environment variables on the Dagster deployment.
# DLT credentials: DESTINATION__SNOWFLAKE__CREDENTIALS
# dbt credentials: DBT_PROFILES_DIR + profiles.yml (or env vars in profiles)
# See: shared-references/data-engineering/security-compliance-patterns.md
# ─────────────────────────────────────────────────────────────────────

# --- DLT Ingestion Assets ---

@dlt.source
def stripe_source():
    yield stripe_customers()
    yield stripe_charges()

@dlt_assets(
    dlt_source=stripe_source(),
    dlt_pipeline=dlt.pipeline(
        pipeline_name="stripe_ingest",
        destination="snowflake",
        dataset_name="raw_stripe",
    ),
    name="stripe",
    group_name="ingestion",
)
def stripe_dlt_assets(context: AssetExecutionContext, dlt: DagsterDltResource):
    yield from dlt.run(context=context)

# --- dbt Transformation Assets ---

dbt_project = DbtProject(project_dir="path/to/dbt/project")

@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
    name="dbt",
)
def dbt_transform_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()

# --- Jobs & Schedules ---

daily_pipeline = define_asset_job(
    name="daily_pipeline",
    selection=[stripe_dlt_assets, dbt_transform_assets],
)

daily_schedule = ScheduleDefinition(
    job=daily_pipeline,
    cron_schedule="0 6 * * *",
)

# --- Definitions ---

defs = Definitions(
    assets=[stripe_dlt_assets, dbt_transform_assets],
    resources={
        "dlt": DagsterDltResource(),
        "dbt": DbtCliResource(project_dir=dbt_project),
    },
    jobs=[daily_pipeline],
    schedules=[daily_schedule],
)
```

**Key benefits of the trifecta:**

- DLT assets automatically depend on source availability
- dbt assets automatically depend on the raw tables DLT creates
- Dagster shows the complete lineage from API → raw → staging → marts
- Backfills can target specific date ranges across both DLT and dbt
- Failures in DLT stop dbt from running against stale data

---

## Common Patterns

### Retry Strategy

```python
# Dagster: retries via asset/op config
from dagster import asset, RetryPolicy

@asset(
    retry_policy=RetryPolicy(
        max_retries=3,
        delay=30,  # seconds between retries
        backoff=Backoff.EXPONENTIAL,
    ),
)
def flaky_api_asset():
    """Asset that calls an unreliable external API."""
    return call_external_api()
```

```python
# Airflow: retries via default_args
default_args = {
    "retries": 3,
    "retry_delay": timedelta(minutes=5),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=30),
}
```

### Alerting

```python
# Dagster: freshness policies + Slack alerts
from dagster import asset, FreshnessPolicy

@asset(
    freshness_policy=FreshnessPolicy(
        maximum_lag_minutes=120,  # Alert if stale > 2 hours
    ),
)
def fct_orders(stg_orders):
    """Mart table with 2-hour freshness SLA."""
    pass

# Configure Slack/PagerDuty alerts in Dagster Cloud UI
# or via dagster-slack resource for self-hosted
```

```python
# Airflow: callbacks for alerting
def on_failure_callback(context):
    """Send Slack alert on task failure."""
    dag_id = context["dag"].dag_id
    task_id = context["task"].task_id
    execution_date = context["ds"]
    send_slack_alert(
        channel="#data-alerts",
        message=f"Task {dag_id}.{task_id} failed on {execution_date}",
    )

@dag(
    on_failure_callback=on_failure_callback,
    ...
)
```

### Partitioned Backfills

```python
# Dagster: daily partitions with backfill support
from dagster import asset, DailyPartitionsDefinition

daily_partitions = DailyPartitionsDefinition(start_date="2024-01-01")

@asset(partitions_def=daily_partitions)
def daily_orders(context):
    """Load orders for a specific date partition."""
    date = context.partition_key  # "2024-01-15"
    orders = fetch_orders(date=date)
    load_to_warehouse(orders, partition=date)
    return MaterializeResult(
        metadata={"row_count": len(orders), "partition": date}
    )

# Backfill: select date range in Dagster UI → "Materialize"
# Or via CLI: dagster asset materialize --partition "2024-01-01...2024-01-31"
```

### Cross-Pipeline Dependencies

```python
# Dagster: asset checks for cross-pipeline quality gates
from dagster import asset_check, AssetCheckResult, AssetCheckSeverity

@asset_check(asset=fct_orders)
def orders_row_count_check():
    """Fail downstream assets if orders are empty."""
    count = execute_sql("SELECT COUNT(*) FROM marts.fct_orders")[0][0]
    return AssetCheckResult(
        passed=count > 0,
        severity=AssetCheckSeverity.ERROR,
        metadata={"row_count": count},
    )
```

---

## Security Posture

This skill generates orchestration code including DAG definitions, asset configurations, connection setups, and scheduling logic.
See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for the full security framework.

**Credentials required**: Warehouse connections, API keys for sources, secrets manager access, alerting webhooks
**Where to configure**: Dagster EnvVar resources, Airflow Connections, environment variables
**Minimum role/permissions**: Orchestrator service account with scoped warehouse access

### By Security Tier

| Capability | Tier 1 (Cloud-Native) | Tier 2 (Regulated) | Tier 3 (Air-Gapped) |
|------------|----------------------|--------------------|--------------------|
| Execute pipelines | Against dev/staging | Generate pipeline code for review | Generate code only |
| Configure schedules | Deploy to dev environments | Generate schedule configs for review | Generate configs only |
| View run metadata | Full access to dev run history | Metadata and logs only (no data) | No access to run history |
| Manage connections | Configure dev connections | Generate connection templates | Document connection requirements |
| Backfill data | Execute against dev partitions | Generate backfill plans for review | Generate plans only |

### Credential Best Practices by Tool

**Dagster:**
- Use `EnvVar` for all resource configuration (never hardcode)
- Store secrets in the deployment environment (Dagster Cloud, k8s secrets, Vault)
- Use `ConfigurableResource` for typed, validated resource configuration
- Scope service accounts to minimum required warehouse permissions

**Airflow:**
- Use Connections for all external system credentials (never in DAG code)
- Store connection extras as JSON for additional parameters
- Use `SecretsBackend` to pull from Vault/AWS Secrets Manager/GCP Secret Manager
- Prefer environment variable connections (`AIRFLOW_CONN_*`) for CI/CD

---

## Reference Files

This skill includes detailed reference documentation for deep dives:

- [Dagster Patterns →](references/dagster-patterns.md) — Assets, resources, sensors, schedules, partitions, backfills, I/O managers, asset checks
- [Dagster Integrations →](references/dagster-integrations.md) — `dagster-dbt` (DbtProject, @dbt_assets), `dagster-dlt` (@dlt_assets), dagster-k8s, dagster-cloud
- [Airflow Patterns →](references/airflow-patterns.md) — TaskFlow API, operators, connections, dynamic task mapping, `cosmos` (dbt), MWAA/Composer
- [Embedded Orchestration →](references/embedded-orchestration.md) — When NOT to add an orchestrator: dbt Cloud, Databricks Workflows, Snowflake Tasks, Prefect
