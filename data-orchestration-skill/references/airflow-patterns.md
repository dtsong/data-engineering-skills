# Airflow Patterns Reference

> Production Airflow patterns for data engineering teams. Part of the [Data Orchestration Skill](../SKILL.md).

---

## TaskFlow API (Modern Pattern)

The TaskFlow API (Airflow 2.0+) is the recommended way to write DAGs. It uses Python decorators and handles XCom serialization automatically.

### Basic TaskFlow DAG

```python
from airflow.decorators import dag, task
from datetime import datetime, timedelta

@dag(
    dag_id="taskflow_example",
    schedule="0 6 * * *",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["example", "taskflow"],
    default_args={
        "owner": "data-team",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "retry_exponential_backoff": True,
        "max_retry_delay": timedelta(minutes=30),
    },
    doc_md="""
    ## Daily Orders Pipeline
    Extracts orders, transforms, and loads to warehouse.
    """,
)
def daily_orders():

    @task()
    def extract(ds: str = None) -> list:
        """Extract orders for the execution date."""
        return fetch_orders(date=ds)

    @task()
    def transform(raw_orders: list) -> list:
        """Clean and deduplicate orders."""
        import pandas as pd
        df = pd.DataFrame(raw_orders)
        df = df.drop_duplicates(subset=["order_id"])
        return df.to_dict(orient="records")

    @task()
    def load(clean_orders: list) -> int:
        """Load to warehouse and return row count."""
        load_to_warehouse(clean_orders, table="raw.orders")
        return len(clean_orders)

    @task()
    def notify(row_count: int):
        """Send completion notification."""
        send_slack_message(f"Loaded {row_count} orders")

    raw = extract()
    clean = transform(raw)
    count = load(clean)
    notify(count)

daily_orders()
```

### TaskFlow with Multiple Outputs

```python
@task(multiple_outputs=True)
def extract_and_validate() -> dict:
    """Return multiple named outputs."""
    orders = fetch_orders()
    return {
        "orders": orders,
        "row_count": len(orders),
        "has_errors": any(o.get("error") for o in orders),
    }

@task()
def process(orders: list, has_errors: bool):
    if has_errors:
        handle_errors(orders)
    else:
        process_clean(orders)

result = extract_and_validate()
process(result["orders"], result["has_errors"])
```

### TaskFlow with Branch

```python
from airflow.decorators import task
from airflow.operators.python import BranchPythonOperator

@task.branch()
def choose_path(data_size: int) -> str:
    """Branch based on data volume."""
    if data_size > 100000:
        return "heavy_transform"
    return "light_transform"

@task()
def heavy_transform():
    """Spark-based transform for large datasets."""
    pass

@task()
def light_transform():
    """Pandas-based transform for small datasets."""
    pass
```

---

## Dynamic Task Mapping

Dynamic task mapping (Airflow 2.3+) replaces the need for dynamically generated DAGs.

### Map Over a List

```python
@task()
def get_regions() -> list:
    """Return list of regions to process."""
    return ["us-east", "us-west", "eu-west", "ap-southeast"]

@task()
def process_region(region: str) -> dict:
    """Process data for a single region."""
    data = fetch_regional_data(region)
    load_to_warehouse(data, table=f"raw.{region}_orders")
    return {"region": region, "rows": len(data)}

@task()
def aggregate_results(results: list):
    """Combine results from all regions."""
    total = sum(r["rows"] for r in results)
    send_summary(f"Total rows across all regions: {total}")

regions = get_regions()
results = process_region.expand(region=regions)  # Runs N tasks in parallel
aggregate_results(results)
```

### Map with Zip

```python
@task()
def get_configs() -> list:
    return [
        {"table": "customers", "query": "SELECT * FROM src.customers"},
        {"table": "orders", "query": "SELECT * FROM src.orders"},
        {"table": "products", "query": "SELECT * FROM src.products"},
    ]

@task()
def extract_table(config: dict):
    data = execute_query(config["query"])
    load_to_warehouse(data, table=f"raw.{config['table']}")

configs = get_configs()
extract_table.expand(config=configs)
```

---

## Connections

Airflow Connections store credentials securely, separate from DAG code.

### Connection Configuration

```bash
# Environment variable format (recommended for CI/CD)
# Format: AIRFLOW_CONN_{CONN_ID}="{conn_type}://{login}:{password}@{host}:{port}/{schema}?{extras}"

export AIRFLOW_CONN_SNOWFLAKE_DEFAULT="snowflake://svc_airflow:${SF_PASSWORD}@account.snowflakecomputing.com/ANALYTICS/PUBLIC?warehouse=COMPUTE_WH&role=LOADER_ROLE"

export AIRFLOW_CONN_POSTGRES_SOURCE="postgresql://reader:${PG_PASSWORD}@db.example.com:5432/production"

# BigQuery uses extras JSON for service account
export AIRFLOW_CONN_BIGQUERY_DEFAULT='google-cloud-platform://?extra__google_cloud_platform__project=my-project&extra__google_cloud_platform__key_path=/secrets/sa-key.json'
```

