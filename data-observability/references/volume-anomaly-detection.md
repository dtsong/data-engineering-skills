> **Part of:** [data-observability](../SKILL.md)

# Volume Anomaly Detection Patterns

Queries and configurations for detecting unexpected changes in data volume. A sudden drop to zero rows is obvious; a 30% decline over a week is not — both need detection.

## Row Count Tracking (Daily/Hourly Baselines)

Establish baselines before setting thresholds:

```sql
-- Daily row count history (last 90 days)
CREATE OR REPLACE TABLE volume_baseline AS
SELECT
    DATE(loaded_at) AS load_date,
    COUNT(*) AS row_count,
    AVG(COUNT(*)) OVER (ORDER BY DATE(loaded_at) ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS rolling_7d_avg,
    AVG(COUNT(*)) OVER (ORDER BY DATE(loaded_at) ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS rolling_30d_avg
FROM raw.orders
GROUP BY DATE(loaded_at)
ORDER BY load_date DESC;
```

**Hourly variant for high-frequency sources:**
```sql
SELECT
    DATE_TRUNC('hour', loaded_at) AS load_hour,
    COUNT(*) AS row_count
FROM raw.events
GROUP BY DATE_TRUNC('hour', loaded_at)
ORDER BY load_hour DESC
LIMIT 168;  -- last 7 days of hourly data
```

---

## Sudden Drop/Spike Detection

Flag loads that deviate significantly from baseline:

```sql
-- Percentage deviation from 7-day rolling average
WITH daily_counts AS (
    SELECT
        DATE(loaded_at) AS load_date,
        COUNT(*) AS row_count
    FROM raw.orders
    GROUP BY DATE(loaded_at)
),
with_baseline AS (
    SELECT
        load_date,
        row_count,
        AVG(row_count) OVER (ORDER BY load_date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS baseline_avg,
        STDDEV(row_count) OVER (ORDER BY load_date ROWS BETWEEN 7 PRECEDING AND 1 PRECEDING) AS baseline_std
    FROM daily_counts
)
SELECT
    load_date,
    row_count,
    ROUND(baseline_avg) AS baseline,
    ROUND(100.0 * (row_count - baseline_avg) / NULLIF(baseline_avg, 0), 1) AS pct_deviation,
    CASE
        WHEN row_count = 0 THEN 'ZERO_ROWS'
        WHEN row_count < baseline_avg * 0.5 THEN 'SEVERE_DROP'
        WHEN row_count < baseline_avg * 0.7 THEN 'DROP'
        WHEN row_count > baseline_avg * 2.0 THEN 'SEVERE_SPIKE'
        WHEN row_count > baseline_avg * 1.5 THEN 'SPIKE'
        ELSE 'NORMAL'
    END AS volume_status
FROM with_baseline
ORDER BY load_date DESC
LIMIT 30;
```

**Recommended thresholds:**

| Status | Condition | Severity | Action |
|--------|-----------|----------|--------|
| ZERO_ROWS | count = 0 | P0 | Immediate alert, page on-call |
| SEVERE_DROP | < 50% of baseline | P1 | Alert + investigate |
| DROP | < 70% of baseline | P2 | Warning, investigate within SLA |
| SPIKE | > 150% of baseline | P2 | Warning, check for duplicates |
| SEVERE_SPIKE | > 200% of baseline | P1 | Alert, likely duplicate load |
| NORMAL | 70-150% of baseline | -- | No action |

---

## Zero-Row Detection (Empty Load Detection)

Catch completely empty loads that succeed silently:

```sql
-- dbt test: assert row count > 0
-- tests/generic/assert_row_count_positive.sql
{% test assert_row_count_positive(model) %}
SELECT 1
WHERE (SELECT COUNT(*) FROM {{ model }}) = 0
{% endtest %}
```

**Standalone SQL check:**
```sql
SELECT
    'raw.orders' AS table_name,
    COUNT(*) AS total_rows,
    COUNT(*) FILTER (WHERE DATE(loaded_at) = CURRENT_DATE) AS today_rows,
    CASE
        WHEN COUNT(*) FILTER (WHERE DATE(loaded_at) = CURRENT_DATE) = 0
        THEN 'ALERT: Zero rows loaded today'
        ELSE 'OK'
    END AS status
FROM raw.orders;
```

---

## dbt Volume Tests (Custom Generic Tests)

```yaml
# models/staging/schema.yml
version: 2

models:
  - name: stg_orders
    tests:
      - assert_row_count_positive
      - row_count_anomaly:
          baseline_days: 7
          drop_threshold: 0.5
          spike_threshold: 2.0
```

**Custom generic test macro:**
```sql
-- macros/tests/row_count_anomaly.sql
{% test row_count_anomaly(model, baseline_days=7, drop_threshold=0.5, spike_threshold=2.0) %}
WITH baseline AS (
    SELECT AVG(cnt) AS avg_count
    FROM (
        SELECT DATE(_loaded_at) AS dt, COUNT(*) AS cnt
        FROM {{ model }}
        WHERE _loaded_at >= CURRENT_DATE - {{ baseline_days }}
        GROUP BY DATE(_loaded_at)
    )
),
today AS (
    SELECT COUNT(*) AS cnt
    FROM {{ model }}
    WHERE DATE(_loaded_at) = CURRENT_DATE
)
SELECT 1
FROM today CROSS JOIN baseline
WHERE today.cnt < baseline.avg_count * {{ drop_threshold }}
   OR today.cnt > baseline.avg_count * {{ spike_threshold }}
{% endtest %}
```

---

## Seasonal Adjustment for Volume Checks

Account for known patterns (weekends, holidays, month-end):

```sql
-- Day-of-week seasonal baseline
WITH daily_counts AS (
    SELECT
        DATE(loaded_at) AS load_date,
        DAYOFWEEK(DATE(loaded_at)) AS dow,
        COUNT(*) AS row_count
    FROM raw.orders
    WHERE loaded_at >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY DATE(loaded_at)
),
dow_baseline AS (
    SELECT
        dow,
        AVG(row_count) AS dow_avg,
        STDDEV(row_count) AS dow_std
    FROM daily_counts
    GROUP BY dow
)
SELECT
    d.load_date,
    d.row_count,
    ROUND(b.dow_avg) AS dow_baseline,
    ROUND(100.0 * (d.row_count - b.dow_avg) / NULLIF(b.dow_avg, 0), 1) AS pct_deviation
FROM daily_counts d
JOIN dow_baseline b ON d.dow = b.dow
WHERE d.load_date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY d.load_date DESC;
```

**When to use seasonal adjustment:**
- Weekday/weekend patterns (retail, B2C)
- Month-end spikes (financial data)
- Holiday dips (corporate systems)
- Quarter-end surges (enterprise SaaS)
