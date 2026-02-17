## Contents

- [Structure](#structure)
- [Linking to Decisions](#linking-to-decisions)
- [Maintenance](#maintenance)
- [Client Presentation](#client-presentation)

---

# Transform Log — Procedural Reference

> **Part of:** [client-delivery](../SKILL.md)

The transform log is a chronological record of every transformation applied during the engagement.

## Structure

```markdown
# Transform Log — {{CLIENT_NAME}}

## Entry 001: Initial Load
- **Date:** YYYY-MM-DD
- **Action:** Loaded raw files into DuckDB staging
- **Files:** clients.csv (15,234 rows), orders.xlsx (42,891 rows)
- **Row counts:** clients: 15,234 → 15,234, orders: 42,891 → 42,891
- **Decision:** ADR-001 (Tier 2 selected)

## Entry 002: Deduplication
- **Date:** YYYY-MM-DD
- **Action:** Removed duplicate rows from clients table
- **Before:** 15,234 rows
- **After:** 14,987 rows (247 duplicates removed)
- **Decision:** ADR-003 (Deduplicate on customer_id + email)
- **dbt model:** stg_raw__clients

## Entry 003: Type Standardization
- **Date:** YYYY-MM-DD
- **Action:** Cast date columns from VARCHAR to DATE
- **Affected columns:** date_of_birth, registration_date
- **Failures:** 12 rows with unparseable dates (set to NULL, flagged in quality report)
- **Decision:** ADR-004 (NULL for unparseable dates, log in exceptions table)
```

## Linking to Decisions

Every transform log entry that involves a judgment call must link to an ADR entry in `decisions.md`. This creates an audit trail from raw data to final output.

## Maintenance

The transform log is maintained manually during the engagement. Each dbt model change, data decision, or pipeline modification gets an entry. Number entries sequentially. Include before/after row counts for every data-modifying step.

## Client Presentation

Walk through the transform log to show methodology and decision trail. Leave the runbook as the final handoff document.
