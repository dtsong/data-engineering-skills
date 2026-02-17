## Contents

- [Structure](#structure)
- [Required Columns](#required-columns)
- [Completeness Check](#completeness-check)
- [Generation Automation](#generation-automation)
- [Client Presentation](#client-presentation)

---

# Mapping Document — Procedural Reference

> **Part of:** [client-delivery](../SKILL.md)

The mapping document records every source-to-target field transformation.

## Structure

```markdown
# Mapping Document — {{CLIENT_NAME}}

## Source: {{SOURCE_FILE}}
## Target: {{TARGET_TABLE}}

| Source Column | Target Column | Data Type Change | Transformation | Business Rule |
|--------------|--------------|-----------------|----------------|---------------|
| CustID | customer_id | VARCHAR → INT | CAST, trim whitespace | Primary key |
| First Name | first_name | — | LOWER, TRIM | — |
| DOB | date_of_birth | VARCHAR → DATE | Parse MM/DD/YYYY | Must be > 1900-01-01 |
| Status | status_code | — | Map: "Active"→"A", "Inactive"→"I" | Lookup table |
| — | created_at | — | CURRENT_TIMESTAMP | System-generated |
| Legacy_Field | — | — | Dropped | No business use per client |
```

## Required Columns

| Column | Description |
|--------|-------------|
| Source Column | Original column name from source file |
| Target Column | Destination column name in target table |
| Data Type Change | Original → target type, or "—" if unchanged |
| Transformation | SQL/Python logic applied |
| Business Rule | Client-provided rule or constraint |

## Completeness Check

Every source column must appear in the mapping. Columns dropped must be documented with rationale. Columns added (surrogate keys, timestamps) must note "System-generated."

## Generation Automation

```bash
# Generate mapping document template from profiler output
python scripts/generate_mapping.py \
    --profiler-dir data/profiling/ \
    --output deliverables/mapping-document.md
```

## Client Presentation

Use the mapping document as a reference during technical review. Walk through transformations column-by-column with client stakeholders.
