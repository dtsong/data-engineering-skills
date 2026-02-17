## Contents

- [When to Use](#when-to-use)
- [Core Concepts](#core-concepts)
- [Write Dispositions](#write-dispositions)
- [Incremental Loading](#incremental-loading)
- [Schema Management](#schema-management)
- [REST API Source (Declarative)](#rest-api-source-declarative)
- [SQL Database Source](#sql-database-source)
- [Nested Data Handling](#nested-data-handling)
- [Performance](#performance)
- [Testing](#testing)
- [Orchestration](#orchestration)
- [Security](#security)
- [Troubleshooting](#troubleshooting)

---

# DLT (Data Load Tool) Pipeline Patterns

Python-first library for declarative data ingestion. Auto-schema, incremental state, nested JSON normalization.

## When to Use

**DLT:** Python-native pipelines, auto-schema evolution, built-in incremental cursors, nested JSON normalization, code-over-config.
**Fivetran/Airbyte:** 300+ managed connectors, zero-code, SLA-backed uptime.
**Custom Python:** Transforms deeply coupled to extraction, sub-second latency, mature in-house frameworks.

## Core Concepts

```python
import dlt

# Pipeline: connects source to destination, manages state/schema
pipeline = dlt.pipeline(
    pipeline_name="github_to_snowflake",
    destination="snowflake",  # bigquery, databricks, duckdb, postgres, filesystem
    staging="filesystem",     # Optional: S3/GCS for faster bulk loading
    dataset_name="github_raw",
)

# Source: collection of resources (use @dlt.source decorator)
# Resource: single data stream / table (use @dlt.resource decorator)
# Secrets resolved from: env vars > .dlt/secrets.toml > explicit params
```

## Write Dispositions

| Disposition | Behavior | Use Case |
|-------------|----------|----------|
| `append` | Insert new rows only | Event logs, audit trails |
| `replace` | Drop and recreate | Small reference tables |
| `merge` | Upsert on primary/merge key | Mutable entities |

**SCD2 merge:** `write_disposition={"disposition": "merge", "strategy": "scd2", "validity_column_names": ["_valid_from", "_valid_to"]}`. Tracks full history with validity ranges.

## Incremental Loading

```python
@dlt.resource(write_disposition="merge", primary_key="id")
def orders(
    updated_at: dlt.sources.incremental[str] = dlt.sources.incremental(
        cursor_path="updated_at",
        initial_value="2024-01-01T00:00:00Z",
    ),
):
    params = {"updated_since": updated_at.last_value}
    while True:
        page = fetch_orders_page(params)
        if not page: break
        yield page
        params["cursor"] = page[-1]["cursor"]
```

State persisted in `_dlt_pipeline_state` table at destination. Reset with `pipeline.drop()`.

## Schema Management

**Auto-evolution:** New source fields automatically added as columns. **Schema contracts** control strictness:

| Contract Mode | Behavior |
|---------------|----------|
| `evolve` | Allow changes (default) |
| `freeze` | Raise exception on change |
| `discard_rows` | Drop violating rows |
| `discard_columns` | Load row, drop unknown columns |

Use Pydantic models as `columns` parameter for type-safe validation.

## REST API Source (Declarative)

```python
from dlt.sources.rest_api import rest_api_source

source = rest_api_source({
    "client": {
        "base_url": "https://api.github.com",
        "auth": {"type": "bearer", "token": dlt.secrets["sources.rest_api.github.access_token"]},
        "paginator": {"type": "header_link"},
    },
    "resources": [
        {"name": "repos", "endpoint": {"path": "orgs/{org}/repos", "params": {"org": "myorg"}}},
        {"name": "issues", "endpoint": {
            "path": "repos/{org}/{repo}/issues",
            "params": {"since": {"type": "incremental", "cursor_path": "updated_at", "initial_value": "2024-01-01T00:00:00Z"}},
        }},
    ],
})
```

**Paginators:** `header_link` (GitHub), `json_link`, `offset`, `cursor`, `page_number`, `single_page`.

## SQL Database Source

```python
from dlt.sources.sql_database import sql_database

source = sql_database(
    credentials=dlt.secrets["sources.sql_database.credentials"],
    schema="public",
    table_names=["customers", "orders"],
    incremental=dlt.sources.incremental("updated_at"),
    chunk_size=50000,
)
```

Backends: `sqlalchemy` (default), `pyarrow`, `pandas`, `connectorx`.

## Nested Data Handling

Input `{"id": 1, "contacts": [{"email": "a@b.com"}]}` produces parent table + `__contacts` child table linked by `_dlt_parent_id`.

| Nesting Level | Behavior |
|---------------|----------|
| `0` | All nested as JSON columns |
| `1` | Top-level arrays as child tables |
| `2` (default) | Two levels of child tables |

## Performance

Use `staging="filesystem"` with `loader_file_format="parquet"` for 100K+ rows. DLT auto-parallelizes resource extraction (default 20 workers). Increase load workers for many small tables.

## Testing

```python
def test_pipeline():
    pipeline = dlt.pipeline(pipeline_name="test", destination="duckdb", dev_mode=True)
    load_info = pipeline.run(my_source())
    assert not load_info.has_failed_jobs
    with pipeline.sql_client() as client:
        result = client.execute_sql("SELECT count(*) FROM my_table")
        assert result[0][0] > 0
```

Test schema contracts, data quality (nulls, duplicates), and incremental behavior.

## Orchestration

**Dagster:** Use `@dlt_assets` decorator with `dagster-dlt` package. **Airflow:** Run `pipeline.run()` inside `@task`. **Serverless:** Deploy handler calling `pipeline.run()` as Lambda/Cloud Function.

## Security

Never commit `.dlt/secrets.toml`. Use env vars in production. Use `dlt.secrets.value` for auto-resolution. Prefer IAM/service accounts over static credentials. Scope tokens to minimum permissions.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Missing credentials | Check env vars or `.dlt/secrets.toml` |
| Schema mismatch | Use `schema_contract` or `pipeline.drop()` |
| Incremental not filtering | Verify `cursor_path` matches field name |
| Slow loading | Add `staging="filesystem"`, use parquet |
| Memory issues | Use generators (yield), reduce `chunk_size` |

CLI: `dlt pipeline <name> info`, `schema`, `trace`, `drop`, `--list`.
