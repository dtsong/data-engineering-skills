## Contents

- [COPY TO CSV](#copy-to-csv)
- [COPY TO Parquet](#copy-to-parquet)
- [COPY TO JSON](#copy-to-json)
- [Python API Export](#python-api-export)
- [Partitioned Writes](#partitioned-writes)
- [Export to Multiple Formats](#export-to-multiple-formats)

---

# Export Patterns

> **Part of:** [duckdb](../SKILL.md)

## COPY TO CSV

```sql
COPY (SELECT * FROM customers_clean)
TO 'output/customers.csv'
(
    HEADER true,              -- include column names (default: true)
    DELIMITER ',',            -- column separator
    NULL 'NULL',              -- string representation for NULLs
    QUOTE '"',                -- quoting character
    ESCAPE '"',               -- escape character inside quoted fields
    FORCE_QUOTE (name, notes) -- always quote these columns
);
```

### Common CSV Variations

```sql
-- Tab-separated for Excel compatibility
COPY query TO 'output.tsv' (DELIMITER '\t', HEADER);

-- Pipe-delimited
COPY query TO 'output.txt' (DELIMITER '|', HEADER);

-- No header (for systems that expect raw data)
COPY query TO 'output.csv' (HEADER false);

-- Custom NULL representation
COPY query TO 'output.csv' (HEADER, NULL '\\N');
```

## COPY TO Parquet

```sql
COPY (SELECT * FROM customers_clean)
TO 'output/customers.parquet'
(
    FORMAT PARQUET,
    COMPRESSION 'zstd',       -- 'zstd' (default), 'snappy', 'gzip', 'uncompressed'
    ROW_GROUP_SIZE 122880      -- rows per row group (default: 122880)
);
```

### Compression Comparison

| Compression | Speed | Size | Use When |
|-------------|-------|------|----------|
| `zstd` | Fast | Smallest | Default; best balance |
| `snappy` | Fastest | Medium | Speed-critical pipelines |
| `gzip` | Slow | Small | Compatibility with older tools |
| `uncompressed` | Fastest | Largest | Debugging; temporary files |

### Row Group Size

Smaller row groups improve predicate pushdown for targeted queries. Larger row groups improve compression ratio.

```sql
-- Small row groups for frequently filtered data
COPY query TO 'output.parquet' (FORMAT PARQUET, ROW_GROUP_SIZE 10000);

-- Large row groups for bulk reads
COPY query TO 'output.parquet' (FORMAT PARQUET, ROW_GROUP_SIZE 1000000);
```

## COPY TO JSON

```sql
-- Array of objects (default)
COPY (SELECT * FROM customers_clean)
TO 'output/customers.json'
(FORMAT JSON);

-- Newline-delimited JSON (NDJSON) -- preferred for streaming/log pipelines
COPY (SELECT * FROM customers_clean)
TO 'output/customers.ndjson'
(FORMAT JSON, ARRAY false);
```

| Format | `ARRAY` | Output Shape | Use When |
|--------|---------|-------------|----------|
| JSON array | `true` (default) | `[{...}, {...}]` | Small datasets, APIs |
| NDJSON | `false` | `{...}\n{...}\n` | Large datasets, streaming, log processing |

## Python API Export

### To Pandas DataFrame

```python
import duckdb

con = duckdb.connect("analysis.duckdb")

# fetchdf() returns a Pandas DataFrame
df = con.sql("SELECT * FROM customers_clean").fetchdf()
df.to_excel("output/customers.xlsx", index=False)
```

### To Python Lists

```python
# fetchall() returns list of tuples
rows = con.sql("SELECT id, name FROM customers").fetchall()

# fetchone() returns a single tuple
row = con.sql("SELECT count(*) FROM customers").fetchone()
count = row[0]

# description gives column names
result = con.sql("SELECT * FROM customers")
columns = [desc[0] for desc in result.description]
```

### To Arrow Table

```python
# fetch_arrow_table() returns a PyArrow Table
arrow_table = con.sql("SELECT * FROM customers_clean").fetch_arrow_table()

# Write to Parquet with PyArrow (more control over metadata)
import pyarrow.parquet as pq
pq.write_table(arrow_table, "output/customers.parquet")

# Convert to Polars
import polars as pl
polars_df = pl.from_arrow(arrow_table)
```

## Partitioned Writes

Write output partitioned by column values (Hive-style directory structure):

```sql
-- Partition by year and month
COPY (SELECT * FROM events)
TO 'output/events'
(FORMAT PARQUET, PARTITION_BY (year, month));
-- Creates: output/events/year=2024/month=01/data_0.parquet
```

### Partitioning Strategy

| Column Cardinality | Recommendation |
|-------------------|----------------|
| Low (< 50 values) | Partition directly |
| Medium (50-1000) | Partition if queries filter on it |
| High (> 1000) | Do not partition; use Parquet row groups |

```sql
-- Add partition columns if not present
COPY (
    SELECT
        *
        , year(event_date) AS year
        , month(event_date) AS month
    FROM events
)
TO 'output/events'
(FORMAT PARQUET, PARTITION_BY (year, month));
```

## Export to Multiple Formats

Generate CSV (for stakeholders), Parquet (for pipelines), and JSON (for APIs) from the same query:

```sql
-- Create a view to avoid repeating the query
CREATE VIEW export_data AS
SELECT * FROM customers_clean WHERE status = 'active';

-- Export to all formats
COPY (SELECT * FROM export_data) TO 'output/active_customers.csv' (HEADER);
COPY (SELECT * FROM export_data) TO 'output/active_customers.parquet' (FORMAT PARQUET);
COPY (SELECT * FROM export_data) TO 'output/active_customers.json' (FORMAT JSON, ARRAY false);
```

### Python Batch Export

```python
import duckdb

con = duckdb.connect("analysis.duckdb")

exports = {
    "csv": "COPY (SELECT * FROM export_data) TO 'output/data.csv' (HEADER)",
    "parquet": "COPY (SELECT * FROM export_data) TO 'output/data.parquet' (FORMAT PARQUET)",
    "json": "COPY (SELECT * FROM export_data) TO 'output/data.ndjson' (FORMAT JSON, ARRAY false)",
}

for fmt, query in exports.items():
    con.execute(query)
    print(f"Exported {fmt}")
```
