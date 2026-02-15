# Airflow Patterns Reference

> Production Airflow patterns for data engineering teams. Part of the [Data Orchestration Skill](../SKILL.md).

---

## TaskFlow API (Modern Pattern)

```python
from airflow.decorators import dag, task
from datetime import datetime, timedelta

@dag(
    dag_id="daily_orders",
    schedule="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["orders", "daily"],
    default_args={"retries": 2, "retry_delay": timedelta(minutes=5),
                  "retry_exponential_backoff": True},
)
def daily_orders():
    @task()
    def extract(ds: str = None) -> list:
        return fetch_orders(date=ds)

    @task()
    def transform(raw_orders: list) -> list:
        import pandas as pd
        df = pd.DataFrame(raw_orders).drop_duplicates(subset=["order_id"])
        return df.to_dict(orient="records")

    @task()
    def load(clean_orders: list) -> int:
        load_to_warehouse(clean_orders, table="raw.orders")
        return len(clean_orders)

    load(transform(extract()))

daily_orders()
```

### Classic Operator Pattern

```python
from airflow import DAG
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator

with DAG("snowflake_elt", schedule="0 6 * * *", start_date=datetime(2024, 1, 1),
         catchup=False, default_args={"snowflake_conn_id": "snowflake_default", "retries": 2}) as dag:
    load_raw = CopyFromExternalStageToSnowflakeOperator(
        task_id="load_raw", table="RAW.ORDERS", stage="S3_STAGE",
        file_format="(TYPE=PARQUET)", pattern="orders/.*\\.parquet")
    run_dbt = BashOperator(task_id="run_dbt",
        bash_command="cd /opt/dbt && dbt run --select staging.stg_orders+")
    quality_check = SnowflakeOperator(task_id="quality_check", sql="""
        SELECT CASE WHEN COUNT(*) = 0 THEN 1/0 ELSE 1 END
        FROM STAGING.STG_ORDERS WHERE ORDER_DATE = '{{ ds }}'""")
    load_raw >> run_dbt >> quality_check
```

---

## Dynamic Task Mapping

```python
@task()
def get_regions() -> list:
    return ["us-east", "us-west", "eu-west", "ap-southeast"]

@task()
def process_region(region: str) -> dict:
    data = fetch_regional_data(region)
    load_to_warehouse(data, table=f"raw.{region}_orders")
    return {"region": region, "rows": len(data)}

@task()
def aggregate_results(results: list):
    total = sum(r["rows"] for r in results)
    send_summary(f"Total rows: {total}")

regions = get_regions()
results = process_region.expand(region=regions)  # Runs N tasks in parallel
aggregate_results(results)
```

---

## Connections

```bash
# Environment variable format (recommended for CI/CD)
export AIRFLOW_CONN_SNOWFLAKE_DEFAULT="snowflake://svc_airflow:${SF_PASSWORD}@account.snowflakecomputing.com/ANALYTICS/PUBLIC?warehouse=COMPUTE_WH&role=LOADER_ROLE"

# Secrets backend (production)
# airflow.cfg: backend = airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
# backend_kwargs = {"connections_prefix": "airflow/connections"}
```

```python
# Using connections in DAGs
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

@task()
def extract_with_connection():
    sf_hook = SnowflakeHook(snowflake_conn_id="snowflake_default")
    return sf_hook.get_records("SELECT * FROM raw.orders LIMIT 10")
```

---

## Cosmos (dbt Integration)

```python
from cosmos import DbtDag, ProjectConfig, ProfileConfig, DbtTaskGroup, RenderConfig
from cosmos.profiles import SnowflakeUserPasswordProfileMapping

profile_config = ProfileConfig(
    profile_name="my_project", target_name="prod",
    profile_mapping=SnowflakeUserPasswordProfileMapping(
        conn_id="snowflake_default", profile_args={"database": "ANALYTICS", "schema": "PROD"}))

# Full DAG
dbt_dag = DbtDag(
    dag_id="dbt_cosmos", project_config=ProjectConfig(dbt_project_path="/opt/dbt/project"),
    profile_config=profile_config, schedule="0 7 * * *",
    start_date=datetime(2024, 1, 1), catchup=False)

# Or as task group within a larger DAG
@dag(...)
def full_pipeline():
    extract = extract_raw_data()
    dbt_staging = DbtTaskGroup(group_id="dbt_staging",
        project_config=ProjectConfig(dbt_project_path="/opt/dbt/project"),
        profile_config=profile_config,
        render_config=RenderConfig(select=["path:models/staging"]))
    extract >> dbt_staging
```

---

## Managed Airflow

**MWAA (AWS):**
```bash
aws s3 sync dags/ s3://my-mwaa-bucket/dags/
aws s3 cp requirements.txt s3://my-mwaa-bucket/requirements.txt
# Use AWS Secrets Manager for connections
aws secretsmanager create-secret --name "airflow/connections/snowflake_default" \
    --secret-string "snowflake://user:pass@account/db/schema?warehouse=WH"
```

**Composer (GCP):** `gsutil cp dags/*.py gs://us-central1-my-composer-bucket/dags/`

**Astronomer:** `astro dev init && astro dev start && astro deploy`

---

## Best Practices

### DAG Factory Pattern

```python
def create_ingestion_dag(source: str, schedule: str, conn_id: str):
    @dag(dag_id=f"ingest_{source}", schedule=schedule, start_date=datetime(2024, 1, 1),
         catchup=False, tags=["ingestion", source])
    def ingestion():
        @task()
        def extract():
            return fetch_data(BaseHook.get_connection(conn_id))
        @task()
        def load(data):
            load_to_warehouse(data, table=f"raw.{source}")
        load(extract())
    return ingestion()

github_dag = create_ingestion_dag("github", "@hourly", "github_api")
```

### Idempotency

```python
@task()
def idempotent_load(ds: str = None):
    sf_hook = SnowflakeHook("snowflake_default")
    sf_hook.run(f"DELETE FROM raw.orders WHERE order_date = '{ds}'")
    sf_hook.run(f"INSERT INTO raw.orders SELECT * FROM external_stage WHERE order_date = '{ds}'")
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| DAG not in UI | Check `airflow dags list-import-errors` |
| Task stuck in queued | Check executor config, increase parallelism |
| XCom too large | Use external storage (S3/GCS) instead of XCom |
| Catchup runs all history | Set `catchup=False` |
| Cosmos dbt errors | Pin both cosmos and dbt versions explicitly |
