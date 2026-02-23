---
name: data-testing
description: "Use this skill when designing testing strategies for data pipelines, writing SQL assertions, validating pipeline output, or packaging tests as client deliverables. Covers dbt test patterns, pipeline validation, SQL assertion libraries, test coverage targets, and test-as-deliverable packaging. Common phrases: \"data testing strategy\", \"pipeline validation\", \"SQL assertions\", \"test coverage\", \"test as deliverable\", \"data quality tests\". Do NOT use for writing dbt models (use dbt-transforms), DuckDB analytical queries (use duckdb), or pipeline scheduling (use data-pipelines)."
model:
  preferred: sonnet
  acceptable: [sonnet, opus]
  minimum: sonnet
  allow_downgrade: false
  reasoning_demand: medium
version: 0.1.0
---

# Data Testing Skill

Designs data testing strategies, generates SQL assertions, validates pipeline output, and packages test suites as client deliverables. Produces test code and configurations; does NOT execute tests against live data.

## When to Use This Skill

**Activate when:** Designing test strategies for data pipelines, writing SQL assertions for data quality, validating dbt model output, setting test coverage targets, building regression test suites, comparing pre/post migration data, or packaging test results as client deliverables.

**Don't use for:**
- Writing or modifying dbt models → use `dbt-transforms`
- Running DuckDB analytical queries without testing intent → use `duckdb`
- Scheduling or orchestrating test jobs → use `data-pipelines`
- Production monitoring or alerting on data freshness → use `data-observability`

## Scope Constraints

- Generates test code and configurations only — does not execute tests against databases or access data files.
- Local execution model: all generated tests target the user's machine or CI environment; no cloud deployment scaffolding unless explicitly requested.
- Security tier default: Tier 1 (schema/metadata only). User must explicitly elevate to Tier 2 (sample data) or Tier 3 (full data access).
- Reference files loaded one at a time — never pre-load multiple references simultaneously.
- No cross-references to other specialist skills; use handoff protocol for adjacent work.

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| medium | Sonnet | Sonnet, Opus | Sonnet |

## Core Principles

1. **Test-driven delivery** — Define expected data behavior before writing transformation logic. Tests are the specification.
2. **Coverage targets** — 100% primary key integrity on all models; 80%+ column-level coverage on marts; document any gaps with justification.
3. **Regression as handoff artifact** — Every client engagement produces a regression suite that the client team can run independently after handoff.
4. **Fail-fast** — Tests run early in the pipeline (source → staging → marts); catch problems at the lowest layer to prevent downstream propagation.
5. **Test at every layer** — Schema tests at staging, row-level assertions at intermediate, aggregate reconciliation at marts, cross-system checks at integration boundaries.

## Testing Layers

| Layer | Scope | Example | When |
|-------|-------|---------|------|
| Schema | Column types, not-null, accepted values | `dbt test` on staging models | Every run |
| Row-level | Per-row business rules | `amount > 0 WHERE status = 'completed'` | Every run |
| Aggregate | Sum/count reconciliation across layers | Source row count = staging row count | Every run |
| Cross-system | Source-to-target validation across databases | ERP totals match warehouse totals | Migration / initial load |
| Regression | Before/after comparison on known datasets | Golden dataset produces identical output | Pre-release / handoff |
| Performance | Query timing, row throughput, freshness SLA | Model builds in < 30 minutes | CI / scheduled |

## Procedure

> **Progress checklist** (tick off as you complete each step):
> - [ ] 1. Classify testing need
> - [ ] 2. Select testing layer
> - [ ] 3. Generate test code
> - [ ] 4. Validate results
> - [ ] 5. Package as deliverable (if client-facing)

> **Compaction recovery:** If context is compressed mid-procedure, re-read this SKILL.md to restore context. Check which checklist items are complete, then resume from the next unchecked step.

### Step 1 — Classify testing need

Determine which mode applies before generating test code:

- **Strategy mode**: User wants a testing plan or coverage assessment. Identify gaps and recommend test types.
- **Implementation mode**: User wants specific test code (SQL assertions, dbt YAML, Python checks). Default mode.
- **Validation mode**: User wants to verify pipeline output against expected results. Focus on reconciliation.
- **Deliverable mode**: User wants test results packaged for client review. Add deliverable step after validation.

### Step 2 — Select testing layer

