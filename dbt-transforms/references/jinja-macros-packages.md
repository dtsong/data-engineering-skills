## Contents

- [Jinja Fundamentals](#jinja-fundamentals)
  - [Key Context Objects](#key-context-objects)
  - [Whitespace Control](#whitespace-control)
- [Control Flow Patterns](#control-flow-patterns)
- [Writing Custom Macros](#writing-custom-macros)
  - [generate_schema_name](#generate_schema_name)
  - [Deduplicate (Warehouse-Adaptive)](#deduplicate-warehouse-adaptive)
- [Essential Packages](#essential-packages)
  - [Installation](#installation)
  - [dbt-utils Key Features](#dbt-utils-key-features)
  - [dbt-expectations Key Features](#dbt-expectations-key-features)
- [Debugging Jinja](#debugging-jinja)

---

# Jinja, Macros & Packages

> **Part of:** [dbt-transforms](../SKILL.md)

## Jinja Fundamentals

| Tag | Syntax | Purpose |
|-----|--------|---------|
| Expression | `{{ }}` | Output values (ref, source, config, var, env_var) |
| Statement | `{% %}` | Control flow, variable assignment |
| Comment | `{# #}` | Documentation (stripped during compilation) |

### Key Context Objects

| Object | Example |
|--------|---------|
| `ref()` | `{{ ref('stg_stripe__payments') }}` |
| `source()` | `{{ source('shopify', 'orders') }}` |
| `config()` | `{{ config(materialized='table') }}` |
| `var()` | `{{ var('start_date', '2020-01-01') }}` |
| `env_var()` | `{{ env_var('DBT_TARGET', 'dev') }}` |
| `this` | Current model relation (incremental models) |
| `target` | `target.name`, `target.type` |
| `is_incremental()` | `{% if is_incremental() %}` |

### Whitespace Control

`{%- ... %}` strips before, `{% ... -%}` strips after, `{%- ... -%}` strips both sides.

## Control Flow Patterns

```sql
-- Environment-specific logic
{% if target.name == 'dev' %}
    where order_date >= dateadd('month', -3, current_date)
{% endif %}

-- Dynamic pivot columns
{% set payment_methods = dbt_utils.get_column_values(table=ref('stg_stripe__payments'), column='payment_method') %}
{% for method in payment_methods %}
    sum(case when payment_method = '{{ method }}' then amount_dollars else 0 end) as {{ method }}_amount
    {%- if not loop.last %},{% endif %}
{% endfor %}

-- Variable assignment
{% set days_lookback = 90 %}
{% set statuses = ['completed', 'refunded'] %}
```

## Writing Custom Macros

```sql
-- macros/utils/safe_divide.sql
{% macro safe_divide(numerator, denominator) %}
    {% if target.type == 'snowflake' %}
        div0({{ numerator }}, {{ denominator }})
    {% elif target.type == 'bigquery' %}
        safe_divide({{ numerator }}, {{ denominator }})
    {% else %}
        case when {{ denominator }} != 0 then {{ numerator }} / {{ denominator }} else 0 end
    {% endif %}
{% endmacro %}
```

**Macro organization:** `macros/utils/` (helpers), `macros/schema/` (generate_schema_name, generate_alias_name), `macros/tests/` (custom generic tests), `macros/grants/` (post-hook grants).

**When to extract:** 1 use + high complexity = extract for readability. 2+ uses = always extract. Cross-project = extract to package.

### generate_schema_name

Override where models are built. In prod: use custom schema directly (`finance`). In dev/ci: prefix with target schema (`dbt_dsong_finance`).

```sql
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if target.name == 'prod' -%}
        {{ custom_schema_name | trim if custom_schema_name is not none else default_schema }}
    {%- else -%}
        {%- if custom_schema_name is not none -%}
            {{ default_schema }}_{{ custom_schema_name | trim }}
        {%- else -%}
            {{ default_schema }}
        {%- endif -%}
    {%- endif -%}
{%- endmacro %}
```

### Deduplicate (Warehouse-Adaptive)

```sql
{% macro deduplicate(relation, partition_by, order_by) %}
    {% if target.type == 'snowflake' %}
        select * from {{ relation }}
        qualify row_number() over (partition by {{ partition_by }} order by {{ order_by }} desc) = 1
    {% elif target.type == 'bigquery' %}
        select * except(rn) from (
            select *, row_number() over (partition by {{ partition_by }} order by {{ order_by }} desc) as rn
            from {{ relation }}
        ) where rn = 1
    {% endif %}
{% endmacro %}
```

## Essential Packages

| Package | Priority | Purpose |
|---------|----------|---------|
| `dbt-labs/dbt_utils` | Must-have | Surrogate keys, pivot, date spine, testing helpers |
| `calogica/dbt_expectations` | Must-have | Great Expectations-style data tests |
| `dbt-labs/codegen` | Dev only | Generate YAML and base models from sources |
| `dbt-labs/audit_helper` | Situational | Compare model versions during refactoring |
| `dbt-labs/dbt_project_evaluator` | Recommended | Lint project structure and naming in CI |
| `elementary-data/elementary` | Recommended | Anomaly detection, observability reports |

### Installation

```yaml
# packages.yml -- always pin version ranges
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.3.0", "<2.0.0"]
  - package: calogica/dbt_expectations
    version: [">=0.10.0", "<0.11.0"]
```

Commit `packages.yml` and `package-lock.yml`. Add `dbt_packages/` to `.gitignore`. Run `dbt deps` after clone, after editing packages.yml, and in every CI run.

### dbt-utils Key Features

- `generate_surrogate_key(['order_id', 'payment_id'])` -- deterministic surrogate key
- `pivot('payment_method', ..., agg='sum', then_value='amount_dollars')` -- dynamic pivot
- `date_spine(datepart="day", start_date="cast('2020-01-01' as date)", end_date="current_date")` -- fill date gaps

### dbt-expectations Key Features

- `expect_column_values_to_be_between: {min_value: 0, max_value: 100000}` -- range checks
- `expect_table_row_count_to_be_between: {min_value: 1000}` -- row count bounds
- `expect_column_distinct_count_to_be_between: {min_value: 3, max_value: 6}` -- distribution checks

## Debugging Jinja

1. `dbt compile --select <model>` -- inspect generated SQL in `target/compiled/`
2. `{{ log("var=" ~ my_var, info=true) }}` -- print during compilation
3. `dbt run-operation <macro> --args '{...}'` -- test macros in isolation
4. `dbt --debug run --select <model>` -- full verbose output

**Common errors:** `'xxx' is undefined` = typo in ref/macro name. Missing `endif`/`endfor` = mismatched tags. `run_query is not defined` = wrap with `{% if execute %}`.

The `execute` guard: `run_query()` only works during execution, not parsing. Always wrap: `{% if execute %} {% set results = run_query(...) %} {% endif %}`.

---

**Back to:** [Main Skill File](../SKILL.md)
