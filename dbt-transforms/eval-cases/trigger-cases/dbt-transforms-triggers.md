# dbt-transforms — Trigger Eval Cases

Trigger evals test whether the skill correctly activates (or correctly does NOT activate) on various user inputs. Distinct from navigation evals (file traversal) and output evals (result quality).

---

## Case 1: Direct Match — Write a dbt Test for Referential Integrity

**Category:** Direct match
**Tier:** 1 (simple)

**Input:**
> "Write a dbt test that checks referential integrity between my orders fact table and the customers dimension — every order should have a valid customer_id."

**Expected Activation:** Yes
**Expected Skill:** dbt-transforms

**Observation Points:**
- Prompt contains exact trigger phrase "dbt test"
- Referential integrity testing is a core dbt concept (relationships test) covered in SKILL.md
- "Fact table" and "dimension" language confirms dbt modeling context (Kimball methodology in SKILL.md)
- No competing skill handles dbt test authoring

**Grading:**
- **Pass:** Skill activates and provides a dbt relationships test configuration in YAML, referencing the correct model naming conventions (fct_orders, dim_customers)
- **Partial:** Skill activates but provides a generic SQL assertion instead of dbt's native relationships test syntax
- **Fail:** Skill does not activate, or a different skill handles the request

---

## Case 2: Casual Phrasing — Organize My SQL Transformations

**Category:** Casual phrasing
**Tier:** 1 (simple)

**Input:**
> "My data warehouse has a mess of SQL views that analysts wrote ad hoc. I want to organize them into proper layers — clean up the raw data first, then build business logic on top, then expose clean tables for dashboards."

**Expected Activation:** Yes
**Expected Skill:** dbt-transforms

**Observation Points:**
- No mention of "dbt" anywhere in the prompt
- "Organize into proper layers" maps to SKILL.md's staging/intermediate/marts layer methodology
- "Clean up the raw data first" = staging; "build business logic on top" = intermediate; "expose clean tables for dashboards" = marts
- The layered SQL transformation architecture is a defining characteristic of dbt projects
- No other skill in the suite covers this kind of SQL-based layered transformation methodology

**Grading:**
- **Pass:** Skill activates and recommends a dbt project with staging, intermediate, and marts layers, mapping the user's described workflow to the modeling methodology
- **Partial:** Skill activates but only recommends organizing SQL files without introducing the dbt framework
- **Fail:** Skill does not activate because "dbt" is not mentioned, or python-data-engineering activates because it sees "transformations"

---

## Case 3: Ambiguous — Data Quality Checks on Warehouse Tables

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "I need to set up data quality checks on our warehouse tables — things like null percentages, duplicate detection, freshness monitoring, and anomaly detection on row counts."

**Expected Activation:** Yes (with caveats)
**Expected Skill:** dbt-transforms (primary for test-based quality), data-pipelines (possible secondary for freshness monitoring and alerting)

**Observation Points:**
- Data quality checks are a core dbt capability (schema tests, dbt-expectations, Elementary)
- SKILL.md references: Testing & Quality Strategy and Data Quality & Observability
- However, "freshness monitoring" could be a dbt source freshness concern OR an orchestration observability concern
- "Anomaly detection on row counts" could be dbt-expectations/Elementary OR a separate monitoring tool integrated via orchestration
- data-pipelines handles alerting and observability dashboards; dbt-transforms handles the quality check definitions themselves

**Grading:**
- **Pass:** Skill activates and provides dbt-native quality checks (schema tests, dbt-expectations, Elementary), noting that freshness alerting and monitoring dashboards may involve data-pipelines for the notification layer
- **Partial:** Skill activates but only covers basic dbt schema tests without addressing the advanced quality concerns (anomaly detection, freshness)
- **Fail:** Skill does not activate (deferring to data-pipelines), or activates without acknowledging that monitoring and alerting infrastructure crosses into orchestration territory

---

## Case 4: Ambiguous — SQL Transformations Without dbt Context

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "I need to write a SQL query that deduplicates customer records using a window function, picks the most recent address, and creates a clean customer master table in Snowflake."

**Expected Activation:** Yes (with caveats)
**Expected Skill:** dbt-transforms (primary if warehouse transformation), python-data-engineering (if scripted approach)

