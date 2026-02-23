> **Part of:** [data-testing](../SKILL.md)

# SQL Assertion Patterns

Reference for standalone SQL data quality assertions. Each pattern includes the assertion logic, expected result, and cross-database syntax variants.

## Row Count Reconciliation

```sql
-- Assert: source and target have equal row counts
SELECT
    'row_count_reconciliation' AS assertion,
    source_ct,
    target_ct,
    CASE WHEN source_ct = target_ct THEN 'PASS' ELSE 'FAIL' END AS result
FROM (
    SELECT
        (SELECT count(*) FROM source_table) AS source_ct,
        (SELECT count(*) FROM target_table) AS target_ct
);
```

**Tolerance variant** (accept up to 1% drift):

```sql
SELECT CASE
    WHEN abs(source_ct - target_ct)::float / NULLIF(source_ct, 0) <= 0.01
    THEN 'PASS' ELSE 'FAIL'
END AS result
FROM (/* counts subquery */);
```

---

## Sum Reconciliation

```sql
-- Assert: aggregate totals match within rounding tolerance
SELECT
    'sum_reconciliation' AS assertion,
    abs(source_total - target_total) AS drift,
    CASE WHEN abs(source_total - target_total) < 0.01 THEN 'PASS' ELSE 'FAIL' END AS result
FROM (
    SELECT
        (SELECT sum(amount) FROM source_table) AS source_total,
        (SELECT sum(amount) FROM target_table) AS target_total
);
```

---

## Null Introduction Detection

Detect columns where transformations introduced new NULLs not present in source:

```sql
-- Assert: no new NULLs introduced by transformation
SELECT
    'null_introduction' AS assertion,
    target_nulls - source_nulls AS new_nulls,
    CASE WHEN target_nulls <= source_nulls THEN 'PASS' ELSE 'FAIL' END AS result
FROM (
    SELECT
        (SELECT count(*) FROM source_table WHERE col IS NULL) AS source_nulls,
        (SELECT count(*) FROM target_table WHERE col IS NULL) AS target_nulls
);
```

---

## Uniqueness Verification

```sql
-- Assert: column has no duplicate values
SELECT
    'uniqueness' AS assertion,
    count(*) AS total_rows,
    count(DISTINCT pk_column) AS distinct_values,
    CASE WHEN count(*) = count(DISTINCT pk_column) THEN 'PASS' ELSE 'FAIL' END AS result
FROM target_table;
```

**Composite key variant:**

```sql
SELECT
    count(*) AS total_rows,
    count(DISTINCT (col_a, col_b)) AS distinct_keys,
    CASE WHEN count(*) = count(DISTINCT (col_a, col_b)) THEN 'PASS' ELSE 'FAIL' END AS result
FROM target_table;
```

---

## Referential Integrity

```sql
-- Assert: all foreign keys exist in parent table
SELECT
    'referential_integrity' AS assertion,
    count(*) AS orphan_count,
    CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS result
FROM child_table c
LEFT JOIN parent_table p ON c.parent_id = p.id
WHERE p.id IS NULL;
```

---

## Date Continuity

```sql
-- Assert: no gaps in daily date sequence
WITH date_range AS (
    SELECT
        date_col,
        lead(date_col) OVER (ORDER BY date_col) AS next_date,
        lead(date_col) OVER (ORDER BY date_col) - date_col AS gap_days
    FROM target_table
)
SELECT
    'date_continuity' AS assertion,
    count(*) AS gaps_found,
    CASE WHEN count(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS result
FROM date_range
WHERE gap_days > 1;
```

**Weekly variant:** Replace `gap_days > 1` with `gap_days > 7`.

---

## Distribution Drift

Compare value distributions between two datasets (e.g., current vs previous load):

```sql
-- Assert: category distribution drift < 5% per bucket
WITH current_dist AS (
    SELECT category, count(*)::float / sum(count(*)) OVER () AS pct
    FROM current_table GROUP BY category
),
baseline_dist AS (
    SELECT category, count(*)::float / sum(count(*)) OVER () AS pct
    FROM baseline_table GROUP BY category
)
SELECT
    coalesce(c.category, b.category) AS category,
    abs(coalesce(c.pct, 0) - coalesce(b.pct, 0)) AS drift,
    CASE WHEN abs(coalesce(c.pct, 0) - coalesce(b.pct, 0)) < 0.05
         THEN 'PASS' ELSE 'FAIL' END AS result
FROM current_dist c
FULL OUTER JOIN baseline_dist b USING (category);
```

---

## Cross-Database Syntax Variants

| Pattern | DuckDB | Snowflake | SQL Server |
|---------|--------|-----------|------------|
| Row hash | `md5(row_to_json(t)::text)` | `hash(*)` | `HASHBYTES('MD5', CONCAT(col1, col2))` |
| Approximate distinct | `approx_count_distinct(col)` | `APPROX_COUNT_DISTINCT(col)` | `APPROX_COUNT_DISTINCT(col)` |
| FILTER clause | `count(*) FILTER (WHERE ...)` | `COUNT_IF(...)` | `SUM(CASE WHEN ... THEN 1 ELSE 0 END)` |
| Composite distinct | `count(DISTINCT (a, b))` | `count(DISTINCT a || b)` | `COUNT(DISTINCT CONCAT(a, b))` |
| EXCEPT | `EXCEPT` | `EXCEPT` | `EXCEPT` |
| Date arithmetic | `date + INTERVAL '1 day'` | `DATEADD(day, 1, date)` | `DATEADD(day, 1, date)` |
| UNPIVOT | `UNPIVOT (...)` | `UNPIVOT (...)` | `UNPIVOT (...)` |
| String agg | `string_agg(col, ',')` | `LISTAGG(col, ',')` | `STRING_AGG(col, ',')` |

**Usage note:** When generating assertions for a specific platform, use the platform-native syntax from this table. Default to DuckDB syntax for local validation.
