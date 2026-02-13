# Dagster Patterns Reference

> Advanced Dagster patterns for production data platforms. Part of the [Data Orchestration Skill](../SKILL.md).

---

## Asset Patterns

### Multi-Asset (One Op, Multiple Outputs)

Use `@multi_asset` when a single computation produces multiple tables or artifacts.

```python
from dagster import multi_asset, AssetOut, Output

@multi_asset(
    outs={
        "customers": AssetOut(description="Customer dimension table"),
        "orders": AssetOut(description="Order fact table"),
        "order_items": AssetOut(description="Order line items"),
    },
    group_name="raw",
    compute_kind="python",
)
def extract_ecommerce(context):
    """Single API call returns multiple related datasets."""
    data = fetch_ecommerce_data()

    yield Output(data["customers"], output_name="customers")
    yield Output(data["orders"], output_name="orders")
    yield Output(data["order_items"], output_name="order_items")
```

### Asset Dependencies (Explicit)

```python
from dagster import asset, AssetKey

@asset(
    deps=[AssetKey("raw_customers"), AssetKey("raw_orders")],
    description="Joined customer-order view",
)
def customer_orders():
    """Depends on raw tables but doesn't receive them as function args."""
    return execute_sql("""
        SELECT c.*, o.order_count, o.total_spend
        FROM raw.customers c
        JOIN (
            SELECT customer_id, COUNT(*) order_count, SUM(amount) total_spend
            FROM raw.orders GROUP BY customer_id
        ) o ON c.id = o.customer_id
    """)
```

### Asset Groups and Tags

```python
@asset(
    group_name="marts",
    tags={"domain": "finance", "tier": "gold"},
    owners=["team:analytics"],
    kinds={"sql", "snowflake"},
)
def fct_revenue():
    """Finance mart — revenue by month."""
    pass
```

---

## Partitions

### Daily Partitions

```python
from dagster import asset, DailyPartitionsDefinition, AssetExecutionContext

daily_partitions = DailyPartitionsDefinition(
    start_date="2024-01-01",
    end_offset=0,  # Don't create future partitions
)

@asset(partitions_def=daily_partitions)
def daily_events(context: AssetExecutionContext):
    """Load events for a specific date."""
    date = context.partition_key  # "2024-03-15"
    context.log.info(f"Processing events for {date}")

    events = fetch_events(date=date)
    load_to_warehouse(events, table="raw.events", partition=date)

    return MaterializeResult(
        metadata={"row_count": len(events), "partition": date}
    )
```

### Monthly Partitions

```python
from dagster import MonthlyPartitionsDefinition

monthly_partitions = MonthlyPartitionsDefinition(start_date="2024-01-01")

@asset(partitions_def=monthly_partitions)
def monthly_report(context: AssetExecutionContext):
    """Generate monthly aggregation report."""
    month = context.partition_key  # "2024-03"
    return generate_report(month=month)
```

### Static Partitions

```python
from dagster import StaticPartitionsDefinition

region_partitions = StaticPartitionsDefinition(["us-east", "us-west", "eu-west", "ap-southeast"])

@asset(partitions_def=region_partitions)
def regional_metrics(context: AssetExecutionContext):
    """Compute metrics per region."""
    region = context.partition_key
    return compute_metrics(region=region)
```

### Multi-Dimensional Partitions

```python
from dagster import MultiPartitionsDefinition, DailyPartitionsDefinition, StaticPartitionsDefinition

multi_partitions = MultiPartitionsDefinition({
    "date": DailyPartitionsDefinition(start_date="2024-01-01"),
    "region": StaticPartitionsDefinition(["us", "eu", "ap"]),
})

@asset(partitions_def=multi_partitions)
def partitioned_sales(context: AssetExecutionContext):
    """Sales data partitioned by date AND region."""
    keys = context.partition_key.keys_by_dimension
    date = keys["date"]      # "2024-03-15"
    region = keys["region"]  # "us"
    return fetch_sales(date=date, region=region)
```

### Backfill Strategies

