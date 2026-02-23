## Contents

- [Overview](#overview)
- [Tier Definitions](#tier-definitions)
- [Tier Selection Decision Tree](#tier-selection-decision-tree)
- [Per-Tier Tool Configuration](#per-tier-tool-configuration)
- [Relationship to Organizational Security Tiers](#relationship-to-organizational-security-tiers)
- [Client Conversation Guidance](#client-conversation-guidance)

---

# Consulting Security Tier Model

> **Shared reference** — used by client-delivery, dbt-transforms, dlt-extract, duckdb

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

## Full Tier Model (Tiers 0–4)

The three consulting tiers above (Schema-Only, Sampled, Full Access) cover most engagements. The extended model below adds Tier 0 (pre-engagement) and subdivides production access for organizations adopting AI-assisted workflows.

| Tier | Name | Data Access | Typical Context |
|------|------|-------------|-----------------|
| **0** | External Schema-Only | Published documentation, ERDs, data dictionaries — no live system access | Pre-engagement evaluation, RFP response, architecture review |
| **1** | Local Execution Permitted | DDL exports, column metadata, row counts; local DuckDB execution on schema stubs | Early discovery, pre-NDA, regulated industries (= Consulting Tier 1) |
| **2** | Supervised Non-Production Access | Representative sample (10-100 rows), anonymized/masked; non-production environment | Active engagement, post-NDA, validated cleaning patterns (= Consulting Tier 2) |
| **3** | Supervised Production Access | Read access to production data; human-in-the-loop for all write operations | Trusted engagement with audit logging; consultant operates under client supervision |
| **4** | Full Autonomous Access | Full read/write via MCP or direct connection; automated guardrails replace human review | Long-term retainer, AI-integrated workflows, programmatic access with audit trail |

**Default:** Start at Tier 1. Escalate only when deliverable requirements demand it and client authorization is documented.

---

## ENGAGEMENT.yaml Manifest Schema

Every engagement should have an `ENGAGEMENT.yaml` at its root. This manifest declares the security tier, permissions, and audit requirements for the engagement.

See [ENGAGEMENT.yaml.template](../../templates/engagement/ENGAGEMENT.yaml.template) for a ready-to-use starting point.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `engagement.id` | string | Unique engagement identifier |
| `engagement.client` | string | Client name |
| `engagement.lead` | string | Consultant name |
| `engagement.created` | date | ISO 8601 creation date |
| `access.tier` | integer (0-4) | Current security tier |
| `access.tier_approved_by` | string | Person who approved the tier |
| `access.tier_approval_date` | date | Date of tier approval |
| `audit.log_path` | string | Path to the access audit log |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `engagement.last_reviewed` | date | Last tier review date |
| `access.tier_approval_artifact` | string | Link to email, ticket, or signed agreement |
| `access.granted_permissions` | list | Explicitly granted permission strings |
| `access.denied_permissions` | list | Explicitly denied permission strings |
| `sources` | list | Source inventory with name, type, location, classification |
| `audit.require_log_on_every_operation` | boolean | Whether every data operation must be logged |

---

## Tier Transition Protocol

Tier changes follow a three-step process:

1. **Approval** — Client or client-designated approver authorizes the new tier in writing (email, ticket, or signed agreement).
2. **Manifest update** — Update `ENGAGEMENT.yaml`: set `access.tier`, `tier_approved_by`, `tier_approval_date`, and `tier_approval_artifact`. Commit the change.
3. **Audit log entry** — Record the transition in the audit log: `[ISO timestamp] TIER_CHANGE: {old_tier} → {new_tier}, approved_by: {name}, artifact: {link}`.

**Downgrade:** Follow the same protocol. Revoking access is immediate; the manifest update documents the change.

---

## Graceful Degradation

When an operation requires a higher tier than the current `access.tier`, the skill must block the operation and emit a structured message:

```
BLOCKED: Operation "{operation}" requires Tier {required} access.
Current tier: {current} ({tier_name}).
To proceed: request tier escalation per the Tier Transition Protocol.
See: ENGAGEMENT.yaml → access.tier
```

Skills must never silently downgrade output quality. If a deliverable cannot be produced at the current tier, state what is missing and what tier would enable it.

---

## Client Conversation Guidance

**Opening question:** "What level of data access are you comfortable providing for this engagement?"

**Tier 1 pitch:** "We can start with just your schema definitions — column names, types, and relationships. This lets us assess your data model and propose a cleaning architecture without seeing any actual data."

**Tier 2 pitch:** "A representative sample of 50-100 rows per table lets us validate our cleaning logic against real patterns. We can work with anonymized data if needed."

**Tier 3 pitch:** "For production-ready deliverables with accurate quality metrics, we'd need access to the full dataset in a sandbox environment. We'll sign a data handling agreement and work within your security controls."

**Handling resistance:** Never pressure for higher tiers. Document what can and cannot be delivered at the current tier. Let deliverable quality drive tier escalation naturally.
