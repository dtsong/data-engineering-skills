## Contents

- [Profiling Methodology](#profiling-methodology)
- [SQL Profiling Patterns for DuckDB](#sql-profiling-patterns-for-duckdb)
- [schema_profiler.py Usage](#schema_profilerpy-usage)
- [Interpreting Profiling Results](#interpreting-profiling-results)
- [Output Format](#output-format)

# Schema Profiling — Procedural Reference

> **Part of:** [client-delivery](../SKILL.md)

---

## Profiling Methodology

Profile in three layers, each building on the previous:

### File-Level Profiling

Capture before opening any file:

| Metric | How to Detect |
|--------|--------------|
| Encoding | `chardet` detection; flag non-UTF-8 |
| Row count | Line count (CSV) or sheet row count (Excel) |
| Column count | Header row length |
| Delimiter | CSV sniffer; flag if inconsistent |
| Sheet name | Excel only; note if multiple sheets |
| File size | OS-level; flag files >100MB for chunked processing |

### Column-Level Profiling

For each column, compute:

| Metric | Formula | Red Flag |
|--------|---------|----------|
| Inferred type | Most frequent parseable type | Mixed types in >5% of values |
| Null count / pct | `COUNT(*) - COUNT(col)` | >50% nulls |
| Distinct count | `COUNT(DISTINCT col)` | 1 (constant) or equals row count (potential key) |
| Cardinality ratio | `distinct / total` | Very low on expected-unique columns |
| Min/max length | `MIN(LENGTH(col))`, `MAX(LENGTH(col))` | Large variance suggests mixed formats |
| Top values | Most frequent 5 values | Reveals encoding issues, placeholder values |
| Pattern match | Regex for dates, emails, phones | Inconsistent formats within same column |

### Cross-Column Profiling

Detect relationships across columns:

| Check | Method | Action |
|-------|--------|--------|
| Duplicate rows | `GROUP BY ALL HAVING COUNT(*) > 1` | Flag count and sample |
| Candidate keys | Columns with cardinality ratio = 1.0 | Document in mapping |
| Foreign key candidates | Shared column names across files | Validate referential integrity |
| Derived columns | Correlation between column pairs | Note in mapping document |

---

## SQL Profiling Patterns for DuckDB

Basic column profile query:

```sql
SELECT
    COUNT(*) AS total_rows,
    COUNT(col) AS non_null_count,
    COUNT(*) - COUNT(col) AS null_count,
    ROUND((COUNT(*) - COUNT(col))::FLOAT / COUNT(*) * 100, 2) AS null_pct,
    COUNT(DISTINCT col) AS distinct_count,
    ROUND(COUNT(DISTINCT col)::FLOAT / COUNT(*), 4) AS cardinality_ratio,
    MIN(LENGTH(col::VARCHAR)) AS min_length,
    MAX(LENGTH(col::VARCHAR)) AS max_length
FROM read_csv_auto('data/raw/file.csv')
```

Top values query:

```sql
SELECT col, COUNT(*) AS freq
FROM read_csv_auto('data/raw/file.csv')
WHERE col IS NOT NULL
GROUP BY col
ORDER BY freq DESC
LIMIT 10
```

Duplicate detection:

```sql
SELECT *, COUNT(*) AS dup_count
FROM read_csv_auto('data/raw/file.csv')
GROUP BY ALL
HAVING COUNT(*) > 1
ORDER BY dup_count DESC
```

---

## schema_profiler.py Usage

```bash
# Basic profiling (Tier 1 / schema metadata)
python scripts/schema_profiler.py data/raw/clients.csv data/profiling/clients.json

# With sample values (Tier 2+)
python scripts/schema_profiler.py data/raw/clients.xlsx data/profiling/clients.json --include-sample 10

# Profile all files in a directory
for f in data/raw/*; do
    python scripts/schema_profiler.py "$f" "data/profiling/$(basename "$f" | sed 's/\.[^.]*$//').json"
done
```

**Input formats supported:** CSV (any delimiter, any encoding), Excel (.xlsx, .xls via openpyxl).

**Dependencies:** `pip install openpyxl chardet`

---

## Interpreting Profiling Results

### Red Flags

| Flag | Threshold | Action |
|------|-----------|--------|
| High nulls | >50% null rate | Investigate: optional field or data loss? |
| Mixed types | String column with >5% numeric values | Check for placeholder values ("N/A", "TBD") |
| PII column names | Matches: ssn, social_security, dob, date_of_birth, email, phone, address | Flag for security review, mask in Tier 2 samples |
| Encoding issues | Non-UTF-8 detected | Convert before loading; document original encoding |
| Date inconsistency | Multiple date formats in same column | Standardize in staging model |
| Constant columns | Cardinality = 1 | Drop or document reason for retention |
| High cardinality text | Cardinality ratio >0.9 on text columns | May be free-text; consider NLP or exclusion |

### Quality Scoring

Assign each column a quality score:

| Score | Criteria |
|-------|----------|
| Green | <5% nulls, consistent type, no PII flags |
| Yellow | 5-50% nulls, minor type issues, or PII flagged but handled |
| Red | >50% nulls, mixed types, unhandled PII, encoding errors |

---

## Output Format

The profiler produces JSON with this structure:

```json
{
  "file_metadata": {
    "filename": "clients.csv",
    "encoding": "utf-8",
    "row_count": 15234,
    "column_count": 12,
    "delimiter": ",",
    "file_size_bytes": 2048576
  },
  "columns": [
    {
      "name": "customer_id",
      "inferred_type": "integer",
      "null_count": 0,
      "null_pct": 0.0,
      "distinct_count": 15234,
      "cardinality_ratio": 1.0,
      "min_length": 4,
      "max_length": 6,
      "sample_values": ["1001", "1002", "1003"]
    }
  ],
  "issues": [
    {
      "column": "email",
      "issue_type": "pii_detected",
      "severity": "warning",
      "detail": "Column name matches PII pattern: email"
    }
  ]
}
```
