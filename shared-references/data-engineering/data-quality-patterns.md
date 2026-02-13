# Data Quality Patterns

> Tool-agnostic patterns for ensuring data quality across pipelines, warehouses, and downstream consumers.

This reference provides frameworks and patterns that apply regardless of your specific tooling choices. Use these patterns to build robust data quality practices in dbt, Python pipelines, SQL workflows, or streaming systems.

---

## Four Pillars of Data Quality

### 1. Accuracy

**Definition**: Data correctly represents the real-world entity or event it describes.

**Measurement Approaches**:
- Source reconciliation (compare row counts, aggregates)
- Business rule validation (valid ranges, formats, relationships)
- Statistical profiling (distribution analysis, outlier detection)
- External validation (third-party data sources)

**Example Metrics**:
```yaml
metrics:
  - name: revenue_reconciliation_rate
    formula: warehouse_revenue / source_revenue
    threshold: ">= 0.999"

  - name: email_format_validity_rate
    formula: valid_email_count / total_email_count
    threshold: ">= 0.95"

  - name: referential_integrity_score
    formula: valid_foreign_keys / total_foreign_keys
    threshold: "= 1.0"
```

### 2. Completeness

**Definition**: All required data is present with no unexpected gaps or nulls.

**Measurement Approaches**:
- Null rate tracking by column
- Expected vs actual row count comparison
- Time series gap detection
- Required field presence validation

**Example Metrics**:
```yaml
metrics:
  - name: critical_field_null_rate
    formula: null_count / total_rows
    threshold: "< 0.01"
    critical_fields: [user_id, event_timestamp, product_id]

  - name: daily_record_completeness
    formula: actual_days_with_data / expected_days
    threshold: ">= 0.99"

  - name: record_volume_stability
    formula: abs(today_count - 7day_avg) / 7day_avg
    threshold: "< 0.20"
```

### 3. Consistency

**Definition**: Data is uniform across systems, doesn't contradict itself, and follows defined standards.

**Measurement Approaches**:
- Cross-system comparison (source vs warehouse vs mart)
- Field-level standardization checks
- Historical consistency validation
- Derived field recalculation

**Example Metrics**:
```yaml
metrics:
  - name: cross_system_order_count_match
    formula: abs(shopify_orders - warehouse_orders) / shopify_orders
    threshold: "< 0.001"

  - name: naming_convention_adherence
    formula: compliant_field_names / total_field_names
    threshold: ">= 0.95"

  - name: derived_field_accuracy
    formula: recalculated_total = stored_total
    threshold: "= 1.0"
    example: "total_price = quantity * unit_price"
```

### 4. Timeliness

**Definition**: Data is available when needed and reflects the current state appropriately.

**Measurement Approaches**:
- Freshness SLA monitoring (time since last update)
- Pipeline latency tracking (source extraction to warehouse load)
- Streaming lag measurement (event time vs processing time)
- Update frequency validation

**Example Metrics**:
```yaml
metrics:
  - name: table_freshness_sla
    formula: now() - max(updated_at)
    threshold: "< 2 hours"
    critical_tables: [orders, customers, inventory]

  - name: pipeline_end_to_end_latency
    formula: warehouse_load_time - source_extraction_time
    threshold: "< 30 minutes"

  - name: streaming_lag
    formula: processing_time - event_time
    threshold: "< 60 seconds"
```

---

## Anomaly Detection Approaches

| Approach | Method | Complexity | Accuracy | Setup Cost | Best For |
|----------|--------|------------|----------|------------|----------|
| **Statistical** | Z-score, IQR, moving average | Low | Medium | Low | Numeric metrics with stable distributions |
| **ML-based** | Isolation Forest, Autoencoders | High | High | High | Complex multivariate patterns |
| **Rule-based** | Thresholds, business rules | Low | Low-Medium | Low | Known failure modes, compliance |
| **Time-series** | Prophet, ARIMA, seasonal decomposition | Medium | High | Medium | Seasonal data, trends |

### Statistical Anomaly Detection

**Z-Score Method**:
```sql
-- Flag records more than 3 standard deviations from mean
WITH stats AS (
  SELECT
    AVG(order_value) AS mean_value,
    STDDEV(order_value) AS std_value
  FROM orders
  WHERE order_date >= CURRENT_DATE - 30
)
SELECT
  o.order_id,
  o.order_value,
  ABS(o.order_value - s.mean_value) / s.std_value AS z_score,
  CASE
    WHEN ABS(o.order_value - s.mean_value) / s.std_value > 3
    THEN 'anomaly'
    ELSE 'normal'
  END AS status
FROM orders o
CROSS JOIN stats s
WHERE o.order_date = CURRENT_DATE;
```

