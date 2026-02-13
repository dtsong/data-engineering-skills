# Embedded Orchestration Reference

> When NOT to add a standalone orchestrator. Part of the [Data Orchestration Skill](../SKILL.md).

---

## Overview

Not every data workflow needs Dagster or Airflow. Many tools have built-in scheduling and orchestration capabilities. Adding a standalone orchestrator introduces complexity, cost, and maintenance burden. Start with embedded orchestration and graduate to Dagster/Airflow when you outgrow it.

### When Embedded Orchestration Is Enough

- Your entire pipeline lives in one tool (dbt Cloud, Databricks, Snowflake)
- You don't need cross-tool dependency management
- Your scheduling needs are simple (cron-based, no event-driven triggers)
- You have fewer than ~20 scheduled jobs
- Your team doesn't have dedicated platform engineering resources

### When You Need a Standalone Orchestrator

- Pipelines span multiple tools (DLT → dbt → Reverse ETL)
- You need event-driven triggers (new files in S3, API webhooks)
- You need asset-level lineage across ingestion and transformation
- You need partitioned backfills across multiple systems
- You have complex retry/alerting requirements that differ by pipeline
- Your team manages 50+ scheduled jobs

---

## dbt Cloud

dbt Cloud provides built-in scheduling, CI, and monitoring for dbt projects.

### Jobs and Schedules

```yaml
# dbt Cloud job configuration (via UI or API)
# Job: Daily Production Run
#   - Schedule: 0 6 * * * (6 AM daily)
#   - Commands: dbt build --select staging.* marts.*
#   - Environment: Production
#   - Triggers on: Schedule, PR merge, API call
```

### CI/CD in dbt Cloud

dbt Cloud runs `dbt build` on pull requests, providing:
- Model compilation checks
- Test execution against a temporary schema
- PR comments with build results
- Merge blocking on test failures

### dbt Cloud API (Trigger from External Tools)

```python
import requests
import os

# ── Credential boundary ──────────────────────────────────────────────
# Configure: export DBT_CLOUD_API_TOKEN="your-api-token"
# Configure: export DBT_CLOUD_ACCOUNT_ID="12345"
# ─────────────────────────────────────────────────────────────────────

def trigger_dbt_cloud_job(job_id: int, cause: str = "API trigger"):
    """Trigger a dbt Cloud job via API."""
    response = requests.post(
        f"https://cloud.getdbt.com/api/v2/accounts/{os.environ['DBT_CLOUD_ACCOUNT_ID']}/jobs/{job_id}/run/",
        headers={"Authorization": f"Token {os.environ['DBT_CLOUD_API_TOKEN']}"},
        json={"cause": cause},
    )
    response.raise_for_status()
    return response.json()["data"]["id"]  # Run ID

def wait_for_dbt_cloud_run(run_id: int, timeout_minutes: int = 60):
    """Poll until dbt Cloud run completes."""
    import time
    for _ in range(timeout_minutes * 6):  # Check every 10 seconds
        response = requests.get(
            f"https://cloud.getdbt.com/api/v2/accounts/{os.environ['DBT_CLOUD_ACCOUNT_ID']}/runs/{run_id}/",
            headers={"Authorization": f"Token {os.environ['DBT_CLOUD_API_TOKEN']}"},
        )
        status = response.json()["data"]["status_humanized"]
        if status in ("Success", "Error", "Cancelled"):
            return status
        time.sleep(10)
    return "Timeout"
```

### When to Graduate from dbt Cloud Scheduling

| Signal | Recommendation |
|--------|---------------|
| dbt Cloud is your only tool | Stay with dbt Cloud |
| You add DLT or custom Python ingestion | Consider Dagster for cross-tool orchestration |
| You need event-driven triggers (new S3 files) | Add Dagster sensor or Airflow sensor |
| You need data activation (Reverse ETL) | Consider orchestrator to sequence: ingest → transform → activate |
| You need complex retry logic per model | Dagster retry policies or Airflow task retries |

---

## Databricks Workflows

Databricks Workflows provides orchestration for notebooks, Python scripts, dbt, and Spark jobs.

### Workflow Definition (JSON)

