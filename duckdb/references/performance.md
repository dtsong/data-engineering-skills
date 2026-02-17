## Contents

- [Memory Configuration](#memory-configuration)
- [Thread Configuration](#thread-configuration)
- [External Sorting](#external-sorting)
- [Query Profiling](#query-profiling)
- [Pragma Settings Reference](#pragma-settings-reference)
- [Persistent vs In-Memory Databases](#persistent-vs-in-memory-databases)
- [File Format Performance Comparison](#file-format-performance-comparison)

---

# Performance

> **Part of:** [duckdb](../SKILL.md)

## Memory Configuration

DuckDB operates in-memory by default but can spill to disk for large datasets.

```sql
-- Set memory limit (default: 80% of system RAM)
SET memory_limit = '4GB';

-- Check current setting
SELECT current_setting('memory_limit');
```

### Guidelines

| System RAM | Recommended Limit | Reasoning |
|-----------|-------------------|-----------|
| 8 GB | `4GB` | Leave headroom for OS and other apps |
| 16 GB | `8GB` | Comfortable for most local analysis |
| 32 GB+ | `16GB` | Large datasets; increase as needed |

Reduce memory limit when running alongside memory-heavy applications (IDEs, browsers, Docker).

## Thread Configuration

```sql
-- Set thread count (default: number of CPU cores)
SET threads = 4;

-- Check current setting
SELECT current_setting('threads');
```

### Guidelines

| Scenario | Threads | Reasoning |
|----------|---------|-----------|
| Dedicated analysis | CPU cores | Maximum throughput |
| Background task | CPU cores / 2 | Leave resources for foreground work |
| CI/shared server | 2-4 | Avoid starving other processes |

## External Sorting

When datasets exceed memory, DuckDB spills sort operations to disk.

```sql
-- Set temp directory for spill-to-disk
SET temp_directory = '/tmp/duckdb_temp';

-- Verify
SELECT current_setting('temp_directory');
```

The temp directory must exist and have sufficient free space. DuckDB creates temporary files during large sorts, joins, and aggregations.

### Estimating Temp Space

Rule of thumb: temp space needed is approximately 2x the size of the data being sorted. For a 10GB dataset sort, ensure at least 20GB free in the temp directory.

## Query Profiling

### EXPLAIN

```sql
-- Show query plan (logical)
EXPLAIN SELECT count(*) FROM read_parquet('data/*.parquet') WHERE year = 2024;

-- Show query plan with physical operators
EXPLAIN ANALYZE SELECT count(*) FROM read_parquet('data/*.parquet') WHERE year = 2024;
```

### EXPLAIN ANALYZE Output

Key things to look for:

| Indicator | What It Means | Action |
|-----------|--------------|--------|
| `FILTER` after `SCAN` | Predicate not pushed down | Move filter to source or use Parquet |
| High `rows_scanned` vs `rows_returned` | Scanning too much data | Add filters or partition data |
| `EXTERNAL` in sort/join | Spilling to disk | Increase memory or reduce data |
| Large `HASH_JOIN` | Memory-intensive join | Filter inputs before joining |

### Profiling in Python

```python
import duckdb

con = duckdb.connect()
con.execute("PRAGMA enable_profiling = 'json'")
con.execute("PRAGMA profiling_output = 'profile.json'")

con.execute("SELECT count(*) FROM read_parquet('data.parquet') WHERE status = 'active'")

# Read the profiling output
import json
with open("profile.json") as f:
    profile = json.load(f)
```

## Pragma Settings Reference

| Pragma | Default | Description |
|--------|---------|-------------|
| `memory_limit` | 80% RAM | Maximum memory usage |
| `threads` | CPU cores | Worker thread count |
| `temp_directory` | `.tmp` (cwd) | Spill-to-disk location |
| `enable_progress_bar` | `false` | Show progress for long queries |
| `enable_profiling` | `false` | Enable query profiling (`json` or `query_tree`) |
| `profiling_output` | stdout | File path for profiling output |
| `force_compression` | auto | Override compression for Parquet writes |
| `preserve_insertion_order` | `true` | Maintain row order (disable for speed) |
| `enable_object_cache` | `false` | Cache Parquet metadata between queries |

### Performance-Oriented Settings

```sql
-- Speed up repeated Parquet queries (caches file metadata)
SET enable_object_cache = true;

-- Disable row order preservation for bulk operations
SET preserve_insertion_order = false;
```

## Persistent vs In-Memory Databases

| Mode | Command | Use When |
|------|---------|----------|
| In-memory | `duckdb.connect()` or `:memory:` | One-off analysis, scripts, testing |
| Persistent | `duckdb.connect('analysis.duckdb')` | Multi-session work, large data, sharing results |

### Persistent Database Advantages

- Avoid re-reading source files on each session.
- Create indexes and views that persist.
- Share the `.duckdb` file with colleagues.
- Resume analysis across sessions.

### When to Use In-Memory

- Single script execution (read file, transform, export).
- CI/CD pipelines where state should not persist.
- When source files change frequently and re-reading is desired.

### Database Size Management

```sql
-- Check database size
SELECT database_size, block_size FROM pragma_database_size();

-- Reclaim space after deleting data
CHECKPOINT;
VACUUM;
```

## File Format Performance Comparison

Benchmarks for reading a 1GB dataset (approximate, varies by hardware and data):

| Format | Read Time | File Size | Column Pruning | Predicate Pushdown |
|--------|-----------|-----------|----------------|-------------------|
| **Parquet** | ~1s | ~200MB | Yes | Yes |
| **CSV** | ~8s | ~1GB | No | No |
| **JSON** | ~15s | ~1.5GB | No | No |
| **Excel** | ~30s+ | ~800MB | No | No |

### Recommendations

1. **Convert to Parquet early.** If you query the same CSV more than twice, convert it.
2. **Use column pruning.** Select only needed columns; Parquet skips unread columns entirely.
3. **Filter early.** Parquet predicate pushdown skips row groups that do not match.
4. **Glob Parquet over CSV.** Multi-file reads are significantly faster with Parquet.

```sql
-- One-time conversion from CSV to Parquet
COPY (SELECT * FROM read_csv_auto('large_data.csv'))
TO 'large_data.parquet' (FORMAT PARQUET, COMPRESSION 'zstd');

-- All subsequent queries use Parquet
SELECT * FROM read_parquet('large_data.parquet') WHERE region = 'US';
```
