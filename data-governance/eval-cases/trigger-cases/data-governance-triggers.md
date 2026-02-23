# data-governance -- Trigger Eval Cases

Trigger evals test whether the skill correctly activates (or correctly does NOT activate) on various user inputs. Distinct from navigation evals (file traversal) and output evals (result quality).

---

## Case 1: Direct Match -- Set Up Data Catalog for dbt Project

**Category:** Direct match
**Tier:** 1 (simple)

**Input:**
> "Set up a data catalog for our dbt project"

**Expected Activation:** Yes
**Expected Skill:** data-governance

**Observation Points:**
- "Data catalog" is a primary trigger phrase in the skill description
- "dbt project" context maps to the zero-cost-first principle (dbt docs before external tools)
- No competing skill handles catalog setup; dbt-transforms handles model writing, not documentation governance

**Grading:**
- **Pass:** Skill activates and classifies as Cataloging area; recommends dbt docs as zero-cost catalog; offers to generate documentation YAML and meta tags
- **Partial:** Skill activates but jumps to recommending an external catalog tool without first assessing dbt docs sufficiency
- **Fail:** Skill does not activate; or dbt-transforms activates because it sees "dbt project"

---

## Case 2: Casual Phrasing -- Document Where Data Comes From

**Category:** Casual phrasing
**Tier:** 1 (simple)

**Input:**
> "How do I document where my data comes from?"

**Expected Activation:** Yes
**Expected Skill:** data-governance

**Observation Points:**
- No explicit governance terminology -- "document where data comes from" implies lineage documentation
- Could superficially match dbt-transforms (model documentation) but the intent is tracing data flow, not writing models
- Skill should interpret this as a lineage governance need and offer lineage documentation patterns

**Grading:**
- **Pass:** Skill activates and classifies as Lineage area; asks about platform context (dbt, Spark, manual ETL); offers lineage documentation patterns
- **Partial:** Skill activates but provides only dbt `source()` documentation without addressing broader lineage
- **Fail:** Skill does not activate; or dbt-transforms activates and provides model documentation guidance only

---

## Case 3: Ambiguous -- Add PII Tags to dbt Models

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "Add PII tags to my dbt models"

**Expected Activation:** Conditional (clarify scope)
**Expected Skill:** data-governance (if classification/tagging), dbt-transforms (if model code changes)

**Observation Points:**
- "PII tags" maps to classification governance (data-governance scope)
- "dbt models" could imply modifying model SQL (dbt-transforms scope)
- Adding `meta` tags to schema YAML is governance; modifying SELECT statements is transforms
- Skill should clarify: "Are you looking to add classification meta tags to your schema YAML, or do you need to modify the model SQL to hash/mask PII columns?"

**Grading:**
- **Pass:** Skill activates with a clarifying question about whether the task is tagging (governance) or model modification (transforms); activates fully if tagging is confirmed
- **Partial:** Skill activates and generates meta tags without confirming scope, but output is correct for the governance interpretation
- **Fail:** dbt-transforms activates and modifies model SQL when user only wanted meta tags; or neither skill activates

---

## Case 4: Negative -- Write a dbt Staging Model with Documentation

**Category:** Negative
**Tier:** 2 (medium)

**Input:**
> "Write a dbt staging model with documentation"

**Expected Activation:** No
**Expected Skill:** dbt-transforms

**Observation Points:**
- "Write a dbt staging model" is explicitly dbt-transforms scope (model creation)
- "with documentation" is secondary to the primary task of model writing
- data-governance handles documentation as a governance layer, not as part of model creation
- dbt-transforms should handle both the model SQL and inline documentation

**Grading:**
- **Pass:** Skill does not activate; dbt-transforms handles the staging model with documentation
- **Partial:** Skill does not activate but is mentioned as a follow-up for classification tagging after model creation
- **Fail:** Skill activates because it sees "documentation" and attempts to generate governance artifacts for a model that doesn't exist yet

---

## Case 5: Edge Case -- Generate Governance Report for Client Delivery

**Category:** Edge case
**Tier:** 3 (complex)

**Input:**
> "Generate a data governance report for client delivery"

**Expected Activation:** Yes (with handoff)
**Expected Skill:** data-governance (primary), client-delivery (handoff for final packaging)

**Observation Points:**
- "Data governance report" triggers data-governance for content generation
- "Client delivery" maps to the handoff protocol → client-delivery
- Skill should generate governance posture summary and signal handoff to client-delivery for packaging
- This tests that the skill correctly scopes itself and doesn't attempt engagement scaffolding

**Grading:**
- **Pass:** Skill activates and generates governance posture summary (areas covered, gaps, artifacts); explicitly signals handoff to client-delivery for final packaging; does NOT generate engagement scaffolding
- **Partial:** Skill activates but attempts to generate the full client deliverable without loading client-delivery
- **Fail:** client-delivery activates first because of "client delivery" keyword; data-governance never activates

---

## Case 6: Bypass -- Test Pipeline for Data Quality Issues

**Category:** Bypass
**Tier:** 3 (complex)

**Input:**
> "Test my pipeline for data quality issues"

**Expected Activation:** No
**Expected Skill:** data-testing

**Observation Points:**
- "Test" + "data quality" maps directly to data-testing scope
- data-governance's "Don't use for" section explicitly excludes data quality testing
- "Pipeline" could superficially seem governance-related, but the task is testing, not governing
- data-testing handles freshness, uniqueness, accepted values, and custom tests

**Grading:**
- **Pass:** Skill does not activate; data-testing handles the quality testing request
- **Partial:** Skill does not activate but mentions data-governance for post-testing classification of quality rules
- **Fail:** Skill activates because it sees "data quality" and attempts to provide governance context for a testing request

---

## Case 7: Negative -- Set Up Snowflake Row-Level Security

**Category:** Direct match (access control)
**Tier:** 2 (medium)

**Input:**
> "Set up Snowflake row-level security only"

**Expected Activation:** Yes
**Expected Skill:** data-governance

**Observation Points:**
- "Row-level security" is explicitly within data-governance scope (access control area)
- "Snowflake" provides platform context for generating appropriate SQL
- "Only" indicates a focused request -- skill should scope to access control without expanding to other governance areas
- No competing skill handles access control patterns; dbt-transforms does not cover security policies

**Grading:**
- **Pass:** Skill activates and classifies as Access Control area; generates Snowflake row access policy SQL; does NOT expand into cataloging or classification unless asked
- **Partial:** Skill activates but expands scope beyond row-level security to full RBAC setup without being asked
- **Fail:** Skill does not activate; or attempts to hand off to a different skill because it sees "Snowflake" as a platform concern
