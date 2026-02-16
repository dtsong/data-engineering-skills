## Contents

- [Overview](#overview)
- [Tier Definitions](#tier-definitions)
- [Tier Selection Decision Tree](#tier-selection-decision-tree)
- [Per-Tier Tool Configuration](#per-tier-tool-configuration)
- [Relationship to Organizational Security Tiers](#relationship-to-organizational-security-tiers)
- [Client Conversation Guidance](#client-conversation-guidance)

---

# Consulting Security Tier Model

> **Shared reference** — used by consulting-engagement-skill, dbt-skill, dlt-extraction-skill, duckdb-local-skill

## Overview

Consulting security tiers describe **data access levels during an engagement**, not organizational security posture. A Tier 1 (Cloud-Native) organization may still restrict a consultant to Schema-Only access until trust is established.

Three tiers: **Schema-Only → Sampled → Full Access**. Start at the lowest tier that enables the engagement deliverables.

---

## Tier Definitions

### Tier 1: Schema-Only

**What you receive:** DDL exports, column names, data types, row counts, constraint definitions. No actual data values.

**What you can deliver:** Data model assessment, naming convention audit, schema normalization plan, preliminary cleaning architecture, dbt project scaffold with source definitions.

**Typical context:** Early discovery phase, pre-NDA, regulated industries (healthcare, finance), client evaluating consultant fit.

### Tier 2: Sampled

**What you receive:** Representative sample (10-100 rows per table), typically anonymized or masked. Schema metadata plus enough data to validate patterns.

**What you can deliver:** Everything in Tier 1 plus: data profiling report, cleaning pattern identification, deduplication strategy with test cases, transformation logic validated against sample, quality rules with concrete thresholds.

**Typical context:** Post-NDA, active engagement, client comfortable sharing non-production subsets. Most consulting engagements operate here.

### Tier 3: Full Access

**What you receive:** Full dataset access — development or production copy. May include PII, financial data, or other sensitive content.

**What you can deliver:** Everything in Tier 2 plus: complete pipeline execution, full data quality report with exact metrics, production-ready dbt models tested against real data, performance benchmarks, anomaly detection with real baselines.

**Typical context:** Trusted long-term engagement, client-provisioned sandbox environment, consultant on-site or on VPN. Requires explicit written authorization.

---

## Tier Selection Decision Tree

```
Start: What data can the client share?
│
├─ Only schema/DDL, no data values → Tier 1 (Schema-Only)
│
├─ A representative sample (anonymized OK) → Tier 2 (Sampled)
│   └─ Confirm: sample covers edge cases (nulls, duplicates, format variants)
│
└─ Full dataset in a sandbox environment → Tier 3 (Full Access)
    └─ Confirm: written authorization + data handling agreement signed
```

**Escalation path:** Start Tier 1 → deliver schema assessment → client gains confidence → escalate to Tier 2 with sample → deliver profiling report → escalate to Tier 3 if needed for production validation.

---

## Per-Tier Tool Configuration

### DuckDB

| Setting | Tier 1 | Tier 2 | Tier 3 |
|---------|--------|--------|--------|
| Data source | Schema DDL files only | Sample CSV/Parquet | Full dataset files |
| Memory limit | Default | Default | Set based on file size |
| Output | Schema analysis queries | Profiling queries + results | Full pipeline execution |

### dbt

| Setting | Tier 1 | Tier 2 | Tier 3 |
|---------|--------|--------|--------|
| profiles.yml target | `schema_only` (no warehouse) | `dev` (DuckDB with sample) | `dev` (DuckDB/warehouse with full data) |
| Sources | Defined from DDL, no freshness | Defined + tested against sample | Full freshness + loaded_at |
| Tests | Schema tests only (types, constraints) | Schema + data tests on sample | Full test suite with real thresholds |
| Seeds | Empty or schema-only stubs | Sample data as seeds for testing | Not needed (real data available) |

### DLT

| Setting | Tier 1 | Tier 2 | Tier 3 |
|---------|--------|--------|--------|
| Pipeline mode | Schema discovery only (`dlt.schema`) | Extract sample + load to DuckDB | Full extract + load |
| Schema contracts | Define from DDL | Validate against sample | Enforce on full data |
| Destinations | None (schema analysis) | DuckDB local | DuckDB dev → warehouse prod |

---

## Relationship to Organizational Security Tiers

The existing security-compliance-patterns.md defines **organizational** tiers:
- Tier 1 Cloud-Native: Standard cloud security
- Tier 2 Regulated: SOC2/HIPAA/PCI environments
- Tier 3 Air-Gapped: Maximum restriction

These are **orthogonal** to consulting tiers. A regulated (Org Tier 2) client may grant Full Access (Consulting Tier 3) within their controlled environment. An unregulated startup (Org Tier 1) may still restrict to Schema-Only (Consulting Tier 1) during evaluation.

| | Org Tier 1 (Cloud-Native) | Org Tier 2 (Regulated) | Org Tier 3 (Air-Gapped) |
|---|---|---|---|
| Consulting Tier 1 | Schema export from cloud | Schema via secure transfer | Schema printout/PDF |
| Consulting Tier 2 | Sample via shared drive | Sample via encrypted channel | Sample on-site only |
| Consulting Tier 3 | Dev environment access | Sandbox with audit logging | On-premises workstation |

---

## Client Conversation Guidance

**Opening question:** "What level of data access are you comfortable providing for this engagement?"

**Tier 1 pitch:** "We can start with just your schema definitions — column names, types, and relationships. This lets us assess your data model and propose a cleaning architecture without seeing any actual data."

**Tier 2 pitch:** "A representative sample of 50-100 rows per table lets us validate our cleaning logic against real patterns. We can work with anonymized data if needed."

**Tier 3 pitch:** "For production-ready deliverables with accurate quality metrics, we'd need access to the full dataset in a sandbox environment. We'll sign a data handling agreement and work within your security controls."

**Handling resistance:** Never pressure for higher tiers. Document what can and cannot be delivered at the current tier. Let deliverable quality drive tier escalation naturally.
