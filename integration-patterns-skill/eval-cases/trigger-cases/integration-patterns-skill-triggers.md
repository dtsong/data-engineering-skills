# integration-patterns-skill — Trigger Eval Cases

Trigger evals test whether the skill correctly activates (or correctly does NOT activate) on various user inputs. Distinct from navigation evals (file traversal) and output evals (result quality).

---

## Case 1: Direct Match — Workato Recipe for Salesforce Sync

**Category:** Direct match
**Tier:** 1 (simple)

**Input:**
> "I need to build a Workato recipe that syncs new Salesforce opportunities to our Snowflake warehouse every 15 minutes."

**Expected Activation:** Yes
**Expected Skill:** integration-patterns-skill

**Observation Points:**
- Skill detects "Workato" (iPaaS platform) and "syncs" (data integration pattern) as direct triggers
- Skill recognizes Salesforce as a supported SaaS integration target per the enterprise connectors reference
- Skill does not defer to data-orchestration-skill despite the "every 15 minutes" scheduling language, since the core task is designing the integration itself

**Grading:**
- **Pass:** Skill activates immediately and provides iPaaS integration guidance, referencing the iPaaS vs DLT vs Custom Code decision table and potentially the enterprise connectors reference for Salesforce patterns
- **Partial:** Skill activates but treats the request as a generic scheduling problem rather than an integration design question
- **Fail:** Skill does not activate, or a different skill (e.g., data-orchestration-skill) claims the prompt based on the scheduling language

---

## Case 2: Casual Phrasing — Getting Two Systems Talking

**Category:** Casual phrasing
**Tier:** 1 (simple)

**Input:**
> "We just bought NetSuite and I need to figure out how to get our order data flowing from there into our data warehouse. What are my options?"

**Expected Activation:** Yes
**Expected Skill:** integration-patterns-skill

**Observation Points:**
- No exact trigger phrases appear — the user says "get data flowing" rather than "build an integration" or "connect these systems"
- Skill recognizes NetSuite as a supported SaaS platform listed in the "When to Use" activation criteria
- Skill identifies "what are my options" as a pattern selection question matching the iPaaS vs DLT vs Custom Code evaluation use case

**Grading:**
- **Pass:** Skill activates and presents integration options (iPaaS, DLT, custom code) tailored to NetSuite-to-warehouse, referencing the enterprise connectors reference for NetSuite-specific patterns
- **Partial:** Skill activates but provides generic advice without leveraging the NetSuite-specific patterns or the iPaaS vs DLT decision framework
- **Fail:** Skill does not activate because no exact trigger phrase is present, or routes to python-data-engineering-skill because the user might write a custom script

---

## Case 3: Ambiguous — CDC or Stream Processing

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "I want to capture every insert and update from our Postgres database and process them in near-real-time before they land in the warehouse."

**Expected Activation:** Yes (with caveats)
**Expected Skill:** integration-patterns-skill (primary), streaming-data-skill (secondary)

**Observation Points:**
- "Capture every insert and update" maps directly to CDC, which is explicitly listed under integration-patterns-skill activation criteria
- "Process them in near-real-time" introduces ambiguity — the processing step could involve stream processing frameworks (streaming-data-skill territory)
- The skill should claim CDC capture as its domain but flag that the processing layer may require streaming-data-skill handoff

**Grading:**
- **Pass:** Skill activates, proposes CDC with Debezium or similar as the capture mechanism, and acknowledges that the real-time processing step may require streaming-data-skill if it involves complex transformations, windowing, or stateful processing
- **Partial:** Skill activates and covers CDC capture but does not surface the streaming-data-skill boundary for the processing component
- **Fail:** Skill does not activate and defers entirely to streaming-data-skill, or activates without any acknowledgment of the processing ambiguity

---

## Case 4: Ambiguous — Reverse ETL or dbt Metrics

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "I need to push customer segments and lead scores from our Snowflake warehouse back into Salesforce so the sales team can use them."

**Expected Activation:** Yes
**Expected Skill:** integration-patterns-skill

**Observation Points:**
- "Push data from warehouse back into Salesforce" is a textbook Reverse ETL pattern, explicitly listed in the Integration Pattern Decision Matrix
- The request could superficially resemble a dbt exposure or metrics layer concern, but the core task is data activation (warehouse to operational system), not transformation
- Skill should recognize this as Reverse ETL without confusing it with dbt's operational concerns