```json
{
    "name": "daily_data_pipeline",
    "tasks": [
        {
            "task_key": "extract_data",
            "notebook_task": {
                "notebook_path": "/pipelines/extract_orders",
                "base_parameters": {
                    "date": "{{job.parameters.date}}"
                }
            },
            "job_cluster_key": "extract_cluster"
        },
        {
            "task_key": "run_dbt",
            "depends_on": [{"task_key": "extract_data"}],
            "dbt_task": {
                "project_directory": "/Repos/main/dbt_project",
                "commands": ["dbt build --select staging.* marts.*"],
                "warehouse_id": "abc123"
            }
        },
        {
            "task_key": "quality_checks",
            "depends_on": [{"task_key": "run_dbt"}],
            "notebook_task": {
                "notebook_path": "/pipelines/quality_checks"
            },
            "job_cluster_key": "compute_cluster"
        }
    ],
    "schedule": {
        "quartz_cron_expression": "0 0 6 * * ?",
        "timezone_id": "America/New_York"
    },
    "job_clusters": [
        {
            "job_cluster_key": "extract_cluster",
            "new_cluster": {
                "spark_version": "14.3.x-scala2.12",
                "num_workers": 2,
                "node_type_id": "i3.xlarge"
            }
        }
    ]
}
```

### Delta Live Tables (DLT — Databricks)

> **Note:** Databricks DLT (Delta Live Tables) is a separate product from dlthub's dlt (Data Load Tool). They share an acronym but are different tools.

```python
# Delta Live Tables pipeline definition
import dlt as delta_live_tables  # Databricks DLT, not dlthub dlt

@delta_live_tables.table(
    name="raw_orders",
    comment="Raw orders from source database",
)
def raw_orders():
    return spark.read.format("jdbc").options(
        url="jdbc:postgresql://host:5432/db",
        dbtable="public.orders",
    ).load()

@delta_live_tables.table(
    name="clean_orders",
    comment="Cleaned and validated orders",
)
@delta_live_tables.expect("valid_amount", "amount > 0")
@delta_live_tables.expect_or_drop("valid_customer", "customer_id IS NOT NULL")
def clean_orders():
    return delta_live_tables.read("raw_orders").where("status != 'cancelled'")
```

### When to Graduate from Databricks Workflows

| Signal | Recommendation |
|--------|---------------|
| All pipelines are Spark/notebook-based | Stay with Databricks Workflows |
| You add non-Databricks ingestion (DLT, APIs) | Consider Dagster for cross-tool orchestration |
| You need asset lineage across ingestion + transformation | Dagster provides this natively |
| You need fine-grained alerting per pipeline step | Dagster or Airflow have richer alerting |
| You're running 100+ Databricks jobs | Consider orchestrator for better visibility |

---

## Snowflake Tasks

Snowflake Tasks provide serverless scheduling for SQL and stored procedures.

### Basic Task

```sql
-- Create a task that runs every hour
CREATE OR REPLACE TASK refresh_staging
    WAREHOUSE = COMPUTE_WH
    SCHEDULE = 'USING CRON 0 * * * * America/New_York'
    AS
    CALL refresh_staging_tables();

-- Task with dependency (child task)
CREATE OR REPLACE TASK build_marts
    WAREHOUSE = COMPUTE_WH
    AFTER refresh_staging  -- Runs after parent task completes
    AS
    CALL build_mart_tables();

-- Enable tasks (they start in suspended state)
ALTER TASK build_marts RESUME;
ALTER TASK refresh_staging RESUME;
```

### Task DAG

```sql
-- Root task (scheduled)
CREATE TASK ingest_raw
    WAREHOUSE = LOADING_WH
    SCHEDULE = 'USING CRON 0 6 * * * UTC'
    AS CALL ingest_raw_data();

-- Child tasks (triggered by parent)
CREATE TASK transform_staging
    WAREHOUSE = TRANSFORM_WH
    AFTER ingest_raw
    AS CALL run_staging_transforms();

CREATE TASK transform_marts
    WAREHOUSE = TRANSFORM_WH
    AFTER transform_staging
    AS CALL run_mart_transforms();

CREATE TASK run_quality_checks
    WAREHOUSE = TRANSFORM_WH
    AFTER transform_marts
    AS CALL check_data_quality();

-- Monitor task history
SELECT *
FROM TABLE(INFORMATION_SCHEMA.TASK_HISTORY(
    TASK_NAME => 'ingest_raw',
    SCHEDULED_TIME_RANGE_START => DATEADD(HOUR, -24, CURRENT_TIMESTAMP())
))
ORDER BY scheduled_time DESC;
```

