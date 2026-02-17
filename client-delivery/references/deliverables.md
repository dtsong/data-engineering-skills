## Contents

- [Quality Report](#quality-report)
- [Mapping Document](#mapping-document)
- [Transform Log](#transform-log)
- [Generation Automation](#generation-automation)
- [Client Presentation Format](#client-presentation-format)

# Deliverables — Procedural Reference

> **Part of:** [client-delivery](../SKILL.md)

---

## Quality Report

The quality report is the primary client-facing deliverable. It summarizes data quality findings, severity-ranked, with actionable recommendations.

### Structure

```markdown
# Data Quality Report — {{CLIENT_NAME}}

## Executive Summary
- Total tables profiled: N
- Critical issues: N
- Warnings: N
- Overall quality score: X/10

## Methodology
- Security tier: Tier N
- Tools: schema_profiler.py, dbt tests, DuckDB queries
- Date range analyzed: YYYY-MM-DD to YYYY-MM-DD

## Findings by Table

### {{TABLE_NAME}}
| Column | Issue | Severity | Detail | Recommendation |
|--------|-------|----------|--------|----------------|
| email | PII detected | critical | Column contains email addresses | Mask or hash before loading |
| status | Mixed types | warning | 3% numeric values in string column | Clean in staging model |

## Recommendations
1. [Critical] ...
2. [Warning] ...
3. [Info] ...
```

### Severity Levels

| Severity | Criteria | Action Required |
|----------|----------|-----------------|
| Critical | Data loss risk, PII exposure, >50% nulls on key column | Must fix before production |
| Warning | Quality degradation, mixed types, inconsistent formats | Should fix; document if deferred |
| Info | Cosmetic issues, naming conventions, minor nulls | Fix if time permits |

### Generation from Artifacts

- **dbt test results:** Parse `target/run_results.json` for test failures. Map test names to columns.
- **Profiler output:** Parse `data/profiling/*.json` for column-level issues.
- **Merge:** Combine profiler issues + dbt test failures. Deduplicate. Assign severity.

---

## Mapping Document

The mapping document records every source-to-target field transformation.

### Structure

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

### Required Columns

| Column | Description |
|--------|-------------|
| Source Column | Original column name from source file |
| Target Column | Destination column name in target table |
| Data Type Change | Original → target type, or "—" if unchanged |
| Transformation | SQL/Python logic applied |
| Business Rule | Client-provided rule or constraint |

### Completeness Check

Every source column must appear in the mapping. Columns dropped must be documented with rationale. Columns added (surrogate keys, timestamps) must note "System-generated."

---

## Transform Log

The transform log is a chronological record of every transformation applied during the engagement.

### Structure

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

### Linking to Decisions

Every transform log entry that involves a judgment call must link to an ADR entry in `decisions.md`. This creates an audit trail from raw data to final output.

---

## Generation Automation

### From dbt Artifacts

```bash
# After dbt run + dbt test:
# Parse target/run_results.json for test results
# Parse target/manifest.json for model metadata
# Parse target/sources.json for source freshness

python scripts/generate_quality_report.py \
    --profiler-dir data/profiling/ \
    --dbt-target dbt_project/target/ \
    --output deliverables/quality-report.md
```

### From Profiler Output

```bash
# Generate mapping document template from profiler output
python scripts/generate_mapping.py \
    --profiler-dir data/profiling/ \
    --output deliverables/mapping-document.md
```

### Manual Sections

The transform log is maintained manually during the engagement. Each dbt model change, data decision, or pipeline modification gets an entry.

---

## Client Presentation Format

### Markdown to PDF

```bash
# Using pandoc (recommended)
pandoc deliverables/quality-report.md -o deliverables/quality-report.pdf \
    --pdf-engine=xelatex -V geometry:margin=1in

# Using grip (GitHub-flavored markdown preview)
grip deliverables/quality-report.md --export deliverables/quality-report.html
```

### Presentation Tips

- Lead with the executive summary and overall quality score.
- Show critical issues first; group by table for walkthrough.
- Use the mapping document as a reference during technical review.
- Walk through the transform log to show methodology and decision trail.
- Leave the runbook as the final handoff document.
