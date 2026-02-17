## Contents

- [CSV Ingestion](#csv-ingestion)
- [Excel Ingestion](#excel-ingestion)
- [Parquet Ingestion](#parquet-ingestion)
- [JSON and NDJSON](#json-and-ndjson)
- [SharePoint](#sharepoint)
- [SFTP](#sftp)
- [Glob Patterns and File Filtering](#glob-patterns-and-file-filtering)
- [Incremental File Processing](#incremental-file-processing)

---

# DLT File Source Patterns

> **Part of:** [dlt-extract](../SKILL.md)

## CSV Ingestion

Use the filesystem source with the `read_csv` transformer:

```python
from dlt.sources.filesystem import filesystem, read_csv

source = filesystem(
    bucket_url="./data/input",
    file_glob="*.csv",
) | read_csv(
    delimiter=",",          # Auto-detected if omitted
    encoding="utf-8",       # Handle encoding explicitly for client files
    double_precision=True,  # Preserve decimal precision
)
```

**Encoding handling:** Client files often arrive in non-UTF-8 encodings. Detect encoding before loading:

```python
import chardet

def detect_encoding(filepath: str) -> str:
    with open(filepath, "rb") as f:
        result = chardet.detect(f.read(10000))
    return result["encoding"] or "utf-8"
```

**Delimiter detection:** For files with unknown delimiters, use `csv.Sniffer`:

```python
import csv

def detect_delimiter(filepath: str) -> str:
    with open(filepath, "r") as f:
        sample = f.read(4096)
    return csv.Sniffer().sniff(sample).delimiter
```

## Excel Ingestion

DLT does not have a built-in Excel reader. Use a custom resource with openpyxl:

```python
import dlt
from openpyxl import load_workbook

@dlt.resource(write_disposition="replace")
def excel_data(filepath: str, sheet_name: str = None):
    """Read Excel file into DLT resource."""
    wb = load_workbook(filepath, read_only=True, data_only=True)

    sheets = [sheet_name] if sheet_name else wb.sheetnames
    for sheet in sheets:
        ws = wb[sheet]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue

        # First row as headers
        headers = [str(h).strip().lower().replace(" ", "_") for h in rows[0]]
        for row in rows[1:]:
            record = dict(zip(headers, row))
            record["_source_sheet"] = sheet
            yield record
    wb.close()
```

**Header detection:** Skip rows before the actual header. Inspect the first N rows for a row where most cells are non-empty strings:

```python
def find_header_row(ws, max_scan: int = 10) -> int:
    for i, row in enumerate(ws.iter_rows(max_row=max_scan, values_only=True)):
        non_empty = sum(1 for c in row if c is not None and isinstance(c, str))
        if non_empty >= len(row) * 0.6:
            return i
    return 0
```

**Multi-sheet iteration:** Use `dlt.mark.with_table_name` to route sheets to separate tables:

```python
@dlt.resource
def excel_multi_table(filepath: str):
    wb = load_workbook(filepath, read_only=True, data_only=True)
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            continue
        headers = [str(h).strip().lower().replace(" ", "_") for h in rows[0]]
        records = [dict(zip(headers, r)) for r in rows[1:]]
        yield dlt.mark.with_table_name(records, sheet.lower().replace(" ", "_"))
    wb.close()
```

## Parquet Ingestion

Use the filesystem source with the `read_parquet` transformer. Schema is preserved from the Parquet file metadata:

```python
from dlt.sources.filesystem import filesystem, read_parquet

source = filesystem(
    bucket_url="s3://client-bucket/exports",
    file_glob="**/*.parquet",
) | read_parquet()
```

Parquet preserves column types, nested structures, and null handling. Preferred format when the upstream system supports it.

## JSON and NDJSON

Use the filesystem source with `read_jsonl` for newline-delimited JSON:

```python
from dlt.sources.filesystem import filesystem, read_jsonl

source = filesystem(
    bucket_url="./data/events",
    file_glob="*.jsonl",
) | read_jsonl()
```

**Nested struct handling:** Control nesting depth with `max_table_nesting`:

```python
pipeline = dlt.pipeline(
    pipeline_name="json_extract",
    destination="duckdb",
    dataset_name="raw",
)

# Flatten to max 1 level of child tables
pipeline.run(source, max_table_nesting=1)
```

| Nesting Level | Behavior |
|---------------|----------|
| 0 | All nested data as JSON columns |
| 1 | Top-level arrays as child tables |
| 2 (default) | Two levels of child tables |

For single JSON files (not NDJSON), use a custom resource:

```python
import json

@dlt.resource
def json_file(filepath: str):
    with open(filepath, "r") as f:
        data = json.load(f)
    if isinstance(data, list):
        yield from data
    else:
        yield data
```

## SharePoint

Use the filesystem source with the fsspec SharePoint backend:

```python
from dlt.sources.filesystem import filesystem, read_csv

source = filesystem(
    bucket_url="sharepoint://sites/DataTeam/Shared Documents/exports",
    file_glob="*.csv",
) | read_csv()
```

**Auth config** in `.dlt/secrets.toml`:

```toml
[sources.filesystem.credentials]
client_id = "your-app-client-id"
client_secret = "your-app-client-secret"
tenant_id = "your-tenant-id"
```

Register an Azure AD app with Sites.Read.All permission for read-only access.

## SFTP

Use the filesystem source with fsspec SFTP backend:

```python
from dlt.sources.filesystem import filesystem, read_csv

source = filesystem(
    bucket_url="sftp://sftp.client.com/exports",
    file_glob="*.csv",
) | read_csv()
```

**Key-based auth** in `.dlt/secrets.toml`:

```toml
[sources.filesystem.credentials]
username = "data_user"
key_filename = "/path/to/private_key"
# Or use password auth:
# password = "your-password"
```

Prefer key-based auth over passwords. Ensure the private key file has `chmod 600` permissions.

## Glob Patterns and File Filtering

| Pattern | Matches |
|---------|---------|
| `*.csv` | All CSVs in root directory |
| `**/*.csv` | All CSVs recursively |
| `2024-*.csv` | CSVs starting with "2024-" |
| `{orders,invoices}*.csv` | Orders or invoices CSVs |
| `**/export_????????.csv` | Files matching date-like pattern |

Combine glob patterns with filesystem source:

```python
source = filesystem(
    bucket_url="./data",
    file_glob="**/{orders,invoices}_*.csv",
)
```

## Incremental File Processing

**Modified-since tracking:** DLT filesystem source tracks file modification timestamps automatically. Only new or modified files are processed on subsequent runs.

```python
source = filesystem(
    bucket_url="./data/incoming",
    file_glob="*.csv",
) | read_csv()

# First run: processes all files
# Second run: processes only new/modified files
pipeline.run(source, write_disposition="append")
```

**Filename-based dedup:** For sources that rewrite files with the same content, track processed filenames:

```python
@dlt.resource(write_disposition="merge", primary_key="filename")
def tracked_files(base_path: str):
    """Track processed files by filename to avoid reprocessing."""
    import glob
    for filepath in sorted(glob.glob(f"{base_path}/*.csv")):
        filename = os.path.basename(filepath)
        records = list(read_csv_file(filepath))
        for record in records:
            record["_source_filename"] = filename
            record["_loaded_at"] = datetime.utcnow().isoformat()
            yield record
```