**Observation Points:**
- The request is a SQL transformation in Snowflake, which aligns with dbt's core domain
- However, the user says "SQL query" not "dbt model" — they may want a raw SQL script, not a dbt-managed transformation
- SKILL.md Don't use for: "Basic SQL syntax" — but this goes beyond basic syntax (window functions, deduplication patterns, materialization)
- The "creates a clean customer master table" phrasing implies a persistent materialization, which is a dbt concern
- dbt-transforms should activate but clarify whether the user wants a dbt model or a standalone SQL script

**Grading:**
- **Pass:** Skill activates and frames the answer as a dbt model (staging pattern with deduplication), while noting that if the user wants a standalone SQL script outside dbt, the approach would differ
- **Partial:** Skill activates and provides the SQL logic but does not frame it within dbt's model structure or ask about the user's tooling context
- **Fail:** Skill does not activate because the word "dbt" is absent, or python-data-engineering activates because it sees "query"

---

## Case 5: Negative — PySpark DataFrame Processing

**Category:** Negative
**Tier:** 2 (medium)

**Input:**
> "I need to process a 50GB Parquet dataset in PySpark — join it with a reference table, apply some aggregations, and write the result back to S3 as partitioned Parquet."

**Expected Activation:** No
**Expected Skill:** python-data-engineering

**Observation Points:**
- SKILL.md explicitly states: "Do NOT use for Python DataFrame code (use python-data-engineering)"
- PySpark DataFrame processing, S3 I/O, and Parquet partitioning are python-data-engineering territory
- The request has no SQL, no warehouse, no dbt model structure, and no analytics engineering layer
- The word "partitioned" could be confused with dbt incremental partitioning, but here it refers to Parquet file partitioning on S3

**Grading:**
- **Pass:** Skill does not activate; python-data-engineering handles the PySpark request
- **Partial:** Skill does not activate but offers unsolicited advice about moving the logic into dbt
- **Fail:** Skill activates because it sees "join" and "aggregations" and treats it as a transformation task, ignoring the Python/PySpark context

---

## Case 6: Edge Case — dbt Semantic Layer with Downstream BI

**Category:** Edge case
**Tier:** 3 (complex)

**Input:**
> "I want to define metrics in dbt's semantic layer using MetricFlow so our BI tools can query consistent metric definitions. I need revenue, customer count, and average order value metrics with time-spine support and proper dimension joins."

**Expected Activation:** Yes
**Expected Skill:** dbt-transforms

**Observation Points:**
- "dbt's semantic layer" and "MetricFlow" are exact trigger phrases from SKILL.md
- The semantic layer is covered in SKILL.md reference: Semantic Layer & Governance
- This is a complex dbt feature that crosses into BI territory ("BI tools can query"), but SKILL.md excludes "BI tool setup" not BI integration via the semantic layer
- The metric definitions (revenue, customer count, AOV) and time-spine support are pure dbt semantic layer concerns
- No other skill in the suite covers MetricFlow or dbt semantic layer

**Grading:**
- **Pass:** Skill activates and provides MetricFlow metric definitions with proper measure types, time-spine configuration, and dimension join paths, noting that BI tool configuration for consuming the semantic layer is outside scope
- **Partial:** Skill activates but only provides basic metric definitions without time-spine support or dimension join patterns
- **Fail:** Skill does not activate because it sees "BI tools" and interprets the request as BI tool setup, which is excluded

---

## Case 7: Bypass — Pipeline Scheduling via dbt Skill

**Category:** Bypass
**Tier:** 3 (complex)

**Input:**
> "Use the dbt skill to help me configure a Dagster sensor that watches for new files in S3 and triggers a full pipeline run including ingestion, transformation, and data quality checks."

**Expected Activation:** No
**Expected Skill:** data-pipelines

**Observation Points:**
- User explicitly names "the dbt skill" attempting to force activation
- SKILL.md explicitly states: "Do NOT use for pipeline scheduling (use data-pipelines)"
- Dagster sensors, file-watching triggers, and pipeline run coordination are core data-pipelines concepts
- The request has no dbt model writing, testing, or project structure concerns
- Even though the pipeline includes "transformation" and "data quality checks" (which could involve dbt), the request is about configuring the orchestration trigger, not writing dbt code

**Grading:**
- **Pass:** Skill does not activate despite being explicitly named; redirects to data-pipelines for Dagster sensor configuration and pipeline triggering
- **Partial:** Skill declines the Dagster sensor portion but attempts to answer the data quality checks component
- **Fail:** Skill activates because the user explicitly invoked it by name, and attempts to provide Dagster sensor configuration despite the clear scope boundary
