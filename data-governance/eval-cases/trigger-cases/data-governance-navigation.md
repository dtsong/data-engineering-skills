# data-governance -- Navigation Eval Cases

Navigation evals test which reference files get loaded during a conversation. Correct navigation means the right file is loaded at the right time -- and no unnecessary files are pre-loaded. Distinct from trigger evals (activation) and output evals (result quality).

---

## Case 1: SKILL.md Sufficient -- Simple Governance Area Question

**Category:** SKILL.md-sufficient
**Tier:** 1 (simple)

**Input:**
> "What governance areas should I cover for a new dbt project?"

**Expected Skill Activated:** data-governance
**Expected Files Loaded:** SKILL.md only

**Observation Points:**
- The Governance Areas table in SKILL.md answers this question directly
- No specific implementation detail is needed -- user is asking for an overview
- Loading any reference file here would violate the "one reference at a time" rule without justification
- The Core Principles section provides the prioritization framework (zero-cost-first, classify-then-protect)

**Grading:**
- **Pass:** Skill answers from SKILL.md Governance Areas table and Core Principles only; recommends starting with Cataloging (dbt docs) and Classification; does NOT load any reference files
- **Partial:** Skill answers correctly but preemptively loads data-catalog.md to show dbt docs patterns
- **Fail:** Skill loads multiple reference files to provide a comprehensive answer to an overview question; or provides incorrect governance area recommendations

---

## Case 2: Reference Target -- PII Detection Patterns

**Category:** classification-policies target
**Tier:** 2 (medium)

**Input:**
> "Give me regex patterns for detecting PII in our column names and data values"

**Expected Skill Activated:** data-governance
**Expected Files Loaded:** SKILL.md + classification-policies.md (Step 3)

**Observation Points:**
- "Regex patterns for detecting PII" requires the PII_PATTERNS and PII_COLUMN_NAMES from classification-policies.md
- Only classification-policies.md should be loaded -- not data-catalog.md or access-control.md
- Loading access-control.md here would be premature; user has not asked about protecting the data yet
- This tests single-reference precision: exactly one reference loaded, correctly targeted

**Grading:**
- **Pass:** Skill loads classification-policies.md only; provides PII detection regex patterns for column names and sample values; explains the four-tier classification taxonomy; unloads after answering
- **Partial:** Skill loads classification-policies.md but also preemptively loads access-control.md to recommend masking
- **Fail:** Skill answers from SKILL.md without loading classification-policies.md (no regex patterns available in SKILL.md); or loads multiple references simultaneously

---

## Case 3: Sequential Load -- Full Governance Implementation

**Category:** Sequential procedure
**Tier:** 3 (complex)

**Input:**
> "Implement full data governance for our Snowflake dbt project: catalog everything, classify PII columns, and set up RBAC with row-level security."

**Expected Skill Activated:** data-governance
**Expected Files Loaded:** SKILL.md -> data-catalog.md (Step 3, cataloging) -> classification-policies.md (Step 3, classification) -> access-control.md (Step 3, access control)

**Observation Points:**
- Three governance areas requested: Cataloging, Classification, Access Control
- References must be loaded sequentially, not simultaneously
- Peak load at any single point: SKILL.md (~1,800 tokens) + one reference (~1,300 tokens) <= 5,500 ceiling
- After generating catalog artifacts from data-catalog.md, that file should be unloaded before loading classification-policies.md
- After generating classification tags, classification-policies.md should be unloaded before loading access-control.md
- Compliance-frameworks.md and lineage-patterns.md should NOT be loaded (not requested)

**Grading:**
- **Pass:** Skill follows 3-reference sequential load pattern; generates dbt docs config, PII classification meta tags, Snowflake RBAC SQL and row access policies in distinct steps; never holds more than one reference simultaneously
- **Partial:** Skill loads two references simultaneously (e.g., classification-policies + access-control at once) but produces correct artifacts
- **Fail:** Skill loads all three references simultaneously; or loads compliance-frameworks.md or lineage-patterns.md when neither compliance nor lineage was requested

---

## Case 4: Conditional Deliverable -- Compliance Framework Load

**Category:** Conditional deliverable
**Tier:** 2 (medium)

**Input:**
> "We need to make sure our pipeline handles GDPR right-to-erasure requirements."

**Expected Skill Activated:** data-governance
**Expected Files Loaded:** SKILL.md + compliance-frameworks.md (Step 3, compliance)

**Observation Points:**
- "GDPR right-to-erasure" is a specific compliance requirement that requires compliance-frameworks.md
- compliance-frameworks.md should ONLY be loaded when compliance context is explicitly needed
- This tests that the conditional load rule is respected: compliance reference is not pre-loaded at skill activation
- Other reference files (data-catalog, classification-policies, access-control) should NOT be loaded unless user expands scope
- The disclaimer about legal review should be included in the output

**Grading:**
- **Pass:** Skill loads compliance-frameworks.md only; provides GDPR right-to-erasure implementation pattern (soft-delete + hard-delete job); includes `# LEGAL REVIEW REQUIRED` disclaimer; does NOT load other reference files
- **Partial:** Skill loads compliance-frameworks.md but also loads classification-policies.md to recommend PII tagging as a prerequisite
- **Fail:** compliance-frameworks.md is never loaded; skill provides generic GDPR advice from memory without the standardized patterns; or multiple references are loaded simultaneously

---

## Case 5: No-Reference Handoff -- Governance for dbt Model Changes

**Category:** Handoff without reference load
**Tier:** 1 (simple)

**Input:**
> "I need to add data masking to my dbt staging models by changing the SQL"

**Expected Skill Activated:** data-governance (briefly), then handoff to dbt-transforms
**Expected Files Loaded:** SKILL.md only (for handoff decision)

**Observation Points:**
- "Changing the SQL" in dbt models is dbt-transforms scope, not data-governance
- data-governance may briefly activate to assess the request but should recognize the SQL modification intent
- No reference files should be loaded -- the handoff decision can be made from SKILL.md alone
- The skill should note that classification-policies.md has masking recommendations but the actual SQL change belongs to dbt-transforms

**Grading:**
- **Pass:** Skill reads SKILL.md, recognizes that modifying dbt model SQL is dbt-transforms scope, signals handoff without loading any reference files; optionally notes that data-governance can help with classification tagging after models are updated
- **Partial:** Skill loads classification-policies.md to show masking patterns before handing off to dbt-transforms
- **Fail:** Skill loads reference files and attempts to generate dbt model SQL changes directly; or fails to recognize the handoff need
