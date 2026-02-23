> **Part of:** [data-observability](../SKILL.md)

# Schema Change Detection Patterns

Configurations and queries for detecting column additions, removals, type changes, and contract violations. Schema changes are the second most common cause of silent pipeline failures after stale data.

## dbt Schema Contracts (v1.5+)

Enforce schema contracts to catch breaking changes at build time:

```yaml
# models/marts/fct_orders.yml
version: 2

models:
  - name: fct_orders
    config:
      contract:
        enforced: true
    columns:
      - name: order_id
        data_type: bigint
        constraints:
          - type: not_null
          - type: primary_key
      - name: customer_id
        data_type: bigint
        constraints:
          - type: not_null
      - name: order_date
        data_type: date
      - name: total_amount
        data_type: numeric(12,2)
      - name: status
        data_type: varchar(20)
```

**Run with strict enforcement:**
```bash
dbt build --select fct_orders --warn-error
```

Contract violations produce clear error messages:
- Column added not in contract -> ERROR
- Column removed from source -> ERROR
- Data type mismatch -> ERROR

---

## Schema Snapshots and Diffing

Capture schema state and compare across runs:

```sql
-- Capture current schema snapshot
CREATE OR REPLACE TABLE schema_snapshots AS
SELECT
    CURRENT_TIMESTAMP AS snapshot_ts,
    table_schema,
    table_name,
    column_name,
    ordinal_position,
    data_type,
    is_nullable,
    character_maximum_length
FROM information_schema.columns
WHERE table_schema IN ('raw', 'staging', 'marts');
```

**Diff between snapshots:**
```sql
-- Detect schema changes between two snapshots
WITH latest AS (
    SELECT * FROM schema_snapshots
    WHERE snapshot_ts = (SELECT MAX(snapshot_ts) FROM schema_snapshots)
),
previous AS (
    SELECT * FROM schema_snapshots
    WHERE snapshot_ts = (SELECT MAX(snapshot_ts) FROM schema_snapshots WHERE snapshot_ts < (SELECT MAX(snapshot_ts) FROM schema_snapshots))
)
SELECT
    COALESCE(l.table_name, p.table_name) AS table_name,
    COALESCE(l.column_name, p.column_name) AS column_name,
    CASE
        WHEN p.column_name IS NULL THEN 'ADDED'
        WHEN l.column_name IS NULL THEN 'REMOVED'
        WHEN l.data_type != p.data_type THEN 'TYPE_CHANGED'
        WHEN l.is_nullable != p.is_nullable THEN 'NULLABLE_CHANGED'
        ELSE 'UNCHANGED'
    END AS change_type,
    p.data_type AS old_type,
    l.data_type AS new_type
FROM latest l
FULL OUTER JOIN previous p
    ON l.table_schema = p.table_schema
    AND l.table_name = p.table_name
    AND l.column_name = p.column_name
WHERE l.column_name IS NULL
   OR p.column_name IS NULL
   OR l.data_type != p.data_type
   OR l.is_nullable != p.is_nullable;
```

---

## DLT Schema Contracts

Configure schema evolution and enforcement in DLT pipelines:

```python
import dlt

# Strict contract: raise on any schema change
@dlt.resource(
    write_disposition="merge",
    schema_contract={
        "tables": "evolve",       # allow new tables
        "columns": "freeze",      # reject new columns
        "data_type": "freeze",    # reject type changes
    }
)
def orders_resource():
    yield from api_client.get_orders()

# Permissive contract: allow evolution with logging
@dlt.resource(
    schema_contract={
        "tables": "evolve",
        "columns": "evolve",      # allow new columns
        "data_type": "discard_value",  # drop rows with type mismatches
    }
)
def events_resource():
    yield from api_client.get_events()
```

**DLT contract modes:**

| Mode | Behavior | Use When |
|------|----------|----------|
| `evolve` | Accept changes, update schema | Development, exploratory sources |
| `freeze` | Reject changes, raise error | Production, critical tables |
| `discard_value` | Drop rows that violate | Non-critical, high-volume |
| `discard_row` | Drop entire row on violation | Strict quality requirements |

---

## Alerting on Schema Changes

Automated schema change notifications:

```python
# schema_change_alert.py
import json
import requests

def check_and_alert(current_schema: dict, previous_schema: dict, webhook_url: str):
    changes = []
    for table, columns in current_schema.items():
        prev_columns = previous_schema.get(table, {})
        for col, dtype in columns.items():
            if col not in prev_columns:
                changes.append({"table": table, "column": col, "change": "ADDED", "type": dtype})
            elif prev_columns[col] != dtype:
                changes.append({"table": table, "column": col, "change": "TYPE_CHANGED",
                               "old": prev_columns[col], "new": dtype})
        for col in prev_columns:
            if col not in columns:
                changes.append({"table": table, "column": col, "change": "REMOVED"})

    if changes:
        payload = {
            "text": f"Schema changes detected ({len(changes)} changes)",
            "blocks": [{"type": "section", "text": {"type": "mrkdwn",
                "text": "\n".join(f"- {c['table']}.{c['column']}: {c['change']}" for c in changes)
            }}]
        }
        requests.post(webhook_url, json=payload)
    return changes
```

---

## Schema Migration Documentation

Track schema changes in a changelog:

```yaml
# observability/schema_changelog.yml
schema_changes:
  - date: "2025-01-15"
    table: raw.orders
    change: column_added
    column: discount_code
    type: varchar(50)
    reason: "Marketing promo tracking"
    approved_by: "@data-lead"
    downstream_impact:
      - stg_orders (add passthrough)
      - fct_order_metrics (no impact)

  - date: "2025-01-10"
    table: raw.customers
    change: type_changed
    column: phone_number
    old_type: integer
    new_type: varchar(20)
    reason: "International phone format support"
    approved_by: "@data-lead"
    downstream_impact:
      - stg_customers (cast update required)
```

**Schema change review checklist:**
1. Identify all downstream models consuming the changed table
2. Verify dbt contract compatibility
3. Update staging model column definitions
4. Run `dbt build` with `--warn-error` to validate
5. Update schema changelog
6. Notify downstream consumers via alerting channel
