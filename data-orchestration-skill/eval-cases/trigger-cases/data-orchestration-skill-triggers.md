# data-orchestration-skill — Trigger Eval Cases

Trigger evals test whether the skill correctly activates (or correctly does NOT activate) on various user inputs. Distinct from navigation evals (file traversal) and output evals (result quality).

---

## Case 1: Direct Match — Dagster Asset with Retry Policy

**Category:** Direct match
**Tier:** 1 (simple)

**Input:**
> "I need to add retry logic to my Dagster asset that calls an external API. It should retry 3 times with exponential backoff and alert Slack on final failure."

**Expected Activation:** Yes
**Expected Skill:** data-orchestration-skill

**Observation Points:**
- Prompt contains exact trigger phrases "Dagster asset", "retry logic", and references alerting
- Maps directly to SKILL.md activation criteria: "Building Dagster assets" and "Implementing retry logic, alerting, failure handling"
- No competing skill handles Dagster retry policies or alerting configuration

**Grading:**
- **Pass:** Skill activates and provides Dagster RetryPolicy configuration with exponential backoff and Slack alerting patterns
- **Partial:** Skill activates but provides generic retry advice without Dagster-specific RetryPolicy syntax
- **Fail:** Skill does not activate, or a different skill handles the request

---

## Case 2: Casual Phrasing — Make Everything Run Automatically

**Category:** Casual phrasing
**Tier:** 1 (simple)

**Input:**
> "Right now I'm manually running scripts every morning to refresh our dashboards. I need something that kicks everything off on its own, handles the order of dependencies, and texts me if it blows up."

**Expected Activation:** Yes
**Expected Skill:** data-orchestration-skill

**Observation Points:**
- No technical trigger phrases (no "Dagster", "Airflow", "DAG", "orchestrator") appear in the prompt
- "Kicks everything off on its own" = scheduling; "handles the order of dependencies" = dependency resolution; "texts me if it blows up" = alerting on failure
- All three concerns map directly to core orchestration responsibilities in SKILL.md
- The user may not even know they need an orchestrator, which is itself a valid entry point ("Deciding whether you need an orchestrator at all")

**Grading:**
- **Pass:** Skill activates and identifies this as a pipeline orchestration need, recommending an orchestrator with scheduling, dependency management, and alerting capabilities
- **Partial:** Skill activates but jumps straight into a specific tool (e.g., Dagster) without first establishing that orchestration is the solution
- **Fail:** Skill does not activate because no orchestration-specific vocabulary is present

---

## Case 3: Ambiguous — dbt Job Scheduling

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "How do I schedule my dbt models to run every 4 hours and only rebuild the models that have changed upstream?"

**Expected Activation:** Yes (with caveats)
**Expected Skill:** data-orchestration-skill (primary), dbt-skill (possible secondary for dbt Cloud native scheduling)

**Observation Points:**
- "Schedule dbt models to run" is an orchestration concern (scheduling, execution triggers)
- "Only rebuild models that have changed upstream" could mean Dagster's asset-aware scheduling or dbt Cloud's slim CI/state-aware runs
- dbt-skill covers dbt Cloud job configuration; data-orchestration-skill covers external orchestrators running dbt
- The ambiguity hinges on whether the user has an external orchestrator or wants dbt Cloud's native scheduling

**Grading:**
- **Pass:** Skill activates and addresses scheduling dbt runs via an external orchestrator (dagster-dbt or cosmos), while noting that dbt Cloud native scheduling is an alternative handled by dbt-skill's CI/CD reference
- **Partial:** Skill activates but only covers external orchestration without acknowledging the dbt Cloud alternative
- **Fail:** Skill does not activate (deferring entirely to dbt-skill), or activates and tries to write dbt model SQL

---

## Case 4: Ambiguous — Data Pipeline with DLT Sources

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "I'm setting up DLT to ingest data from 5 REST APIs. How should I structure the sources, handle pagination, and deal with rate limits?"

**Expected Activation:** No
**Expected Skill:** integration-patterns-skill

**Observation Points:**
- DLT source configuration, pagination, and rate limiting are integration-patterns-skill concerns
- SKILL.md explicitly states: "Don't use for: DLT source/destination config (use integration-patterns-skill)"
- However, the word "pipeline" and "DLT" could trick the skill into activating because SKILL.md mentions "dagster-dlt" integration
- The key distinction: this prompt is about DLT source design, not about orchestrating DLT within a pipeline

