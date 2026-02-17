## Contents

- [Recurring Engagement Patterns](#recurring-engagement-patterns)
- [File-Drop Sensors](#file-drop-sensors)
- [Client-Specific Scheduling](#client-specific-scheduling)
- [Engagement Lifecycle as Dagster Assets](#engagement-lifecycle-as-dagster-assets)
- [Monitoring and SLA Tracking](#monitoring-and-sla-tracking)

# Consulting Orchestration — Reference

> **Part of:** [data-pipelines](../SKILL.md)

---

## Recurring Engagement Patterns

Many consulting engagements become recurring: weekly cleaning runs, monthly data refreshes, or ongoing data quality monitoring. Orchestrate these as scheduled Dagster jobs.

**Weekly cleaning pipeline:**

```python
from dagster import ScheduleDefinition, define_asset_job

weekly_cleaning_job = define_asset_job(
    name="weekly_cleaning",
    selection=["file_received", "profiled", "cleaned", "validated", "delivered"],
    tags={"client_id": "acme_corp", "engagement_type": "recurring"},
)

weekly_schedule = ScheduleDefinition(
    job=weekly_cleaning_job,
    cron_schedule="0 6 * * 1",  # Monday 6 AM
)
```

**Monthly refresh pattern:** Use `MonthlyPartitionsDefinition` to partition by month. Each run processes the current month's files and appends to the historical quality report.

---

## File-Drop Sensors

Dagster sensors watch for new client file uploads, triggering pipeline runs automatically.

**S3 file-drop sensor:**

```python
from dagster import sensor, RunRequest, SensorEvaluationContext
import boto3

@sensor(job=weekly_cleaning_job, minimum_interval_seconds=300)
def s3_file_drop_sensor(context: SensorEvaluationContext):
    # SECURITY: Uses IAM role, no hardcoded credentials
    s3 = boto3.client("s3")
    bucket = "client-uploads"
    prefix = "acme_corp/incoming/"

    response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
    new_files = [
        obj["Key"] for obj in response.get("Contents", [])
        if obj["Key"] > (context.cursor or "")
    ]

    if new_files:
        context.update_cursor(max(new_files))
        yield RunRequest(
            run_key=f"file_drop_{max(new_files)}",
            run_config={"ops": {"file_received": {"config": {"files": new_files}}}},
        )
```

**Local directory sensor (development):**

```python
from dagster import sensor, RunRequest
from pathlib import Path

@sensor(job=weekly_cleaning_job, minimum_interval_seconds=60)
def local_file_sensor(context):
    watch_dir = Path("data/raw/incoming")
    processed_marker = Path("data/raw/.processed")
    processed = set(processed_marker.read_text().splitlines()) if processed_marker.exists() else set()

    new_files = [f.name for f in watch_dir.iterdir() if f.is_file() and f.name not in processed]

    if new_files:
        processed.update(new_files)
        processed_marker.write_text("\n".join(sorted(processed)))
        yield RunRequest(
            run_key=f"local_{'-'.join(sorted(new_files))}",
            run_config={"ops": {"file_received": {"config": {"files": new_files}}}},
        )
```

---

## Client-Specific Scheduling

Use Dagster partitions and config to run the same pipeline for multiple clients with client-specific parameters.

**Config-driven multi-client pipeline:**

```python
from dagster import StaticPartitionsDefinition, asset, Config

client_partitions = StaticPartitionsDefinition(["acme_corp", "globex", "initech"])

class ClientConfig(Config):
    client_id: str
    security_tier: int = 2
    source_bucket: str = ""
    alert_channel: str = "#data-alerts"

@asset(partitions_def=client_partitions)
def profiled(context):
    client_id = context.partition_key
    # Load client-specific config from YAML or env
    config = load_client_config(client_id)
    return run_profiler(client_id, config)
```

**Per-client schedule factory:**

```python
def make_client_schedule(client_id: str, cron: str) -> ScheduleDefinition:
    job = define_asset_job(
        name=f"{client_id}_cleaning",
        selection=["file_received", "profiled", "cleaned", "validated", "delivered"],
        tags={"client_id": client_id},
        partitions_def=client_partitions,
    )
    return ScheduleDefinition(job=job, cron_schedule=cron)

acme_schedule = make_client_schedule("acme_corp", "0 6 * * 1")
globex_schedule = make_client_schedule("globex", "0 8 1 * *")
```

---

## Engagement Lifecycle as Dagster Assets

Model the engagement lifecycle as a Dagster asset chain:

```
file_received → profiled → cleaned → validated → delivered
```

```python
from dagster import asset, AssetIn, Output, MetadataValue

@asset(group_name="engagement")
def file_received(context) -> Output:
    """Ingest raw client files into staging area."""
    files = list(Path("data/raw").glob("*"))
    context.add_output_metadata({"file_count": len(files)})
    return Output(value=[str(f) for f in files])

@asset(group_name="engagement", ins={"file_received": AssetIn()})
def profiled(context, file_received) -> Output:
    """Run schema profiler against received files."""
    results = []
    for f in file_received:
        result = profile_file(f)
        results.append(result)
    context.add_output_metadata({"issues_found": sum(len(r["issues"]) for r in results)})
    return Output(value=results)

@asset(group_name="engagement", ins={"profiled": AssetIn()})
def cleaned(context, profiled) -> Output:
    """Execute dbt cleaning models."""
    # Trigger dbt run via dagster-dbt
    dbt_result = run_dbt(["run", "--select", "staging"])
    context.add_output_metadata({"models_run": len(dbt_result)})
    return Output(value=dbt_result)

@asset(group_name="engagement", ins={"cleaned": AssetIn()})
def validated(context, cleaned) -> Output:
    """Run dbt tests and quality checks."""
    test_result = run_dbt(["test"])
    context.add_output_metadata({
        "tests_passed": test_result["passed"],
        "tests_failed": test_result["failed"],
    })
    return Output(value=test_result)

@asset(group_name="engagement", ins={"validated": AssetIn()})
def delivered(context, validated) -> Output:
    """Generate client deliverables."""
    generate_quality_report(validated)
    generate_mapping_doc()
    generate_transform_log()
    context.add_output_metadata({"deliverables": ["quality_report", "mapping_doc", "transform_log"]})
    return Output(value="delivered")
```

---

## Monitoring and SLA Tracking

### Per-Client Dagster UI Tags

Tag all assets and runs with `client_id` for filtering in the Dagster UI:

```python
@asset(tags={"client_id": "acme_corp", "engagement_type": "recurring"})
def acme_profiled(context): ...
```

Filter in Dagster UI: **Runs** > filter by tag `client_id=acme_corp`.

### Freshness Policies (SLA Tracking)

```python
from dagster import FreshnessPolicy

@asset(freshness_policy=FreshnessPolicy(maximum_lag_minutes=1440))  # 24 hours
def daily_client_data(context): ...

@asset(freshness_policy=FreshnessPolicy(maximum_lag_minutes=10080))  # 7 days
def weekly_client_data(context): ...
```

### Client-Specific Alerting

```python
from dagster_slack import SlackResource

@asset(required_resource_keys={"slack"})
def validated_with_alerts(context, cleaned):
    result = run_dbt(["test"])
    if result["failed"] > 0:
        client_channel = get_client_config(context)["alert_channel"]
        context.resources.slack.get_client().chat_postMessage(
            channel=client_channel,
            text=f"Data quality alert: {result['failed']} tests failed for {context.partition_key}",
        )
    return result
```
