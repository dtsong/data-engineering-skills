# Data Quality Patterns

> Tool-agnostic patterns for ensuring data quality across pipelines, warehouses, and downstream consumers.

---

## Four Pillars

### 1. Accuracy

Data correctly represents the real-world entity or event. Measure via source reconciliation, business rule validation, statistical profiling.

### 2. Completeness

All required data present with no unexpected gaps. Track null rates, expected vs actual row counts, time series gaps.

### 3. Consistency

Data uniform across systems, follows standards. Compare cross-system counts, validate naming conventions, recalculate derived fields.

### 4. Timeliness

Data available when needed. Monitor freshness SLAs, pipeline latency, streaming lag.

---

## Key Metrics

| Metric | Formula | Threshold | Frequency |
|--------|---------|-----------|-----------|
| Freshness SLA | `now() - max(updated_at)` | < 2 hours | Every 15 min |
| Null Rate | `null_count / total_rows` | < 1% | Daily |
| Duplicate Rate | `duplicate_rows / total_rows` | < 0.1% | Daily |
| Schema Drift | `new_cols + removed_cols + type_changes` | 0 | On every load |
| Referential Integrity | `valid_fks / total_fks` | 100% | Daily |
| Row Count Variance | `abs(today - 7d_avg) / 7d_avg` | < 20% | Daily |

---

## Anomaly Detection

| Approach | Method | Best For |
|----------|--------|----------|
| Statistical | Z-score, IQR | Numeric metrics with stable distributions |
| ML-based | Isolation Forest | Complex multivariate patterns |
| Rule-based | Thresholds | Known failure modes, compliance |
| Time-series | Prophet, ARIMA | Seasonal data, trends |

### Z-Score

```sql
WITH stats AS (
  SELECT AVG(order_value) AS mean_val, STDDEV(order_value) AS std_val
  FROM orders WHERE order_date >= CURRENT_DATE - 30
)
SELECT order_id, order_value,
  ABS(order_value - s.mean_val) / s.std_val AS z_score
FROM orders o CROSS JOIN stats s
WHERE ABS(order_value - s.mean_val) / s.std_val > 3;
```

### Rule-Based

```yaml
rules:
  - name: no_negative_revenue
    sql: "SELECT COUNT(*) FROM orders WHERE revenue < 0"
    threshold: "= 0"
    severity: P0
  - name: future_dates_blocked
    sql: "SELECT COUNT(*) FROM events WHERE event_date > CURRENT_DATE"
    threshold: "= 0"
    severity: P1
```

---

## Alerting Matrix

| Severity | Condition | Route | Response |
|----------|-----------|-------|----------|
| **P0** | Pipeline halted, critical data missing | PagerDuty | < 15 min |
| **P1** | Quality drop >5%, SLA breach | Slack incidents | < 1 hour |
| **P2** | Anomaly detected, threshold warning | Slack monitoring | < 4 hours |
| **P3** | Schema drift, non-critical | Dashboard | Next business day |

---

## Quality by Pipeline Stage

### Stage 1: Source Validation

Check connectivity, expected schema, row count within range, incremental watermark advances.

```python
def validate_source(response):
    assert 'data' in response, "Missing data key"
    assert len(response['data']) > 0, "Empty data"
    assert len(response['data']) < 1_000_000, "Suspiciously high count"
```

### Stage 2: In-Flight (Transformation)

Check type conversions, join integrity (no fan-outs), aggregation correctness, deduplication.

```yaml
# dbt tests
models:
  - name: stg_orders
    tests:
      - dbt_utils.equal_rowcount:
          compare_model: source('ecom', 'raw_orders')
    columns:
      - name: order_id
        tests: [unique, not_null]
      - name: order_total
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 100000
```

### Stage 3: Post-Load Assertions

Check referential integrity, business logic constraints, materialization success.

```sql
-- Referential integrity
SELECT COUNT(*) AS orphans FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;  -- Expect: 0
```

### Stage 4: Consumer Validation

Reconcile report totals to source, verify metric definitions match business logic.

---

## Implementation by Tool

### dbt

```yaml
models:
  - name: fct_orders
    tests:
      - dbt_utils.recency:
          datepart: hour
          field: created_at
          interval: 2
      - dbt_expectations.expect_table_row_count_to_be_between:
          min_value: 1000
          max_value: 100000
```

### Python (Pandera)

```python
import pandera as pa

schema = pa.DataFrameSchema({
    "order_id": pa.Column(int, pa.Check.greater_than(0), unique=True),
    "order_total": pa.Column(float, pa.Check.in_range(0, 1000000)),
    "order_date": pa.Column(pa.DateTime),
})
df = schema.validate(df)
```

### SQL (Universal)

```sql
-- Custom monitoring table
INSERT INTO data_quality_metrics
SELECT
  'freshness_minutes', 'orders',
  DATEDIFF('minute', MAX(updated_at), CURRENT_TIMESTAMP()),
  120,
  CASE WHEN DATEDIFF('minute', MAX(updated_at), CURRENT_TIMESTAMP()) > 120
       THEN 'fail' ELSE 'pass' END,
  CURRENT_TIMESTAMP(), NULL
FROM orders;
```