```bash
# CLI backfill for date range
dagster asset materialize \
    --select daily_events \
    --partition "2024-01-01...2024-01-31"

# Backfill all partitions
dagster asset materialize \
    --select daily_events \
    --partition-range-start "2024-01-01" \
    --partition-range-end "2024-12-31"
```

In the Dagster UI: Navigate to the asset → Partitions tab → Select range → Click "Materialize".

---

## Sensors

### S3 File Arrival Sensor

```python
from dagster import sensor, RunRequest, SensorEvaluationContext, SkipReason
import boto3

@sensor(
    job=ingest_job,
    minimum_interval_seconds=60,
    default_status=DefaultSensorStatus.RUNNING,
)
def s3_file_sensor(context: SensorEvaluationContext):
    """Trigger ingestion when new files land in S3."""
    s3 = boto3.client("s3")
    last_modified = context.cursor or "1970-01-01T00:00:00Z"

    response = s3.list_objects_v2(
        Bucket="data-landing",
        Prefix="orders/",
    )

    new_files = [
        obj for obj in response.get("Contents", [])
        if obj["LastModified"].isoformat() > last_modified
    ]

    if not new_files:
        yield SkipReason("No new files in S3")
        return

    for f in new_files:
        yield RunRequest(
            run_key=f["Key"],
            run_config={"resources": {"s3_key": f["Key"]}},
        )

    latest = max(f["LastModified"].isoformat() for f in new_files)
    context.update_cursor(latest)
```

### Asset Freshness Sensor

```python
from dagster import asset, FreshnessPolicy, AutoMaterializePolicy

# Auto-materialize when upstream changes OR when stale
@asset(
    freshness_policy=FreshnessPolicy(maximum_lag_minutes=60),
    auto_materialize_policy=AutoMaterializePolicy.eager(),
)
def fct_orders(stg_orders):
    """Orders mart with 1-hour freshness SLA."""
    pass
```

### Multi-Asset Sensor

```python
from dagster import multi_asset_sensor, RunRequest, AssetKey

@multi_asset_sensor(
    monitored_assets=[AssetKey("raw_customers"), AssetKey("raw_orders")],
    job=transform_job,
)
def transform_trigger(context):
    """Trigger transforms when BOTH raw tables are materialized."""
    customers_event = context.latest_materialization_records_by_key().get(
        AssetKey("raw_customers")
    )
    orders_event = context.latest_materialization_records_by_key().get(
        AssetKey("raw_orders")
    )

    if customers_event and orders_event:
        yield RunRequest(run_key=f"{customers_event.timestamp}-{orders_event.timestamp}")
```

---

## I/O Managers

I/O managers handle how assets are stored and loaded. Use them to decouple asset logic from storage details.

### Snowflake I/O Manager

```python
from dagster_snowflake_pandas import SnowflakePandasIOManager
from dagster import Definitions

defs = Definitions(
    assets=[...],
    resources={
        "io_manager": SnowflakePandasIOManager(
            account=EnvVar("SNOWFLAKE_ACCOUNT"),
            user=EnvVar("SNOWFLAKE_USER"),
            password=EnvVar("SNOWFLAKE_PASSWORD"),
            database="ANALYTICS",
            warehouse="COMPUTE_WH",
            schema="STAGING",
        ),
    },
)

# Assets return DataFrames; I/O manager handles storage
@asset
def stg_orders() -> pd.DataFrame:
    """Return DataFrame — I/O manager writes to Snowflake."""
    return pd.read_sql("SELECT * FROM raw.orders", conn)
```

### DuckDB I/O Manager (Local Dev)

```python
from dagster_duckdb_pandas import DuckDBPandasIOManager

# Use DuckDB locally, Snowflake in production
defs = Definitions(
    assets=[...],
    resources={
        "io_manager": DuckDBPandasIOManager(database="dev.duckdb")
        if os.environ.get("DAGSTER_ENV") == "local"
        else SnowflakePandasIOManager(...),
    },
)
```

---

## Asset Checks

Asset checks validate data quality after materialization.