### Secrets Backend

Use a secrets backend to pull credentials from external secret stores.

```python
# airflow.cfg or environment variable
# AIRFLOW__SECRETS__BACKEND=airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
# AIRFLOW__SECRETS__BACKEND_KWARGS={"connections_prefix": "airflow/connections", "variables_prefix": "airflow/variables"}

# AWS Secrets Manager
[secrets]
backend = airflow.providers.amazon.aws.secrets.secrets_manager.SecretsManagerBackend
backend_kwargs = {"connections_prefix": "airflow/connections"}

# GCP Secret Manager
[secrets]
backend = airflow.providers.google.cloud.secrets.secret_manager.CloudSecretManagerBackend
backend_kwargs = {"connections_prefix": "airflow-connections", "project_id": "my-project"}

# HashiCorp Vault
[secrets]
backend = airflow.providers.hashicorp.secrets.vault.VaultBackend
backend_kwargs = {"connections_path": "airflow/connections", "url": "https://vault.example.com"}
```

### Using Connections in DAGs

```python
from airflow.hooks.base import BaseHook
from airflow.providers.snowflake.hooks.snowflake import SnowflakeHook

@task()
def extract_with_connection():
    """Use Airflow connection for credentials."""
    # Generic hook
    conn = BaseHook.get_connection("orders_api")
    api_url = conn.host
    api_key = conn.password

    # Provider-specific hook (preferred)
    sf_hook = SnowflakeHook(snowflake_conn_id="snowflake_default")
    results = sf_hook.get_records("SELECT * FROM raw.orders LIMIT 10")
    return results
```

---

## Cosmos (dbt Integration)

