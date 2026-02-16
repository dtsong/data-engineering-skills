## Contents

- [CSV Ingestion](#csv-ingestion)
- [Parquet Ingestion](#parquet-ingestion)
- [JSON Ingestion](#json-ingestion)
- [Glob Patterns](#glob-patterns)
- [Schema Inference](#schema-inference)
- [Common Issues](#common-issues)

---

# File Ingestion

> **Part of:** [duckdb-local-skill](../SKILL.md)

## CSV Ingestion

### read_csv_auto() Parameters

```sql
SELECT * FROM read_csv_auto(
    'data.csv',
    delim = ',',           -- delimiter (auto-detected if omitted)
    header = true,         -- first row is header (auto-detected)
    skip = 0,              -- skip N rows before header
    columns = {            -- explicit column types (overrides inference)
        'id': 'INTEGER',
        'name': 'VARCHAR',
        'amount': 'DECIMAL(10,2)'
    },
    max_line_size = 2097152,  -- increase for rows with large text fields
    null_padding = true,      -- pad short rows with NULLs instead of error
    ignore_errors = true,     -- skip malformed rows
    all_varchar = false,      -- force all columns to VARCHAR (disable inference)
    sample_size = 20480,      -- rows sampled for type inference (default: 20480)
    dateformat = '%Y-%m-%d',  -- explicit date parsing format
    timestampformat = '%Y-%m-%d %H:%M:%S'
);
```

### Common CSV Patterns

```sql
-- Tab-separated
SELECT * FROM read_csv_auto('data.tsv', delim = '\t');

-- Pipe-delimited
SELECT * FROM read_csv_auto('data.txt', delim = '|');

-- Skip metadata rows at top of file
SELECT * FROM read_csv_auto('report.csv', skip = 3);

-- Force all strings (for initial inspection)
SELECT * FROM read_csv_auto('data.csv', all_varchar = true);
```

## Parquet Ingestion

### read_parquet() Parameters

```sql
SELECT * FROM read_parquet(
    'data.parquet',
    hive_partitioning = false,  -- auto-detect Hive partition columns
    union_by_name = false       -- align schemas across multiple files by column name
);
```

### Hive-Partitioned Data

```sql
-- Directory structure: data/year=2024/month=01/part-0001.parquet
SELECT * FROM read_parquet('data/**/*.parquet', hive_partitioning = true);
-- year and month columns auto-created from directory names
```

### Column Pruning

Parquet supports column pruning -- only requested columns are read from disk:

```sql
-- Only reads 'id' and 'amount' columns from the file
SELECT id, amount FROM read_parquet('large_file.parquet');
```

## JSON Ingestion

### read_json_auto() Parameters

```sql
SELECT * FROM read_json_auto(
    'data.json',
    format = 'auto',           -- 'auto', 'array', or 'newline_delimited'
    maximum_object_size = 16777216,  -- max size per JSON object in bytes
    sample_size = 20480,       -- rows sampled for type inference
    records = 'auto'           -- 'auto', 'true' (array of records), 'false' (single object)
);
```

### NDJSON (Newline-Delimited JSON)

```sql
SELECT * FROM read_json_auto('logs.ndjson', format = 'newline_delimited');
```

### Nested Struct Flattening

DuckDB preserves JSON structure as native STRUCT types. Flatten with dot notation or `unnest()`:

```sql
-- Access nested fields
SELECT
    data.user.name as user_name
    , data.user.email as user_email
    , data.metadata.created_at as created_at
FROM read_json_auto('nested.json');

-- Flatten arrays
SELECT
    id
    , unnest(items) as item
FROM read_json_auto('orders.json');

-- Fully flatten nested arrays
SELECT
    id
    , unnest(items, recursive := true)
FROM read_json_auto('orders.json');
```

## Glob Patterns

Read multiple files with pattern matching:

```sql
-- All CSVs in a directory
SELECT * FROM read_csv_auto('data/*.csv');

-- Recursive glob
SELECT * FROM read_csv_auto('data/**/*.csv');

-- Union by name (align schemas when column order differs)
SELECT * FROM read_csv_auto('data/*.csv', union_by_name = true);

-- Include filename as a column
SELECT *, filename FROM read_csv_auto('data/*.csv', filename = true);
```

### Filename Column

Track which file each row came from:

```sql
SELECT
    filename
    , count(*) as row_count
FROM read_csv_auto('data/*.csv', filename = true)
GROUP BY filename;
```

## Schema Inference

### How Inference Works

DuckDB samples the first `sample_size` rows (default: 20,480) to detect types.

| Scenario | Strategy |
|----------|----------|
| Small file (<20K rows) | Full scan; inference is reliable |
| Large file, consistent types | Default sample; works well |
| Large file, mixed types late | Increase `sample_size` or use `all_varchar` |
| Known schema | Provide explicit `columns` parameter |

### Override Inference

```sql
-- Force all columns to strings for inspection
SELECT * FROM read_csv_auto('data.csv', all_varchar = true) LIMIT 100;

-- Then define explicit types
SELECT
    cast(id as integer) as id
    , name
    , cast(amount as decimal(10,2)) as amount
FROM read_csv_auto('data.csv', all_varchar = true);
```

### Increase Sample Size

```sql
-- Sample more rows for better inference on inconsistent data
SELECT * FROM read_csv_auto('data.csv', sample_size = -1);  -- -1 = scan entire file
```

## Common Issues

| Issue | Symptom | Fix |
|-------|---------|-----|
| Encoding errors | `Invalid byte sequence` | Save as UTF-8 or use `encoding` parameter |
| Mixed types in column | Column cast as VARCHAR | Increase `sample_size` or use `columns` |
| Extra columns in some rows | Row parse error | Use `null_padding = true` |
| Quoted delimiters | Columns misaligned | Usually auto-detected; try explicit `quote = '"'` |
| Large text fields | `Maximum line size exceeded` | Increase `max_line_size` |
| Date parsing fails | Dates as VARCHAR | Use `dateformat` parameter |
| BOM (byte order mark) | Extra characters in first column | DuckDB handles UTF-8 BOM automatically |
| Empty file | Schema inference fails | Check file existence before reading |
