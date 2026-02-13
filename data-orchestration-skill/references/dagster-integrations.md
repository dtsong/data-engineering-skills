# Dagster Integrations Reference

> First-class integrations between Dagster and the modern data stack. Part of the [Data Orchestration Skill](../SKILL.md).

---

## dagster-dbt

`dagster-dbt` maps dbt models to Dagster assets automatically, giving you full lineage, partitioning, and scheduling for your dbt project.

### Installation

```bash
pip install dagster-dbt dbt-core dbt-snowflake  # or dbt-bigquery, dbt-databricks
```

### DbtProject + @dbt_assets (Recommended)

```python
from pathlib import Path
from dagster import Definitions, AssetExecutionContext
from dagster_dbt import DbtCliResource, DbtProject, dbt_assets

# Point to your dbt project
dbt_project = DbtProject(
    project_dir=Path(__file__).parent / "dbt_project",
    packaged_project_dir=Path(__file__).parent / "dbt_project",  # For deployment
)

# Prepare manifest (runs dbt parse at import time)
dbt_project.prepare_if_dev()

@dbt_assets(
    manifest=dbt_project.manifest_path,
    project=dbt_project,
)
def my_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    """All dbt models as Dagster assets."""
    yield from dbt.cli(["build"], context=context).stream()

defs = Definitions(
    assets=[my_dbt_assets],
    resources={
        "dbt": DbtCliResource(project_dir=dbt_project),
    },
)
```

**What this gives you:**

- Every dbt model appears as a Dagster asset in the UI
- Dependencies between models are visible in the asset graph
- dbt sources appear as external assets (upstream dependencies)
- dbt tests run as part of `dbt build` and report to Dagster
- Metadata (row counts, execution time) flows into Dagster

### Selecting Specific Models

```python
@dbt_assets(
    manifest=dbt_project.manifest_path,
    select="staging.*",  # Only staging models
)
def staging_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()

@dbt_assets(
    manifest=dbt_project.manifest_path,
    select="marts.*",  # Only mart models
)
def marts_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()
```

### Partitioned dbt Assets

```python
from dagster import DailyPartitionsDefinition

@dbt_assets(
    manifest=dbt_project.manifest_path,
    partitions_def=DailyPartitionsDefinition(start_date="2024-01-01"),
)
def partitioned_dbt(context: AssetExecutionContext, dbt: DbtCliResource):
    """Run dbt for a specific date partition."""
    date = context.partition_key
    yield from dbt.cli(
        ["build", "--vars", f'{{"run_date": "{date}"}}'],
        context=context,
    ).stream()
```

### dbt Asset Checks from dbt Tests

```python
from dagster_dbt import build_dbt_asset_selection

# dbt tests automatically become Dagster asset checks
@dbt_assets(manifest=dbt_project.manifest_path)
def my_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    # "build" runs both models and tests
    yield from dbt.cli(["build"], context=context).stream()

# dbt test results appear as asset check results in the Dagster UI
```

### Custom Metadata from dbt

```python
@dbt_assets(manifest=dbt_project.manifest_path)
def my_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    for event in dbt.cli(["build"], context=context).stream_raw_events():
        # Add custom metadata for each model
        if event.event_type_value == "RunResultEvent":
            context.log.info(
                f"Model {event.raw_event['data']['node_info']['unique_id']} "
                f"completed in {event.raw_event['data']['execution_time']}s"
            )
        yield from event.to_default_asset_events()
```

### Profiles Configuration

```yaml
# dbt_project/profiles.yml
# ── Credential boundary ──────────────────────────────────────────────
# All values come from environment variables set on the Dagster deployment.
# Never hardcode credentials in profiles.yml.
# See: shared-references/data-engineering/security-compliance-patterns.md
# ─────────────────────────────────────────────────────────────────────
my_project:
  target: "{{ env_var('DBT_TARGET', 'dev') }}"
  outputs:
    dev:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      private_key_path: "{{ env_var('SNOWFLAKE_PRIVATE_KEY_PATH') }}"
      role: "{{ env_var('SNOWFLAKE_ROLE', 'TRANSFORMER') }}"
      database: "{{ env_var('SNOWFLAKE_DATABASE', 'ANALYTICS') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE', 'TRANSFORM_WH') }}"
      schema: "{{ env_var('SNOWFLAKE_SCHEMA', 'DEV') }}"
      threads: 4
```