**IQR (Interquartile Range) Method**:
```sql
-- Flag records outside 1.5 * IQR from quartiles
WITH quartiles AS (
  SELECT
    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY revenue) AS q1,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY revenue) AS q3
  FROM daily_revenue
  WHERE date >= CURRENT_DATE - 90
),
bounds AS (
  SELECT
    q1,
    q3,
    q3 - q1 AS iqr,
    q1 - 1.5 * (q3 - q1) AS lower_bound,
    q3 + 1.5 * (q3 - q1) AS upper_bound
  FROM quartiles
)
SELECT
  dr.date,
  dr.revenue,
  b.lower_bound,
  b.upper_bound,
  CASE
    WHEN dr.revenue < b.lower_bound OR dr.revenue > b.upper_bound
    THEN 'anomaly'
    ELSE 'normal'
  END AS status
FROM daily_revenue dr
CROSS JOIN bounds b
WHERE dr.date >= CURRENT_DATE - 7;
```

### ML-Based Anomaly Detection

**When to use**:
- Multivariate patterns (multiple features interact)
- Unknown anomaly types
- Complex seasonal patterns
- High-stakes applications where accuracy matters

**Example implementation** (Python with scikit-learn):
```python
from sklearn.ensemble import IsolationForest
import pandas as pd

# Load metrics
df = pd.read_sql("""
  SELECT date, row_count, null_rate, avg_value, max_value
  FROM daily_table_metrics
  WHERE date >= CURRENT_DATE - 90
""", conn)

# Train isolation forest
model = IsolationForest(contamination=0.05, random_state=42)
df['anomaly'] = model.fit_predict(df[['row_count', 'null_rate', 'avg_value', 'max_value']])

# -1 indicates anomaly, 1 indicates normal
anomalies = df[df['anomaly'] == -1]
```

### Rule-Based Detection

**When to use**:
- Known failure modes (e.g., "orders should never be negative")
- Compliance requirements (e.g., "PII must be masked")
- Business logic validation (e.g., "discount < list_price")

**Example rules**:
```yaml
rules:
  - name: no_negative_revenue
    sql: "SELECT COUNT(*) FROM orders WHERE revenue < 0"
    threshold: "= 0"
    severity: P0

  - name: future_dates_not_allowed
    sql: "SELECT COUNT(*) FROM events WHERE event_date > CURRENT_DATE"
    threshold: "= 0"
    severity: P1

  - name: discount_less_than_price
    sql: "SELECT COUNT(*) FROM products WHERE discount_price >= list_price"
    threshold: "< 10"
    severity: P2
```

---

## Data Quality Metrics Framework

### Key Metrics to Track

| Metric | Formula | Typical Threshold | Tracking Frequency |
|--------|---------|-------------------|-------------------|
| **Freshness SLA** | `now() - max(updated_at)` | < 2 hours | Every 15 min |
| **Null Rate** | `null_count / total_rows` | < 1% | Daily |
| **Duplicate Rate** | `duplicate_rows / total_rows` | < 0.1% | Daily |
| **Schema Drift Count** | `new_columns + removed_columns + type_changes` | 0 | On every load |
| **Referential Integrity Score** | `valid_foreign_keys / total_foreign_keys` | 100% | Daily |
| **Row Count Variance** | `abs(today - 7day_avg) / 7day_avg` | < 20% | Daily |
| **Value Distribution Shift** | `KL_divergence(today, baseline)` | < 0.1 | Weekly |

### Exposing Metrics

**Option 1: dbt Metrics**
```yaml
# models/metrics/data_quality_metrics.yml
metrics:
  - name: orders_freshness_minutes
    label: Orders Table Freshness (minutes)
    model: ref('stg_orders')
    calculation_method: derived
    expression: "DATEDIFF('minute', MAX(updated_at), CURRENT_TIMESTAMP())"
    timestamp: updated_at
    time_grains: [day, week, month]

  - name: customers_null_rate
    label: Customer Email Null Rate
    model: ref('stg_customers')
    calculation_method: derived
    expression: "SUM(CASE WHEN email IS NULL THEN 1 ELSE 0 END) * 1.0 / COUNT(*)"
    timestamp: created_at
    time_grains: [day, week, month]
```

