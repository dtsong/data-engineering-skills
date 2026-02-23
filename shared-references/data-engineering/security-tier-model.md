## Contents

- [Overview](#overview)
- [Tier Definitions](#tier-definitions)
- [Tier Selection Decision Tree](#tier-selection-decision-tree)
- [Per-Tier Tool Configuration](#per-tier-tool-configuration)
- [Relationship to Organizational Security Tiers](#relationship-to-organizational-security-tiers)

---

# Consulting Security Tier Model

> **Shared reference** — used by client-delivery, dbt-transforms, dlt-extract, duckdb

## Overview

Consulting security tiers describe **data access levels during an engagement** — not organizational security posture. Three tiers: **Schema-Only → Sampled → Full Access**. Start at the lowest tier that enables deliverables.

---

## Tier Definitions

### Tier 1: Schema-Only

**What you receive:** DDL exports, column names, data types, row counts, constraint definitions. No actual data values.

**What you can deliver:** Data model assessment, naming convention audit, schema normalization plan, preliminary cleaning architecture, dbt project scaffold with source definitions.

**Typical context:** Early discovery, pre-NDA, regulated industries, or evaluation phase.

### Tier 2: Sampled

**What you receive:** Representative sample (10-100 rows per table), typically anonymized or masked. Schema metadata plus enough data to validate patterns.

**What you can deliver:** Everything in Tier 1 plus: data profiling report, cleaning pattern identification, deduplication strategy with test cases, transformation logic validated against sample, quality rules with concrete thresholds.

**Typical context:** Post-NDA, active engagement, non-production data. Most engagements operate here.

### Tier 3: Full Access

**What you receive:** Full dataset access — development or production copy. May include PII, financial data, or other sensitive content.

**What you can deliver:** Everything in Tier 2 plus: complete pipeline execution, full data quality report with exact metrics, production-ready dbt models tested against real data, performance benchmarks, anomaly detection with real baselines.

**Typical context:** Trusted long-term engagement, sandbox environment, explicit written authorization required.

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
| profiles.yml target | `schema_only` (no warehouse) | `dev` (DuckDB, sample) | `dev` (DuckDB/warehouse, full data) |
| Sources | Defined from DDL, no freshness | Defined + tested against sample | Full freshness + loaded_at |
| Tests | Schema tests only | Schema + data tests on sample | Full test suite |
| Seeds | Schema-only stubs | Sample seeds | Not needed |

### DLT

| Setting | Tier 1 | Tier 2 | Tier 3 |
|---------|--------|--------|--------|
| Pipeline mode | Schema discovery only (`dlt.schema`) | Extract sample + load to DuckDB | Full extract + load |
| Schema contracts | Define from DDL | Validate against sample | Enforce on full data |
| Destinations | None (schema analysis) | DuckDB local | DuckDB dev → warehouse prod |

---

## Relationship to Organizational Security Tiers

Consulting tiers are **orthogonal** to organizational tiers (defined in security-compliance-patterns.md). A regulated client (Org Tier 2) may grant Full Access (Consulting Tier 3) in a controlled environment; an unregulated client (Org Tier 1) may restrict to Schema-Only during evaluation.

| | Org Tier 1 (Cloud-Native) | Org Tier 2 (Regulated) | Org Tier 3 (Air-Gapped) |
|---|---|---|---|
| Consulting Tier 1 | Schema export from cloud | Schema via secure transfer | Schema printout/PDF |
| Consulting Tier 2 | Sample via shared drive | Sample via encrypted channel | Sample on-site only |
| Consulting Tier 3 | Dev environment access | Sandbox with audit logging | On-premises workstation |

---

## Full Tier Model (Tiers 0–4)

Extended model adding Tier 0 (pre-engagement) and subdivided production access for AI-assisted workflows.

| Tier | Name | Data Access | Typical Context |
|------|------|-------------|-----------------|
| **0** | External Schema-Only | Published docs, ERDs, data dictionaries; no live access | Pre-engagement, RFP, architecture review |
| **1** | Local Execution Permitted | DDL exports, column metadata, row counts; local DuckDB on schema stubs | Early discovery, pre-NDA, regulated industries (= Consulting Tier 1) |
| **2** | Supervised Non-Production Access | Sample (10-100 rows), anonymized/masked; non-production | Active engagement, post-NDA (= Consulting Tier 2) |
| **3** | Supervised Production Access | Read-only production; human approval for all writes | Trusted engagement, audit logging, client supervision |
| **4** | Full Autonomous Access | Full read/write via MCP; automated guardrails | Long-term retainer, AI workflows, audit trail |

**Default:** Start at Tier 1. Escalate only when deliverable requirements demand it and client authorization is documented.

---

## ENGAGEMENT.yaml Manifest Schema

Place `ENGAGEMENT.yaml` at the engagement root. See [ENGAGEMENT.yaml.template](../../templates/engagement/ENGAGEMENT.yaml.template) for a ready-to-use starting point.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `engagement.id` | string | Unique identifier |
| `engagement.client` | string | Client name |
| `engagement.lead` | string | Consultant name |
| `engagement.created` | date | ISO 8601 creation date |
| `access.tier` | integer (0-4) | Current tier |
| `access.tier_approved_by` | string | Approver name |
| `access.tier_approval_date` | date | Approval date |
| `audit.log_path` | string | Audit log path |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `engagement.last_reviewed` | date | Last review date |
| `access.tier_approval_artifact` | string | Email, ticket, or agreement URL |
| `access.granted_permissions` | list | Granted permissions |
| `access.denied_permissions` | list | Denied permissions |
| `sources` | list | Source inventory (name, type, location, classification) |
| `audit.require_log_on_every_operation` | boolean | Log every data operation |

---

## Tier Transition Protocol

1. **Approval** — Get written authorization (email, ticket, or signed agreement).
2. **Manifest update** — Set `access.tier`, `tier_approved_by`, `tier_approval_date`, `tier_approval_artifact` in `ENGAGEMENT.yaml`. Commit.
3. **Audit log entry** — `[ISO timestamp] TIER_CHANGE: {old} → {new}, approved_by: {name}, artifact: {link}`

**Downgrade:** same protocol; access revocation is immediate.

---

## Graceful Degradation

Block operations requiring a higher tier and emit:

```
BLOCKED: Operation "{operation}" requires Tier {required} access.
Current tier: {current} ({tier_name}).
To proceed: request tier escalation per the Tier Transition Protocol.
See: ENGAGEMENT.yaml → access.tier
```

Never silently downgrade output quality — state what is missing and what tier enables it.