[Cosmos](https://astronomer.github.io/astronomer-cosmos/) maps dbt models to Airflow tasks, providing lineage and parallel execution.

### Installation

```bash
pip install astronomer-cosmos dbt-core dbt-snowflake
```

### Basic Cosmos DAG

```python
from cosmos import DbtDag, ProjectConfig, ProfileConfig, ExecutionConfig
from cosmos.profiles import SnowflakeUserPasswordProfileMapping
from datetime import datetime

# ── Credential boundary ──────────────────────────────────────────────
# dbt credentials come from the Airflow Snowflake connection.
# Configure: Admin → Connections → snowflake_default
# ─────────────────────────────────────────────────────────────────────

profile_config = ProfileConfig(
    profile_name="my_project",
    target_name="prod",
    profile_mapping=SnowflakeUserPasswordProfileMapping(
        conn_id="snowflake_default",
        profile_args={
            "database": "ANALYTICS",
            "schema": "PROD",
        },
    ),
)

dbt_dag = DbtDag(
    dag_id="dbt_cosmos_pipeline",
    project_config=ProjectConfig(
        dbt_project_path="/opt/dbt/my_project",
    ),
    profile_config=profile_config,
    execution_config=ExecutionConfig(
        dbt_executable_path="/opt/venv/bin/dbt",
    ),
    schedule="0 7 * * *",  # After raw data lands
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={"retries": 1},
)
```

### Cosmos with Selection

```python
from cosmos import DbtTaskGroup, RenderConfig

# Only run specific models as a task group within a larger DAG
@dag(...)
def full_pipeline():

    extract = extract_raw_data()

    dbt_staging = DbtTaskGroup(
        group_id="dbt_staging",
        project_config=ProjectConfig(dbt_project_path="/opt/dbt/project"),
        profile_config=profile_config,
        render_config=RenderConfig(
            select=["path:models/staging"],  # Only staging models
        ),
    )

    dbt_marts = DbtTaskGroup(
        group_id="dbt_marts",
        project_config=ProjectConfig(dbt_project_path="/opt/dbt/project"),
        profile_config=profile_config,
        render_config=RenderConfig(
            select=["path:models/marts"],
        ),
    )

    extract >> dbt_staging >> dbt_marts
```

---

## Managed Airflow

### MWAA (Amazon Managed Workflows for Apache Airflow)

```bash
# DAG deployment: upload to S3
aws s3 sync dags/ s3://my-mwaa-bucket/dags/
aws s3 cp requirements.txt s3://my-mwaa-bucket/requirements.txt

# Requirements format (versions must be pinned)
# requirements.txt
apache-airflow-providers-snowflake==5.3.0
astronomer-cosmos==1.4.0
dbt-core==1.7.0
dbt-snowflake==1.7.0
```

**MWAA connection management:**

```bash
# Use AWS Secrets Manager for connections
# Store connection JSON at: airflow/connections/snowflake_default
aws secretsmanager create-secret \
    --name "airflow/connections/snowflake_default" \
    --secret-string "snowflake://user:pass@account/db/schema?warehouse=WH"
```

### Cloud Composer (Google)

```bash
# DAG deployment: upload to GCS
gsutil cp dags/*.py gs://us-central1-my-composer-bucket/dags/

# Install packages via Composer UI or CLI
gcloud composer environments update my-env \
    --location us-central1 \
    --update-pypi-package "astronomer-cosmos>=1.4.0"
```

### Astronomer

```bash
# Deploy via Astro CLI
astro dev init        # Create project
astro dev start       # Local development
astro deploy          # Deploy to Astronomer Cloud

# Project structure
├── dags/             # Your DAG files
├── include/          # SQL files, dbt project, etc.
├── plugins/          # Custom operators/hooks
├── packages.txt      # OS-level packages
├── requirements.txt  # Python packages
└── Dockerfile        # Custom image
```

---

## DAG Best Practices

### DAG Organization

```
dags/
├── __init__.py
├── config/
│   └── dag_configs.yaml       # Centralized DAG configuration
├── ingestion/
│   ├── __init__.py
│   ├── github_ingestion.py
│   └── stripe_ingestion.py
├── transformation/
│   ├── __init__.py
│   └── dbt_transform.py
├── activation/
│   ├── __init__.py
│   └── reverse_etl.py
└── utils/
    ├── __init__.py
    └── alerts.py
```

### DAG Design Patterns

```python
# Pattern: Factory function for similar DAGs
def create_ingestion_dag(source_name: str, schedule: str, conn_id: str):
    @dag(
        dag_id=f"ingest_{source_name}",
        schedule=schedule,
        start_date=datetime(2024, 1, 1),
        catchup=False,
        tags=["ingestion", source_name],
    )
    def ingestion_dag():
        @task()
        def extract():
            hook = BaseHook.get_connection(conn_id)
            return fetch_data(hook)

        @task()
        def load(data):
            load_to_warehouse(data, table=f"raw.{source_name}")

        load(extract())

    return ingestion_dag()

# Generate DAGs
github_dag = create_ingestion_dag("github", "@hourly", "github_api")
stripe_dag = create_ingestion_dag("stripe", "0 */4 * * *", "stripe_api")
```

### Idempotency Patterns

```python
@task()
def idempotent_load(ds: str = None):
    """Load is safe to re-run — uses execution date partition."""
    sf_hook = SnowflakeHook("snowflake_default")

    # Delete existing data for this partition, then re-insert
    sf_hook.run(f"DELETE FROM raw.orders WHERE order_date = '{ds}'")
    sf_hook.run(f"""
        INSERT INTO raw.orders
        SELECT * FROM external_stage
        WHERE order_date = '{ds}'
    """)
```

---

## Testing Airflow DAGs

### DAG Validation

```python
import pytest
from airflow.models import DagBag

def test_dags_load():
    """Verify all DAGs load without import errors."""
    dag_bag = DagBag(include_examples=False)
    assert len(dag_bag.import_errors) == 0, f"DAG import errors: {dag_bag.import_errors}"

def test_dag_has_expected_tasks():
    """Verify DAG structure."""
    dag_bag = DagBag(include_examples=False)
    dag = dag_bag.get_dag("daily_orders")

    assert dag is not None
    assert len(dag.tasks) == 4
    task_ids = [t.task_id for t in dag.tasks]
    assert "extract" in task_ids
    assert "transform" in task_ids
    assert "load" in task_ids
```

### Task Testing

```python
def test_extract_task():
    """Test individual task logic."""
    from dags.ingestion.orders import extract

    # TaskFlow tasks can be called as regular functions
    result = extract(ds="2024-03-15")
    assert isinstance(result, list)
    assert len(result) > 0
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| DAG not showing in UI | Import error or wrong folder | Check `airflow dags list-import-errors` |
| Task stuck in "queued" | Executor at capacity or pool limit | Check executor config, increase parallelism |
| XCom too large | Passing large data between tasks | Use external storage (S3/GCS) instead of XCom |
| Catchup runs all history | `catchup=True` (default) | Set `catchup=False` for most DAGs |
| Connection not found | Wrong conn_id or not configured | Check `airflow connections list` |
| Dynamic tasks fail silently | Map input is empty list | Add guard: `if not items: raise ValueError(...)` |
| Cosmos dbt errors | Version mismatch | Pin both cosmos and dbt versions explicitly |