**Option 2: Custom Monitoring Table**
```sql
CREATE TABLE data_quality_metrics (
  metric_name VARCHAR,
  table_name VARCHAR,
  metric_value FLOAT,
  threshold_value FLOAT,
  status VARCHAR, -- 'pass', 'warn', 'fail'
  measured_at TIMESTAMP,
  details JSON
);

-- Insert freshness metric
INSERT INTO data_quality_metrics
SELECT
  'freshness_minutes' AS metric_name,
  'orders' AS table_name,
  DATEDIFF('minute', MAX(updated_at), CURRENT_TIMESTAMP()) AS metric_value,
  120 AS threshold_value, -- 2 hours
  CASE
    WHEN DATEDIFF('minute', MAX(updated_at), CURRENT_TIMESTAMP()) > 120 THEN 'fail'
    WHEN DATEDIFF('minute', MAX(updated_at), CURRENT_TIMESTAMP()) > 90 THEN 'warn'
    ELSE 'pass'
  END AS status,
  CURRENT_TIMESTAMP() AS measured_at,
  OBJECT_CONSTRUCT('last_updated', MAX(updated_at)) AS details
FROM orders;
```

**Option 3: Streaming Metrics (Kafka/Flink)**
```python
# Emit metrics to monitoring system
from datadog import statsd

# Track lag
lag_seconds = (processing_time - event_time).total_seconds()
statsd.gauge('kafka.consumer.lag_seconds', lag_seconds, tags=['topic:orders'])

# Track throughput
statsd.increment('kafka.messages.processed', tags=['topic:orders'])

# Track null rate
if record['email'] is None:
    statsd.increment('data_quality.null_count', tags=['field:email'])
```

---

## Alerting Matrix

| Severity | Condition | Action | Example | Response Time |
|----------|-----------|--------|---------|---------------|
| **P0** | Pipeline halted, critical data missing | Page on-call engineer immediately | "Orders table not updated in 4 hours" | < 15 min |
| **P1** | Data quality drop >5%, SLA breach | Alert team channel, create incident | "Revenue reconciliation at 94% (threshold 99%)" | < 1 hour |
| **P2** | Anomaly detected, threshold warning | Notify in channel, log for review | "Daily order count 25% below 7-day average" | < 4 hours |
| **P3** | Informational drift, non-critical | Log to dashboard, weekly review | "New column detected in source schema" | Next business day |

### Alert Routing Logic

```yaml
alert_rules:
  - name: critical_table_freshness
    condition: "freshness > 4 hours"
    tables: [orders, payments, inventory]
    severity: P0
    route: pagerduty

  - name: data_quality_sla_breach
    condition: "accuracy_score < 0.95"
    tables: [revenue_daily, customers]
    severity: P1
    route: slack_incidents

  - name: anomaly_detection
    condition: "z_score > 3"
    tables: [all]
    severity: P2
    route: slack_monitoring

  - name: schema_drift
    condition: "column_count_change != 0"
    tables: [all]
    severity: P3
    route: dashboard_only
```

---

## Quality by Pipeline Stage

### Stage 1: Source Validation (at extraction)

**What to check**:
- Source system connectivity
- Expected schema present
- Row count within normal range
- Incremental load watermark advances

**Example checks**:
```python
# In Fivetran/Airbyte custom connector or extraction script
def validate_source(api_response):
    assert 'data' in api_response, "Missing data key in API response"
    assert len(api_response['data']) > 0, "Empty data array"
    assert 'id' in api_response['data'][0], "Missing required field: id"

    # Row count sanity check
    row_count = len(api_response['data'])
    assert row_count < 1_000_000, f"Suspiciously high row count: {row_count}"
```

### Stage 2: In-Flight Checks (during transformation)

**What to check**:
- Data type conversions successful
- Join integrity (no unexpected fan-outs)
- Aggregation logic correctness
- Deduplication effectiveness

**Example checks** (dbt):
```yaml
# models/staging/stg_orders.yml
models:
  - name: stg_orders
    tests:
      - dbt_utils.equal_rowcount:
          compare_model: source('ecom', 'raw_orders')
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: order_total
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              max_value: 100000
```

### Stage 3: Warehouse Assertions (post-load)

