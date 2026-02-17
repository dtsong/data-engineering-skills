---
name: client-delivery
description: "Use this skill when managing a consulting data cleaning engagement. Covers engagement setup, schema profiling, security tier selection, project scaffolding, deliverable generation, and client handoff. Common phrases: \"set up a cleaning project\", \"profile this schema\", \"data cleaning engagement\", \"generate deliverables\", \"client handoff\". Do NOT use for writing dbt models (use dbt-transforms), DuckDB queries (use duckdb), or pipeline orchestration (use data-pipelines)."
model_tier: analytical
version: 1.0.0
---

# Consulting Engagement Skill for Claude

Guides data cleaning engagements from discovery through client handoff. Microsoft-heavy environments, file-based sources, 1-2 day delivery.

## When to Use This Skill

**Activate when:**
- Setting up a new cleaning engagement for a client
- Profiling client schemas and source files
- Selecting the appropriate security tier for data access
- Scaffolding the project directory and templates
- Generating client deliverables (quality report, mapping doc, transform log)
- Preparing for client handoff and post-engagement support

**Don't use for:** dbt model writing (use `dbt-transforms`), DuckDB analytical queries (use `duckdb`), DLT pipeline building (use `dlt-extract`), pipeline scheduling or orchestration (use `data-pipelines`).

## Scope Constraints

- Consulting engagement lifecycle only: discovery, profiling, development, validation, delivery.
- Delegates to `dbt-transforms` for transformation code generation.
- Delegates to `duckdb` for local analytical queries.
- Delegates to `dlt-extract` for pipeline building.
- Never hardcode credentials. Reference environment variables and `.env` templates.

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| medium | Sonnet | Opus, Haiku | Haiku |

## Core Principles

1. **Tier-first** — Select the security tier before touching any data. The tier determines what tools you configure, what data you request, and what you deliver.
2. **Deliverable-driven** — Every step produces a client-facing artifact. If a step does not contribute to a deliverable, question whether it belongs.
3. **Portable** — Engagement output must work without the consultant. READMEs, runbooks, and documented environment variables ensure the client can maintain the pipeline independently.
4. **Incremental trust** — Start Schema-Only (Tier 1), escalate to Sampled (Tier 2) or Full Access (Tier 3) as trust builds. Document each escalation in `decisions.md`.
5. **Tool-agnostic** — The methodology works regardless of the target warehouse. DuckDB for local dev, Snowflake/BigQuery/Postgres for production.

---

## Engagement Lifecycle

### Phase 1: Discovery

Understand the client's data landscape, pain points, and constraints. Identify source files, target systems, and security requirements. **Outputs:** engagement README, security tier decision (ADR-001), source file inventory.

### Phase 2: Profiling

Run schema profiling against source files at the permitted tier level. Identify data quality issues, type inconsistencies, PII columns, and relationship patterns. **Outputs:** profiler JSON output, quality issue inventory, column-level statistics.

### Phase 3: Development

Build the cleaning pipeline: dbt models for transformations, DuckDB for local validation, scripts for file processing. Follow the scaffold structure. **Outputs:** dbt project, cleaning scripts, mapping document draft.

### Phase 4: Validation

Run dbt tests, validate row counts, confirm business rules with the client. Cross-check profiler findings against cleaned output. **Outputs:** dbt test results, quality report draft, before/after comparisons.

### Phase 5: Delivery

Generate final deliverables, prepare handoff documentation, walk the client through the runbook. **Outputs:** quality report, mapping document, transform log, runbook, post-engagement support plan.

---

## Security Tier Selection

Quick decision — ask: "What data can the client share?"

| Client Answer | Tier | Access Level |
|--------------|------|-------------|
| "Only our schema / DDL" | Tier 1: Schema-Only | DDL exports, no row data |
| "We can share anonymized samples" | Tier 2: Sampled | Anonymized or masked sample rows |
| "Full access to a dev/staging copy" | Tier 3: Full Access | Complete dataset in sandbox |

If unsure, start at Tier 1 and escalate. See [Security Tiers Reference](references/security-tiers.md) for procedural detail on each tier.

See also [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) and [Security Tier Model](../shared-references/data-engineering/security-tier-model.md) for organization-level security guidance.

