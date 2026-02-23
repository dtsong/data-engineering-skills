> **Part of:** [data-observability](../SKILL.md)

# Freshness Monitoring Patterns

Configurations and queries for detecting stale data in pipelines. Freshness is the highest-priority observability pillar — stale data silently corrupts every downstream consumer.

## dbt Source Freshness Configuration

Define freshness SLAs in `sources.yml`:

```yaml
# models/staging/sources.yml
version: 2

sources:
  - name: raw_orders
    database: analytics
    schema: raw
    freshness:
      warn_after: {count: 12, period: hour}
      error_after: {count: 24, period: hour}
    loaded_at_field: _etl_loaded_at
    tables:
      - name: orders
      - name: order_items
      - name: customers
        freshness:
          # Override: customers refresh weekly
          warn_after: {count: 8, period: day}
          error_after: {count: 14, period: day}
```

**Run freshness check:**
```bash
dbt source freshness --select source:raw_orders
```

---

## Custom Freshness Queries (No loaded_at_field)

When the source table lacks a reliable `loaded_at` field, use `max(event_timestamp)`:

```sql
-- Freshness check: time since most recent record
SELECT
    'raw_orders.orders' AS source_table,
    MAX(order_date) AS last_record_ts,
    NOW() - MAX(order_date) AS staleness,
    CASE
        WHEN NOW() - MAX(order_date) > INTERVAL '24 hours' THEN 'ERROR'
        WHEN NOW() - MAX(order_date) > INTERVAL '12 hours' THEN 'WARN'
        ELSE 'OK'
    END AS freshness_status
FROM raw.orders;
```

**Multi-table freshness dashboard:**
```sql
-- Check freshness across all critical sources
WITH freshness_checks AS (
    SELECT 'orders' AS table_name, MAX(order_date) AS last_ts FROM raw.orders
    UNION ALL
    SELECT 'customers', MAX(updated_at) FROM raw.customers
    UNION ALL
    SELECT 'payments', MAX(payment_date) FROM raw.payments
)
SELECT
    table_name,
    last_ts,
    NOW() - last_ts AS staleness,
    CASE
        WHEN NOW() - last_ts > INTERVAL '24 hours' THEN 'ERROR'
        WHEN NOW() - last_ts > INTERVAL '12 hours' THEN 'WARN'
        ELSE 'OK'
    END AS status
FROM freshness_checks
ORDER BY staleness DESC;
```

---

## Freshness SLA Definitions

Define SLAs based on business requirements, not technical defaults:

| Source Type | Warn Threshold | Error Threshold | Rationale |
|-------------|---------------|-----------------|-----------|
| Transactional (orders, payments) | 12 hours | 24 hours | Daily dashboards depend on T-1 data |
| Reference (customers, products) | 3 days | 7 days | Slowly changing dimensions |
| Event streams (clicks, pageviews) | 1 hour | 4 hours | Real-time dashboards |
| Third-party APIs | 24 hours | 48 hours | Vendor SLAs are unreliable |
| Weekly batch loads | 8 days | 14 days | Aligned to load schedule + buffer |

**SLA definition template:**
```yaml
# observability/freshness_slas.yml
freshness_slas:
  - source: raw_orders.orders
    warn_after_hours: 12
    error_after_hours: 24
    owner: data-team
    escalation: "#data-alerts"
  - source: raw_orders.customers
    warn_after_hours: 72
    error_after_hours: 168
    owner: data-team
    escalation: "#data-alerts"
```

---

## Stale Data Detection Patterns

Detect data that loads successfully but contains outdated records:

```sql
-- Detect loads where max date hasn't advanced
WITH daily_max AS (
    SELECT
        DATE(loaded_at) AS load_date,
        MAX(order_date) AS max_record_date
    FROM raw.orders
    GROUP BY DATE(loaded_at)
)
SELECT
    load_date,
    max_record_date,
    LAG(max_record_date) OVER (ORDER BY load_date) AS prev_max_date,
    CASE
        WHEN max_record_date = LAG(max_record_date) OVER (ORDER BY load_date)
        THEN 'STALE_LOAD'
        ELSE 'OK'
    END AS load_status
FROM daily_max
ORDER BY load_date DESC
LIMIT 14;
```

---

## DuckDB-Based Freshness Checks (Local Development)

Run freshness checks locally against Parquet or CSV files:

```sql
-- DuckDB freshness check for local files
SELECT
    'sales_data' AS source,
    MAX(order_date) AS last_record,
    CURRENT_TIMESTAMP - MAX(order_date) AS staleness,
    CASE
        WHEN CURRENT_TIMESTAMP - MAX(order_date) > INTERVAL '48 hours' THEN 'STALE'
        ELSE 'FRESH'
    END AS status
FROM read_parquet('data/raw/sales_*.parquet');
```

**Batch freshness for multiple files:**
```sql
-- Check all Parquet files in a directory
SELECT
    filename AS source_file,
    MAX(event_timestamp) AS last_event,
    CURRENT_TIMESTAMP - MAX(event_timestamp) AS staleness
FROM read_parquet('data/raw/*.parquet', filename=true)
GROUP BY filename
ORDER BY staleness DESC;
```