---

## dagster-dlt

`dagster-dlt` wraps DLT sources as Dagster multi-assets, giving you asset lineage from ingestion through transformation.

### Installation

```bash
pip install dagster-dlt "dlt[snowflake]"  # or dlt[bigquery], dlt[databricks]
```

### Basic @dlt_assets

```python
from dagster import Definitions, AssetExecutionContext
from dagster_dlt import DagsterDltResource, dlt_assets
import dlt

# ── Credential boundary ──────────────────────────────────────────────
# DLT credentials come from environment variables on the Dagster deployment.
# Configure: DESTINATION__SNOWFLAKE__CREDENTIALS="snowflake://..."
# ─────────────────────────────────────────────────────────────────────

@dlt.source
def github_source(access_token: str = dlt.secrets.value):
    @dlt.resource(write_disposition="merge", primary_key="id")
    def issues(
        updated_at=dlt.sources.incremental("updated_at", initial_value="2024-01-01T00:00:00Z"),
    ):
        yield fetch_github_issues(token=access_token, since=updated_at.last_value)

    @dlt.resource(write_disposition="merge", primary_key="id")
    def pull_requests():
        yield fetch_github_prs(token=access_token)

    return issues, pull_requests

@dlt_assets(
    dlt_source=github_source(),
    dlt_pipeline=dlt.pipeline(
        pipeline_name="github_dagster",
        destination="snowflake",
        dataset_name="raw_github",
    ),
    name="github",
    group_name="ingestion",
)
def github_dlt_assets(context: AssetExecutionContext, dlt: DagsterDltResource):
    yield from dlt.run(context=context)

defs = Definitions(
    assets=[github_dlt_assets],
    resources={"dlt": DagsterDltResource()},
)
```

**What this gives you:**

- Each DLT resource becomes a Dagster asset (e.g., `github/issues`, `github/pull_requests`)
- DLT load metadata (row counts, schema) flows to Dagster
- Downstream dbt assets can depend on DLT assets
- Dagster handles scheduling, retries, and alerting

### Custom Asset Key Mapping

```python
from dagster_dlt import DagsterDltTranslator
from dagster import AssetKey

class MyDltTranslator(DagsterDltTranslator):
    def get_asset_key(self, resource) -> AssetKey:
        """Custom asset key: raw/source/table format."""
        return AssetKey(["raw", "github", resource.name])

    def get_deps_asset_keys(self, resource):
        """No upstream dependencies for source assets."""
        return []

@dlt_assets(
    dlt_source=github_source(),
    dlt_pipeline=pipeline,
    dagster_dlt_translator=MyDltTranslator(),
)
def github_assets(context, dlt: DagsterDltResource):
    yield from dlt.run(context=context)
```

### DLT + dbt Combined Pipeline

```python
# The full trifecta: DLT ingests → dbt transforms → Dagster orchestrates

@dlt_assets(
    dlt_source=stripe_source(),
    dlt_pipeline=dlt.pipeline(
        pipeline_name="stripe",
        destination="snowflake",
        dataset_name="raw_stripe",
    ),
    group_name="ingestion",
)
def stripe_assets(context, dlt: DagsterDltResource):
    yield from dlt.run(context=context)

@dbt_assets(
    manifest=dbt_project.manifest_path,
    # dbt sources reference the raw_stripe schema that DLT creates
    # Dagster automatically links dbt source → DLT asset
)
def dbt_assets(context, dbt: DbtCliResource):
    yield from dbt.cli(["build"], context=context).stream()

# In your dbt project:
# models/staging/sources.yml
# sources:
#   - name: raw_stripe
#     schema: raw_stripe
#     tables:
#       - name: customers
#       - name: charges
```

---

## dagster-k8s

Run Dagster ops and assets on Kubernetes for resource isolation and scaling.

### Per-Asset Kubernetes Configuration

```python
from dagster_k8s import k8s_job_executor

@asset(
    op_tags={
        "dagster-k8s/config": {
            "container_config": {
                "resources": {
                    "requests": {"cpu": "500m", "memory": "1Gi"},
                    "limits": {"cpu": "2", "memory": "4Gi"},
                },
            },
        },
    },
)
def heavy_computation():
    """This asset runs in its own k8s pod with dedicated resources."""
    pass
```

