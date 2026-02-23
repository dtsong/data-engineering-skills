---
name: data-governance
description: "Use this skill when implementing data governance as part of engineering work. Covers data cataloging (dbt docs, external tools), lineage documentation, data classification (PII/PHI taxonomy), access control patterns (RBAC, row-level security), and compliance frameworks (GDPR, HIPAA, SOX, CCPA). Common phrases: \"data catalog\", \"data lineage\", \"PII classification\", \"access control\", \"RBAC\", \"data governance\", \"compliance requirements\". Do NOT use for writing dbt models (use dbt-transforms), pipeline orchestration (use data-pipelines), or data quality testing (use data-testing)."
model:
  preferred: sonnet
  acceptable: [sonnet, opus]
  minimum: sonnet
  allow_downgrade: false
  reasoning_demand: medium
version: 0.1.0
---

# Data Governance Skill

Implements data governance as a layer inside engineering work -- cataloging, lineage, classification, access control, and compliance. Governance is code, not overhead.

## When to Use This Skill

**Activate when:** Cataloging data assets (dbt docs or external tools), documenting data lineage, classifying sensitive data (PII/PHI), implementing access control patterns (RBAC, row-level security), or applying compliance frameworks (GDPR, HIPAA, SOX, CCPA) to data pipelines.

**Don't use for:**
- Writing or modifying dbt models → use `dbt-transforms`
- Pipeline orchestration or scheduling → use `data-pipelines`
- Data quality testing (freshness, uniqueness, accepted values) → use `data-testing`
- Data observability and monitoring → use `data-observability`

## Scope Constraints

- Engineering governance only -- does not provide legal counsel or regulatory interpretation.
- Generates governance artifacts (YAML configs, SQL grants, documentation) -- does not execute DDL against production databases.
- Security tier default: Tier 1 (schema/metadata only). User must explicitly elevate to Tier 2 (sample data) or Tier 3 (full data access).
- Reference files loaded one at a time -- never pre-load multiple references simultaneously.
- No cross-references to other specialist skills; use handoff protocol for adjacent work.

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| medium | Sonnet | Sonnet, Opus | Sonnet |

## Core Principles

1. **Governance-as-code** -- Define governance rules in version-controlled config files (YAML, SQL, dbt meta), not spreadsheets or wiki pages.
2. **Zero-cost-first** -- Use dbt docs and native metadata before reaching for external catalog tools. Upgrade only when dbt docs hit documented limitations.
3. **Classify-then-protect** -- Always classify data sensitivity before implementing access controls. Classification drives the protection level.
4. **Least-privilege** -- Default to minimal access grants. Expand only with documented justification and audit trail.
5. **Compliance-aware** -- Provide reference-level guidance on regulatory frameworks. Flag when legal review is required; never substitute for legal counsel.

## Governance Areas

| Area | Scope | Primary Reference |
|------|-------|-------------------|
| Cataloging | dbt docs, external catalogs, source metadata, tagging | data-catalog.md |
| Lineage | dbt lineage, column-level lineage, cross-system documentation | lineage-patterns.md |
| Classification | PII/PHI taxonomy, automated detection, sensitivity tagging | classification-policies.md |
| Access Control | RBAC, row-level security, grants, audit documentation | access-control.md |
| Compliance | GDPR, HIPAA, SOX, CCPA pipeline requirements | compliance-frameworks.md |

## Procedure

> **Progress checklist** (tick off as you complete each step):
> - [ ] 1. Classify governance need
> - [ ] 2. Assess current state
> - [ ] 3. Generate governance artifacts
> - [ ] 4. Validate implementation
> - [ ] 5. Package deliverable (conditional)

> **Compaction recovery:** If context is compressed mid-procedure, re-read this SKILL.md to restore context. Check which checklist items are complete, then resume from the next unchecked step.

### Step 1 -- Classify governance need

Determine which governance area(s) apply before generating any artifacts:

- **Cataloging**: User wants to document data assets, add descriptions, or set up a data catalog.
- **Lineage**: User wants to trace data flow, document dependencies, or produce lineage diagrams.
- **Classification**: User wants to identify or tag sensitive data (PII, PHI, financial).
- **Access Control**: User wants to implement RBAC, grants, row-level security, or audit access.
- **Compliance**: User wants to apply regulatory framework requirements to pipeline design.

If multiple areas overlap, prioritize: Classification → Access Control → Compliance → Cataloging → Lineage.

### Step 2 -- Assess current state

Gather context before generating artifacts:

