## Contents

- [Structure](#structure)
- [Severity Levels](#severity-levels)
- [Generation from Artifacts](#generation-from-artifacts)
- [Generation Automation](#generation-automation)
- [Client Presentation](#client-presentation)

---

# Quality Report — Procedural Reference

> **Part of:** [client-delivery](../SKILL.md)

The quality report is the primary client-facing deliverable. It summarizes data quality findings, severity-ranked, with actionable recommendations.

## Structure

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

## Severity Levels

| Severity | Criteria | Action Required |
|----------|----------|-----------------|
| Critical | Data loss risk, PII exposure, >50% nulls on key column | Must fix before production |
| Warning | Quality degradation, mixed types, inconsistent formats | Should fix; document if deferred |
| Info | Cosmetic issues, naming conventions, minor nulls | Fix if time permits |

## Generation from Artifacts

- **dbt test results:** Parse `target/run_results.json` for test failures. Map test names to columns.
- **Profiler output:** Parse `data/profiling/*.json` for column-level issues.
- **Merge:** Combine profiler issues + dbt test failures. Deduplicate. Assign severity.

## Generation Automation

```bash
# After dbt run + dbt test:
python scripts/generate_quality_report.py \
    --profiler-dir data/profiling/ \
    --dbt-target dbt_project/target/ \
    --output deliverables/quality-report.md
```

Parse `target/run_results.json` for test results, `target/manifest.json` for model metadata, `target/sources.json` for source freshness.

## Client Presentation

Lead with the executive summary and overall quality score. Show critical issues first; group by table for walkthrough. Convert to PDF with pandoc:

```bash
pandoc deliverables/quality-report.md -o deliverables/quality-report.pdf \
    --pdf-engine=xelatex -V geometry:margin=1in
```
