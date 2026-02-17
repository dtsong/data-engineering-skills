## Contents

- [DuckDB Destination](#duckdb-destination)
- [Snowflake Destination](#snowflake-destination)
- [BigQuery Destination](#bigquery-destination)
- [Staging Configuration](#staging-configuration)
- [Destination Swapping](#destination-swapping)
- [Write Dispositions](#write-dispositions)
- [Loader File Format](#loader-file-format)

---

# DLT Destination Configuration

> **Part of:** [dlt-extract](../SKILL.md)

## DuckDB Destination

Zero-config local destination for development and testing:

```python
pipeline = dlt.pipeline(
    pipeline_name="dev_pipeline",
    destination="duckdb",
    dataset_name="raw",
)
```

**Configuration options:**

```toml
# .dlt/config.toml
[destination.duckdb]
credentials = "pipeline_data.duckdb"  # File path (default: <pipeline_name>.duckdb)
```

| Setting | Default | Notes |
|---------|---------|-------|
| File path | `<pipeline_name>.duckdb` | Relative to working directory |
| In-memory | `:memory:` | Lost on process exit, use for tests |
| Thread safety | Single writer | Use separate files for parallel pipelines |

**Query loaded data** directly:

```python
import duckdb
conn = duckdb.connect("pipeline_data.duckdb")
df = conn.execute("SELECT * FROM raw.my_table LIMIT 10").fetchdf()
```

## Snowflake Destination

Production warehouse destination with staging support:

```toml
# .dlt/secrets.toml
[destination.snowflake.credentials]
database = "ANALYTICS"
password = "your-password"
username = "LOADER_USER"
host = "account.snowflakecomputing.com"
warehouse = "LOADING_WH"
role = "LOADER_ROLE"
```

**Key-pair auth** (recommended for production):

```toml
[destination.snowflake.credentials]
database = "ANALYTICS"
username = "LOADER_USER"
host = "account.snowflakecomputing.com"
warehouse = "LOADING_WH"
role = "LOADER_ROLE"
private_key = "your-private-key-pem-content"
```

| Setting | Required | Notes |
|---------|----------|-------|
| `database` | Yes | Target database |
| `warehouse` | Yes | Compute warehouse for loading |
| `role` | Recommended | Scoped role for loader |
| `schema` | No | Overridden by `dataset_name` |

## BigQuery Destination

Google Cloud warehouse destination:

```toml
# .dlt/secrets.toml
[destination.bigquery]
location = "US"

[destination.bigquery.credentials]
project_id = "your-project-id"
client_email = "loader@your-project.iam.gserviceaccount.com"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
```

Alternatively, set `GOOGLE_APPLICATION_CREDENTIALS` environment variable pointing to a service account JSON key file.

| Setting | Required | Notes |
|---------|----------|-------|
| `project_id` | Yes | GCP project |
| `location` | Recommended | Dataset location (US, EU, etc.) |
| `credentials` | Yes | Service account key |

## Staging Configuration

Staging improves load performance by bulk-loading files from cloud storage rather than row-by-row inserts.

```python
pipeline = dlt.pipeline(
    pipeline_name="prod_pipeline",
    destination="snowflake",
    staging="filesystem",
    dataset_name="raw",
)
```

**S3 staging config:**

```toml
# .dlt/secrets.toml
[destination.filesystem]
bucket_url = "s3://my-staging-bucket/dlt-staging"

[destination.filesystem.credentials]
aws_access_key_id = "AKIA..."
aws_secret_access_key = "your-secret-key"
region_name = "us-east-1"
```

**GCS staging config:**

```toml
[destination.filesystem]
bucket_url = "gs://my-staging-bucket/dlt-staging"

[destination.filesystem.credentials]
project_id = "your-project-id"
client_email = "loader@your-project.iam.gserviceaccount.com"
private_key = "..."
```

| Destination | Recommended Staging | Performance Gain |
|-------------|-------------------|-----------------|
| Snowflake | S3 or GCS | 10-100x for large loads |
| BigQuery | GCS | 10-100x for large loads |
| DuckDB | None needed | Local I/O is fast enough |

## Destination Swapping

Drive destination selection from environment variables for dev/prod parity:

```python
import os

DESTINATION = os.getenv("DLT_DESTINATION", "duckdb")
STAGING = os.getenv("DLT_STAGING", None)

pipeline = dlt.pipeline(
    pipeline_name="client_extract",
    destination=DESTINATION,
    staging=STAGING,
    dataset_name=os.getenv("DLT_DATASET", "raw"),
)
```

**Environment configurations:**

| Environment | DLT_DESTINATION | DLT_STAGING | Secrets Source |
|-------------|----------------|-------------|----------------|
| Local dev | (unset → duckdb) | (unset) | `.dlt/secrets.toml` |
| CI/CD test | `duckdb` | (unset) | `.dlt/secrets.toml` |
| Staging | `snowflake` | `filesystem` | Environment variables |
| Production | `snowflake` | `filesystem` | Secrets manager |

**Config layering:** DLT resolves config in order: explicit params > env vars > `.dlt/secrets.toml` > `.dlt/config.toml`. Use this layering to keep pipeline code destination-agnostic.

## Write Dispositions

| Disposition | SQL Equivalent | Use Case | Idempotent |
|-------------|---------------|----------|------------|
| `append` | INSERT | Event logs, audit trails | No (duplicates on re-run) |
| `replace` | DROP + CREATE + INSERT | Reference tables, full refresh | Yes |
| `merge` | MERGE / UPSERT | Mutable entities, incremental | Yes (with primary_key) |

**Merge with primary key:**

```python
@dlt.resource(write_disposition="merge", primary_key="id")
def customers():
    yield from fetch_customers()
```

**Merge with compound key:**

```python
@dlt.resource(write_disposition="merge", primary_key=["customer_id", "order_id"])
def orders():
    yield from fetch_orders()
```

**SCD Type 2** for historical tracking:

```python
@dlt.resource(
    write_disposition={"disposition": "merge", "strategy": "scd2"},
    primary_key="id",
)
def customers_history():
    yield from fetch_customers()
# Generates _valid_from and _valid_to columns automatically
```

## Loader File Format

| Format | Size | Speed | Compatibility | Recommended For |
|--------|------|-------|---------------|----------------|
| `jsonl` | Larger | Slower | All destinations | Default, simple data |
| `parquet` | Smaller | Faster | Most destinations | Warehouse loads, large volumes |

Set loader file format:

```python
pipeline = dlt.pipeline(
    pipeline_name="prod_pipeline",
    destination="snowflake",
    staging="filesystem",
    dataset_name="raw",
)

# Use parquet for warehouse destinations
load_info = pipeline.run(source, loader_file_format="parquet")
```

**Rule of thumb:** Use `parquet` for warehouse destinations (Snowflake, BigQuery) when staging is enabled. Use `jsonl` for DuckDB or when data contains deeply nested structures that parquet struggles with.