- What platform? (Snowflake, Azure SQL, BigQuery, Databricks)
- dbt project present? (if yes, governance-as-code via dbt meta is preferred)
- Existing governance artifacts? (check for `meta:` tags, grants config, documentation blocks)
- Security tier? (default Tier 1 unless user elevates)

### Step 3 -- Generate governance artifacts

Load the appropriate reference file for the classified governance area:

- **Cataloging** → Load **[data-catalog.md](references/data-catalog.md)** and generate documentation YAML, meta tags, or catalog configuration.
- **Lineage** → Load **[lineage-patterns.md](references/lineage-patterns.md)** and generate lineage documentation or diagram specifications.
- **Classification** → Load **[classification-policies.md](references/classification-policies.md)** and generate classification tags, detection patterns, or masking configs.
- **Access Control** → Load **[access-control.md](references/access-control.md)** and generate RBAC SQL, grants config, or row-level security policies.
- **Compliance** → Load **[compliance-frameworks.md](references/compliance-frameworks.md)** and generate compliance checklists, pipeline requirements, or audit documentation.

Unload the reference file after generating artifacts before loading the next one if multiple areas are needed.

### Step 4 -- Validate implementation

After generating artifacts, validate against the governance area requirements:

- Cataloging: all sources and models have descriptions; meta tags are consistent.
- Lineage: no undocumented sources; cross-system boundaries are explicit.
- Classification: all sensitive columns tagged; no unclassified PII/PHI columns.
- Access Control: grants follow least-privilege; no role has unnecessary permissions.
- Compliance: required controls are present for the applicable framework(s).

### Step 5 -- Package deliverable (conditional)

If user requests a client-facing deliverable or governance report:

1. Summarize governance posture (areas covered, gaps identified)
2. List all generated artifacts with file paths
3. Document assumptions and limitations
4. Signal handoff to `client-delivery` for final packaging

## Security Posture

# SECURITY: This skill generates governance configuration artifacts (YAML, SQL, documentation). No DDL execution against production databases. Generated SQL grants should be reviewed before execution.

See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for the full framework.
See [Consulting Security Tier Model](../shared-references/data-engineering/security-tier-model.md) for tier definitions.

| Capability | Tier 1 (Default) | Tier 2 (Sampled) | Tier 3 (Full Access) |
|------------|-----------------|-------------------|---------------------|
| Catalog generation | Schema/column names only | Stats on sample data | Full profiling |
| Classification | Pattern-based detection | Sample data scanning | Full column scanning |
| Access control SQL | Generate grants (not execute) | Execute on dev | Execute on production |
| Compliance docs | Template with placeholders | Populated from samples | Fully populated |

## Input Sanitization

When user provides schema names, table names, or role names for governance artifacts:
- Validate identifiers against `^[a-zA-Z_][a-zA-Z0-9_]*$` pattern before use in generated SQL.
- Reject identifiers containing SQL injection patterns (`--`, `;`, `'`, `"`, `/*`).
- Never interpolate user-provided strings directly into shell commands or unparameterized SQL.

## Reference Files

Reference files loaded on demand -- one at a time:

- **[data-catalog.md](references/data-catalog.md)** -- dbt docs patterns, column documentation, source metadata, meta tagging, external catalog tool guidance. Load at Step 3 for cataloging needs.
- **[lineage-patterns.md](references/lineage-patterns.md)** -- dbt lineage graphs, column-level lineage, cross-system documentation, lineage diagrams, gap detection. Load at Step 3 for lineage needs.
- **[classification-policies.md](references/classification-policies.md)** -- PII/PHI taxonomy, detection regex patterns, automated classification, sensitivity tagging, masking recommendations. Load at Step 3 for classification needs.
- **[access-control.md](references/access-control.md)** -- Snowflake and Azure SQL RBAC, dbt grants config, least-privilege patterns, row-level security, audit documentation. Load at Step 3 for access control needs.
- **[compliance-frameworks.md](references/compliance-frameworks.md)** -- GDPR, HIPAA, SOX, CCPA pipeline requirements, compliance documentation, legal review guidance. Load at Step 3 for compliance needs.

## Handoffs

- **dbt-native governance** → [dbt-transforms](../dbt-transforms/SKILL.md) (when governance requires writing or modifying dbt models, not just adding meta/docs)
- **Governance deliverables** → [client-delivery](../client-delivery/SKILL.md) (engagement scaffolding, client-facing governance reports)
- **Quality validation** → [data-testing](../data-testing/SKILL.md) (data quality tests that enforce governance rules)
- **Monitoring governance** → [data-observability](../data-observability/SKILL.md) (ongoing governance monitoring, alerting on policy violations)