Use the Testing Layers table above to determine scope. Ask if ambiguous:
- What layer are the models in? (staging / intermediate / marts)
- Is this validating within one system or across systems? (single → row/aggregate; cross → cross-system)
- Is this a one-time migration check or ongoing? (one-time → cross-system + regression; ongoing → schema + row + aggregate)

Load **[dbt-testing-strategy.md](references/dbt-testing-strategy.md)** if user needs dbt-specific test organization or CI/CD integration.

### Step 3 — Generate test code

Based on classified need and selected layer:

- **dbt tests** → Load **[dbt-testing-strategy.md](references/dbt-testing-strategy.md)** for YAML schema tests, custom generic tests, `store_failures` configuration.
- **SQL assertions** → Load **[sql-assertion-patterns.md](references/sql-assertion-patterns.md)** for standalone SQL checks (row counts, sum reconciliation, null detection, referential integrity).
- **Pipeline validation** → Load **[pipeline-validation.md](references/pipeline-validation.md)** for DuckDB-based validation, row hash comparison, data contract validation.

Unload each reference after generating the relevant test code before loading the next.

### Step 4 — Validate results

Generate validation queries that confirm tests behave correctly:
1. Run tests against known-good data (expect all pass)
2. Run tests against intentionally broken data (expect specific failures)
3. Confirm `store_failures` captures failing rows if configured

### Step 5 — Package as deliverable (deliverable mode only)

Load **[test-as-deliverable.md](references/test-as-deliverable.md)** and generate:

1. Test summary report with pass/fail counts and coverage percentages
2. Failing row samples from `store_failures` tables
3. Before/after quality comparison metrics
4. Regression suite documentation for client handoff

## Security Posture

# SECURITY: This skill generates test code for local or CI execution only. No network calls, credential access, or data file reads are performed by Claude. Generated scripts read local files via DuckDB or dbt — validate file paths before execution.

See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for the full framework.
See [Consulting Security Tier Model](../shared-references/data-engineering/security-tier-model.md) for tier definitions.

| Capability | Tier 1 (Default) | Tier 2 (Sampled) | Tier 3 (Full Access) |
|------------|-----------------|-------------------|---------------------|
| Schema tests | Column types / shape only | Tests on sample data | Tests on full data |
| SQL assertions | Generate SQL (not execute) | Execute on samples | Execute on full data |
| Validation | Template checks only | Validate sample output | Validate full output |
| Deliverables | Template with placeholders | Populated from samples | Fully populated |

### Input Sanitization

When user provides file paths for test scripts or data validation:
- Validate path exists and is within the working directory before use in generated code.
- Reject paths containing `..`, `~`, environment variables, or shell metacharacters.
- Never interpolate user-provided strings directly into shell commands.

## Reference Files

Reference files loaded on demand — one at a time:

- **[dbt-testing-strategy.md](references/dbt-testing-strategy.md)** — Test coverage targets, test organization by layer, incremental testing, CI/CD integration, slim CI selection, failure triage. Load at Step 2 or Step 3 for dbt-specific testing.
- **[pipeline-validation.md](references/pipeline-validation.md)** — Source profiling, DuckDB-based validation, row hash comparison, data contract validation, Soda/GE patterns as SQL. Load at Step 3 for pipeline validation.
- **[sql-assertion-patterns.md](references/sql-assertion-patterns.md)** — Row count reconciliation, sum reconciliation, null detection, uniqueness, referential integrity, date continuity, distribution drift, cross-database syntax. Load at Step 3 for SQL assertions.
- **[test-as-deliverable.md](references/test-as-deliverable.md)** — Test summary report format, dbt output to client scorecard, store_failures review, coverage metrics, before/after comparison, regression suite as handoff artifact. Load at Step 5 (deliverable mode only).

## Handoffs

- **dbt-native model tests** → [dbt-transforms](../dbt-transforms/SKILL.md) (tests embedded in model YAML when writing models, not standalone test strategy)
- **Local data validation with DuckDB** → [duckdb](../duckdb/SKILL.md) (ad-hoc queries for exploratory validation, not structured test suites)
- **Test deliverable packaging** → [client-delivery](../client-delivery/SKILL.md) (engagement scaffolding, client handoff documentation)
- **Production data monitoring** → [data-observability](../data-observability/SKILL.md) (alerting, freshness SLAs, anomaly detection in production)
