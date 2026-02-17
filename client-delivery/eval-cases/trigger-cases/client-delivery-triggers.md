# Trigger Eval Cases — client-delivery

---

## Case 1: Direct Match

**Category:** Direct match
**Tier:** 1
**Input:** "I need to set up a data cleaning engagement for a new client"
**Expected Activation:** Yes
**Expected Skill:** client-delivery
**Observation Points:**
- Recognizes "data cleaning engagement" as primary trigger
- Routes to engagement lifecycle, not dbt or DuckDB
- Does not activate dbt-transforms or duckdb
**Grading:** Pass if client-delivery activates. Fail if any other skill activates instead.

---

## Case 2: Casual Phrasing

**Category:** Casual phrasing
**Tier:** 2
**Input:** "A client just sent me a bunch of messy Excel files and I need to figure out what's wrong with the data and clean it up"
**Expected Activation:** Yes
**Expected Skill:** client-delivery
**Observation Points:**
- Identifies "client" + "messy files" + "clean it up" as consulting engagement context
- Does not route to duckdb despite file analysis being involved
- Does not route to dbt-transforms despite cleaning being involved
- Engagement framing (client, messy files, clean up) is the key differentiator
**Grading:** Pass if client-delivery activates. Partial if it activates alongside duckdb. Fail if only dbt-transforms activates.

---

## Case 3: Ambiguous — Profiling

**Category:** Ambiguous
**Tier:** 2
**Input:** "How should I profile this client's data?"
**Expected Activation:** Yes
**Expected Skill:** client-delivery (primary), duckdb (secondary for SQL profiling)
**Observation Points:**
- "Client's data" + "profile" signals consulting engagement context
- Profiling methodology lives in client-delivery
- Actual SQL execution could involve duckdb
- Should activate client-delivery for methodology, may reference DuckDB for execution
**Grading:** Pass if client-delivery activates. Partial if duckdb activates alone. Fail if neither activates.

---

## Case 4: Ambiguous — Quality Report

**Category:** Ambiguous
**Tier:** 2
**Input:** "Generate a data quality report"
**Expected Activation:** Yes (with caveats)
**Expected Skill:** client-delivery (if engagement context), dbt-transforms (if dbt test results context)
**Observation Points:**
- Without additional context, "quality report" maps to consulting deliverable
- If prior conversation mentions dbt tests, dbt-transforms may be more appropriate
- If prior conversation mentions client engagement, client-delivery is correct
- Standalone, client-delivery is the better default
**Grading:** Pass if client-delivery activates. Partial if dbt-transforms activates (reasonable in dbt context). Fail if neither activates.

---

## Case 5: Negative — dbt Model

**Category:** Negative
**Tier:** 1
**Input:** "Write a dbt model to deduplicate customer records"
**Expected Activation:** No
**Expected Skill:** dbt-transforms
**Observation Points:**
- "Write a dbt model" is an explicit dbt-transforms trigger
- Deduplication is a transformation task, not an engagement management task
- client-delivery should NOT activate for direct dbt model writing
**Grading:** Pass if dbt-transforms activates and client-delivery does not. Fail if client-delivery activates.

---

## Case 6: Edge Case — Schema-Only Tier

**Category:** Edge case
**Tier:** 2
**Input:** "I'm starting a new engagement but the client can only share their schema, no actual data"
**Expected Activation:** Yes
**Expected Skill:** client-delivery
**Observation Points:**
- Recognizes Tier 1 (Schema-Only) scenario
- "New engagement" + "client" signals consulting context
- "Schema only, no actual data" maps to security tier selection
- Should reference security tier selection and Tier 1 workflow
**Grading:** Pass if client-delivery activates and references Tier 1. Partial if it activates without tier context. Fail if it does not activate.

---

## Case 7: Bypass — Wrong Domain

**Category:** Bypass
**Tier:** 1
**Input:** "Use the consulting skill to help me configure Kafka topics"
**Expected Activation:** No
**Expected Skill:** event-streaming
**Observation Points:**
- Explicit skill mention ("consulting skill") should not override domain mismatch
- Kafka topic configuration is event-streaming territory
- client-delivery has no Kafka/streaming coverage
- Should redirect to event-streaming
**Grading:** Pass if event-streaming activates. Fail if client-delivery activates for Kafka configuration.
