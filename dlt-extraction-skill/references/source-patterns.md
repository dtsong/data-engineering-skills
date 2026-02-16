## Contents

- [Custom Source Decorators](#custom-source-decorators)
- [Source Factory Pattern](#source-factory-pattern)
- [Error Handling](#error-handling)
- [Yield Patterns](#yield-patterns)
- [Resource Configuration](#resource-configuration)
- [Testing Sources](#testing-sources)

---

# DLT Source Patterns

> **Part of:** [dlt-extraction-skill](../SKILL.md)

## Custom Source Decorators

Use `@dlt.source` to group related resources. Use `@dlt.resource` for individual data streams.

```python
import dlt

@dlt.source
def client_files(base_path: str = "./data"):
    """Source that reads multiple file types from a client directory."""
    return [csv_data(base_path), excel_data(base_path)]

@dlt.resource(write_disposition="append", primary_key="row_id")
def csv_data(base_path: str):
    """Read CSV files from the client directory."""
    import glob
    for filepath in glob.glob(f"{base_path}/*.csv"):
        yield from read_csv_file(filepath)

@dlt.resource(write_disposition="replace")
def excel_data(base_path: str):
    """Read Excel files — replace on each run."""
    import glob
    for filepath in glob.glob(f"{base_path}/*.xlsx"):
        yield from read_excel_file(filepath)
```

Resources inherit source-level config (credentials, settings) automatically.

## Source Factory Pattern

Parameterize sources for different clients or configurations:

```python
def make_client_source(client_name: str, bucket_url: str, file_glob: str = "*.csv"):
    """Factory: create a configured source for a specific client."""

    @dlt.source(name=f"{client_name}_files")
    def client_source():
        from dlt.sources.filesystem import filesystem, read_csv
        files = filesystem(bucket_url=bucket_url, file_glob=file_glob) | read_csv()
        return files

    return client_source

# Usage: different clients, same pipeline logic
acme_source = make_client_source("acme", "s3://acme-data/exports")
globex_source = make_client_source("globex", "./data/globex", "*.tsv")
```

Use factory pattern when: multiple clients share pipeline logic but differ in config (paths, schemas, credentials).

## Error Handling

**Retry logic** for transient file access failures:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=30))
def read_file_with_retry(filepath: str):
    """Retry file reads for network/SFTP flakiness."""
    with open(filepath, "r") as f:
        return f.read()
```

**Dead letter handling** for malformed records:

```python
@dlt.resource
def safe_csv_data(base_path: str):
    """Skip bad rows, log to dead letter table."""
    dead_letters = []
    for filepath in glob.glob(f"{base_path}/*.csv"):
        for i, row in enumerate(read_csv_rows(filepath)):
            try:
                yield validate_and_transform(row)
            except (ValueError, KeyError) as e:
                dead_letters.append({
                    "file": filepath, "row": i, "error": str(e),
                    "raw_data": str(row)[:500]
                })
    if dead_letters:
        yield dlt.mark.with_table_name(dead_letters, "_dead_letters")
```

**Partial load recovery:** DLT tracks load state. If a pipeline fails mid-run, re-running it resumes from the last checkpoint. Use `write_disposition="merge"` with `primary_key` to make reloads idempotent.

## Yield Patterns

Use generators for memory-efficient processing of large files:

```python
@dlt.resource
def large_csv(filepath: str, chunk_size: int = 10000):
    """Stream large CSV in chunks — constant memory usage."""
    import csv
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        chunk = []
        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:
            yield chunk
```

| Pattern | Memory | Use Case |
|---------|--------|----------|
| `yield row` | Minimal | Small-medium files |
| `yield chunk` (list) | Bounded | Large files, batch operations |
| `return list` | Full dataset in RAM | Small reference tables only |

Prefer `yield` over `return` for any file over 10MB.

## Resource Configuration

Control parallelism, chunking, and nesting:

```python
@dlt.resource(
    parallelized=True,           # Enable parallel extraction
    table_name="client_orders",  # Override default table name
    max_table_nesting=1,         # Limit nested struct expansion
    write_disposition="merge",
    primary_key="order_id",
)
def orders(updated_after: dlt.sources.incremental[str] = dlt.sources.incremental(
    cursor_path="updated_at",
    initial_value="2024-01-01T00:00:00Z",
)):
    yield from fetch_orders(updated_after.last_value)
```

| Setting | Default | Recommendation |
|---------|---------|----------------|
| `parallelized` | False | True for I/O-bound sources (network, SFTP) |
| `max_table_nesting` | 2 | 0-1 for flat file sources |
| `table_name` | Function name | Override for clarity |

## Testing Sources

Test with DuckDB in dev mode for fast, isolated validation:

```python
def test_client_source():
    pipeline = dlt.pipeline(
        pipeline_name="test_client",
        destination="duckdb",
        dev_mode=True,  # Fresh schema on each run
    )

    source = client_files(base_path="./tests/fixtures")
    load_info = pipeline.run(source, write_disposition="replace")

    # Verify no failed jobs
    assert not load_info.has_failed_jobs

    # Verify row counts
    with pipeline.sql_client() as client:
        result = client.execute_sql("SELECT COUNT(*) FROM csv_data")
        assert result[0][0] > 0

    # Verify schema shape
    schema = pipeline.default_schema
    assert "csv_data" in schema.tables
    assert "row_id" in [c["name"] for c in schema.tables["csv_data"]["columns"].values()]
```

Run tests with: `pytest tests/ -v`. Use `write_disposition="replace"` in tests for deterministic results.