---

## Schema Profiling Procedure

1. **Inventory source files** — List all files the client has provided. Record format (CSV, Excel, Parquet), encoding, approximate size.
2. **Run schema profiler** — Execute `python scripts/schema_profiler.py <input_path> <output_path>`. Add `--include-sample 10` for Tier 2+ engagements.
3. **Review profiler output** — Check the JSON output for column types, null rates, cardinality ratios, and detected issues.
4. **Identify issues** — Flag columns with >50% nulls, mixed types, PII column names, encoding problems, or date format inconsistencies.
5. **Document findings** — Record issues in the quality report draft. Link each finding to a specific column and file.

See [Schema Profiling Reference](references/schema-profiling.md) for methodology detail, SQL profiling patterns, and output interpretation.

---

## Project Scaffolding

Initialize the engagement directory structure:

```
client-engagement/
├── README.md
├── .env
├── .gitignore
├── decisions.md
├── data/
│   ├── raw/
│   ├── profiling/
│   └── samples/
├── dbt_project/
├── pipelines/
├── scripts/
└── deliverables/
    ├── quality-report.md
    ├── mapping-document.md
    └── transform-log.md
```

Use `templates/engagement/` for initial file content. See [Engagement Scaffold Reference](references/engagement-scaffold.md) for template inventory, initialization steps, and tier-specific variations.

---

## Deliverable Generation

Three client-facing deliverables, generated from pipeline artifacts:

| Deliverable | Source Data | Output File |
|-------------|------------|-------------|
| **Quality Report** | dbt test results + profiler JSON | quality-report.md in deliverables dir |
| **Mapping Document** | Source schema → target schema mapping | mapping-document.md in deliverables dir |
| **Transform Log** | Chronological record of transformations | transform-log.md in deliverables dir |

See reference files: [Quality Report](references/deliverable-quality-report.md), [Mapping Document](references/deliverable-mapping-doc.md), [Transform Log](references/deliverable-transform-log.md).

---

## Handoff Checklist

Before closing the engagement, confirm:

- [ ] README.md completed with scope, source files, and run instructions
- [ ] Environment variables documented in `.env.template` (not `.env`)
- [ ] dbt docs generated (`dbt docs generate && dbt docs serve`)
- [ ] Quality Report finalized and reviewed with client
- [ ] Mapping Document complete with all source-to-target mappings
- [ ] Transform Log captures all decisions with rationale
- [ ] Runbook written: step-by-step instructions for re-running the pipeline
- [ ] Post-engagement support plan agreed (maintenance window, escalation contacts)

---

## Security Posture

This skill generates engagement scaffolds, profiling scripts, and client deliverables. See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) and [Security Tier Model](../shared-references/data-engineering/security-tier-model.md).

**Credentials required**: Client file access, warehouse connections (Tier 3 only)
**Where to configure**: `.env` file (never committed), `profiles.yml` (never committed)
**Minimum role/permissions**: Read access to source files; write to engagement directory

| Capability | Tier 1 (Schema-Only) | Tier 2 (Sampled) | Tier 3 (Full Access) |
|------------|---------------------|------------------|---------------------|
| Read source files | DDL/schema only | Anonymized samples | Full dataset |
| Run profiler | Schema metadata only | Sample statistics | Full statistics |
| Execute dbt models | Schema-only target | Sample data target | Full dev target |
| Generate deliverables | Data model assessment | Profiling report | Production artifacts |

---

## Reference Files

- [Security Tiers](references/security-tiers.md) — Procedural detail for each consulting tier: what to request, how to configure, what to deliver
- [Schema Profiling](references/schema-profiling.md) — Profiling methodology, SQL patterns, script usage, output interpretation
- [Engagement Scaffold](references/engagement-scaffold.md) — Directory structure, template inventory, initialization steps, tier variations
- [Quality Report](references/deliverable-quality-report.md) — Structure, severity levels, generation automation, presentation
- [Mapping Document](references/deliverable-mapping-doc.md) — Source-to-target mapping structure, completeness check, generation
- [Transform Log](references/deliverable-transform-log.md) — Chronological transform record, ADR linking, maintenance
