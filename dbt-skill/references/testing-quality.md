# Testing & Quality Strategy

> **Part of:** [dbt-skill](../SKILL.md)

## Schema Tests (YAML-based)

Four built-in tests: `unique`, `not_null`, `accepted_values`, `relationships`.

```yaml
models:
  - name: fct_orders
    columns:
      - name: order_id
        data_tests:
          - unique
          - not_null
      - name: order_status
        data_tests:
          - accepted_values:
              values: ['completed', 'pending', 'cancelled', 'refunded']
      - name: customer_id
        data_tests:
          - not_null:
              where: "order_status != 'draft'"
          - relationships:
              to: ref('dim_customers')
              field: customer_id
```

**Config options:** `severity: warn|error`, `where:` (filter scope), `store_failures: true` (persist failing rows), `tags:` (selective execution).

**Compound uniqueness:** `dbt_utils.unique_combination_of_columns: {combination_of_columns: [order_id, line_item_id]}`.

## Singular Tests

Standalone SQL in `tests/`. Query must return zero rows to pass. Prefix with `assert_`.

```sql
-- tests/assert_payment_revenue_matches_orders.sql
with orders as (
    select sum(total_amount) as total from {{ ref('fct_orders') }} where order_status = 'completed'
),
payments as (
    select sum(amount_dollars) as total from {{ ref('stg_stripe__payments') }} where payment_status = 'completed'
)
select * from orders cross join payments
where abs(orders.total - payments.total) > 1.00
```

Use singular tests for: business rules specific to one model, cross-table reconciliation, complex multi-step validation. Use generic tests for reusable patterns with parameters.

## Custom Generic Tests

```sql
-- tests/generic/is_positive.sql
{% test is_positive(model, column_name) %}
select {{ column_name }} from {{ model }} where {{ column_name }} < 0
{% endtest %}
```

Apply in YAML: `data_tests: [is_positive]`. Supports parameters with defaults.

## Unit Tests (dbt 1.8+)

Validate transformation logic with mocked inputs. No warehouse queries.

```yaml
unit_tests:
  - name: test_tiered_discount
    model: int_orders_with_discount
    given:
      - input: ref('stg_shopify__orders')
        rows:
          - {order_id: 1, customer_id: 100, subtotal: 600.00}
          - {order_id: 2, customer_id: 101, subtotal: 300.00}
    expect:
      rows:
        - {order_id: 1, discount_amount: 60.00, total_after_discount: 540.00}
        - {order_id: 2, discount_amount: 15.00, total_after_discount: 285.00}
```

**Use for:** Complex CASE/WHEN logic, multi-step calculations, Jinja conditional paths. **Skip for:** Simple staging renames, incremental merge behavior, warehouse functions.

## dbt-expectations (Top Tests)

```yaml
packages:
  - package: calogica/dbt_expectations
    version: [">=0.10.0", "<0.11.0"]
```

| Test | Purpose |
|------|---------|
| `expect_column_values_to_be_between` | Range validation (min/max with row_condition) |
| `expect_table_row_count_to_be_between` | Catch data drops or duplication |
| `expect_column_distinct_count_to_equal` | Detect schema drift in enum columns |
| `expect_column_values_to_match_regex` | String format validation (email, etc.) |
| `expect_column_mean_to_be_between` | Statistical guardrail for anomalous shifts |
| `expect_column_pair_values_A_to_be_greater_than_B` | Column ordering (total >= discount) |
| `expect_table_row_count_to_equal_other_table` | Migration validation |

## dbt-utils Testing Helpers

| Test | Purpose |
|------|---------|
| `equal_rowcount` | Two models have same row count (1:1 grain) |
| `fewer_rows_than` | Dimensional check (customers < orders) |
| `not_accepted_values` | Block test/debug data from prod |
| `expression_is_true` | Assert any SQL expression for all rows |
| `recency` | Most recent record within expected window |

## Test Configuration

- `severity: error` (default) blocks pipeline. `severity: warn` logs and continues.
- Use `error` for PK integrity, referential integrity, critical business rules.
- Use `warn` for statistical checks, soft constraints, monitoring.
- `store_failures: true` persists failing rows for debugging. Enable globally in `dbt_project.yml`.
- `tags:` for selective execution: `dbt test --select tag:critical`.

## Testing Strategy by Layer

| Layer | Required | Recommended | Optional |
|-------|----------|-------------|----------|
| Sources | Freshness | not_null on PKs | unique on PKs |
| Staging | unique + not_null on PK | accepted_values on status | Relationships |
| Intermediate | None (tested downstream) | unique/not_null if materialized | expression_is_true |
| Marts (facts) | PK unique+not_null, FK not_null, relationships | accepted_values, row count, recency | Statistical, reconciliation |
| Marts (dims) | PK unique+not_null | accepted_values on types | Regex on formatted cols |

## Anti-Patterns

- **Over-testing staging:** Keep staging tests to PK integrity. Statistical and row count tests belong on marts.
- **Skipping mart tests:** Joins change guarantees (LEFT JOIN introduces NULLs, many-to-many creates duplicates). Always re-test at mart layer.
- **All warnings:** When everything is `warn`, nothing is. Use `error` for anything that produces incorrect analytics.
- **No store_failures:** Without it, debugging requires re-running test queries manually.

---

**Back to:** [Main Skill File](../SKILL.md)
