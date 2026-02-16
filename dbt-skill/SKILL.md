---
name: dbt-skill
description: "Use this skill when building or reviewing dbt models, tests, or project structure. Triggers on analytics engineering tasks including staging/marts layers, materializations, incremental strategies, Jinja macros, sources, warehouse configuration, DuckDB adapter, data cleaning, and deduplication patterns. Common phrases: \"dbt model\", \"write a dbt test\", \"incremental strategy\", \"semantic layer\", \"dbt DuckDB\", \"cleaning patterns\". Do NOT use for Python DataFrame code (use python-data-engineering-skill), pipeline scheduling (use data-orchestration-skill), or standalone DuckDB queries without dbt (use duckdb-local-skill)."
model_tier: analytical
version: 1.0.0
---

# dbt Skill for Claude

Comprehensive dbt guidance covering project structure, modeling, testing, CI/CD, and production patterns. Targets Snowflake, BigQuery, and DuckDB. Beginner-friendly with progressive scaling.

## When to Use This Skill

**Activate when:** Creating/modifying dbt models, choosing materializations, structuring layers, setting up tests, CI/CD, sources, Jinja macros, or making analytics engineering decisions.

**Don't use for:** Basic SQL syntax, warehouse administration, raw pipeline config (Fivetran/Airbyte), BI tool setup.

## Scope Constraints

- Targets Snowflake, BigQuery, and DuckDB; other warehouses may need adaptation.
- Assumes dbt Core 1.6+ or dbt Cloud; earlier versions lack governance features.
- Does not cover raw data ingestion, BI tool configuration, or warehouse admin.
- Reference files are loaded on demand -- do not pre-load multiple references.

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| medium | Sonnet | Opus, Haiku | Haiku |

## Core Principles

1. **DRY via ref()/source()** -- Never hardcode table names; use `ref()` or `source()` exclusively.
2. **Single Source of Truth** -- Staging = entry point for raw data; marts = consumer interface.
3. **Idempotent Transformations** -- Ensure `dbt run` is safe to re-execute.
4. **Test Everything** -- Every model has at minimum PK uniqueness + not_null tests.
5. **Progressive Complexity** -- Start with views/tables; add incremental only when volume demands it.

## Project Structure

```
dbt_project/
├── dbt_project.yml
├── packages.yml
├── profiles.yml                 # Local only, never committed
├── models/
│   ├── staging/                 # 1:1 with source tables
│   │   └── <source>/
│   │       ├── _<source>__models.yml
│   │       ├── _<source>__sources.yml
│   │       └── stg_<source>__<entity>.sql
│   ├── intermediate/            # Business logic, joins, pivots
│   └── marts/                   # Business-facing facts and dimensions
├── macros/
├── tests/
├── seeds/
├── snapshots/
└── analyses/
```

## Modeling Methodology -- Medallion + Kimball

### Layer Decision Matrix

| Layer | Materialization | Purpose | Naming | Tests |
|-------|----------------|---------|--------|-------|
| **Staging** | `view` | Clean/rename raw data, 1:1 with source | `stg_<source>__<entity>` | not_null, unique on PK |
| **Intermediate** | `ephemeral` | Business logic, joins, pivots | `int_<entity>_<verb>ed` | Tested via downstream |
| **Marts** | `table`/`incremental` | Business-facing facts and dimensions | `fct_<entity>`, `dim_<entity>` | Full coverage |
| **Reports** | `table` | Pre-aggregated for dashboards | `rpt_<entity>` | Acceptance tests |

### Staging Model Pattern

```sql
-- stg_stripe__payments.sql
with source as (
    select * from {{ source('stripe', 'payments') }}
),

renamed as (
    select
        id as payment_id,
        order_id,
        customer_id,
        lower(payment_method) as payment_method,
        status as payment_status,
        amount / 100.0 as amount_dollars,
        created_at,
        updated_at
    from source
)

select * from renamed
```

### Intermediate / Marts (Compact)

```sql
-- int_payments_pivoted.sql: pivot payments by method per order
-- fct_orders.sql: join orders + pivoted payments into final fact table
-- Pattern: with <cte> as (select * from {{ ref('...') }}), final as (...) select * from final
```

## Model Naming Conventions

| Layer | Pattern | Example |
|-------|---------|---------|
| Staging | `stg_<source>__<entity>` | `stg_stripe__payments` |
| Intermediate | `int_<entity>_<verb>ed` | `int_payments_pivoted` |
| Facts | `fct_<entity>` | `fct_orders` |
| Dimensions | `dim_<entity>` | `dim_customers` |
| Reports | `rpt_<entity>` | `rpt_monthly_revenue` |
| YAML model config | `_<source>__models.yml` | `_stripe__models.yml` |
| YAML sources | `_<source>__sources.yml` | `_stripe__sources.yml` |