```python
from dagster import asset_check, AssetCheckResult, AssetCheckSeverity

@asset_check(asset=fct_orders)
def orders_not_empty():
    """Fail if orders table is empty."""
    count = execute_sql("SELECT COUNT(*) FROM marts.fct_orders")[0][0]
    return AssetCheckResult(
        passed=count > 0,
        severity=AssetCheckSeverity.ERROR,
        metadata={"row_count": count},
    )

@asset_check(asset=fct_orders)
def orders_no_negative_amounts():
    """Warn if negative order amounts exist."""
    negatives = execute_sql(
        "SELECT COUNT(*) FROM marts.fct_orders WHERE total_amount < 0"
    )[0][0]
    return AssetCheckResult(
        passed=negatives == 0,
        severity=AssetCheckSeverity.WARN,
        metadata={"negative_count": negatives},
    )

@asset_check(asset=fct_orders)
def orders_freshness():
    """Fail if latest order is older than 24 hours."""
    latest = execute_sql(
        "SELECT MAX(order_date) FROM marts.fct_orders"
    )[0][0]
    hours_old = (datetime.now() - latest).total_seconds() / 3600
    return AssetCheckResult(
        passed=hours_old < 24,
        severity=AssetCheckSeverity.ERROR,
        metadata={"hours_since_latest": hours_old},
    )
```

---

## Deployment Patterns

### Dagster Cloud

```yaml
# dagster_cloud.yaml
locations:
  - location_name: analytics
    code_source:
      package_name: my_dagster_project
    build:
      directory: .
      registry: us-docker.pkg.dev/my-project/dagster/analytics
    container_context:
      k8s:
        env_vars:
          - SNOWFLAKE_ACCOUNT
          - SNOWFLAKE_USER
          - SNOWFLAKE_PRIVATE_KEY_PATH
```

### Self-Hosted (Kubernetes)

```yaml
# Helm values for dagster on k8s
dagster-user-deployments:
  deployments:
    - name: analytics-pipeline
      image:
        repository: my-registry/dagster-analytics
        tag: latest
      dagsterApiGrpcArgs:
        - "-m"
        - "my_dagster_project"
      envSecrets:
        - name: snowflake-credentials
        - name: dlt-credentials
```

### Docker Compose (Development)

```yaml
version: "3.8"
services:
  dagster-webserver:
    image: dagster-project:latest
    command: dagster-webserver -h 0.0.0.0 -p 3000
    ports:
      - "3000:3000"
    environment:
      DAGSTER_HOME: /opt/dagster
      SNOWFLAKE_ACCOUNT: ${SNOWFLAKE_ACCOUNT}
    volumes:
      - dagster-storage:/opt/dagster/storage

  dagster-daemon:
    image: dagster-project:latest
    command: dagster-daemon run
    environment:
      DAGSTER_HOME: /opt/dagster
    volumes:
      - dagster-storage:/opt/dagster/storage

volumes:
  dagster-storage:
```

---

## Testing

### Asset Unit Tests

```python
from dagster import materialize

def test_stg_orders():
    """Test asset materialization."""
    result = materialize(
        [raw_orders, stg_orders],
        resources={"snowflake": MockSnowflakeResource()},
    )
    assert result.success

    # Check output metadata
    stg_output = result.output_for_node("stg_orders")
    assert len(stg_output) > 0
```

### Sensor Tests

```python
from dagster import build_sensor_context

def test_s3_sensor():
    """Test sensor detects new files."""
    context = build_sensor_context(cursor="2024-01-01T00:00:00Z")
    result = s3_file_sensor(context)

    run_requests = list(result)
    assert len(run_requests) > 0
```

### Schedule Tests

```python
from dagster import validate_run_config

def test_daily_pipeline_config():
    """Validate daily pipeline produces valid run config."""
    assert validate_run_config(daily_pipeline_job)
```

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Asset doesn't materialize | Missing upstream dependency | Check asset graph in UI for unresolved deps |
| Sensor fires but run fails | Run config mismatch | Log `run_config` in sensor, validate with `validate_run_config` |
| Backfill stuck | Concurrency limit reached | Check `dagster.yaml` concurrency settings |
| I/O manager errors | Credential misconfiguration | Verify `EnvVar` values are set in deployment |
| `dagster dev` slow | Large project loading | Use `--module` flag to load specific module |
| Partition key format wrong | Timezone mismatch | Use `timezone` param in partition definition |
