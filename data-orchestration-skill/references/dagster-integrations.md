## Contents

- [dagster-dbt](#dagster-dbt)
  - [DbtProject + @dbt_assets](#dbtproject--dbt_assets)
  - [Selecting Models and Partitions](#selecting-models-and-partitions)
  - [Profiles Configuration](#profiles-configuration)
- [dagster-dlt](#dagster-dlt)
  - [Basic @dlt_assets](#basic-dlt_assets)
- [Trifecta: DLT + dbt + Dagster](#trifecta-dlt--dbt--dagster)
- [dagster-k8s](#dagster-k8s)
- [dagster-slack](#dagster-slack)
- [dagster-cloud](#dagster-cloud)
- [Integration Matrix](#integration-matrix)

---

# Dagster Integrations Reference

> First-class integrations between Dagster and the modern data stack. Part of the [Data Orchestration Skill](../SKILL.md).

---

## dagster-dbt

```bash
pip install dagster-dbt dbt-core dbt-snowflake
```

### DbtProject + @dbt_assets

```python
from dagster import Definitions, AssetExecutionContext
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

dbt_project = DbtProject(project_dir=Path(__file__).parent / "dbt_project")
dbt_project.prepare_if_dev()

@dbt_assets(manifest=dbt_project.manifest_path, project=dbt_project)
def my_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()

defs = Definitions(assets=[my_dbt_assets],
    resources={"dbt": DbtCliResource(project_dir=dbt_project)})
```

Every dbt model becomes a Dagster asset with visible dependencies. dbt sources appear as external assets. dbt tests run as part of `build` and report to Dagster.

### Selecting Models and Partitions

```python
@dbt_assets(manifest=dbt_project.manifest_path, select="staging.*")
def staging_assets(context, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()

@dbt_assets(manifest=dbt_project.manifest_path,
    partitions_def=DailyPartitionsDefinition(start_date="2024-01-01"))
def partitioned_dbt(context, dbt: DbtCliResource):
    date = context.partition_key
    yield from dbt.cli(["build", "--vars", f'{{"run_date": "{date}"}}'], context=context).stream()
```

### Profiles Configuration

```yaml
# dbt_project/profiles.yml — all values from environment variables
# All values from environment variables — never inline credentials.
my_project:
  target: "{{ env_var('DBT_TARGET', 'dev') }}"
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      private_key_path: "{{ env_var('SNOWFLAKE_PRIVATE_KEY_PATH') }}"
      database: "{{ env_var('SNOWFLAKE_DATABASE', 'ANALYTICS') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE', 'TRANSFORM_WH') }}"
      schema: "{{ env_var('SNOWFLAKE_SCHEMA', 'DEV') }}"
```

---

## dagster-dlt

```bash
pip install dagster-dlt "dlt[snowflake]"
```

### Basic @dlt_assets

```python
from dagster_dlt import DagsterDltResource, dlt_assets
import dlt

# Credentials: DESTINATION__SNOWFLAKE__CREDENTIALS="snowflake://..."
@dlt.source
def github_source(access_token=dlt.secrets.value):
    @dlt.resource(write_disposition="merge", primary_key="id")
    def issues(updated_at=dlt.sources.incremental("updated_at", initial_value="2024-01-01T00:00:00Z")):
        yield fetch_github_issues(token=access_token, since=updated_at.last_value)
    return issues

@dlt_assets(
    dlt_source=github_source(), dlt_pipeline=dlt.pipeline(
        pipeline_name="github", destination="snowflake", dataset_name="raw_github"),
    name="github", group_name="ingestion")
def github_dlt_assets(context, dlt: DagsterDltResource):
    yield from dlt.run(context=context)
```

Each DLT resource becomes a Dagster asset. DLT metadata (row counts, schema) flows to Dagster. Downstream dbt assets can depend on DLT assets.

---

## Trifecta: DLT + dbt + Dagster

```python
from dagster import Definitions, AssetExecutionContext, define_asset_job, ScheduleDefinition
from dagster_dbt import DbtCliResource, dbt_assets, DbtProject
from dagster_dlt import DagsterDltResource, dlt_assets
import dlt

# DLT ingestion
@dlt_assets(
    dlt_source=stripe_source(),
    dlt_pipeline=dlt.pipeline(pipeline_name="stripe", destination="snowflake", dataset_name="raw_stripe"),
    group_name="ingestion")
def stripe_dlt_assets(context, dlt: DagsterDltResource):
    yield from dlt.run(context=context)

# dbt transformation (auto-links to DLT assets via dbt sources)
dbt_project = DbtProject(project_dir="path/to/dbt/project")

@dbt_assets(manifest=dbt_project.manifest_path, project=dbt_project)
def dbt_transform_assets(context, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()

# Schedule
daily_pipeline = define_asset_job("daily_pipeline", selection=[stripe_dlt_assets, dbt_transform_assets])
daily_schedule = ScheduleDefinition(job=daily_pipeline, cron_schedule="0 6 * * *")

defs = Definitions(
    assets=[stripe_dlt_assets, dbt_transform_assets],
    resources={"dlt": DagsterDltResource(), "dbt": DbtCliResource(project_dir=dbt_project)},
    jobs=[daily_pipeline], schedules=[daily_schedule])
```

---

## dagster-k8s

```python
@asset(op_tags={"dagster-k8s/config": {
    "container_config": {"resources": {"requests": {"cpu": "500m", "memory": "1Gi"},
                                        "limits": {"cpu": "2", "memory": "4Gi"}}}}})
def heavy_computation():
    """Runs in its own k8s pod with dedicated resources."""
    pass
```

## dagster-slack

```python
from dagster import failure_hook, HookContext
from dagster_slack import SlackResource

@failure_hook
def slack_on_failure(context: HookContext):
    context.resources.slack.get_client().chat_postMessage(
        channel="#data-alerts",
        text=f"Asset `{context.op.name}` FAILED — Run: {context.run_id}")

defs = Definitions(resources={"slack": SlackResource(token=EnvVar("SLACK_BOT_TOKEN"))})
```

## dagster-cloud

```yaml
# .github/workflows/dagster-cloud.yml
- uses: dagster-io/dagster-cloud-action@v2
  with:
    dagster-cloud-token: ${{ secrets.DAGSTER_CLOUD_TOKEN }}
    location-name: analytics
    deployment: ${{ github.event_name == 'push' && 'prod' || 'branch' }}
```

## Integration Matrix

| Integration | Package | Maturity |
|-------------|---------|----------|
| dbt Core | `dagster-dbt` | Stable |
| DLT | `dagster-dlt` | Stable |
| Snowflake | `dagster-snowflake` | Stable |
| BigQuery | `dagster-gcp` | Stable |
| Databricks | `dagster-databricks` | Stable |
| DuckDB | `dagster-duckdb` | Stable |
| Kubernetes | `dagster-k8s` | Stable |
| Slack | `dagster-slack` | Stable |
