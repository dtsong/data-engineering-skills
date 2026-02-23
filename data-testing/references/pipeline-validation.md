> **Part of:** [data-testing](../SKILL.md)

# Pipeline Validation

Reference for source profiling, DuckDB-based validation patterns, row hash comparison, data contract validation, and common framework patterns expressed as SQL.

## Source Profiling Validation

Before building transformations, profile source data to establish baselines:

```sql
-- DuckDB source profiling: column stats
SELECT
    column_name,
    column_type,
    count,
    null_percentage,
    approx_unique,
    min,
    max,
    avg
FROM (SUMMARIZE SELECT * FROM read_parquet('source_data.parquet'));
```

### Profiling Checklist

| Check | SQL Pattern | Action if Fails |
|-------|------------|-----------------|
| Row count baseline | `SELECT count(*) FROM source` | Log expected count; alert on > 10% drift |
| Null rate per column | `SELECT count(*) FILTER (WHERE col IS NULL) / count(*)::float` | Flag columns exceeding 5% null threshold |
| Distinct count | `SELECT approx_count_distinct(col)` | Compare against expected cardinality |
| Min/max range | `SELECT min(col), max(col)` | Validate within business-reasonable bounds |
| Date range | `SELECT min(date_col), max(date_col)` | Confirm expected temporal coverage |

---

## DuckDB-Based Validation Patterns

### Row Count Reconciliation

```sql
-- Compare source to target row counts
WITH counts AS (
    SELECT
        (SELECT count(*) FROM read_parquet('source.parquet')) AS source_ct,
        (SELECT count(*) FROM read_parquet('target.parquet')) AS target_ct
)
SELECT
    source_ct,
    target_ct,
    CASE WHEN source_ct = target_ct THEN 'PASS' ELSE 'FAIL' END AS result
FROM counts;
```

### Sum Reconciliation

```sql
-- Compare aggregate totals between source and target
SELECT
    abs(s.total - t.total) AS drift,
    CASE WHEN abs(s.total - t.total) < 0.01 THEN 'PASS' ELSE 'FAIL' END AS result
FROM
    (SELECT sum(amount) AS total FROM read_parquet('source.parquet')) s,
    (SELECT sum(amount) AS total FROM read_parquet('target.parquet')) t;
```

---

## Row Hash Comparison for Idempotency

Verify that re-running a pipeline produces identical output:

```sql
-- Generate row-level hash for comparison
CREATE TABLE run_1_hashes AS
SELECT md5(row_to_json(t)::text) AS row_hash
FROM read_parquet('output_run_1.parquet') t
ORDER BY primary_key_col;

CREATE TABLE run_2_hashes AS
SELECT md5(row_to_json(t)::text) AS row_hash
FROM read_parquet('output_run_2.parquet') t
ORDER BY primary_key_col;

-- Compare: should return 0 rows if idempotent
SELECT * FROM run_1_hashes
EXCEPT
SELECT * FROM run_2_hashes;
```

**Use cases:** Migration validation, incremental model re-run checks, refactoring verification.

---

## Data Contract Validation (DLT Schemas)

When using DLT (data load tool) or similar schema-enforced loaders:

```sql
-- Validate schema contract: expected columns and types
WITH expected AS (
    SELECT * FROM (VALUES
        ('order_id', 'INTEGER'),
        ('customer_id', 'INTEGER'),
        ('amount', 'DECIMAL'),
        ('order_date', 'DATE'),
        ('status', 'VARCHAR')
    ) AS t(column_name, expected_type)
),
actual AS (
    SELECT column_name, data_type AS actual_type
    FROM information_schema.columns
    WHERE table_name = 'orders'
)
SELECT
    e.column_name,
    e.expected_type,
    a.actual_type,
    CASE WHEN a.actual_type IS NULL THEN 'MISSING'
         WHEN a.actual_type != e.expected_type THEN 'TYPE_MISMATCH'
         ELSE 'PASS' END AS result
FROM expected e
LEFT JOIN actual a USING (column_name);
```

---

## Soda-Style Checks as SQL

Express Soda Core checks as standalone SQL for environments without Soda:

```sql
-- Soda: row_count > 0
SELECT CASE WHEN count(*) > 0 THEN 'PASS' ELSE 'FAIL' END AS check_result,
       'row_count > 0' AS check_name
FROM target_table;

-- Soda: missing_percent(email) < 5
SELECT CASE WHEN (count(*) FILTER (WHERE email IS NULL))::float / count(*) < 0.05
            THEN 'PASS' ELSE 'FAIL' END AS check_result,
       'missing_percent(email) < 5%' AS check_name
FROM target_table;

-- Soda: duplicate_percent(order_id) = 0
SELECT CASE WHEN count(*) - count(DISTINCT order_id) = 0
            THEN 'PASS' ELSE 'FAIL' END AS check_result,
       'duplicate_percent(order_id) = 0' AS check_name
FROM target_table;
```

---

## Great Expectations Patterns as SQL

Express common GE expectations as portable SQL:

| GE Expectation | SQL Pattern | Assert |
|----------------|------------|--------|
| `expect_column_values_to_not_be_null` | `SELECT count(*) FROM t WHERE col IS NULL` | = 0 |
| `expect_column_values_to_be_between` | `SELECT count(*) FROM t WHERE col NOT BETWEEN a AND b` | = 0 |
| `expect_column_pair_A_greater_than_B` | `SELECT count(*) FROM t WHERE end_date < start_date` | = 0 |
| `expect_table_row_count_to_equal` | `SELECT abs((SELECT count(*) FROM a) - (SELECT count(*) FROM b))` | = 0 |

**When to use SQL vs framework:** Use SQL assertions when the client environment does not support Soda or Great Expectations, or when tests must run in the warehouse natively (Snowflake, BigQuery, Redshift).
