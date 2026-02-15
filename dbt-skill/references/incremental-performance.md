## Contents

- [Strategy Decision Matrix](#strategy-decision-matrix)
- [Microbatch (dbt 1.9+)](#microbatch-dbt-19)
- [Traditional Patterns](#traditional-patterns)
  - [Merge (Default)](#merge-default)
  - [is_incremental() Patterns](#is_incremental-patterns)
  - [on_schema_change](#on_schema_change)
- [Full Refresh](#full-refresh)
- [Snowflake Performance](#snowflake-performance)
- [BigQuery Performance](#bigquery-performance)
- [Query Optimization](#query-optimization)
- [Cost Monitoring](#cost-monitoring)

---

# Incremental Models & Performance

> **Part of:** [dbt-skill](../SKILL.md)

## Strategy Decision Matrix

| Strategy | How It Works | Best For | Snowflake | BigQuery |
|----------|-------------|----------|-----------|----------|
| `microbatch` (1.9+) | Time-based batches processed independently | Event/time-series data | Yes | Yes |
| `merge` | MERGE with unique_key | Most use cases, upserts | Default | Default |
| `delete+insert` | Delete matching rows, then insert | When merge is expensive | Yes | No |
| `insert_overwrite` | Replace entire partitions | Partition-aligned events | No | Yes |
| `append` | Insert only, no updates | Immutable event logs | Yes | Yes |

**Decision flow:** Time-series? If rows never update: `insert_overwrite` (BQ) / `microbatch` (SF). If rows update: `microbatch` (1.9+) or `merge` with lookback. Non-time-series with unique key: `merge` (BQ) / `delete+insert` (SF). No unique key: `append`.

## Microbatch (dbt 1.9+)

Processes data in discrete time batches. Each batch runs independently -- enables parallel execution and targeted retries. No `{% if is_incremental() %}` block needed.

```sql
{{ config(
    materialized='incremental',
    incremental_strategy='microbatch',
    event_time='event_occurred_at',
    begin='2023-01-01',
    batch_size='day',
    unique_key='event_id',
    lookback=3              -- Reprocess 3 prior days for late-arriving data
) }}

select event_id, user_id, event_type, event_occurred_at
from {{ ref('stg_app__events') }}
```

| Config | Required | Description |
|--------|----------|-------------|
| `event_time` | Yes | Timestamp column for batch slicing |
| `begin` | Yes | Earliest date to process (ISO format) |
| `batch_size` | Yes | `'hour'`, `'day'`, `'month'`, `'year'` |
| `lookback` | No | Extra prior batches to reprocess (default: 0) |

**Batch size:** `hour` for >10M rows/day, `day` for 100K-10M (most common), `month` for <100K.

```bash
dbt run -s fct_app_events                              # processes latest batch(es)
dbt retry                                              # re-runs only failed batches
dbt run -s fct_app_events --event-time-start 2024-03-01 --event-time-end 2024-03-15  # targeted backfill
```

## Traditional Patterns

### Merge (Default)

```sql
{{ config(materialized='incremental', unique_key='order_id', on_schema_change='append_new_columns') }}

select order_id, customer_id, order_status, order_total, updated_at
from {{ ref('stg_shopify__orders') }}
{% if is_incremental() %}
where updated_at > (select max(updated_at) from {{ this }})
{% endif %}
```

Compound key: `unique_key=['order_id', 'line_item_id']`.

### is_incremental() Patterns

```sql
-- High-watermark (most common)
{% if is_incremental() %}
where updated_at > (select max(updated_at) from {{ this }})
{% endif %}

-- Lookback for late-arriving data (Snowflake)
{% if is_incremental() %}
where event_at > (select dateadd(hour, -3, max(event_at)) from {{ this }})
{% endif %}

-- BigQuery equivalent
{% if is_incremental() %}
where event_at > (select timestamp_sub(max(event_at), interval 3 hour) from {{ this }})
{% endif %}
```

`is_incremental()` returns true only when: materialized as incremental AND target table exists AND not `--full-refresh` AND not first run.

### on_schema_change

| Setting | Behavior | Use When |
|---------|----------|----------|
| `ignore` (default) | Skip new columns | Stable schema |
| `append_new_columns` | Add new columns (nulls for existing) | Evolving sources (recommended) |
| `sync_all_columns` | Add/remove columns to match | Dev/experimentation |
| `fail` | Error on any change | Strict CI |

## Full Refresh

```bash
dbt run --full-refresh -s fct_orders      # single model
dbt run --full-refresh -s fct_orders+     # model + downstream
```

Trigger when: schema changed, logic changed, data quality issue, source reloaded, or switching strategies.

## Snowflake Performance

- **Cluster keys:** Add on tables >1TB with slow filtered queries. Use most-filtered columns first: `cluster_by=['event_date', 'user_id']`.
- **Transient tables:** `transient: true` skips 7-day fail-safe, saves storage. Use for rebuildable models.
- **Dynamic tables:** `materialized='dynamic_table', target_lag='5 minutes'` for near-real-time. Use when transforms are straightforward SQL within same account.
- **Warehouse sizing:** X-SMALL for dev/CI, SMALL-MEDIUM for prod light, LARGE+ for heavy incremental.

## BigQuery Performance

- **Partitioning:** Required for large tables. `partition_by={"field": "order_date", "data_type": "date", "granularity": "day"}`.
- **Clustering:** Up to 4 columns: `cluster_by=['user_id', 'event_type']`. Choose high-cardinality WHERE/JOIN columns.
- **require_partition_filter:** `true` for large fact tables to prevent full scans.
- **maximum_bytes_billed:** Safety limit per model, e.g., `1000000000000` (1 TB).
- **insert_overwrite:** Use `copy_partitions: true` for faster partition replacement.

## Query Optimization

- **Filter before join:** Apply WHERE clauses in CTEs before joining to reduce volume.
- **Column pruning:** Select only needed columns. Critical in BigQuery (bytes billed per column).
- **Extract heavy CTEs:** If a CTE is referenced 3+ times, make it an intermediate model.
- **Window functions:** Always PARTITION BY a high-cardinality column to limit sort scope.
- **No SELECT * in downstream models:** Breaks `on_schema_change` behavior; list columns explicitly.

## Cost Monitoring

| Metric | Warning | Critical |
|--------|---------|----------|
| Daily credits/TB billed | >120% baseline | >200% baseline |
| Query queue time | >5 min avg | >15 min avg |
| Model runtime | >2x historical avg | >5x historical avg |

Tag models in `dbt_project.yml` with `+tags: ['finance']` for cost attribution. Use Snowflake `query_tag` or BigQuery `INFORMATION_SCHEMA.JOBS` for per-model cost tracking.

---

**Back to:** [Main Skill File](../SKILL.md)
