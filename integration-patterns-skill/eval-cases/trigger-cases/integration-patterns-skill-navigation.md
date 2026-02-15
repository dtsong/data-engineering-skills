# integration-patterns-skill — Navigation Eval Cases

Navigation evals test how the agent traverses the skill file tree during execution.
They are distinct from trigger evals (activation) and output evals (result correctness).

---

## Case 1: SKILL.md-sufficient — Pattern Selection

**Category:** SKILL.md-sufficient

**Input:**
> "I need to replicate data from Postgres to Snowflake in near-real-time. What integration pattern should I use?"

**Expected Navigation:**
1. Read `integration-patterns-skill/SKILL.md`
2. Stop — the Integration Pattern Decision Matrix section answers this directly

**Should Read:** `SKILL.md` only
**Should NOT Read:** Any reference file

**Observation Points:**
- Agent locates the Integration Pattern Decision Matrix in SKILL.md
- Agent does not open any `references/` file
- Agent provides a pattern recommendation (CDC, DLT, etc.) citing SKILL.md content

**Grading:**
- **Pass:** Agent answers from SKILL.md without loading references
- **Partial:** Agent reads SKILL.md and one reference but answer comes from SKILL.md
- **Fail:** Agent reads multiple references or answers without consulting SKILL.md

---

## Case 2: Targeted Reference — DLT Incremental Loading

**Category:** Targeted reference

**Input:**
> "Build a DLT pipeline for Stripe with incremental cursor-based loading. Show me the resource pattern."

**Expected Navigation:**
1. Read `integration-patterns-skill/SKILL.md`
2. Follow link to `references/dlt-pipelines.md`
3. Stop — DLT incremental loading patterns are in the DLT reference

**Should Read:** `SKILL.md` → `references/dlt-pipelines.md`
**Should NOT Read:** `references/enterprise-connectors.md`, `references/event-driven-architecture.md`, `references/ipaas-platforms.md`, `references/cdc-patterns.md`, `references/data-mapping-crosswalks.md`

**Observation Points:**
- Agent reads SKILL.md and identifies the dlt-pipelines reference link
- Agent follows exactly one reference link
- Agent does not speculatively read other references

**Grading:**
- **Pass:** Agent reads SKILL.md then dlt-pipelines.md only
- **Partial:** Agent reads SKILL.md, dlt-pipelines.md, and one additional reference
- **Fail:** Agent reads 3+ references or skips dlt-pipelines.md

---

## Case 3: Cross-reference Resistance — iPaaS Selection

**Category:** Cross-reference resistance

**Input:**
> "We're evaluating Workato vs MuleSoft for our Salesforce-to-warehouse integration. Which is better for a mid-size team?"

**Expected Navigation:**
1. Read `integration-patterns-skill/SKILL.md`
2. Stop — the iPaaS Platform Comparison section covers this directly

**Should Read:** `SKILL.md` only
**Should NOT Read:** `references/ipaas-platforms.md` (tempting but unnecessary for high-level comparison)

**Observation Points:**
- Agent locates iPaaS Platform Comparison in SKILL.md
- Agent resists following the link to `references/ipaas-platforms.md`
- Agent provides a comparison recommendation from SKILL.md content

**Grading:**
- **Pass:** Agent answers from SKILL.md iPaaS Platform Comparison without loading ipaas-platforms.md
- **Partial:** Agent reads SKILL.md then ipaas-platforms.md but answer only uses SKILL.md content
- **Fail:** Agent loads ipaas-platforms.md and multiple other references

---

## Case 4: Shared Reference — Webhook Security

**Category:** Shared reference

**Input:**
> "I'm building a Stripe webhook receiver. How should I handle credential storage and signature verification securely?"

**Expected Navigation:**
1. Read `integration-patterns-skill/SKILL.md`
2. Follow Security Posture link to `../shared-references/data-engineering/security-compliance-patterns.md`
3. Stop — credential and webhook security is in the shared security reference

**Should Read:** `SKILL.md` → `../shared-references/data-engineering/security-compliance-patterns.md`
**Should NOT Read:** `references/enterprise-connectors.md`, `references/event-driven-architecture.md`, or other skill-local references

**Observation Points:**
- Agent reads SKILL.md and identifies the security-compliance-patterns link
- Agent navigates to the shared reference (outside the skill directory)
- Agent does not confuse shared references with skill-local references

**Grading:**
- **Pass:** Agent reads SKILL.md then shared security reference only
- **Partial:** Agent reads SKILL.md, shared security reference, and one skill-local reference
- **Fail:** Agent skips the shared security reference or reads 3+ files total

---

## Case 5: Deep Reference — NetSuite Connector

**Category:** Deep reference

**Input:**
> "I need to extract data from NetSuite using SuiteTalk REST API with proper pagination and rate limiting. Show me the pattern."

**Expected Navigation:**
1. Read `integration-patterns-skill/SKILL.md`
2. Follow Reference Files link to `references/enterprise-connectors.md`
3. Read deeply into the enterprise connectors reference for NetSuite patterns

**Should Read:** `SKILL.md` → `references/enterprise-connectors.md`
**Should NOT Read:** `references/dlt-pipelines.md`, `references/event-driven-architecture.md`, `references/ipaas-platforms.md`, `references/cdc-patterns.md`, `references/data-mapping-crosswalks.md`

**Observation Points:**
- Agent reads SKILL.md and follows the enterprise-connectors reference link
- Agent reads enterprise-connectors.md thoroughly (not just the first section)
- Agent provides NetSuite-specific patterns (pagination, rate limiting) from the reference

**Grading:**
- **Pass:** Agent reads SKILL.md then enterprise-connectors.md deeply, answer includes specific NetSuite patterns
- **Partial:** Agent reads correct files but answer only uses surface-level information
- **Fail:** Agent reads wrong reference or reads 3+ files
