## Contents

- [Deduplication Patterns](#deduplication-patterns)
- [Standardization](#standardization)
- [Entity Resolution](#entity-resolution)
- [Validation and Quarantine](#validation-and-quarantine)
- [NULL Handling](#null-handling)
- [Cleaning Layer Architecture](#cleaning-layer-architecture)

---

# Data Cleaning Patterns

> **Part of:** [dbt-skill](../SKILL.md)

## Deduplication Patterns

### ROW_NUMBER Window Function

Standard dedup: partition by business key, order by freshness, keep row 1.

```sql
with ranked as (
    select
        *
        , row_number() over (
            partition by customer_id
            order by updated_at desc
        ) as row_num
    from {{ ref('stg_crm__customers') }}
)

select * from ranked where row_num = 1
```

### QUALIFY Clause (Snowflake, DuckDB)

Eliminates the CTE wrapper for simpler dedup.

```sql
select *
from {{ ref('stg_crm__customers') }}
qualify row_number() over (
    partition by customer_id
    order by updated_at desc
) = 1
```

### Merge-Key Dedup

When duplicates span sources, build a composite merge key before dedup.

```sql
, merge_key as (
    select
        {{ dbt_utils.generate_surrogate_key(['lower(email)', 'phone_digits']) }} as merge_id
        , *
    from unioned_sources
)
```

| Pattern | Use When | Warehouse Support |
|---------|----------|-------------------|
| ROW_NUMBER + CTE | Universal compatibility | All |
| QUALIFY | Cleaner syntax, single-source dedup | Snowflake, DuckDB, BigQuery |
| Merge-key | Multi-source dedup before golden record | All |

## Standardization

### Phone Numbers

Strip non-digits, then format. Handle country codes explicitly.

```sql
, regexp_replace(phone, '[^0-9]', '', 'g') as phone_digits
, case
    when length(phone_digits) = 10
        then '(' || left(phone_digits, 3) || ') ' || substr(phone_digits, 4, 3) || '-' || right(phone_digits, 4)
    when length(phone_digits) = 11 and left(phone_digits, 1) = '1'
        then '+1 (' || substr(phone_digits, 2, 3) || ') ' || substr(phone_digits, 5, 3) || '-' || right(phone_digits, 4)
    else phone  -- preserve original if unparseable
  end as phone_formatted
```

### Email

```sql
, lower(trim(email)) as email_clean
```

### Address Abbreviation Normalization

```sql
, replace(replace(replace(upper(trim(street))
    , 'STREET', 'ST')
    , 'AVENUE', 'AVE')
    , 'BOULEVARD', 'BLVD') as street_normalized
```

For production use, build a macro or seed table mapping full words to abbreviations.

### Date Standardization

Cast all date variants to ISO 8601.

```sql
, try_cast(date_field as date) as date_clean  -- Snowflake
, try_cast(date_field as date) as date_clean   -- DuckDB (same syntax)
, safe_cast(date_field as date) as date_clean  -- BigQuery
```

## Entity Resolution

### Deterministic Matching

Exact match on a canonical key (email, SSN, phone_digits).

```sql
select
    coalesce(a.customer_id, b.customer_id) as resolved_id
    , *
from source_a a
full outer join source_b b
    on lower(trim(a.email)) = lower(trim(b.email))
```

### Fuzzy Matching

| Function | Use Case | Warehouse |
|----------|----------|-----------|
| `jarowinkler_similarity()` | Name matching | Snowflake |
| `jaro_winkler_similarity()` | Name matching | DuckDB |
| `soundex()` | Phonetic matching | All |
| `editdist3()` | Edit distance | DuckDB |

```sql
-- DuckDB fuzzy match example
select *
from customers_a a
join customers_b b
    on jaro_winkler_similarity(a.name_clean, b.name_clean) > 0.85
```

### Golden Record Selection

After matching, pick the most complete / most recent record per entity cluster.

```sql
, row_number() over (
    partition by resolved_id
    order by
        (case when email is not null then 1 else 0 end)
        + (case when phone is not null then 1 else 0 end)
        + (case when address is not null then 1 else 0 end) desc
        , updated_at desc
) as golden_rank
```

## Validation and Quarantine

### Quarantine Pattern

Split rows into valid and invalid streams.

```sql
-- int_customers_validated.sql
with validated as (
    select
        *
        , case
            when customer_id is null then 'missing_pk'
            when email_clean not like '%@%.%' then 'invalid_email'
            when phone_digits is not null and length(phone_digits) not in (10, 11) then 'invalid_phone'
            else 'valid'
          end as validation_status
    from {{ ref('int_customers_cleaned') }}
)

select * from validated where validation_status = 'valid'
```

```sql
-- int_customers_quarantined.sql
select * from {{ ref('int_customers_validated') }}  -- re-run validation
where validation_status != 'valid'
```

### Flag Columns for Manual Review

Add boolean flags instead of splitting, when quarantine is too aggressive.

```sql
, email_clean not like '%@%.%' as needs_email_review
, phone_digits is null or length(phone_digits) not in (10, 11) as needs_phone_review
```

### Anomaly Detection on Row Counts

Use z-score on historical row counts to detect ingestion issues.

```sql
-- singular test: assert row count within 2 standard deviations
select 1
from (
    select
        count(*) as current_count
        , avg(historical_count) as mean_count
        , stddev(historical_count) as std_count
    from {{ ref('_row_count_history') }}
) stats
where abs(current_count - mean_count) > 2 * std_count
```

## NULL Handling

### COALESCE Chains

Order sources by reliability.

```sql
, coalesce(crm.email, billing.email, marketing.email) as email_best
```

### Missing vs Unknown

Distinguish "we never collected this" from "we collected it and it was empty."

```sql
, case
    when source_has_field = false then 'NOT_COLLECTED'
    when field_value is null then 'UNKNOWN'
    else field_value
  end as field_classified
```

### Default Value Strategies

| Data Type | Default | Use When |
|-----------|---------|----------|
| String | `'Unknown'` | Display/reporting |
| Numeric | `0` | Aggregation (sum) |
| Numeric | `null` | Aggregation (avg) -- zeros skew |
| Date | `'1970-01-01'` | Dimension keys (unknown member) |
| Boolean | `false` | Conservative default |

## Cleaning Layer Architecture

| Layer | Responsibility | Example |
|-------|---------------|---------|
| **Staging** | Rename, cast, trim whitespace | `stg_crm__customers` |
| **Intermediate** | Deduplicate, standardize, validate, resolve entities | `int_customers_deduped`, `int_customers_cleaned` |
| **Marts** | Business logic on clean data only | `dim_customers`, `fct_orders` |

Rules:
- Staging never deduplicates or applies business logic.
- Intermediate models do the heavy cleaning; chain them: `_deduped` -> `_cleaned` -> `_validated`.
- Marts assume data is clean; if a mart needs cleaning logic, push it back to intermediate.
- Quarantine tables sit in intermediate, materialized as tables for review.
