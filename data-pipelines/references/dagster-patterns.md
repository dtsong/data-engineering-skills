## Contents

- [Basic Asset](#basic-asset)
- [Resources (Dependency Injection)](#resources-dependency-injection)
- [Schedules and Sensors](#schedules-and-sensors)
- [Multi-Asset](#multi-asset)
- [Partitions](#partitions)
- [Auto-Materialize and Freshness](#auto-materialize-and-freshness)
- [I/O Managers](#io-managers)
- [Asset Checks](#asset-checks)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

# Dagster Patterns Reference

> Advanced Dagster patterns for production data platforms. Part of the [Data Orchestration Skill](../SKILL.md).

---

## Basic Asset

```python
from dagster import asset, Definitions, MaterializeResult, MetadataValue

@asset(description="Raw orders from source", group_name="ingestion", compute_kind="python")
def raw_orders() -> MaterializeResult:
    orders_df = extract_orders_from_source()
    load_to_warehouse(orders_df, "raw.orders")
    return MaterializeResult(
        metadata={"row_count": MetadataValue.int(len(orders_df)),
                  "preview": MetadataValue.md(orders_df.head().to_markdown())}
    )

@asset(description="Staged orders", group_name="staging")
def stg_orders(raw_orders):
    return execute_sql("SELECT DISTINCT order_id, customer_id, ... FROM raw.orders")

defs = Definitions(assets=[raw_orders, stg_orders])
```

## Resources (Dependency Injection)

```python
from dagster import asset, Definitions, ConfigurableResource

class SnowflakeResource(ConfigurableResource):
    account: str = os.environ.get("SNOWFLAKE_ACCOUNT", "")
    user: str = os.environ.get("SNOWFLAKE_USER", "")
    private_key_path: str = os.environ.get("SNOWFLAKE_PRIVATE_KEY_PATH", "")
    warehouse: str = "COMPUTE_WH"

    def execute_sql(self, sql: str):
        conn = snowflake.connector.connect(
            account=self.account, user=self.user,
            private_key_file_path=self.private_key_path, warehouse=self.warehouse)
        return conn.cursor().execute(sql).fetchall()

defs = Definitions(assets=[raw_orders], resources={"snowflake": SnowflakeResource()})
```

## Schedules and Sensors

```python
from dagster import define_asset_job, ScheduleDefinition, sensor, RunRequest

daily_job = define_asset_job(name="daily_pipeline", selection=["raw_orders", "stg_orders"])
daily_schedule = ScheduleDefinition(job=daily_job, cron_schedule="0 6 * * *")

@sensor(job=daily_job, minimum_interval_seconds=60)
def s3_file_sensor(context):
    s3 = boto3.client("s3")
    last_key = context.cursor or ""
    response = s3.list_objects_v2(Bucket="data-landing", Prefix="orders/", StartAfter=last_key)
    new_files = response.get("Contents", [])
    if new_files:
        latest_key = new_files[-1]["Key"]
        context.update_cursor(latest_key)
        yield RunRequest(run_key=latest_key)
```

---

## Multi-Asset

```python
from dagster import multi_asset, AssetOut, Output

@multi_asset(
    outs={"customers": AssetOut(), "orders": AssetOut(), "order_items": AssetOut()},
    group_name="raw",
)
def extract_ecommerce(context):
    data = fetch_ecommerce_data()
    yield Output(data["customers"], output_name="customers")
    yield Output(data["orders"], output_name="orders")
    yield Output(data["order_items"], output_name="order_items")
```

## Partitions

```python
from dagster import DailyPartitionsDefinition, MonthlyPartitionsDefinition, StaticPartitionsDefinition

# Daily
daily = DailyPartitionsDefinition(start_date="2024-01-01")

@asset(partitions_def=daily)
def daily_events(context):
    date = context.partition_key
    events = fetch_events(date=date)
    return MaterializeResult(metadata={"row_count": len(events), "partition": date})

# Multi-dimensional
from dagster import MultiPartitionsDefinition
multi = MultiPartitionsDefinition({
    "date": DailyPartitionsDefinition(start_date="2024-01-01"),
    "region": StaticPartitionsDefinition(["us", "eu", "ap"]),
})

# Backfill: dagster asset materialize --select daily_events --partition "2024-01-01...2024-01-31"
```

## Auto-Materialize and Freshness

```python
from dagster import FreshnessPolicy, AutoMaterializePolicy

@asset(
    freshness_policy=FreshnessPolicy(maximum_lag_minutes=60),
    auto_materialize_policy=AutoMaterializePolicy.eager(),
)
def fct_orders(stg_orders):
    """Orders mart with 1-hour freshness SLA. Auto-materializes when upstream changes."""
    pass
```

---

## I/O Managers

```python
from dagster_snowflake_pandas import SnowflakePandasIOManager
from dagster_duckdb_pandas import DuckDBPandasIOManager

defs = Definitions(
    assets=[...],
    resources={
        "io_manager": SnowflakePandasIOManager(
            account=EnvVar("SNOWFLAKE_ACCOUNT"), user=EnvVar("SNOWFLAKE_USER"),
            password=EnvVar("SNOWFLAKE_PASSWORD"), database="ANALYTICS", schema="STAGING")
        if os.environ.get("DAGSTER_ENV") != "local"
        else DuckDBPandasIOManager(database="dev.duckdb"),
    },
)
```

## Asset Checks

```python
from dagster import asset_check, AssetCheckResult, AssetCheckSeverity

@asset_check(asset=fct_orders)
def orders_not_empty():
    count = execute_sql("SELECT COUNT(*) FROM marts.fct_orders")[0][0]
    return AssetCheckResult(passed=count > 0, severity=AssetCheckSeverity.ERROR,
                            metadata={"row_count": count})

@asset_check(asset=fct_orders)
def orders_freshness():
    latest = execute_sql("SELECT MAX(order_date) FROM marts.fct_orders")[0][0]
    hours_old = (datetime.now() - latest).total_seconds() / 3600
    return AssetCheckResult(passed=hours_old < 24, severity=AssetCheckSeverity.ERROR,
                            metadata={"hours_since_latest": hours_old})
```

---

## Testing

```python
from dagster import materialize, build_sensor_context

def test_stg_orders():
    result = materialize([raw_orders, stg_orders], resources={"snowflake": MockSnowflakeResource()})
    assert result.success

def test_s3_sensor():
    context = build_sensor_context(cursor="2024-01-01T00:00:00Z")
    assert len(list(s3_file_sensor(context))) > 0
```

## Deployment

```yaml
# dagster_cloud.yaml
locations:
  - location_name: analytics
    code_source:
      package_name: my_dagster_project
    container_context:
      k8s:
        env_vars: [SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PRIVATE_KEY_PATH]
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Asset doesn't materialize | Check asset graph for unresolved upstream deps |
| Sensor fires but run fails | Log and validate `run_config` in sensor |
| Backfill stuck | Check `dagster.yaml` concurrency settings |
| I/O manager errors | Verify `EnvVar` values are set in deployment |
| `dagster dev` slow | Use `--module` flag to load specific module |
