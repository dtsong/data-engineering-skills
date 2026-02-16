---
name: dlt-extraction-skill
description: "Use this skill when building DLT pipelines for file-based or consulting data extraction. Covers Excel/CSV/SharePoint ingestion via DLT, destination swapping (DuckDB dev to warehouse prod), schema contracts for cleaning, and portable pipeline patterns. Common phrases: \"dlt pipeline for files\", \"extract Excel with dlt\", \"portable data pipeline\", \"dlt filesystem source\". Do NOT use for core DLT concepts like REST API or SQL database sources (use integration-patterns-skill) or pipeline scheduling (use data-orchestration-skill)."
model_tier: analytical
version: 1.0.0
---

# DLT Extraction Skill for Claude

Expert guidance for building portable DLT pipelines focused on file-based sources and consulting data extraction.

## When to Use This Skill

Activate when:
- Building DLT pipelines for file sources (CSV, Excel, Parquet, JSON)
- Configuring filesystem or SharePoint sources
- Swapping destinations (DuckDB dev to warehouse prod)
- Defining schema contracts for data cleaning
- Building portable pipelines for client handoff
- Processing files from SFTP, local directories, or cloud storage buckets

Do NOT use for:
- Core DLT REST API or SQL database sources (use integration-patterns-skill)
- Pipeline scheduling and orchestration (use data-orchestration-skill)
- Standalone DuckDB queries without DLT (use duckdb-local-skill)
- Stream processing frameworks (use streaming-data-skill)

## Scope Constraints

File-based extraction and consulting portability only. Hands off to integration-patterns-skill for REST API, SQL database, and enterprise connector patterns. Reference files loaded on demand — do not pre-load all references.

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| medium | Sonnet | Opus, Haiku | Haiku |

## Core Principles

**Destination-Agnostic:** Write pipelines that swap DuckDB, Snowflake, BigQuery, or Databricks via a single environment variable. Never hardcode destination config in pipeline logic.

**Schema-First:** Define schema contracts before data flows. Catch drift, type mismatches, and unexpected columns at ingestion time rather than downstream.

**File-Native:** Treat messy file sources as first-class citizens. Handle encoding issues, inconsistent headers, multi-sheet Excel files, and mixed delimiters explicitly.

**Portable:** A pipeline should run with `pip install` + environment variables. No vendor-specific infrastructure required for development. Package dependencies in `requirements.txt`.

**Incremental-by-Default:** Track file modification timestamps or filenames to process only new files. Avoid reprocessing entire directories on every run.

## File Source Decision Matrix

| File Type | DLT Approach | Auto-Schema | Incremental Support |
|-----------|-------------|-------------|---------------------|
| CSV | `filesystem` + `read_csv()` | Yes (infer types) | Modified-since tracking |
| Excel (.xlsx) | Custom `@dlt.resource` with openpyxl | Manual (define columns) | Filename-based dedup |
| Parquet | `filesystem` + `read_parquet()` | Yes (preserved from file) | Modified-since tracking |
| JSON/NDJSON | `filesystem` + `read_jsonl()` | Yes (infer from structure) | Modified-since tracking |
| SharePoint | `filesystem` with fsspec SharePoint backend | Depends on file type | Modified-since tracking |
| SFTP | `filesystem` with fsspec SFTP backend | Depends on file type | Modified-since tracking |

## Destination Swapping Pattern

Same pipeline code targets different destinations via environment variable:

```python
import os
import dlt

DESTINATION = os.getenv("DLT_DESTINATION", "duckdb")

pipeline = dlt.pipeline(
    pipeline_name="client_extract",
    destination=DESTINATION,
    dataset_name="raw",
)

# Development: DLT_DESTINATION unset → DuckDB (local, zero config)
# Production:  DLT_DESTINATION=snowflake → Snowflake (credentials in .dlt/secrets.toml)
```

Add staging for warehouse destinations to improve load performance:

