# Trigger Eval Cases — consulting-engagement-skill

---

## Case 1: Direct Match

**Category:** Direct match
**Tier:** 1
**Input:** "I need to set up a data cleaning engagement for a new client"
**Expected Activation:** Yes
**Expected Skill:** consulting-engagement-skill
**Observation Points:**
- Recognizes "data cleaning engagement" as primary trigger
- Routes to engagement lifecycle, not dbt or DuckDB
- Does not activate dbt-skill or duckdb-local-skill
**Grading:** Pass if consulting-engagement-skill activates. Fail if any other skill activates instead.

---

## Case 2: Casual Phrasing

**Category:** Casual phrasing
**Tier:** 2
**Input:** "A client just sent me a bunch of messy Excel files and I need to figure out what's wrong with the data and clean it up"
**Expected Activation:** Yes
**Expected Skill:** consulting-engagement-skill
**Observation Points:**
- Identifies "client" + "messy files" + "clean it up" as consulting engagement context
- Does not route to duckdb-local-skill despite file analysis being involved
- Does not route to dbt-skill despite cleaning being involved
- Engagement framing (client, messy files, clean up) is the key differentiator
**Grading:** Pass if consulting-engagement-skill activates. Partial if it activates alongside duckdb-local-skill. Fail if only dbt-skill activates.

---

## Case 3: Ambiguous — Profiling

**Category:** Ambiguous
**Tier:** 2
**Input:** "How should I profile this client's data?"
**Expected Activation:** Yes
**Expected Skill:** consulting-engagement-skill (primary), duckdb-local-skill (secondary for SQL profiling)
**Observation Points:**
- "Client's data" + "profile" signals consulting engagement context
- Profiling methodology lives in consulting-engagement-skill
- Actual SQL execution could involve duckdb-local-skill
- Should activate consulting-engagement-skill for methodology, may reference DuckDB for execution
**Grading:** Pass if consulting-engagement-skill activates. Partial if duckdb-local-skill activates alone. Fail if neither activates.

---

## Case 4: Ambiguous — Quality Report

**Category:** Ambiguous
**Tier:** 2
**Input:** "Generate a data quality report"
**Expected Activation:** Yes (with caveats)
**Expected Skill:** consulting-engagement-skill (if engagement context), dbt-skill (if dbt test results context)
**Observation Points:**
- Without additional context, "quality report" maps to consulting deliverable
- If prior conversation mentions dbt tests, dbt-skill may be more appropriate
- If prior conversation mentions client engagement, consulting-engagement-skill is correct
- Standalone, consulting-engagement-skill is the better default
**Grading:** Pass if consulting-engagement-skill activates. Partial if dbt-skill activates (reasonable in dbt context). Fail if neither activates.

---

## Case 5: Negative — dbt Model

**Category:** Negative
**Tier:** 1
**Input:** "Write a dbt model to deduplicate customer records"
**Expected Activation:** No
**Expected Skill:** dbt-skill
**Observation Points:**
- "Write a dbt model" is an explicit dbt-skill trigger
- Deduplication is a transformation task, not an engagement management task
- consulting-engagement-skill should NOT activate for direct dbt model writing
**Grading:** Pass if dbt-skill activates and consulting-engagement-skill does not. Fail if consulting-engagement-skill activates.

---

## Case 6: Edge Case — Schema-Only Tier

**Category:** Edge case
**Tier:** 2
**Input:** "I'm starting a new engagement but the client can only share their schema, no actual data"
**Expected Activation:** Yes
**Expected Skill:** consulting-engagement-skill
**Observation Points:**
- Recognizes Tier 1 (Schema-Only) scenario
- "New engagement" + "client" signals consulting context
- "Schema only, no actual data" maps to security tier selection
- Should reference security tier selection and Tier 1 workflow
**Grading:** Pass if consulting-engagement-skill activates and references Tier 1. Partial if it activates without tier context. Fail if it does not activate.

---

## Case 7: Bypass — Wrong Domain

**Category:** Bypass
**Tier:** 1
**Input:** "Use the consulting skill to help me configure Kafka topics"
**Expected Activation:** No
**Expected Skill:** streaming-data-skill
**Observation Points:**
- Explicit skill mention ("consulting skill") should not override domain mismatch
- Kafka topic configuration is streaming-data-skill territory
- consulting-engagement-skill has no Kafka/streaming coverage
- Should redirect to streaming-data-skill
**Grading:** Pass if streaming-data-skill activates. Fail if consulting-engagement-skill activates for Kafka configuration.
