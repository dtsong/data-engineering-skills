> **Part of:** [data-testing](../SKILL.md)

# dbt Testing Strategy

Reference for dbt test organization, coverage targets, incremental testing, CI/CD integration, and failure triage.

## Coverage Targets

| Layer | PK Integrity | Not-Null | Accepted Values | Custom Tests | Target |
|-------|-------------|----------|-----------------|--------------|--------|
| Staging | 100% | Critical columns | Enum columns | -- | 100% PK, 60%+ column |
| Intermediate | 100% | All join keys | -- | Business rules | 80%+ column |
| Marts | 100% | All columns | All enums | Aggregate checks | 80%+ column, 100% PK |

**Rule of thumb:** Every model has `unique` + `not_null` on its primary key. No exceptions.

---

## Test Organization by Layer

### Staging tests (`models/staging/`)

```yaml
# models/staging/_stg_models.yml
models:
  - name: stg_orders
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: status
        tests:
          - accepted_values:
              values: ['pending', 'shipped', 'delivered', 'cancelled']
      - name: order_date
        tests:
          - not_null
```

### Intermediate tests (`models/intermediate/`)

```yaml
# models/intermediate/_int_models.yml
models:
  - name: int_orders_enriched
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: customer_id
        tests:
          - not_null
          - relationships:
              to: ref('stg_customers')
              field: customer_id
```

### Mart tests (`models/marts/`)

```yaml
# models/marts/_mart_models.yml
models:
  - name: fct_orders
    tests:
      - dbt_utils.equal_rowcount:
          compare_model: ref('int_orders_enriched')
    columns:
      - name: order_id
        tests:
          - unique
          - not_null
      - name: total_amount
        tests:
          - dbt_utils.accepted_range:
              min_value: 0
              inclusive: true
```

---

## Incremental Testing Strategies

For incremental models, test both the full table and the incremental slice:

```yaml
# Full table test (runs on every build)
- name: fct_events
  columns:
    - name: event_id
      tests:
        - unique
        - not_null

# Incremental slice test (custom macro)
- name: fct_events
  tests:
    - row_count_delta:
        min_new_rows: 1
        max_new_rows: 1000000
        config:
          severity: warn
```

**`dbt build` vs `dbt run` + `dbt test`:**
- `dbt build` runs tests immediately after each model — fail-fast, prevents downstream from running on bad data.
- `dbt run` + `dbt test` separates execution — useful when you want all models built before testing (faster wall-clock time, but propagates bad data).
- **Recommendation:** Use `dbt build` in CI and production. Use `dbt run` + `dbt test` only during local development for speed.

---

## CI/CD Integration

### Slim CI Test Selection

```bash
# Run only tests affected by changes in this PR
dbt build --select state:modified+ --state ./prod-manifest --target ci

# Run tests for modified models and their direct children
dbt test --select state:modified+1 --state ./prod-manifest
```

### CI Pipeline Steps

1. `dbt deps` — install packages
2. `dbt seed --target ci` — load test fixtures
3. `dbt build --select state:modified+ --state ./prod-manifest` — build and test changed models
4. Upload `target/run_results.json` as CI artifact for reporting

### Store Failures for CI Review

```yaml
# dbt_project.yml
tests:
  +store_failures: true
  +schema: dbt_test_failures
```

Failed rows land in `dbt_test_failures` schema. CI can query these tables and post summaries as PR comments.

---

## Test Failure Triage Workflow

```
Test fails
  |
  +-- Schema test (unique/not_null/accepted_values)?
  |     +-- Check source data for upstream issues
  |     +-- If new valid value → update accepted_values list
  |     +-- If true duplicate → fix deduplication logic in staging
  |
  +-- Relationship test?
  |     +-- Check for late-arriving dimensions
  |     +-- If expected → add severity: warn
  |     +-- If unexpected → investigate source system join keys
  |
  +-- Custom/aggregate test?
  |     +-- Compare current vs previous run metrics
  |     +-- Check for data volume anomalies (load spike/drop)
  |     +-- If threshold issue → adjust test tolerance
  |
  +-- Performance test?
        +-- Check query plan for table scans
        +-- Verify clustering/partitioning keys
        +-- If transient → mark as flaky with retry config
```

**Severity levels:**
- `error` (default) — blocks pipeline, requires immediate fix
- `warn` — logs warning, pipeline continues, review in next triage cycle
