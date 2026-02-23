> **Part of:** [data-observability](../SKILL.md)

# Incident Response for Data Pipelines

Workflows and templates for classifying, triaging, and resolving data incidents. A structured response prevents panic-driven debugging and ensures stakeholders stay informed.

## Incident Classification

| Category | Description | Typical Severity | Example |
|----------|------------|-----------------|---------|
| Data Quality | Incorrect values in production tables | P1 | Revenue column shows negative values |
| Pipeline Failure | Pipeline run failed or timed out | P1-P2 | dbt run failed on staging model |
| Schema Break | Upstream schema change broke downstream | P1-P2 | Source dropped a required column |
| Stale Data | Data loaded but not refreshed on schedule | P1-P2 | Dashboard shows yesterday's data at noon |
| Data Loss | Records missing or deleted unexpectedly | P0 | Production table truncated during load |
| Duplicate Load | Same batch loaded multiple times | P1 | Row count doubled overnight |

---

## Triage Workflow

Follow this sequence for every data incident:

### 1. Detect
- Alert fires from monitoring (freshness, volume, schema, or manual report)
- Log the incident start time and detection source

### 2. Assess
- Confirm the alert is valid (not a false positive)
- Determine the incident category from the table above
- Assign severity level (P0-P3)
- Identify the blast radius: which downstream tables, dashboards, and consumers are affected

### 3. Communicate
- Post initial notification to the incident channel within 15 minutes
- Use the communication template below
- Tag the data owner and relevant stakeholders

### 4. Fix
- Identify root cause (check orchestrator logs, source systems, schema diffs)
- Apply fix (re-run pipeline, update schema, restore from backup)
- Document the fix in the incident thread

### 5. Verify
- Confirm data freshness and volume are restored to normal
- Run data quality tests on affected tables
- Verify downstream dashboards show correct data
- Close the alert

### 6. Postmortem
- Conduct postmortem within 48 hours of resolution
- Use the postmortem template below
- Track follow-up action items to completion

---

## Impact Assessment Checklist

Run through this checklist within 30 minutes of incident detection:

```markdown
## Impact Assessment

- [ ] **Affected tables:** List all tables with incorrect/stale data
- [ ] **Affected dashboards:** List dashboards consuming affected tables
- [ ] **Affected stakeholders:** Identify teams relying on affected data
- [ ] **Financial impact:** Does this affect revenue reporting or billing?
- [ ] **Regulatory impact:** Does this affect compliance data?
- [ ] **Customer-facing:** Is incorrect data visible to end users?
- [ ] **Blast radius:** How many downstream models are affected?
- [ ] **Recovery estimate:** Expected time to resolve
```

---

## Communication Templates

### Initial Notification

```markdown
**DATA INCIDENT -- [SEVERITY]**

**Summary:** [One sentence describing the issue]
**Detected at:** [timestamp]
**Affected systems:** [list of tables/dashboards]
**Status:** Investigating
**Owner:** @[data-engineer]
**Next update:** [timestamp, within 1 hour for P0/P1]

We are actively investigating. Please hold off on using [affected dashboard/table]
until this is resolved.
```

### Status Update

```markdown
**UPDATE -- [SEVERITY] Data Incident**

**Root cause:** [identified / still investigating]
**Fix status:** [in progress / applied / pending verification]
**ETA to resolution:** [estimate]
**Impact:** [updated blast radius if changed]

Next update in [timeframe].
```

### Resolution

```markdown
**RESOLVED -- Data Incident**

**Summary:** [what happened]
**Root cause:** [why it happened]
**Fix applied:** [what was done]
**Verified at:** [timestamp]
**Data is now:** [fresh and accurate / backfilled to X date]
**Postmortem scheduled:** [date]

All affected dashboards and tables have been verified. Normal operations resumed.
```

---

## Postmortem Template

```markdown
# Data Incident Postmortem

**Date:** [incident date]
**Duration:** [start time] to [resolution time] ([total duration])
**Severity:** [P0/P1/P2/P3]
**Author:** [name]

## Summary
[2-3 sentences describing the incident and impact]

## Timeline
| Time | Event |
|------|-------|
| HH:MM | Alert fired / Issue reported |
| HH:MM | Investigation started |
| HH:MM | Root cause identified |
| HH:MM | Fix applied |
| HH:MM | Verification complete, incident resolved |

## Root Cause
[Detailed explanation of why the incident occurred]

## Impact
- **Data affected:** [tables, row counts]
- **Duration of bad data:** [time window]
- **Downstream impact:** [dashboards, reports, consumers]

## What Went Well
- [Detection was fast / alerting worked]
- [Communication was timely]

## What Could Be Improved
- [Monitoring gap that allowed this]
- [Process improvement needed]

## Action Items
| Item | Owner | Due Date | Status |
|------|-------|----------|--------|
| Add freshness check for X | @engineer | YYYY-MM-DD | Open |
| Update schema contract for Y | @engineer | YYYY-MM-DD | Open |
```

---

## Recovery and Backfill Patterns

### dbt Backfill
```bash
# Re-run specific models with full refresh
dbt run --select stg_orders fct_order_metrics --full-refresh

# Re-run from a specific date (incremental models)
dbt run --select stg_orders --vars '{"backfill_start": "2025-01-01"}'
```

### Dagster Backfill
```python
# Backfill specific partitions via Dagster UI or CLI
dagster asset backfill --asset-key fct_orders --partition-range 2025-01-01...2025-01-15
```

### Manual SQL Backfill
```sql
-- Delete and re-insert for a specific date range
BEGIN;
DELETE FROM marts.fct_orders WHERE order_date BETWEEN '2025-01-01' AND '2025-01-15';
INSERT INTO marts.fct_orders
    SELECT * FROM staging.stg_orders WHERE order_date BETWEEN '2025-01-01' AND '2025-01-15';
COMMIT;

-- Verify backfill
SELECT COUNT(*) AS backfilled_rows,
       MIN(order_date) AS min_date,
       MAX(order_date) AS max_date
FROM marts.fct_orders
WHERE order_date BETWEEN '2025-01-01' AND '2025-01-15';
```