### Snowflake Streams + Tasks (CDC Pattern)

```sql
-- Create a stream to track changes
CREATE OR REPLACE STREAM orders_stream ON TABLE raw.orders;

-- Task processes stream only when new data exists
CREATE OR REPLACE TASK process_order_changes
    WAREHOUSE = COMPUTE_WH
    SCHEDULE = 'USING CRON */5 * * * * UTC'  -- Every 5 minutes
    WHEN SYSTEM$STREAM_HAS_DATA('orders_stream')  -- Only run when there's new data
    AS
    MERGE INTO staging.orders t
    USING orders_stream s
    ON t.order_id = s.order_id
    WHEN MATCHED AND s.METADATA$ACTION = 'INSERT' THEN
        UPDATE SET t.amount = s.amount, t.updated_at = CURRENT_TIMESTAMP()
    WHEN NOT MATCHED AND s.METADATA$ACTION = 'INSERT' THEN
        INSERT (order_id, customer_id, amount, created_at)
        VALUES (s.order_id, s.customer_id, s.amount, CURRENT_TIMESTAMP());
```

### When to Graduate from Snowflake Tasks

| Signal | Recommendation |
|--------|---------------|
| All logic is SQL within Snowflake | Stay with Snowflake Tasks |
| You need Python extraction or API calls | Add DLT/Dagster for ingestion |
| You need cross-system dependencies | Add Dagster or Airflow |
| You need rich alerting and monitoring UI | Add Dagster (superior observability) |
| Task DAGs exceed 20+ nodes | Consider external orchestrator for manageability |

---

## Prefect (Brief Overview)

Prefect is a Python-native orchestrator with minimal infrastructure requirements.

### Basic Flow

```python
from prefect import flow, task
from prefect.tasks import task_input_hash
from datetime import timedelta

@task(retries=3, retry_delay_seconds=60, cache_key_fn=task_input_hash, cache_expiration=timedelta(hours=1))
def extract_data(date: str) -> list:
    """Extract with retry and caching."""
    return fetch_orders(date=date)

@task()
def transform_data(raw: list) -> list:
    return clean_and_dedupe(raw)

@task()
def load_data(clean: list) -> int:
    load_to_warehouse(clean)
    return len(clean)

@flow(name="daily-orders", log_prints=True)
def daily_orders(date: str):
    raw = extract_data(date)
    clean = transform_data(raw)
    count = load_data(clean)
    print(f"Loaded {count} orders for {date}")

# Run locally
daily_orders("2024-03-15")

# Or deploy to Prefect Cloud/Server
# prefect deployment build daily_orders.py:daily_orders -n daily -q default
```

### When to Choose Prefect

- You want the simplest possible Python-native orchestration
- You prefer "just Python" over framework-specific concepts
- Your team is small and doesn't need Dagster's asset model
- You want quick setup without Airflow's infrastructure overhead

### When NOT to Choose Prefect

- You need deep dbt integration (Dagster's `dagster-dbt` is more mature)
- You need DLT integration (Dagster's `dagster-dlt` is first-class)
- You need asset lineage and observability (Dagster excels here)
- You have existing Airflow DAGs (migrate to Dagster, not Prefect)

---

## Decision Flowchart

```
Is your entire pipeline in one tool?
├── Yes: dbt Cloud / Databricks Workflows / Snowflake Tasks
│   └── Growing beyond one tool? → Graduate to Dagster
└── No: Multiple tools involved
    ├── Greenfield (new platform)? → Dagster
    ├── Existing Airflow DAGs? → Keep Airflow, evaluate Dagster for new work
    └── Simple Python workflows only? → Prefect (or Dagster)
```