Leading underscore sorts config files above models in directory listings.

## SQL Style Guide

1. **Leading commas** -- cleaner diffs
2. **Lowercase keywords** -- `select`, not `SELECT`
3. **CTEs over subqueries** -- always use `with` blocks
4. **Explicit columns** -- no `select *` in marts (OK in staging `with source`)
5. **Final CTE** -- name the last CTE `final`
6. **4-space indentation**
7. **One column per line** in select statements

## Materialization Decision Matrix

| Situation | Materialization | Why |
|-----------|----------------|-----|
| Staging models | `view` | Always fresh, minimal storage |
| Intermediate logic | `ephemeral` | Zero cost, inlined as CTE |
| Marts < 100M rows | `table` | Simple, fast reads |
| Marts > 100M rows | `incremental` | Only process new/changed data |
| SCD Type 2 tracking | `snapshot` | Track historical changes |

**For detailed incremental strategies, see:** [Incremental Models & Performance](references/incremental-performance.md)

## Source Configuration

```yaml
sources:
  - name: stripe
    database: raw
    schema: stripe
    loader: fivetran
    loaded_at_field: _fivetran_synced
    freshness:
      warn_after: {count: 12, period: hour}
      error_after: {count: 24, period: hour}
    tables:
      - name: payments
        columns:
          - name: id
            data_tests: [unique, not_null]
          - name: order_id
            data_tests:
              - not_null
              - relationships:
                  to: source('shopify', 'orders')
                  field: id
```

| Concept | Snowflake | BigQuery |
|---------|-----------|----------|
| Top-level container | Database | Project |
| Schema grouping | Schema | Dataset |
| Freshness field | `_fivetran_synced` | `_fivetran_synced` or `_PARTITIONTIME` |

## ref() and source() Rules

1. **`source()` only in staging** -- staging models are the only gateway to raw data.
2. **`ref()` everywhere else** -- all other models reference through `ref()`.
3. **Never skip layers** -- marts must not `ref()` staging directly; go through intermediate.
4. **Never hardcode schema names** -- use `source()` and `ref()` exclusively.

```sql
-- WRONG: select * from raw.stripe.payments
-- WRONG: {{ source('stripe', 'payments') }} in a marts model
-- WRONG: {{ ref('stg_stripe__payments') }} in a marts model
-- CORRECT: {{ ref('int_payments_pivoted') }} in a marts model
```

## Basic Testing Overview

| Layer | Test Type | Examples |
|-------|-----------|---------|
| **Sources** | Freshness, existence | `loaded_at_field`, `not_null` on keys |
| **Staging** | PK integrity | `unique`, `not_null` on PK |
| **Intermediate** | Tested via downstream | -- |
| **Marts** | Full coverage | All keys, accepted values, relationships, row counts |

**For deep testing strategies, see:** [Testing & Quality Strategy](references/testing-quality.md)

## Security Posture

See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for the full framework.

- **Credentials**: `profiles.yml` (never committed) using `env_var()` for all secrets.
- **Auth**: SSO/OAuth for local dev; key-pair (Snowflake) or workload identity (BigQuery) for CI/prod.
- **Data classification**: Tag sensitive columns with `meta.data_classification` in model YAML.
- **Never** put real data in seed files or hardcode credentials.

## Detailed Guides

Reference files loaded on demand:

- **[Testing & Quality Strategy](references/testing-quality.md)** -- Schema, generic, singular, unit tests, dbt-expectations, layer strategy
- **[CI/CD & Deployment](references/ci-cd-deployment.md)** -- Slim CI, GitHub Actions, dbt Cloud jobs, environment strategy, blue/green
- **[Jinja, Macros & Packages](references/jinja-macros-packages.md)** -- Jinja fundamentals, custom macros, packages, debugging
- **[Incremental Models & Performance](references/incremental-performance.md)** -- Microbatch (1.9+), merge, delete+insert, warehouse tuning, cost monitoring
- **[Data Quality & Observability](references/data-quality-observability.md)** -- Source freshness, Elementary, anomaly detection, alerting, incident response
- **[Semantic Layer & Governance](references/semantic-layer-governance.md)** -- MetricFlow, contracts, versions, access controls, dbt Mesh
- **[Data Cleaning Patterns](references/cleaning-patterns.md)** -- Deduplication, standardization, entity resolution, validation, NULL handling, cleaning layer architecture
- **[DuckDB Adapter](references/duckdb-adapter.md)** -- dbt-duckdb setup, external file reading, DuckDB-specific SQL, export patterns, dev-to-prod portability
- **[Consulting Workflow](references/consulting-workflow.md)** -- dbt artifacts as deliverables, security tier awareness, project portability, client handoff
