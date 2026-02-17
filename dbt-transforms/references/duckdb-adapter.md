## Contents

- [Setup](#setup)
- [External File Reading](#external-file-reading)
- [DuckDB-Specific SQL Functions](#duckdb-specific-sql-functions)
- [Export Patterns](#export-patterns)
- [DuckDB vs Snowflake SQL Differences](#duckdb-vs-snowflake-sql-differences)
- [Dev-to-Prod Portability](#dev-to-prod-portability)

---

# DuckDB Adapter

> **Part of:** [dbt-transforms](../SKILL.md)

## Setup

Install the adapter:

```bash
pip install dbt-duckdb
```

Minimal `profiles.yml`:

```yaml
my_project:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "target/dev.duckdb"    # persistent file; use :memory: for ephemeral
      threads: 4
```

For in-memory-only mode (no file on disk):

```yaml
    dev:
      type: duckdb
      path: ":memory:"
```

## External File Reading

dbt-duckdb reads external files directly as sources. Define them in `_sources.yml`:

```yaml
sources:
  - name: external
    schema: main
    tables:
      - name: raw_customers
        meta:
          external_location: "data/customers.csv"
      - name: raw_events
        meta:
          external_location: "data/events/*.parquet"
```

Or use DuckDB functions inline (less portable but useful for ad hoc work):

```sql
-- staging model reading CSV directly
with source as (
    select * from read_csv_auto('data/customers.csv')
)
select * from source
```

| Function | File Types | Auto-Detect | Glob Support |
|----------|-----------|-------------|--------------|
| `read_csv_auto()` | CSV, TSV | delimiter, header, types | Yes |
| `read_parquet()` | Parquet | schema from metadata | Yes |
| `read_json_auto()` | JSON, NDJSON | structure, types | Yes |

### Glob Patterns

```sql
-- Read all CSV files in a directory
select * from read_csv_auto('data/sales/*.csv', union_by_name=true)

-- Read partitioned Parquet (Hive-style)
select * from read_parquet('data/events/**/*.parquet', hive_partitioning=true)
```

## DuckDB-Specific SQL Functions

Functions commonly used for cleaning and transformation:

| Function | Purpose | Example |
|----------|---------|---------|
| `regexp_replace(col, pattern, repl)` | Regex substitution | `regexp_replace(phone, '[^0-9]', '', 'g')` |
| `regexp_extract(col, pattern, grp)` | Regex capture group | `regexp_extract(url, 'utm_source=([^&]+)', 1)` |
| `strftime(col, fmt)` | Date formatting | `strftime(created_at, '%Y-%m-%d')` |
| `strptime(col, fmt)` | String to timestamp | `strptime(date_str, '%m/%d/%Y')` |
| `list_aggregate(col, fn)` | Aggregate list values | `list_aggregate(tags, 'string_agg', ',')` |
| `unnest(col)` | Flatten arrays | `select unnest(items) from orders` |
| `struct_extract(col, key)` | Access struct fields | `struct_extract(address, 'city')` |
| `try_cast(col as type)` | Safe type casting | `try_cast(amount as decimal(10,2))` |

### List and Struct Operations

DuckDB has native list/struct types (unlike most warehouses):

```sql
select
    order_id
    , list_aggregate(item_prices, 'sum') as total_price
    , len(items) as item_count
from {{ ref('stg_shop__orders') }}
```

## Export Patterns

Export query results to files directly from dbt models using post-hooks or custom macros.

```sql
-- Export to CSV
COPY (select * from {{ ref('fct_orders') }}) TO 'output/orders.csv' (HEADER, DELIMITER ',');

-- Export to Parquet (much smaller, faster for downstream)
COPY (select * from {{ ref('fct_orders') }}) TO 'output/orders.parquet' (FORMAT PARQUET);

-- Export to JSON (newline-delimited)
COPY (select * from {{ ref('dim_customers') }}) TO 'output/customers.json' (FORMAT JSON);
```

Use a post-hook macro for automated exports:

```yaml
# dbt_project.yml
models:
  my_project:
    marts:
      +post-hook:
        - "COPY (select * from {{ this }}) TO 'output/{{ this.name }}.parquet' (FORMAT PARQUET)"
```

## DuckDB vs Snowflake SQL Differences

| Feature | DuckDB | Snowflake |
|---------|--------|-----------|
| **String concat** | `||` or `concat()` | `||` or `concat()` |
| **Safe cast** | `try_cast()` | `try_cast()` |
| **Regex replace** | `regexp_replace(col, pat, rep, flags)` | `regexp_replace(col, pat, rep)` |
| **Date trunc** | `date_trunc('month', col)` | `date_trunc('month', col)` |
| **Array type** | Native `LIST` | `ARRAY` |
| **Struct type** | Native `STRUCT` | `OBJECT` |
| **Flatten array** | `unnest()` | `lateral flatten()` |
| **IFF/IF** | `if(cond, a, b)` | `iff(cond, a, b)` |
| **QUALIFY** | Supported | Supported |
| **ILIKE** | Supported | Supported |
| **MERGE** | Supported (0.9+) | Supported |
| **Variant/JSON** | Native JSON type | `VARIANT` |
| **Sequence** | `generate_series()` | `generator()` + `seq4()` |

### Portability Tips

Write warehouse-agnostic SQL where possible. Use macros to abstract differences:

```sql
-- macro: flatten_array.sql
{% macro flatten_array(array_col) %}
  {% if target.type == 'duckdb' %}
    unnest({{ array_col }})
  {% elif target.type == 'snowflake' %}
    lateral flatten(input => {{ array_col }})
  {% endif %}
{% endmacro %}
```

## Dev-to-Prod Portability

Use DuckDB for fast local development, warehouse target for production.

### Profile Configuration

```yaml
my_project:
  target: dev
  outputs:
    dev:
      type: duckdb
      path: "target/dev.duckdb"
      threads: 4
    prod:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      role: transformer
      database: analytics
      warehouse: transforming
      schema: public
      threads: 8
```

### Workflow

1. Develop locally with `dbt run --target dev` (DuckDB -- instant feedback).
2. Run tests with `dbt test --target dev`.
3. CI runs `dbt build --target dev` for fast validation.
4. Deploy to production with `dbt run --target prod` (Snowflake).

### Portability Checklist

- Avoid DuckDB-only functions in models (or wrap in `target.type` macros).
- Use `source()` external locations for DuckDB; warehouse sources for prod.
- Test on both targets in CI if budget allows.
- Keep seed data small (DuckDB loads seeds from CSV automatically).
