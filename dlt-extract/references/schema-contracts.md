## Contents

- [Default Schema Contracts](#default-schema-contracts)
- [Strict Contracts](#strict-contracts)
- [Pydantic Models as Schema](#pydantic-models-as-schema)
- [Drift Detection](#drift-detection)
- [Contract Strategies for Cleaning](#contract-strategies-for-cleaning)
- [Per-Table Contracts](#per-table-contracts)

---

# DLT Schema Contracts

> **Part of:** [dlt-extract](../SKILL.md)

## Default Schema Contracts

DLT defaults to full evolution — new tables, columns, and type changes are accepted automatically:

```python
@dlt.resource(
    schema_contract={"tables": "evolve", "columns": "evolve", "data_type": "evolve"}
)
def flexible_source():
    yield from read_files()
```

| Contract Key | Controls | Default |
|-------------|----------|---------|
| `tables` | New table creation | `evolve` |
| `columns` | New column addition | `evolve` |
| `data_type` | Column type changes | `evolve` |

Use `evolve` during discovery and initial development. Tighten contracts before production deployment.

## Strict Contracts

Lock schema to reject unexpected changes:

```python
@dlt.resource(
    schema_contract={"tables": "freeze", "columns": "freeze", "data_type": "freeze"}
)
def production_source():
    """Fail loudly on any schema deviation."""
    yield from read_files()
```

| Mode | Behavior | When to Use |
|------|----------|-------------|
| `evolve` | Allow changes silently | Discovery, prototyping |
| `freeze` | Raise exception on change | Production, compliance |
| `discard_rows` | Drop rows with violations | Strict validation, data quality |
| `discard_columns` | Drop unknown columns, keep row | Flexible with guardrails |

**Freeze** is recommended for production consulting pipelines where schema changes should trigger review rather than silent acceptance.

## Pydantic Models as Schema

Define expected columns with types using Pydantic models:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import date

class OrderRecord(BaseModel):
    order_id: str
    customer_name: str
    amount: float
    order_date: date
    status: str
    notes: Optional[str] = None

@dlt.resource(columns=OrderRecord, write_disposition="merge", primary_key="order_id")
def orders():
    """Schema validated against Pydantic model at load time."""
    yield from read_order_files()
```

Pydantic models provide:
- Type validation at ingestion time
- Clear documentation of expected schema
- IDE autocompletion and type checking during development
- Automatic column type hints for the destination

**Combining Pydantic with contracts:** Use Pydantic for column definitions and contracts for evolution policy:

```python
@dlt.resource(
    columns=OrderRecord,
    schema_contract={"columns": "freeze", "data_type": "freeze"}
)
def strict_orders():
    yield from read_order_files()
```

## Drift Detection

DLT reports schema changes in the load info after each run:

```python
load_info = pipeline.run(source)

# Check for schema changes
for package in load_info.load_packages:
    for table in package.schema_update:
        print(f"Schema change in {table}:")
        for column, change in package.schema_update[table].items():
            print(f"  {column}: {change}")
```

**Handling new columns:** When using `evolve`, new columns appear automatically. Monitor for unexpected additions:

```python
def check_schema_drift(pipeline, expected_tables: dict):
    """Alert on unexpected schema changes."""
    schema = pipeline.default_schema
    for table_name, expected_cols in expected_tables.items():
        actual_cols = set(schema.tables.get(table_name, {}).get("columns", {}).keys())
        unexpected = actual_cols - set(expected_cols) - {"_dlt_load_id", "_dlt_id"}
        if unexpected:
            print(f"WARNING: Unexpected columns in {table_name}: {unexpected}")
```

**Schema export:** Export the current schema for version control:

```python
# Export schema to YAML
schema_dict = pipeline.default_schema.to_dict()

import yaml
with open("schemas/current_schema.yaml", "w") as f:
    yaml.dump(schema_dict, f)
```

## Contract Strategies for Cleaning

Phase-based approach for consulting engagements:

| Phase | Tables | Columns | Data Types | Purpose |
|-------|--------|---------|------------|---------|
| Discovery | `evolve` | `evolve` | `evolve` | Learn source schema |
| Validation | `evolve` | `evolve` | `discard_rows` | Find type issues |
| Staging | `freeze` | `discard_columns` | `freeze` | Controlled acceptance |
| Production | `freeze` | `freeze` | `freeze` | Full lockdown |

**Discovery workflow:**
1. Run pipeline with full `evolve` — accept everything
2. Inspect generated schema with `pipeline.default_schema`
3. Export schema and define Pydantic models from discovered types
4. Switch to `freeze` contracts with Pydantic validation
5. Handle drift through explicit schema migrations

## Per-Table Contracts

Apply different strictness levels to different source tables:

```python
@dlt.source
def multi_table_source():
    return [reference_data(), event_data()]

@dlt.resource(
    schema_contract={"columns": "freeze", "data_type": "freeze"},
    write_disposition="replace",
)
def reference_data():
    """Reference tables: strict schema, full replace on each load."""
    yield from read_reference_files()

@dlt.resource(
    schema_contract={"columns": "evolve", "data_type": "discard_rows"},
    write_disposition="append",
)
def event_data():
    """Event data: allow new columns, reject type mismatches."""
    yield from read_event_files()
```

**Rule of thumb:**
- Reference/dimension data: `freeze` columns and types, `replace` disposition
- Transactional/event data: `evolve` columns, `freeze` or `discard_rows` types, `append` disposition
- Staging/raw data: full `evolve` during initial load, tighten after validation