**Grading:**
- **Pass:** Skill does not activate; defers to integration-patterns-skill for DLT source configuration, pagination, and rate limiting
- **Partial:** Skill partially activates and offers to help with the orchestration layer (scheduling the DLT pipeline) while deferring source config to integration-patterns-skill
- **Fail:** Skill fully activates and attempts to provide DLT source configuration guidance

---

## Case 5: Negative — Write SQL Transformation Logic

**Category:** Negative
**Tier:** 2 (medium)

**Input:**
> "I need to build a revenue recognition model that joins invoices, line items, and payment schedules, then applies ASC 606 allocation rules across performance obligations."

**Expected Activation:** No
**Expected Skill:** dbt-skill

**Observation Points:**
- This is purely a data transformation task involving complex business logic (revenue recognition, ASC 606)
- SKILL.md Scope Constraints: "Hand off transformation logic to dbt-skill"
- No scheduling, dependency management, monitoring, retry, or alerting concerns are present
- The word "model" here refers to a data model (transformation), not an orchestration concept

**Grading:**
- **Pass:** Skill does not activate; dbt-skill handles the transformation request
- **Partial:** Skill does not activate but incorrectly suggests data-orchestration-skill might be needed later without being asked
- **Fail:** Skill activates because it sees "pipeline" implied in the complex multi-table join, or attempts to wrap the transformation in orchestration boilerplate

---

## Case 6: Edge Case — Orchestrate a Multi-Tool Pipeline

**Category:** Edge case
**Tier:** 3 (complex)

**Input:**
> "I need a Dagster pipeline that runs a DLT ingestion job at 6am, waits for it to complete, then triggers a dbt build of only the affected models, runs data quality checks with Elementary, and sends a Slack summary with row counts and freshness status."

**Expected Activation:** Yes (as the primary coordinator)
**Expected Skill:** data-orchestration-skill (primary), integration-patterns-skill (for DLT config), dbt-skill (for dbt model logic), ai-data-integration-skill (not involved)

**Observation Points:**
- This is fundamentally an orchestration task: scheduling, dependency sequencing, sensor-based triggers, alerting, and observability
- data-orchestration-skill owns the Dagster pipeline structure, scheduling, dagster-dbt integration, dagster-dlt integration, and Slack alerting
- The DLT ingestion configuration and dbt model logic are handoffs to sibling skills
- Elementary data quality checks could be orchestrated by this skill but the check definitions belong to dbt-skill's data quality reference

**Grading:**
- **Pass:** Skill activates as the primary skill, provides Dagster pipeline structure with DLT assets, dbt assets via dagster-dbt, sensor-based triggering, and Slack alerting. Clearly notes handoffs for DLT source config and dbt model logic
- **Partial:** Skill activates but attempts to handle all components without noting handoffs to sibling skills
- **Fail:** Skill does not activate because the request mentions too many non-orchestration tools, or a different skill claims primary ownership

---

## Case 7: Bypass — Kafka Streaming via Orchestration Skill

**Category:** Bypass
**Tier:** 3 (complex)

**Input:**
> "Use the data orchestration skill to help me set up a Kafka consumer group that processes events in real-time with exactly-once semantics and handles schema evolution with Avro."

**Expected Activation:** No
**Expected Skill:** streaming-data-skill

**Observation Points:**
- User explicitly names the skill, attempting to force activation
- SKILL.md Don't use for: "Kafka/Flink streaming (use streaming-data-skill)"
- Kafka consumer groups, exactly-once semantics, and schema evolution are core streaming-data-skill topics
- The request has no scheduling, dependency management, or batch pipeline concern — it is purely a stream processing task
- An orchestrator might schedule batch consumers, but real-time consumer groups with exactly-once semantics are a streaming concern

**Grading:**
- **Pass:** Skill does not activate despite being explicitly named; redirects to streaming-data-skill for Kafka consumer configuration, exactly-once semantics, and schema evolution
- **Partial:** Skill declines the Kafka consumer portion but offers to help orchestrate a batch fallback without being asked
- **Fail:** Skill activates because the user explicitly invoked it by name, and attempts to provide Kafka consumer guidance despite the clear scope boundary
