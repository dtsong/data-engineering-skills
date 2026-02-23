# data-observability -- Trigger Eval Cases

Trigger evals test whether the skill correctly activates (or correctly does NOT activate) on various user inputs. Distinct from navigation evals (file traversal) and output evals (result quality).

---

## Case 1: Direct Match -- Freshness Monitoring for dbt Sources

**Category:** Direct match
**Tier:** 1 (simple)

**Input:**
> "Set up freshness monitoring for my dbt sources"

**Expected Activation:** Yes
**Expected Skill:** data-observability

**Observation Points:**
- Prompt contains exact trigger phrase "freshness monitoring" from SKILL.md description
- "dbt sources" maps to dbt source freshness configuration in freshness-monitoring.md
- No competing skill handles freshness monitoring setup — dbt-transforms handles model authoring, not monitoring

**Grading:**
- **Pass:** Skill activates and classifies as pillar-specific mode (freshness); asks about current sources.yml state and SLA requirements before generating config
- **Partial:** Skill activates but generates generic freshness YAML without asking about warn/error thresholds or source table names
- **Fail:** Skill does not activate; or dbt-transforms activates because it sees "dbt sources"

---

## Case 2: Casual Phrasing -- Detecting Stale Pipeline Data

**Category:** Casual phrasing
**Tier:** 1 (simple)

**Input:**
> "How do I know when my pipeline data goes stale?"

**Expected Activation:** Yes
**Expected Skill:** data-observability

**Observation Points:**
- No mention of specific tooling — keyword is "stale" which maps to "stale data" in SKILL.md description
- "Pipeline data" provides data engineering context, not generic monitoring
- data-pipelines could compete but "stale data" detection is squarely in data-observability scope
- Question is conceptual — skill should explain freshness monitoring before generating code

**Grading:**
- **Pass:** Skill activates, explains freshness monitoring as the core approach, asks about orchestrator and data warehouse before generating specific config
- **Partial:** Skill activates but immediately generates code without understanding the user's stack
- **Fail:** Skill does not activate; or data-pipelines activates because it sees "pipeline"

---

## Case 3: Ambiguous -- Add Alerting to Data Pipeline

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "Add alerting to my data pipeline"

**Expected Activation:** Conditional (ask clarifying question)
**Expected Skill:** data-observability (if data quality/freshness alerting confirmed), data-pipelines (if orchestrator failure alerting)

**Observation Points:**
- "Alerting" is a trigger signal for data-observability, but "data pipeline" overlaps with data-pipelines scope
- Alerting could mean: (a) data quality/freshness alerts (data-observability), or (b) DAG/task failure alerts (data-pipelines)
- Skill should clarify: "Are you looking for data quality and freshness alerting, or pipeline run failure notifications?"
- If user confirms data quality alerting, data-observability activates fully

**Grading:**
- **Pass:** Skill activates with a clarifying question about alerting type before generating configuration; activates fully if data quality/freshness alerting is confirmed
- **Partial:** Skill activates but generates data observability alerting without checking if the user wanted pipeline failure alerts
- **Fail:** Skill does not activate; or data-pipelines activates without distinguishing alerting type

---

## Case 4: Negative -- Data Quality Tests for Client Delivery

**Category:** Negative
**Tier:** 2 (medium)

**Input:**
> "Write data quality tests for client delivery"

**Expected Activation:** No
**Expected Skill:** data-testing

**Observation Points:**
- "Data quality tests" maps to data-testing scope, not data-observability
- "Client delivery" further tips toward data-testing + client-delivery handoff
- data-observability monitors data in production; data-testing validates data quality as deliverables
- SKILL.md "Don't use for" section explicitly excludes "data quality testing as deliverables"

**Grading:**
- **Pass:** Skill does not activate; data-testing handles the quality test authoring; optionally notes that data-observability can monitor these tests in production
- **Partial:** Skill does not activate but provides no redirect to the correct skill
- **Fail:** Skill activates and attempts to generate monitoring configs for a test-authoring request

---

## Case 5: Edge Case -- Incident Response Runbook for Data Failures

**Category:** Edge case
**Tier:** 2 (medium)

**Input:**
> "Build an incident response runbook for data failures"

**Expected Activation:** Yes
**Expected Skill:** data-observability (incident mode)

**Observation Points:**
- "Incident response runbook" directly matches SKILL.md description and incident-response.md reference
- "Data failures" provides clear data engineering context
- Skill should classify as incident mode and skip directly to Step 5 in the procedure
- No other skill handles incident response workflows

**Grading:**
- **Pass:** Skill activates in incident mode; loads incident-response.md; generates classification criteria, triage workflow, communication templates, and postmortem template
- **Partial:** Skill activates but starts from Step 1 instead of jumping to incident mode (Step 5)
- **Fail:** Skill does not activate; or data-pipelines activates because it sees "data failures"

---

## Case 6: Bypass -- Schedule dbt Models to Run Hourly

**Category:** Bypass
**Tier:** 2 (medium)

**Input:**
> "Schedule my dbt models to run every hour"

**Expected Activation:** No
**Expected Skill:** data-pipelines

**Observation Points:**
- "Schedule" + "dbt models" + "run every hour" maps directly to data-pipelines scope (orchestration)
- data-observability's "Don't use for" section explicitly excludes "scheduling or orchestrating pipelines"
- No monitoring, alerting, or observability is requested
- "Every hour" is a scheduling concern, not a freshness SLA

**Grading:**
- **Pass:** Skill does not activate; data-pipelines handles the scheduling request
- **Partial:** Skill does not activate but mentions that freshness monitoring could complement the schedule
- **Fail:** Skill activates because it associates "hourly" with freshness monitoring

---

## Case 7: Negative -- Profile Source Data for Quality Issues

**Category:** Negative
**Tier:** 1 (simple)

**Input:**
> "Profile my source data for quality issues"

**Expected Activation:** No
**Expected Skill:** data-testing or duckdb

**Observation Points:**
- "Profile source data" maps to data profiling, which is duckdb or data-testing scope
- "Quality issues" could superficially resemble observability, but profiling is a one-time analysis, not ongoing monitoring
- data-observability handles production monitoring, not ad-hoc profiling
- duckdb skill handles data profiling with SQL; data-testing handles quality assessment

**Grading:**
- **Pass:** Skill does not activate; duckdb or data-testing handles the profiling request
- **Partial:** Skill does not activate but fails to redirect to the correct skill
- **Fail:** Skill activates because it sees "quality" and attempts to set up monitoring for a profiling request
