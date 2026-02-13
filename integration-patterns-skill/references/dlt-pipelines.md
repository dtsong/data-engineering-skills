# DLT (Data Load Tool) Pipeline Patterns

> Deep-dive reference for [dlt](https://dlthub.com/) — a Python-first library for declarative data ingestion. Part of the [Integration Patterns Skill](../SKILL.md).

---

## When to Use DLT

**Choose DLT when:**

- You want Python-native pipelines with minimal boilerplate
- You need auto-schema creation and evolution at the destination
- You want state management (incremental cursors, deduplication) built in
- You prefer code-over-config for pipeline definitions
- You need to load nested/semi-structured JSON into a normalized schema
- You want a single tool that handles extraction, normalization, and loading

**Choose Fivetran/Airbyte instead when:**

- You need 300+ pre-built connectors with zero-code setup
- Non-technical users manage ingestion
- SLA-backed uptime and monitoring are required out-of-the-box
- You prefer managed infrastructure over self-hosted

**Choose custom Python instead when:**

- Transformations are deeply coupled to extraction logic
- You need sub-second latency (DLT is batch/micro-batch)
- You already have mature in-house extraction frameworks

## DLT vs Fivetran vs Airbyte at a Glance

| Capability | DLT | Fivetran | Airbyte |
|-----------|-----|----------|---------|
| Deployment | Python package (`pip install dlt`) | Fully managed SaaS | Self-hosted or Cloud |
| Pipeline definition | Python code | UI/Terraform | UI/API/Octavia CLI |
| Connector count | 50+ verified sources + custom | 300+ managed | 350+ (community) |
| Schema management | Auto-evolve, contracts, Pydantic | Auto-evolve only | Auto-evolve, basic |
| Incremental loading | Built-in cursor tracking with state | Built-in | Built-in |
| Nested data handling | Auto-normalization with configurable depth | Flattened | Varies by connector |
| Orchestration | Any (Dagster, Airflow, cron) | Built-in scheduler | Built-in scheduler |
| Cost model | Free (Apache 2.0) + compute costs | Per-MAR (Monthly Active Row) | Free (OSS) or per-credit |
| dbt integration | Built-in dbt runner | dbt Cloud integration | Separate |
| State persistence | At destination (queryable) | Managed internally | Managed internally |

---

## Core Concepts

### Pipeline

A pipeline is the top-level object that connects a source to a destination. It manages state, schema, and loading.

```python
import dlt

# ── Credential boundary ──────────────────────────────────────────────
# Destination credentials come from environment variables or .dlt/secrets.toml.
# Configure: export DESTINATION__SNOWFLAKE__CREDENTIALS="snowflake://user:pass@account/db/schema?warehouse=WH&role=ROLE"
# Or use .dlt/secrets.toml for local development (never commit this file).
# See: shared-references/data-engineering/security-compliance-patterns.md
# ─────────────────────────────────────────────────────────────────────

pipeline = dlt.pipeline(
    pipeline_name="github_to_snowflake",
    destination="snowflake",
    dataset_name="github_raw",
)
```

**Key parameters:**

| Parameter | Description |
|-----------|-------------|
| `pipeline_name` | Unique identifier; used for state persistence |
| `destination` | Target: `snowflake`, `bigquery`, `databricks`, `duckdb`, `postgres`, `filesystem`, etc. |
| `dataset_name` | Schema/dataset name at the destination |
| `staging` | Optional staging destination for file-based loading (e.g., `filesystem` with S3) |
| `dev_mode` | If `True`, uses `<dataset_name>_<pipeline_name>` and resets state on each run |

### Source

A source is a collection of related resources. Use the `@dlt.source` decorator to group resources together.

```python
@dlt.source
def github_source(
    owner: str,
    repo: str,
    access_token: str = dlt.secrets.value,  # Resolved from secrets
):
    """GitHub data source with multiple resources."""
    yield issues_resource(owner, repo, access_token)
    yield pull_requests_resource(owner, repo, access_token)
    yield stargazers_resource(owner, repo, access_token)
```

**Secrets resolution order:**

1. Environment variables: `SOURCES__GITHUB_SOURCE__ACCESS_TOKEN`
2. `.dlt/secrets.toml`: `[sources.github_source] access_token = "..."`
3. Explicit parameter at call time

### Resource

A resource is a single data stream — typically one table. Use `@dlt.resource` to define how data is fetched.

```python
@dlt.resource(
    name="issues",
    write_disposition="merge",
    primary_key="id",
    columns={"created_at": {"data_type": "timestamp"}},
)
def issues_resource(
    owner: str,
    repo: str,
    access_token: str,
    updated_at: dlt.sources.incremental[str] = dlt.sources.incremental(
        cursor_path="updated_at",
        initial_value="2024-01-01T00:00:00Z",
    ),
):
    """Fetch GitHub issues with incremental loading."""
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "state": "all",
        "sort": "updated",
        "direction": "asc",
        "since": updated_at.last_value,
        "per_page": 100,
    }

    while url:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        yield response.json()

        # Follow GitHub pagination via Link header
        url = response.links.get("next", {}).get("url")
        params = {}  # Params are in the next URL
```

### Destination

DLT supports all major warehouses. Credentials are configured via environment variables or `.dlt/secrets.toml`.

```toml
# .dlt/secrets.toml — LOCAL DEVELOPMENT ONLY, never commit
# Production: use environment variables exclusively

[destination.snowflake.credentials]
database = "RAW_DB"
password = "local-dev-only"
username = "dlt_loader"
host = "account.snowflakecomputing.com"
warehouse = "LOADING_WH"
role = "LOADER_ROLE"

[destination.bigquery]
location = "US"

[destination.bigquery.credentials]
project_id = "my-project"
private_key = "..."
client_email = "dlt-sa@my-project.iam.gserviceaccount.com"
```

**Per-warehouse destination strings (production — use environment variables):**

```bash
# Snowflake
export DESTINATION__SNOWFLAKE__CREDENTIALS="snowflake://user:pass@account/db/schema?warehouse=WH&role=ROLE"

# BigQuery (uses Application Default Credentials or service account JSON)
export DESTINATION__BIGQUERY__CREDENTIALS__PROJECT_ID="my-project"
export DESTINATION__BIGQUERY__CREDENTIALS__CLIENT_EMAIL="sa@project.iam.gserviceaccount.com"
export DESTINATION__BIGQUERY__CREDENTIALS__PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n..."

# Databricks
export DESTINATION__DATABRICKS__CREDENTIALS__SERVER_HOSTNAME="adb-xxx.azuredatabricks.net"
export DESTINATION__DATABRICKS__CREDENTIALS__HTTP_PATH="/sql/1.0/warehouses/xxx"
export DESTINATION__DATABRICKS__CREDENTIALS__ACCESS_TOKEN="dapi..."
export DESTINATION__DATABRICKS__CREDENTIALS__CATALOG="unity_catalog"

# DuckDB (local development — no credentials needed)
# Uses local file by default: <pipeline_name>.duckdb

# PostgreSQL
export DESTINATION__POSTGRES__CREDENTIALS="postgresql://user:pass@host:5432/dbname"

# Filesystem (S3, GCS, Azure Blob)
export DESTINATION__FILESYSTEM__BUCKET_URL="s3://my-bucket/dlt-data"
export DESTINATION__FILESYSTEM__CREDENTIALS__AWS_ACCESS_KEY_ID="..."
export DESTINATION__FILESYSTEM__CREDENTIALS__AWS_SECRET_ACCESS_KEY="..."
```

---

## Write Dispositions

Write dispositions control how data is loaded at the destination.

| Disposition | Behavior | Use Case |
|-------------|----------|----------|
| `append` | Insert new rows, never modify existing | Event logs, immutable data, audit trails |
| `replace` | Drop and recreate table on each load | Small reference tables, full refreshes |
| `merge` | Upsert based on primary/merge keys | Mutable entities (customers, orders) |

### Merge Sub-Strategies

```python
# Delete-insert (default for merge): Delete matching rows, insert new
@dlt.resource(write_disposition="merge", primary_key="id")
def customers():
    yield fetch_customers()

# Upsert with merge key different from primary key
@dlt.resource(
    write_disposition="merge",
    primary_key="id",
    merge_key="external_id",  # Match on external_id, deduplicate by id
)
def synced_contacts():
    yield fetch_contacts()

# SCD Type 2: Track history with validity ranges
@dlt.resource(
    write_disposition={
        "disposition": "merge",
        "strategy": "scd2",
        "validity_column_names": ["_valid_from", "_valid_to"],
        "active_record_timestamp": "9999-12-31T00:00:00Z",
    },
    primary_key="id",
)
def customers_scd2():
    yield fetch_customers()
```

**SCD2 produces:**

| id | name | _valid_from | _valid_to | _is_active |
|----|------|------------|-----------|-----------|
| 1 | Alice | 2024-01-01 | 2024-06-15 | false |
| 1 | Alice B. | 2024-06-15 | 9999-12-31 | true |

---

## Incremental Loading

DLT tracks cursor state automatically so subsequent runs only fetch new/updated data.

### Cursor-Based Incremental

```python
@dlt.resource(write_disposition="merge", primary_key="id")
def orders(
    updated_at: dlt.sources.incremental[str] = dlt.sources.incremental(
        cursor_path="updated_at",
        initial_value="2024-01-01T00:00:00Z",
    ),
):
    """Load orders incrementally by updated_at cursor."""
    params = {"updated_since": updated_at.last_value}
    while True:
        page = fetch_orders_page(params)
        if not page:
            break
        yield page
        params["cursor"] = page[-1]["cursor"]
```

**How it works:**

1. First run: `updated_at.last_value` = `"2024-01-01T00:00:00Z"` (initial value)
2. DLT processes rows and tracks the max `updated_at` seen
3. State is persisted at the destination in `_dlt_pipeline_state` table
4. Second run: `updated_at.last_value` = max value from previous run
5. Only new/updated rows are fetched and loaded

### Incremental with `last_value_func`

```python
@dlt.resource(write_disposition="append", primary_key="event_id")
def events(
    created_at: dlt.sources.incremental[int] = dlt.sources.incremental(
        cursor_path="created_at_epoch",
        initial_value=0,
        last_value_func=max,  # Track the maximum epoch timestamp
    ),
):
    """Append-only events with epoch cursor."""
    for event in fetch_events(since=created_at.last_value):
        yield event
```

### Incremental with Deduplication

```python
@dlt.resource(write_disposition="merge", primary_key="id")
def deduplicated_records(
    updated_at: dlt.sources.incremental[str] = dlt.sources.incremental(
        cursor_path="updated_at",
        initial_value="2024-01-01T00:00:00Z",
        primary_key="id",  # Deduplicate within batch by id
    ),
):
    yield fetch_records()
```

### State Inspection and Reset

```python
# Inspect pipeline state
pipeline = dlt.pipeline(pipeline_name="my_pipeline", destination="snowflake")
state = pipeline.state  # Full state dict

# Check incremental cursor values
sources_state = state.get("sources", {})
for source_name, source_state in sources_state.items():
    for resource_name, resource_state in source_state.get("resources", {}).items():
        incremental = resource_state.get("incremental", {})
        for cursor_name, cursor_state in incremental.items():
            print(f"{source_name}.{resource_name}.{cursor_name}: {cursor_state['last_value']}")

# Reset state for a fresh full load
pipeline.drop()  # Drops all state and destination tables
```

---

## Schema Management

### Auto-Schema Evolution

DLT automatically creates and evolves schemas at the destination. New columns are added automatically when source data changes.

```python
pipeline = dlt.pipeline(
    pipeline_name="evolving_api",
    destination="snowflake",
    dataset_name="raw_data",
)

# First run: creates table with columns {id, name, email}
pipeline.run(fetch_users())

# API adds a new field "phone" — DLT auto-adds the column
pipeline.run(fetch_users())  # Table now has {id, name, email, phone}
```

### Schema Contracts

Control how DLT handles schema changes. Use contracts to prevent unexpected schema drift in production.

```python
@dlt.resource(
    columns={"id": {"data_type": "bigint"}, "email": {"data_type": "text"}},
    schema_contract={
        "tables": "evolve",       # Allow new tables
        "columns": "freeze",      # Reject new columns (strict)
        "data_type": "freeze",    # Reject data type changes
    },
)
def strict_users():
    yield fetch_users()
```

| Contract Mode | Behavior |
|---------------|----------|
| `evolve` | Allow changes automatically (default) |
| `freeze` | Raise exception on any change |
| `discard_rows` | Drop rows that violate the contract |
| `discard_columns` | Load row but drop unknown columns |

### Pydantic Schema Validation

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class User(BaseModel):
    id: int
    email: str
    name: str
    created_at: datetime
    phone: Optional[str] = None

@dlt.resource(columns=User, write_disposition="merge", primary_key="id")
def validated_users():
    """DLT validates each row against the Pydantic model."""
    for user_data in fetch_users():
        yield user_data  # Invalid rows raise ValidationError
```

---

## REST API Source (Declarative)

DLT's `rest_api` verified source replaces hundreds of lines of custom extraction code with declarative configuration.

```python
from dlt.sources.rest_api import rest_api_source

# ── Credential boundary ──────────────────────────────────────────────
# Configure: export SOURCES__REST_API__GITHUB__ACCESS_TOKEN="ghp_xxx"
# ─────────────────────────────────────────────────────────────────────

source = rest_api_source(
    {
        "client": {
            "base_url": "https://api.github.com",
            "auth": {
                "type": "bearer",
                "token": dlt.secrets["sources.rest_api.github.access_token"],
            },
            "paginator": {
                "type": "header_link",  # GitHub uses Link header pagination
            },
        },
        "resources": [
            {
                "name": "repos",
                "endpoint": {
                    "path": "orgs/{org}/repos",
                    "params": {"org": "myorg", "per_page": 100},
                },
            },
            {
                "name": "issues",
                "endpoint": {
                    "path": "repos/{org}/{repo}/issues",
                    "params": {
                        "org": "myorg",
                        "repo": {"type": "resolve", "resource": "repos", "field": "name"},
                        "state": "all",
                        "sort": "updated",
                        "since": {
                            "type": "incremental",
                            "cursor_path": "updated_at",
                            "initial_value": "2024-01-01T00:00:00Z",
                        },
                    },
                },
            },
            {
                "name": "pull_requests",
                "endpoint": {
                    "path": "repos/{org}/{repo}/pulls",
                    "params": {
                        "org": "myorg",
                        "repo": {"type": "resolve", "resource": "repos", "field": "name"},
                        "state": "all",
                    },
                },
            },
        ],
    }
)

pipeline = dlt.pipeline(
    pipeline_name="github_rest",
    destination="snowflake",
    dataset_name="github_raw",
)

load_info = pipeline.run(source)
print(load_info)
```

**Supported paginators:**

| Paginator | Use When |
|-----------|----------|
| `header_link` | API uses `Link` header (GitHub, many REST APIs) |
| `json_link` | Next page URL in response body |
| `offset` | Offset/limit pagination |
| `cursor` | Cursor-based pagination |
| `page_number` | Page number pagination |
| `single_page` | No pagination needed |

---

## SQL Database Source

Load data from any SQL database using DLT's `sql_database` verified source.

```python
from dlt.sources.sql_database import sql_database

# ── Credential boundary ──────────────────────────────────────────────
# Configure: export SOURCES__SQL_DATABASE__CREDENTIALS="postgresql://user:pass@host:5432/db"
# ─────────────────────────────────────────────────────────────────────

source = sql_database(
    credentials=dlt.secrets["sources.sql_database.credentials"],
    schema="public",
    table_names=["customers", "orders", "products"],
    incremental=dlt.sources.incremental("updated_at"),
    chunk_size=50000,
)

pipeline = dlt.pipeline(
    pipeline_name="postgres_to_snowflake",
    destination="snowflake",
    dataset_name="postgres_raw",
)

load_info = pipeline.run(source)
```

**Options:**

| Parameter | Description |
|-----------|-------------|
| `table_names` | Explicit list of tables to load (recommended over loading all) |
| `schema` | Source schema name |
| `incremental` | Global incremental column for all tables |
| `chunk_size` | Rows per batch for memory-efficient loading |
| `reflection_level` | `full` (default) or `minimal` for schema introspection |
| `defer_table_reflect` | Lazy reflection — only inspect tables as they're read |
| `backend` | `sqlalchemy` (default), `pyarrow`, `pandas`, or `connectorx` |

---

## Nested Data Handling

DLT automatically normalizes nested JSON into relational tables.

### Input

```json
{
  "id": 1,
  "name": "Acme Corp",
  "contacts": [
    {"email": "alice@acme.com", "role": "admin"},
    {"email": "bob@acme.com", "role": "user"}
  ],
  "address": {
    "street": "123 Main St",
    "city": "Springfield"
  }
}
```

### Output Tables

**`companies`:**
| _dlt_id | id | name | address__street | address__city |
|---------|----|------|-----------------|---------------|
| abc123 | 1 | Acme Corp | 123 Main St | Springfield |

**`companies__contacts`:**
| _dlt_parent_id | _dlt_list_idx | email | role |
|----------------|---------------|-------|------|
| abc123 | 0 | alice@acme.com | admin |
| abc123 | 1 | bob@acme.com | user |

### Controlling Nesting Depth

```python
# Flatten everything (no child tables)
pipeline = dlt.pipeline(
    pipeline_name="flat",
    destination="snowflake",
    dataset_name="flat_data",
)

# Set max nesting level: 0 = store nested as JSON, 1 = one level of child tables
pipeline.run(source, max_table_nesting=1)
```

| Level | Behavior |
|-------|----------|
| `0` | Store all nested data as JSON columns (no child tables) |
| `1` | Create child tables for top-level arrays, nest deeper as JSON |
| `2` (default) | Two levels of child tables |
| `1000` | Fully normalize all nesting |

---

## Performance Optimization

### File-Based Staging

Use object storage as an intermediate staging area for faster bulk loading.

```python
pipeline = dlt.pipeline(
    pipeline_name="staged_load",
    destination="snowflake",
    staging="filesystem",  # Stage through S3/GCS before loading
    dataset_name="raw_data",
)

# DLT writes parquet files to staging bucket, then issues COPY INTO
load_info = pipeline.run(source)
```

**Configure staging bucket:**

```bash
# S3 staging
export DESTINATION__FILESYSTEM__BUCKET_URL="s3://my-staging-bucket/dlt/"
export DESTINATION__FILESYSTEM__CREDENTIALS__AWS_ACCESS_KEY_ID="..."
export DESTINATION__FILESYSTEM__CREDENTIALS__AWS_SECRET_ACCESS_KEY="..."

# GCS staging
export DESTINATION__FILESYSTEM__BUCKET_URL="gs://my-staging-bucket/dlt/"
# Uses Application Default Credentials
```

### Parallelism

```python
# DLT auto-parallelizes resource extraction
@dlt.source
def parallel_source():
    # These resources are extracted in parallel (default: 20 workers)
    yield resource_a()
    yield resource_b()
    yield resource_c()

# Control parallelism
import dlt

pipeline = dlt.pipeline(...)
pipeline.run(
    parallel_source(),
    loader_file_format="parquet",  # Parquet is faster than jsonl for staging
    workers=5,  # Number of parallel load workers
)
```

### Performance Tuning Checklist

| Setting | Default | Recommended For Large Loads |
|---------|---------|---------------------------|
| `loader_file_format` | `jsonl` | `parquet` (faster COPY INTO, smaller files) |
| `workers` | `20` (extract), `1` (load) | Increase load workers for many small tables |
| `staging` | None | `filesystem` (S3/GCS) for 100K+ rows |
| `chunk_size` | `10000` | Increase for simple schemas, decrease for complex nested data |
| `max_table_nesting` | `2` | `0` or `1` to reduce table count and JOIN complexity |

---

## Testing DLT Pipelines

### Unit Testing with DuckDB

```python
import dlt
import pytest

def test_github_pipeline():
    """Test pipeline locally with DuckDB."""
    pipeline = dlt.pipeline(
        pipeline_name="test_github",
        destination="duckdb",
        dataset_name="test_data",
        dev_mode=True,  # Isolated state, fresh each run
    )

    # Run with sample data
    source = github_source(owner="dlt-hub", repo="dlt")
    load_info = pipeline.run(source)

    # Assert load succeeded
    assert load_info.has_failed_jobs is False

    # Query loaded data
    with pipeline.sql_client() as client:
        result = client.execute_sql("SELECT count(*) FROM issues")
        assert result[0][0] > 0

    # Check schema
    schema = pipeline.default_schema
    assert "issues" in schema.tables
    assert "id" in [col for col in schema.tables["issues"]["columns"]]
```

### Schema Contract Testing

```python
def test_schema_contract_rejects_new_columns():
    """Verify strict schema contracts reject unexpected columns."""
    pipeline = dlt.pipeline(
        pipeline_name="test_contracts",
        destination="duckdb",
        dev_mode=True,
    )

    @dlt.resource(
        columns={"id": {"data_type": "bigint"}, "name": {"data_type": "text"}},
        schema_contract={"columns": "freeze"},
    )
    def strict_resource():
        yield [{"id": 1, "name": "Alice", "unexpected_col": "oops"}]

    with pytest.raises(Exception, match="column.*not found"):
        pipeline.run(strict_resource)
```

### Data Contract Testing

```python
def test_data_quality():
    """Verify data quality after loading."""
    pipeline = dlt.pipeline(
        pipeline_name="test_quality",
        destination="duckdb",
        dev_mode=True,
    )

    pipeline.run(my_source())

    with pipeline.sql_client() as client:
        # No nulls in required fields
        nulls = client.execute_sql(
            "SELECT count(*) FROM customers WHERE id IS NULL OR email IS NULL"
        )
        assert nulls[0][0] == 0, "Found null values in required fields"

        # No duplicate primary keys
        dupes = client.execute_sql("""
            SELECT id, count(*) as cnt
            FROM customers
            GROUP BY id HAVING count(*) > 1
        """)
        assert len(dupes) == 0, f"Found duplicate IDs: {dupes}"
```

---

## Orchestration Integration

### Dagster (`dagster-dlt`)

```python
from dagster import Definitions, AssetExecutionContext
from dagster_dlt import DagsterDltResource, dlt_assets, DagsterDltTranslator
import dlt

# ── Credential boundary ──────────────────────────────────────────────
# Dagster resolves DLT credentials from environment variables.
# Configure on the Dagster deployment (not in code).
# ─────────────────────────────────────────────────────────────────────

@dlt.source
def github_source():
    yield issues_resource()
    yield pull_requests_resource()

@dlt_assets(
    dlt_source=github_source(),
    dlt_pipeline=dlt.pipeline(
        pipeline_name="github_dagster",
        destination="snowflake",
        dataset_name="github_raw",
    ),
    name="github",
    group_name="ingestion",
)
def github_assets(context: AssetExecutionContext, dlt: DagsterDltResource):
    yield from dlt.run(context=context)

defs = Definitions(
    assets=[github_assets],
    resources={"dlt": DagsterDltResource()},
)
```

See [Dagster Integrations Reference](../../data-orchestration-skill/references/dagster-integrations.md) for full `dagster-dlt` patterns.

### Airflow

```python
# DAG: dlt_github_pipeline.py
from airflow.decorators import dag, task
from datetime import datetime

@dag(
    schedule="@hourly",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["dlt", "ingestion"],
)
def dlt_github_pipeline():

    @task()
    def run_dlt_pipeline():
        """Run DLT pipeline within Airflow task."""
        import dlt

        pipeline = dlt.pipeline(
            pipeline_name="github_airflow",
            destination="snowflake",
            dataset_name="github_raw",
        )

        source = github_source(
            owner="myorg",
            repo="myrepo",
        )

        load_info = pipeline.run(source)

        if load_info.has_failed_jobs:
            raise Exception(f"DLT pipeline failed: {load_info}")

        return str(load_info)

    run_dlt_pipeline()

dlt_github_pipeline()
```

### Serverless (AWS Lambda / Cloud Functions)

```python
# handler.py — Deploy as AWS Lambda or GCP Cloud Function
import dlt

def handler(event, context):
    """Serverless DLT pipeline handler."""
    pipeline = dlt.pipeline(
        pipeline_name="serverless_ingest",
        destination="bigquery",
        dataset_name="raw_events",
    )

    # Source from event payload or scheduled trigger
    source = my_source(
        since=event.get("since", "2024-01-01T00:00:00Z"),
    )

    load_info = pipeline.run(source)

    return {
        "statusCode": 200,
        "body": str(load_info),
    }
```

---

## Project Structure

```
my_dlt_project/
├── .dlt/
│   ├── config.toml          # Non-secret configuration
│   └── secrets.toml          # Local secrets (NEVER commit — add to .gitignore)
├── pipelines/
│   ├── github_pipeline.py    # Pipeline definitions
│   └── salesforce_pipeline.py
├── sources/
│   ├── github.py             # Custom source definitions
│   └── salesforce.py
├── tests/
│   ├── test_github.py        # Pipeline tests
│   └── test_salesforce.py
├── .gitignore                # Must include: .dlt/secrets.toml, *.duckdb
├── requirements.txt          # dlt[snowflake], dlt[bigquery], etc.
└── README.md
```

**`.dlt/config.toml`** — Non-secret configuration:

```toml
[runtime]
log_level = "WARNING"

[extract]
max_table_nesting = 2
workers = 20

[normalize]
loader_file_format = "parquet"

[load]
workers = 5
```

**`.gitignore` additions:**

```
.dlt/secrets.toml
*.duckdb
*.duckdb.wal
```

---

## Verified Sources Catalog

DLT provides 50+ verified (maintained and tested) sources. Install via `pip install dlt[source_name]`.

| Category | Sources | Notes |
|----------|---------|-------|
| **SaaS / APIs** | GitHub, Slack, HubSpot, Shopify, Stripe, Zendesk, Jira, Notion, Asana, Google Sheets, Google Analytics | Most use REST API source under the hood |
| **Databases** | PostgreSQL, MySQL, SQL Server, Oracle, MongoDB | Via `sql_database` source or dedicated connectors |
| **Cloud Storage** | S3, GCS, Azure Blob (CSV, JSON, Parquet) | Via `filesystem` source |
| **Generic** | `rest_api` (declarative), `sql_database`, `filesystem` | Build any API or database connector |

**Installing verified sources:**

```bash
# Install DLT with destination extras
pip install "dlt[snowflake]"
pip install "dlt[bigquery]"
pip install "dlt[databricks]"

# Initialize a verified source
dlt init github snowflake     # Creates github pipeline scaffold for Snowflake
dlt init rest_api bigquery    # Creates REST API pipeline scaffold for BigQuery
dlt init sql_database duckdb  # Creates SQL database pipeline scaffold for DuckDB
```

---

## DLT + dbt Integration

DLT includes a built-in dbt runner that shares credentials with the DLT pipeline.

```python
import dlt

pipeline = dlt.pipeline(
    pipeline_name="github_with_dbt",
    destination="snowflake",
    dataset_name="github_raw",
)

# Step 1: Load raw data
load_info = pipeline.run(github_source())

# Step 2: Run dbt transformations using the same credentials
venv = dlt.dbt.get_venv(pipeline)
dbt_runner = venv.dbt  # or: dbt = dlt.dbt.package(pipeline, "path/to/dbt/project")

# Run dbt models
models = dbt_runner.run_all()

for model in models:
    print(f"Model {model.model_name}: {model.status} ({model.execution_time}s)")
    if model.status == "error":
        print(f"  Error: {model.message}")
```

**Key benefit:** DLT passes its destination credentials to dbt automatically — no separate `profiles.yml` configuration needed.

---

## Common Patterns

### Full Refresh with Replace

```python
@dlt.resource(write_disposition="replace")
def reference_data():
    """Small lookup table — full refresh is fine."""
    yield fetch_all_countries()
    yield fetch_all_currencies()

pipeline.run(reference_data())
```

### Parent-Child Loading

```python
@dlt.source
def ecommerce():
    """Load orders with nested line items."""

    @dlt.resource(write_disposition="merge", primary_key="order_id")
    def orders():
        for order in fetch_orders():
            # Nested line_items will become orders__line_items table
            yield order

    return orders

# Creates: orders, orders__line_items (auto-linked by _dlt_parent_id)
```

### Multi-Source Pipeline

```python
pipeline = dlt.pipeline(
    pipeline_name="multi_source",
    destination="snowflake",
    dataset_name="raw_data",
)

# Load multiple sources into the same dataset
pipeline.run(github_source(), table_name="github_events")
pipeline.run(stripe_source(), table_name="stripe_events")
pipeline.run(salesforce_source(), table_name="sf_accounts")
```

### Transformer (Post-Processing)

```python
@dlt.resource(write_disposition="append")
def raw_events():
    yield fetch_events()

@dlt.transformer(data_from=raw_events, write_disposition="append")
def enriched_events(event):
    """Transform/enrich events before loading."""
    event["event_date"] = event["timestamp"][:10]
    event["is_premium"] = event.get("plan") in ("pro", "enterprise")
    yield event

# Pipeline loads enriched_events (not raw_events)
pipeline.run(enriched_events)
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| `PipelineStepFailed` on first run | Missing destination credentials | Check env vars or `.dlt/secrets.toml` |
| Schema mismatch after source change | Column type changed | Use `schema_contract` or `pipeline.drop()` for dev |
| Incremental not filtering | Cursor column not in yielded data | Verify `cursor_path` matches actual field name |
| Child tables not created | `max_table_nesting=0` | Increase nesting level or remove the setting |
| Slow loading | Loading row-by-row without staging | Add `staging="filesystem"` and use `parquet` format |
| `_dlt_load_id` duplicates | Pipeline re-run without state | Check `_dlt_pipeline_state` table exists at destination |
| Memory issues with large datasets | Loading all data into memory | Use generators (yield), reduce `chunk_size` |

### Debugging Commands

```bash
# Show pipeline state
dlt pipeline <pipeline_name> info

# Show loaded schemas
dlt pipeline <pipeline_name> schema

# Show last load info
dlt pipeline <pipeline_name> trace

# Drop pipeline state (for fresh start in dev)
dlt pipeline <pipeline_name> drop

# List all pipelines
dlt pipeline --list
```

---

## Security Considerations

Follow the [Security & Compliance Patterns](../../shared-references/data-engineering/security-compliance-patterns.md) framework.

**By security tier:**

| Capability | Tier 1 (Cloud-Native) | Tier 2 (Regulated) | Tier 3 (Air-Gapped) |
|------------|----------------------|--------------------|--------------------|
| Run DLT pipelines | Against dev/staging destinations | Generate pipeline code for review | Generate code only |
| Access source APIs | With scoped dev tokens | With read-only tokens, human approval | No API access |
| View loaded data | Query dev/staging datasets | Metadata and row counts only | No data access |
| Manage state | Inspect and reset dev state | View state metadata only | No state access |

**Credential management rules:**

1. **Never** commit `.dlt/secrets.toml` — add to `.gitignore`
2. **Always** use environment variables in production
3. **Use** `dlt.secrets.value` parameter default for automatic resolution
4. **Prefer** IAM roles / service accounts over static credentials when the destination supports it
5. **Scope** API tokens to minimum required permissions (read-only where possible)
6. **Rotate** credentials on a schedule; DLT state survives credential rotation

---

## Quick Reference Card

```python
import dlt

# 1. Define source
@dlt.source
def my_source(api_key: str = dlt.secrets.value):
    yield my_resource(api_key)

# 2. Define resource with incremental
@dlt.resource(write_disposition="merge", primary_key="id")
def my_resource(api_key, updated_at=dlt.sources.incremental("updated_at")):
    yield fetch_data(api_key, since=updated_at.last_value)

# 3. Create pipeline
pipeline = dlt.pipeline(
    pipeline_name="my_pipeline",
    destination="snowflake",       # or: bigquery, databricks, duckdb, postgres
    staging="filesystem",          # Optional: stage through S3/GCS
    dataset_name="raw_data",
)

# 4. Run
load_info = pipeline.run(my_source())
print(load_info)
assert not load_info.has_failed_jobs
```
