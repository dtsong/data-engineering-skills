# Data Quality & Observability

> **Part of:** [dbt-skill](../SKILL.md)

## Source Freshness

Configure `loaded_at_field` and thresholds in sources YAML, then run `dbt source freshness`.

| Ingestion Tool | loaded_at_field |
|----------------|----------------|
| Fivetran | `_fivetran_synced` |
| Airbyte | `_airbyte_extracted_at` |
| Stitch | `_sdc_batched_at` |
| BigQuery native | `_PARTITIONTIME` |

```yaml
sources:
  - name: shopify
    loaded_at_field: _fivetran_synced
    freshness:
      warn_after: {count: 12, period: hour}
      error_after: {count: 24, period: hour}
    tables:
      - name: orders
        columns:
          - name: id
            data_tests: [unique, not_null]
      - name: order_events
        loaded_at_field: event_timestamp     # override source-level field
        freshness:
          warn_after: {count: 1, period: hour}
          error_after: {count: 3, period: hour}
```

```bash
dbt source freshness                           # check all
dbt source freshness --select source:shopify   # check one source
```

## Elementary Package

Anomaly detection and observability inside your warehouse.

```yaml
# packages.yml
packages:
  - package: elementary-data/elementary
    version: "0.16.1"
```

```yaml
# dbt_project.yml
models:
  elementary:
    +schema: elementary
    +materialized: table
```

### Anomaly Tests

```yaml
models:
  - name: fct_orders
    columns:
      - name: order_id
        data_tests:
          - elementary.volume_anomalies:
              timestamp_column: order_date
              sensitivity: 3
          - elementary.freshness_anomalies:
              timestamp_column: order_date
          - elementary.schema_changes: {}
      - name: total_amount
        data_tests:
          - elementary.column_anomalies:
              timestamp_column: order_date
              column_anomalies: [zero_count, null_count, average]
```

Reports: `dbt run-operation elementary.generate_report` for HTML, `elementary.send_slack_report` for Slack alerts.

## DIY Anomaly Patterns

Use when Elementary is unavailable.

```sql
-- tests/assert_order_count_within_range.sql
with daily_counts as (
    select order_date, count(*) as order_count
    from {{ ref('fct_orders') }}
    where order_date >= current_date - 30
    group by order_date
),
stats as (
    select avg(order_count) as avg_count, stddev(order_count) as stddev_count
    from daily_counts
)
select dc.order_date, dc.order_count
from daily_counts dc cross join stats s
where dc.order_count < s.avg_count - (3 * s.stddev_count)
   or dc.order_count > s.avg_count + (3 * s.stddev_count)
```

Similar patterns work for column distribution drift and null rate tracking -- compare current 7-day window against 30-60 day baseline.

## Data Quality Pillars

| Pillar | Measurement | Example |
|--------|-------------|---------|
| **Completeness** | `1 - (null_count / total)` | email 98% populated |
| **Accuracy** | Format/range validation | `order_total > 0` |
| **Timeliness** | `now() - max(loaded_at)` | Orders < 2 hours old |
| **Consistency** | Cross-source reconciliation | Stripe revenue = Shopify revenue |

## Alerting

| Severity | Condition | Channel | Response |
|----------|-----------|---------|----------|
| P1 | Mart data missing/incorrect | PagerDuty | 15 min |
| P2 | Source freshness error | Slack #data-alerts | 1 hour |
| P3 | Test warning threshold | Slack #data-notifications | Next business day |
| P4 | Schema change detected | Log only | Weekly review |

Tag models with `meta.owner` and `meta.severity` to route alerts per team. Use `warn_after` before `error_after` to reduce false-positive pages.

## Lineage & Impact Analysis

```bash
dbt ls --select +fct_orders                    # upstream ancestors
dbt ls --select fct_orders+                    # downstream descendants
dbt ls --select fct_orders+ --resource-type exposure  # affected dashboards
```

Define exposures in YAML to document dashboard/ML model dependencies. Always check `dbt ls --select model+ --resource-type exposure` before modifying a model, then notify listed owners.

## Incident Response

1. **Detect** -- Alert from test failure, freshness error, anomaly, or stakeholder report.
2. **Triage** -- Assess severity per matrix above.
3. **Communicate** -- Notify stakeholders for P1/P2 with impact, ETA, workaround.
4. **Fix** -- `dbt retry` (failed only), `dbt build --select +model` (rebuild branch), `--full-refresh` if corrupted.
5. **Verify** -- Re-run tests, check freshness, generate Elementary report.
6. **Post-mortem** -- Document timeline, root cause, impact, prevention actions.

## Adoption Path

| Tier | When | Implement |
|------|------|-----------|
| 1 Essential | Day 1 | Source freshness, PK tests, model contracts on marts |
| 2 Mature | Running in prod | Elementary, Slack alerts, anomaly tests, exposures |
| 3 Enterprise | Multiple teams | PagerDuty, SLAs per model tier, quality scoring dashboard |

---

**Back to:** [Main Skill File](../SKILL.md)
