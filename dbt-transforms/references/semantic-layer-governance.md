## Contents

- [Semantic Layer Overview](#semantic-layer-overview)
- [MetricFlow Configuration](#metricflow-configuration)
- [Metric Types](#metric-types)
- [Model Contracts (dbt 1.5+)](#model-contracts-dbt-15)
- [Model Versions (dbt 1.6+)](#model-versions-dbt-16)
- [Access Controls (dbt 1.5+)](#access-controls-dbt-15)
- [dbt Mesh (Multi-Project)](#dbt-mesh-multi-project)
- [Maturity Assessment](#maturity-assessment)

---

# Semantic Layer & Governance

> **Part of:** [dbt-transforms](../SKILL.md)

## Semantic Layer Overview

Centralized metric definitions consumed by any BI tool. Define once in dbt, query from anywhere. Solves "different numbers in different dashboards."

**Prerequisites:** dbt Cloud (Team+) for API, MetricFlow OSS for local dev, dbt Core 1.6+, Snowflake/BigQuery/Databricks/Redshift.

| Team Stage | Recommendation |
|------------|---------------|
| Just starting | Skip -- focus on modeling fundamentals |
| Running in prod | Evaluate -- define key metrics centrally |
| Multiple BI tools | Strongly adopt -- single metric truth |
| Enterprise | Full platform -- governance, access, versioning |

## MetricFlow Configuration

```yaml
semantic_models:
  - name: orders
    model: ref('fct_orders')
    defaults:
      agg_time_dimension: order_date
    entities:
      - name: order_id
        type: primary
      - name: customer_id
        type: foreign
    dimensions:
      - name: order_date
        type: time
        type_params: {time_granularity: day}
      - name: order_status
        type: categorical
    measures:
      - name: order_count
        agg: count
        expr: order_id
      - name: total_revenue
        agg: sum
        expr: total_amount
```

**Entity types:** `primary` (PK), `foreign` (join key), `unique`, `natural` (business key).
**Dimension types:** `categorical` (groupable strings), `time` (date/timestamp).
**Aggregations:** `sum`, `count`, `count_distinct`, `average`, `min`, `max`, `median`, `percentile`.

## Metric Types

```yaml
# Simple -- direct measure reference
metrics:
  - name: total_revenue
    type: simple
    type_params:
      measure: total_revenue

# Derived -- math on other metrics
  - name: average_order_value
    type: derived
    type_params:
      expr: total_revenue / order_count
      metrics: [{name: total_revenue}, {name: order_count}]

# Cumulative -- running totals
  - name: trailing_28d_revenue
    type: cumulative
    type_params:
      measure: total_revenue
      window: 28 days

# Conversion -- funnel metrics
  - name: visit_to_purchase_rate
    type: conversion
    type_params:
      conversion_type_params:
        entity: customer_id
        base_measure: site_visits
        conversion_measure: order_count
        window: 7 days
```

Define metrics in dbt, not in individual BI tools -- prevents metric drift.

## Model Contracts (dbt 1.5+)

Enforce column names and data types at build time. Build fails if SQL output mismatches the contract.

```yaml
models:
  - name: fct_orders
    config:
      contract: {enforced: true}
    columns:
      - name: order_id
        data_type: string
        data_tests: [unique, not_null]
      - name: total_amount
        data_type: float
        data_tests: [not_null]
```

| Logical Type | Snowflake | BigQuery |
|-------------|-----------|----------|
| string | VARCHAR | STRING |
| integer | NUMBER(38,0) | INT64 |
| float | FLOAT | FLOAT64 |
| date | DATE | DATE |
| timestamp | TIMESTAMP_NTZ | TIMESTAMP |

**Enforce on:** Marts, public models, Semantic Layer models. **Skip on:** Staging and intermediate (too rigid for evolving schemas).

## Model Versions (dbt 1.6+)

Run multiple versions simultaneously for breaking schema changes on public models.

```yaml
models:
  - name: fct_orders
    latest_version: 2
    config: {contract: {enforced: true}}
    versions:
      - v: 1
        defined_in: fct_orders_v1
        deprecation_date: 2025-06-01
      - v: 2
        defined_in: fct_orders_v2
        columns:
          - include: all
          - name: discount_amount
            data_type: float
```

`{{ ref('fct_orders') }}` references `latest_version`. Pin with `{{ ref('fct_orders', v=1) }}`. Only version models with external consumers; skip for additive changes.

## Access Controls (dbt 1.5+)

| Level | Who Can ref() | Use Case |
|-------|--------------|----------|
| `private` | Same group only | Internal helpers |
| `protected` (default) | Same project | Standard models |
| `public` | Any project | Stable cross-project interfaces |

```yaml
models:
  - name: fct_orders
    access: public
    config: {group: finance, contract: {enforced: true}}
  - name: int_payments_pivoted
    access: private
    config: {group: finance}
```

Public models should always have enforced contracts. Never make intermediate models public.

## dbt Mesh (Multi-Project)

Cross-project `ref()` for large organizations. Each team owns a project; projects reference each other's `public` models.

**Split when:** 50+ models, multiple teams, different deploy cadences, CI builds >30 min.

```sql
-- Consumer project references producer's public model
select * from {{ ref('shared_project', 'dim_date') }}
```

**Before enabling:** All shared models `access: public` with enforced contracts. Groups and owners defined. `dependencies.yml` configured. Deployment order documented. Cross-project tests in place.

## Maturity Assessment

| Capability | Starting | Running in Prod | Multiple Teams | Enterprise |
|------------|---------|----------------|----------------|------------|
| Testing | Basic YAML | Custom generics, unit tests | dbt-expectations, contracts | Full + anomaly detection |
| CI/CD | Manual | GitHub Actions, Slim CI | dbt Cloud, blue/green | Multi-project orchestration |
| Governance | Naming conventions | Access controls, groups | Versions, contracts | dbt Mesh, Semantic Layer |
| Observability | Source freshness | Elementary, Slack | SLAs, runbooks | Full platform, PagerDuty |

**Next steps:** Starting: add PK tests + CI pipeline + freshness. Prod: define groups + access controls + contracts + dbt-expectations. Multi-team: evaluate Mesh + versions + Semantic Layer. Enterprise: integrate Semantic Layer with all BI tools + PagerDuty + governed catalog.

---

**Back to:** [Main Skill File](../SKILL.md)