```python
if DESTINATION != "duckdb":
    pipeline = dlt.pipeline(
        pipeline_name="client_extract",
        destination=DESTINATION,
        staging="filesystem",  # S3 or GCS bucket
        dataset_name="raw",
    )
```

## Schema Contracts for Cleaning

Define expected schema, detect drift, and validate before loading. Schema contracts control how DLT handles unexpected data:

| Contract Mode | Tables | Columns | Data Types | Use Case |
|---------------|--------|---------|------------|----------|
| `evolve` | Add new | Add new | Coerce | Discovery phase |
| `freeze` | Reject new | Reject new | Reject mismatch | Production lockdown |
| `discard_rows` | Reject new | Drop row | Drop row | Strict validation |
| `discard_columns` | Add new | Drop column | Coerce | Flexible with guardrails |

Apply contracts per resource:

```python
@dlt.resource(
    schema_contract={"tables": "evolve", "columns": "freeze", "data_type": "freeze"}
)
def client_data():
    yield from read_files()
```

See [Schema Contracts Reference](references/schema-contracts.md) for Pydantic models, drift detection, and per-table strategies.

## Pipeline Structure

Standard project layout for portable consulting pipelines:

```
pipeline_project/
├── pipeline.py          # Main pipeline definition
├── sources/             # Custom source functions
│   ├── __init__.py
│   └── file_source.py
├── schemas/             # Schema contract files
│   └── expected.yaml
├── .dlt/
│   ├── config.toml      # Non-secret config (committed)
│   └── secrets.toml     # Secrets (gitignored)
├── requirements.txt     # Python dependencies
├── .gitignore           # Ignore .dlt/secrets.toml, *.duckdb
└── tests/               # Pipeline tests
    └── test_pipeline.py
```

## Quick Start Example

Filesystem source reading CSVs into DuckDB:

```python
import dlt
from dlt.sources.filesystem import filesystem, read_csv

pipeline = dlt.pipeline(
    pipeline_name="client_files",
    destination="duckdb",
    dataset_name="raw"
)

source = filesystem(
    bucket_url="./data/raw",
    file_glob="*.csv"
) | read_csv()

load_info = pipeline.run(source)
print(load_info)
```

Verify loaded data:

```python
with pipeline.sql_client() as client:
    for table in pipeline.default_schema.tables:
        if not table.startswith("_dlt"):
            result = client.execute_sql(f"SELECT COUNT(*) FROM {table}")
            print(f"  {table}: {result[0][0]} rows")
```

## Security Posture

See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) and [Security Tier Model](../shared-references/data-engineering/security-tier-model.md) for the full framework.

**Credentials:** All secrets stored in `.dlt/secrets.toml` (gitignored). Use environment variables in CI/CD and production.

| Capability | Tier 1 (Cloud-Native) | Tier 2 (Regulated) | Tier 3 (Air-Gapped) |
|------------|----------------------|--------------------|--------------------|
| File extraction | Execute against dev data | Generate for review | Generate only |
| Destination config | Deploy to dev | Generate for review | Generate only |
| Schema contracts | Deploy and test | Generate with validation | Generate only |
| Pipeline templates | Generate and run | Generate for review | Generate only |

**Credential best practices:** Never commit `.dlt/secrets.toml`. Use `dlt.secrets.value` for auto-resolution from env vars. Prefer IAM/service accounts over static credentials for cloud destinations.

## Reference Files

Load the appropriate reference for deep-dive guidance:

- [Source Patterns](references/source-patterns.md) -- Custom source decorators, factory patterns, error handling, yield patterns, testing
- [File Sources](references/file-sources.md) -- CSV, Excel, Parquet, JSON, SharePoint, SFTP ingestion patterns
- [Schema Contracts](references/schema-contracts.md) -- Contract modes, Pydantic models, drift detection, per-table strategies
- [Destinations](references/destinations.md) -- DuckDB, Snowflake, BigQuery config, staging, write dispositions, format selection