### Step-Level Isolation

```python
from dagster import job, op
from dagster_k8s import k8s_job_executor

@op(
    tags={
        "dagster-k8s/config": {
            "container_config": {
                "resources": {"requests": {"memory": "8Gi"}},
            },
        },
    },
)
def memory_intensive_op():
    """Runs in an isolated pod with 8Gi memory."""
    pass

@job(executor_def=k8s_job_executor)
def isolated_job():
    memory_intensive_op()
```

---

## dagster-slack / dagster-pagerduty

### Slack Alerting

```python
from dagster_slack import SlackResource

# ── Credential boundary ──────────────────────────────────────────────
# Configure: export SLACK_BOT_TOKEN="xoxb-xxx"
# ─────────────────────────────────────────────────────────────────────

@asset
def monitored_asset(context, slack: SlackResource):
    """Asset that sends Slack notification on completion."""
    result = do_work()

    slack.get_client().chat_postMessage(
        channel="#data-alerts",
        text=f"Asset `monitored_asset` completed: {result.row_count} rows loaded",
    )

defs = Definitions(
    assets=[monitored_asset],
    resources={
        "slack": SlackResource(token=EnvVar("SLACK_BOT_TOKEN")),
    },
)
```

### Failure Hooks

```python
from dagster import failure_hook, HookContext

@failure_hook
def slack_on_failure(context: HookContext):
    """Send Slack message on any asset failure."""
    context.resources.slack.get_client().chat_postMessage(
        channel="#data-alerts",
        text=(
            f"Asset `{context.op.name}` FAILED\n"
            f"Run ID: {context.run_id}\n"
            f"Error: {context.op_exception}"
        ),
    )

# Apply to all assets in a job
@job(hooks={slack_on_failure})
def alerting_job():
    ...
```

---

## dagster-cloud

### Branch Deployments

Dagster Cloud supports branch deployments for PR-based development:

```yaml
# .github/workflows/dagster-cloud.yml
name: Dagster Cloud Deploy
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dagster-io/dagster-cloud-action@v2
        with:
          dagster-cloud-token: ${{ secrets.DAGSTER_CLOUD_TOKEN }}
          location-name: analytics
          deployment: ${{ github.event_name == 'push' && 'prod' || 'branch' }}
```

### Environment-Specific Resources

```python
import os
from dagster import Definitions, EnvVar

# Resources change by environment
if os.environ.get("DAGSTER_CLOUD_DEPLOYMENT_NAME") == "prod":
    io_manager = SnowflakePandasIOManager(
        account=EnvVar("SNOWFLAKE_ACCOUNT"),
        database="ANALYTICS_PROD",
        schema="MARTS",
    )
else:
    io_manager = DuckDBPandasIOManager(database="dev.duckdb")

defs = Definitions(
    assets=[...],
    resources={"io_manager": io_manager},
)
```

---

## Integration Matrix

| Integration | Package | Version | Maturity | Notes |
|-------------|---------|---------|----------|-------|
| dbt Core | `dagster-dbt` | 0.24+ | Stable | `@dbt_assets`, `DbtCliResource` |
| DLT | `dagster-dlt` | 0.28+ | Stable | `@dlt_assets`, `DagsterDltResource` |
| Snowflake | `dagster-snowflake` | 0.24+ | Stable | I/O managers, resources |
| BigQuery | `dagster-gcp` | 0.24+ | Stable | I/O managers, resources |
| Databricks | `dagster-databricks` | 0.24+ | Stable | Step launcher, I/O managers |
| DuckDB | `dagster-duckdb` | 0.24+ | Stable | I/O managers (great for local dev) |
| Kubernetes | `dagster-k8s` | 0.24+ | Stable | Executor, step launcher |
| Slack | `dagster-slack` | 0.24+ | Stable | Notifications, hooks |
| PagerDuty | `dagster-pagerduty` | 0.24+ | Stable | Incident creation |
| Fivetran | `dagster-fivetran` | 0.24+ | Stable | Sync monitoring |
| Airbyte | `dagster-airbyte` | 0.24+ | Stable | Sync monitoring |