**What to check**:
- Referential integrity maintained
- Business logic constraints satisfied
- Historical data unchanged (SCD Type 2 integrity)
- Materialization successful

**Example checks**:
```sql
-- Referential integrity check
SELECT
  'orders_customers_integrity' AS check_name,
  COUNT(*) AS orphan_count
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL;
-- Expect: 0

-- Business logic constraint
SELECT
  'order_line_totals' AS check_name,
  COUNT(*) AS mismatch_count
FROM orders o
WHERE ABS(o.order_total - (
  SELECT SUM(quantity * unit_price)
  FROM order_lines ol
  WHERE ol.order_id = o.order_id
)) > 0.01; -- Allow penny rounding
-- Expect: 0

-- Historical integrity (SCD2)
SELECT
  'scd2_overlapping_dates' AS check_name,
  COUNT(*) AS overlap_count
FROM customers c1
INNER JOIN customers c2
  ON c1.customer_id = c2.customer_id
  AND c1.row_id != c2.row_id
WHERE c1.valid_from <= c2.valid_to
  AND c1.valid_to >= c2.valid_from;
-- Expect: 0
```

### Stage 4: Consumer-Side Validation (in mart/BI)

**What to check**:
- Report totals reconcile to source
- Metric definitions match business logic
- Date filters produce expected results
- Performance within acceptable range

**Example checks**:
```sql
-- BI report reconciliation
WITH source_total AS (
  SELECT SUM(revenue) AS total
  FROM raw.orders
  WHERE order_date BETWEEN '2026-01-01' AND '2026-01-31'
),
mart_total AS (
  SELECT SUM(revenue) AS total
  FROM marts.fct_orders
  WHERE order_date BETWEEN '2026-01-01' AND '2026-01-31'
)
SELECT
  'january_revenue_reconciliation' AS check_name,
  s.total AS source_total,
  m.total AS mart_total,
  ABS(s.total - m.total) / s.total AS variance_pct
FROM source_total s
CROSS JOIN mart_total m;
-- Expect: variance_pct < 0.001
```

---

## Implementation Patterns by Tool

### dbt

```yaml
# Use dbt tests + custom macros
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

### Python (Pandas/Polars)

```python
import pandera as pa

schema = pa.DataFrameSchema({
    "order_id": pa.Column(int, pa.Check.greater_than(0), unique=True),
    "customer_id": pa.Column(int, pa.Check.greater_than(0)),
    "order_total": pa.Column(float, pa.Check.in_range(0, 1000000)),
    "order_date": pa.Column(pa.DateTime),
})

df = schema.validate(df)
```

### Spark

```python
from pyspark.sql import functions as F

# Add quality metrics as columns
df_with_quality = df.withColumn(
    "quality_score",
    F.when(F.col("email").rlike(r"^[\w\.-]+@[\w\.-]+\.\w+$"), 1).otherwise(0)
)

# Assert critical metrics
assert df.filter(F.col("order_total") < 0).count() == 0, "Negative order totals found"
```

### SQL (Universal)

```sql
-- Create reusable quality check procedure
CREATE OR REPLACE PROCEDURE run_quality_checks(table_name VARCHAR)
RETURNS VARCHAR
LANGUAGE SQL
AS $$
DECLARE
  check_results VARCHAR;
BEGIN
  -- Run all checks, collect results
  SELECT LISTAGG(check_name || ': ' || status, ', ')
  INTO check_results
  FROM (
    SELECT 'freshness' AS check_name,
           CASE WHEN DATEDIFF('hour', MAX(updated_at), CURRENT_TIMESTAMP()) < 2
           THEN 'PASS' ELSE 'FAIL' END AS status
    FROM IDENTIFIER(:table_name)
    UNION ALL
    SELECT 'null_rate',
           CASE WHEN AVG(CASE WHEN email IS NULL THEN 1 ELSE 0 END) < 0.01
           THEN 'PASS' ELSE 'FAIL' END
    FROM IDENTIFIER(:table_name)
  );
  RETURN check_results;
END;
$$;
```

---

## Further Reading

- [dbt Testing Best Practices](../../../dbt-skill/references/dbt-testing-guide.md)
- [Warehouse Comparison](./warehouse-comparison.md) - See quality features by platform
- [Great Expectations Documentation](https://docs.greatexpectations.io/) - Python-based data quality framework
- [dbt-expectations Package](https://github.com/calogica/dbt-expectations) - 50+ dbt tests based on Great Expectations