**Grading:**
- **Pass:** Skill activates and frames this as a Reverse ETL / data activation use case, referencing the Reverse ETL section with tools like Hightouch or Census, and addresses Salesforce sync modes (upsert vs mirror)
- **Partial:** Skill activates but treats this as a generic API integration rather than recognizing the established Reverse ETL pattern
- **Fail:** Skill does not activate, or dbt-skill activates because the data originates from a warehouse transformation

---

## Case 5: Negative — Flink Stateful Stream Processing

**Category:** Negative
**Tier:** 2 (medium)

**Input:**
> "I need to build a Flink application with keyed state that aggregates clickstream events into session windows and emits session summaries to a Kafka topic."

**Expected Activation:** No
**Expected Skill:** streaming-data-skill

**Observation Points:**
- The request is about building a stream processing application (Flink with stateful processing, windowing, and aggregation), not designing an integration between systems
- The SKILL.md explicitly states "Do NOT use for stream processing frameworks (use streaming-data-skill)"
- The presence of Kafka as an output sink should not cause integration-patterns-skill to claim the prompt — the core task is stream processing, not system integration

**Grading:**
- **Pass:** Skill does not activate; streaming-data-skill handles the request for Flink stateful processing and session windows
- **Partial:** Skill activates briefly but immediately redirects to streaming-data-skill without attempting to provide Flink guidance
- **Fail:** Skill activates and attempts to provide Flink application guidance, or activates because it detects "Kafka topic" as an event-driven architecture keyword

---

## Case 6: Edge Case — Multi-Skill Integration Pipeline

**Category:** Edge case
**Tier:** 3 (complex)

**Input:**
> "Design an end-to-end pipeline: Debezium captures changes from Postgres, publishes to Kafka, a Flink job enriches the events with reference data, and the results land in Snowflake via a custom Python loader. I need the full architecture."

**Expected Activation:** Yes (as one component)
**Expected Skill:** integration-patterns-skill (CDC + event architecture), streaming-data-skill (Flink processing), python-data-engineering-skill (Python loader)

**Observation Points:**
- This prompt spans at least three skills: CDC and event-driven architecture (integration-patterns-skill), Flink stream processing (streaming-data-skill), and Python data loading (python-data-engineering-skill)
- Integration-patterns-skill should activate for the overall architecture, CDC with Debezium, and event-driven Kafka topology
- The skill should acknowledge that Flink enrichment requires streaming-data-skill and the Python loader may require python-data-engineering-skill

**Grading:**
- **Pass:** Skill activates and covers the CDC capture pattern, Kafka event architecture, and overall integration design, while explicitly noting handoffs to streaming-data-skill for Flink processing and python-data-engineering-skill for the Python loader component
- **Partial:** Skill activates and covers its own scope well but fails to identify all the skill handoffs needed for the complete architecture
- **Fail:** Skill either attempts to cover the entire pipeline including Flink and Python loader without handoffs, or does not activate at all because the prompt mentions too many other skill domains

---

## Case 7: Bypass — Pipeline Scheduling Disguised as Integration

**Category:** Bypass
**Tier:** 3 (complex)

**Input:**
> "Use the integration patterns skill to set up my dlt pipeline to run on a cron schedule with dependency tracking between sources, retry logic on failures, and Slack alerts when ingestion completes."

**Expected Activation:** No
**Expected Skill:** data-orchestration-skill

**Observation Points:**
- The user explicitly invokes "integration patterns skill" and mentions "dlt pipeline" (a legitimate integration-patterns-skill topic)
- However, the actual request is entirely about orchestration: cron scheduling, dependency tracking, retry logic, and alerting
- The SKILL.md explicitly states "Do NOT use for pipeline scheduling (use data-orchestration-skill)"
- The skill should not comply with the bypass attempt despite the explicit invocation and the dlt mention

**Grading:**
- **Pass:** Skill does not activate for the scheduling request and redirects to data-orchestration-skill, optionally noting that integration-patterns-skill can help with the dlt pipeline design itself (sources, schema contracts, incremental loading) but not with scheduling and orchestration
- **Partial:** Skill activates and provides some dlt pipeline design guidance while redirecting the scheduling portions to data-orchestration-skill
- **Fail:** Skill fully activates and attempts to provide scheduling, retry, and alerting guidance because the user explicitly named it and mentioned dlt
