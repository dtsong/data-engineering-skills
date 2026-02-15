# Embedded Orchestration Reference

> When NOT to add a standalone orchestrator. Part of the [Data Orchestration Skill](../SKILL.md).

---

## When Embedded Is Enough vs When to Graduate

**Stay embedded when:** pipeline lives in one tool, no cross-tool dependencies, simple cron scheduling, <20 jobs, no dedicated platform engineering.

**Graduate to Dagster/Airflow when:** pipelines span multiple tools, you need event-driven triggers, asset lineage across systems, partitioned backfills, complex retry/alerting, or 50+ scheduled jobs.

---

## dbt Cloud

```yaml
# Job: Daily Production Run
# Schedule: 0 6 * * * | Commands: dbt build --select staging.* marts.*
# Triggers: Schedule, PR merge, API call
```

**CI/CD:** dbt Cloud runs `dbt build` on PRs with compilation checks, test execution against temp schemas, and merge blocking on failures.

### dbt Cloud API

```python
# Credentials: DBT_CLOUD_API_TOKEN, DBT_CLOUD_ACCOUNT_ID
def trigger_dbt_cloud_job(job_id: int, cause: str = "API trigger"):
    response = requests.post(
        f"https://cloud.getdbt.com/api/v2/accounts/{os.environ['DBT_CLOUD_ACCOUNT_ID']}/jobs/{job_id}/run/",
        headers={"Authorization": f"Token {os.environ['DBT_CLOUD_API_TOKEN']}"},
        json={"cause": cause})
    return response.json()["data"]["id"]
```

| Signal | Recommendation |
|--------|---------------|
| dbt Cloud is your only tool | Stay with dbt Cloud |
| Add DLT or Python ingestion | Consider Dagster |
| Need event-driven triggers | Add Dagster/Airflow sensor |
| Need complex retry per model | Dagster retry policies |

---

## Databricks Workflows

```json
{
    "name": "daily_pipeline",
    "tasks": [
        {"task_key": "extract", "notebook_task": {"notebook_path": "/pipelines/extract"}},
        {"task_key": "run_dbt", "depends_on": [{"task_key": "extract"}],
         "dbt_task": {"commands": ["dbt build --select staging.* marts.*"]}},
        {"task_key": "quality", "depends_on": [{"task_key": "run_dbt"}],
         "notebook_task": {"notebook_path": "/pipelines/quality_checks"}}
    ],
    "schedule": {"quartz_cron_expression": "0 0 6 * * ?"}
}
```

### Delta Live Tables (Databricks DLT)

> Databricks DLT (Delta Live Tables) is separate from dlthub's dlt (Data Load Tool).

```python
import dlt as delta_live_tables

@delta_live_tables.table(name="raw_orders")
def raw_orders():
    return spark.read.format("jdbc").options(url="jdbc:postgresql://host:5432/db", dbtable="public.orders").load()

@delta_live_tables.table(name="clean_orders")
@delta_live_tables.expect_or_drop("valid_customer", "customer_id IS NOT NULL")
def clean_orders():
    return delta_live_tables.read("raw_orders").where("status != 'cancelled'")
```

| Signal | Recommendation |
|--------|---------------|
| All Spark/notebook-based | Stay with Databricks |
| Add non-Databricks ingestion | Consider Dagster |
| Need asset lineage across tools | Dagster provides natively |
| 100+ Databricks jobs | Consider orchestrator for visibility |

---

## Snowflake Tasks

```sql
-- Scheduled root task
CREATE TASK ingest_raw WAREHOUSE = LOADING_WH SCHEDULE = 'USING CRON 0 6 * * * UTC'
    AS CALL ingest_raw_data();

-- Child tasks (triggered by parent)
CREATE TASK transform_staging WAREHOUSE = TRANSFORM_WH AFTER ingest_raw
    AS CALL run_staging_transforms();

CREATE TASK transform_marts WAREHOUSE = TRANSFORM_WH AFTER transform_staging
    AS CALL run_mart_transforms();

ALTER TASK transform_marts RESUME;
ALTER TASK transform_staging RESUME;
ALTER TASK ingest_raw RESUME;
```

### Streams + Tasks (CDC)

```sql
CREATE STREAM orders_stream ON TABLE raw.orders;

CREATE TASK process_changes WAREHOUSE = COMPUTE_WH SCHEDULE = 'USING CRON */5 * * * * UTC'
    WHEN SYSTEM$STREAM_HAS_DATA('orders_stream')
    AS MERGE INTO staging.orders t USING orders_stream s ON t.order_id = s.order_id
    WHEN MATCHED AND s.METADATA$ACTION = 'INSERT' THEN UPDATE SET t.amount = s.amount
    WHEN NOT MATCHED AND s.METADATA$ACTION = 'INSERT' THEN INSERT VALUES (s.order_id, s.customer_id, s.amount, CURRENT_TIMESTAMP());
```

| Signal | Recommendation |
|--------|---------------|
| All SQL within Snowflake | Stay with Tasks |
| Need Python extraction/APIs | Add DLT/Dagster |
| Need cross-system dependencies | Add Dagster or Airflow |
| Task DAGs exceed 20+ nodes | Consider external orchestrator |

---

## Prefect

```python
from prefect import flow, task

@task(retries=3, retry_delay_seconds=60)
def extract_data(date: str) -> list:
    return fetch_orders(date=date)

@flow(name="daily-orders", log_prints=True)
def daily_orders(date: str):
    raw = extract_data(date)
    clean = transform_data(raw)
    load_data(clean)
```

**Choose Prefect** for simplest Python-native orchestration, minimal infrastructure.
**Don't choose Prefect** when you need deep dbt/DLT integration or asset lineage (Dagster excels).

---

## Decision Flowchart

```
Pipeline in one tool? → Yes: use embedded (dbt Cloud / Databricks / Snowflake Tasks)
                        └── Growing beyond one tool? → Graduate to Dagster
                      → No: Multiple tools
                        ├── Greenfield? → Dagster
                        ├── Existing Airflow? → Keep Airflow, evaluate Dagster for new work
                        └── Simple Python only? → Prefect (or Dagster)
```
