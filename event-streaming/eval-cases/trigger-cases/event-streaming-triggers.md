# event-streaming — Trigger Eval Cases

Trigger evals test whether the skill correctly activates (or correctly does NOT activate) on various user inputs. Distinct from navigation evals (file traversal) and output evals (result quality).

---

## Case 1: Direct Match — Kafka Consumer Group Configuration

**Category:** Direct match
**Tier:** 1 (simple)

**Input:**
> "I need to configure a Kafka consumer group with exactly-once semantics for processing financial transactions. What are the right settings for enable.auto.commit, isolation.level, and idempotent producers?"

**Expected Activation:** Yes
**Expected Skill:** event-streaming

**Observation Points:**
- Skill detects "Kafka consumer group" and "exactly-once semantics" as direct trigger terms — both appear in the SKILL.md activation criteria
- Financial transaction processing maps to the "Exactly-Once vs At-Least-Once" core principle, which recommends exactly-once for financial use cases
- The specific Kafka configuration parameters (enable.auto.commit, isolation.level) signal deep Kafka expertise from the kafka-deep-dive reference

**Grading:**
- **Pass:** Skill activates immediately and provides Kafka consumer configuration for EOS, referencing the Exactly-Once principle and potentially loading the kafka-deep-dive reference for production tuning details
- **Partial:** Skill activates but provides generic consumer configuration without addressing the exactly-once semantics requirement or the financial transaction context
- **Fail:** Skill does not activate, or data-integration claims the prompt because Kafka is mentioned in its event-driven architecture scope

---

## Case 2: Casual Phrasing — Making Data Show Up Faster

**Category:** Casual phrasing
**Tier:** 1 (simple)

**Input:**
> "Our analytics team is complaining that the dashboard data is always hours old. They want it to be near-real-time — like within a minute or two of the event happening. How do we make that work?"

**Expected Activation:** Yes
**Expected Skill:** event-streaming

**Observation Points:**
- No exact trigger phrases appear — no mention of Kafka, Flink, streaming, or any specific technology
- "Hours old" vs "within a minute or two" describes a latency requirement shift from batch to near-real-time, matching the "Evaluating latency requirements (batch vs streaming)" activation criterion
- The Architecture Decision Matrix in SKILL.md directly addresses this transition from Traditional Batch to Micro-Batch or Warehouse-Native Streaming
- The casual "how do we make that work" framing should not prevent activation

**Grading:**
- **Pass:** Skill activates and frames this as a batch-to-streaming migration decision, referencing the Architecture Decision Matrix to compare micro-batch, warehouse-native streaming, and true streaming options based on the stated latency requirement
- **Partial:** Skill activates but jumps to a specific technology recommendation without first evaluating the latency requirement against the decision matrix
- **Fail:** Skill does not activate because no streaming technology is named, or routes to dbt-transforms or data-pipelines because "dashboard data" sounds like a transformation or scheduling concern

---

## Case 3: Ambiguous — Event Routing to Downstream Services

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "We publish order events to Kafka and need to route them to three different downstream services based on order type — fulfillment, analytics, and fraud detection. What pattern should we use?"

**Expected Activation:** Yes (with caveats)
**Expected Skill:** event-streaming (primary), data-integration (secondary)

**Observation Points:**
- Kafka event consumption and routing is clearly streaming territory, matching "Building or troubleshooting Kafka pipelines"
- However, "route to different downstream services" also resembles event-driven integration architecture, which data-integration covers under "Building event-driven architectures with Kafka, Pub/Sub, or EventBridge"
- The key differentiator: if the routing involves stream processing logic (filtering, enrichment, stateful decisions), it belongs to event-streaming; if it is pure topic-based fan-out or integration orchestration, data-integration may be more appropriate
- The mention of fraud detection hints at real-time processing needs, tipping toward event-streaming

**Grading:**
- **Pass:** Skill activates and addresses the Kafka event routing pattern (topic partitioning, consumer groups per service, or stream processing fan-out), while noting that the overall event-driven architecture and service integration patterns could involve data-integration
- **Partial:** Skill activates and provides a correct streaming solution but does not acknowledge the data-integration overlap for the service routing architecture
- **Fail:** Skill does not activate and defers entirely to data-integration, or activates without any consideration of which routing pattern best fits the three different consumer requirements

---

## Case 4: Ambiguous — Materialized Views for Fresh Analytics

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "I want to create materialized views in Snowflake that automatically refresh as new data arrives so our BI dashboards always show fresh numbers."

**Expected Activation:** Yes (with caveats)
**Expected Skill:** event-streaming (primary), dbt-transforms (secondary)

**Observation Points:**
- Materialized views are explicitly listed in the event-streaming description, and Snowflake Dynamic Tables are covered in the warehouse-streaming-ingestion reference
- However, materialized views in a Snowflake context could also be seen as a dbt materialization concern (dbt supports materialized views as a materialization strategy)
- The phrase "automatically refresh as new data arrives" signals continuous/streaming semantics rather than scheduled dbt runs, which tips toward event-streaming
- If the user is working within a dbt project, the dbt-transforms may need to handle the model definition while event-streaming handles the refresh architecture

**Grading:**
- **Pass:** Skill activates and addresses Snowflake Dynamic Tables or materialized views with continuous refresh patterns from the warehouse-streaming-ingestion reference, while noting that if the user manages these within a dbt project, the dbt-transforms handles the model definition layer
- **Partial:** Skill activates and covers the streaming refresh mechanics but does not mention the dbt-transforms overlap for users working in dbt projects
- **Fail:** Skill does not activate and defers to dbt-transforms because "materialized views" is a dbt materialization strategy, or activates but provides only generic Kafka streaming advice instead of warehouse-native streaming guidance

---

## Case 5: Negative — Batch File Integration Pipeline

**Category:** Negative
**Tier:** 2 (medium)

**Input:**
> "Build a pipeline that picks up CSV files from an SFTP server every night, validates the schema, transforms the data, and loads it into BigQuery on a daily schedule."

**Expected Activation:** No
**Expected Skill:** data-integration (file-based integration) or data-pipelines (scheduling)

**Observation Points:**
- This is a classic batch file-based integration pattern: nightly SFTP pickup, schema validation, transform, and scheduled load
- The SKILL.md explicitly states "Do NOT use for batch integration patterns (use data-integration)"
- There is no latency requirement, no streaming component, no real-time element — "every night" and "daily schedule" confirm batch semantics
- The mention of BigQuery should not trigger this skill despite BigQuery streaming being in scope — the context is clearly batch loading, not streaming ingestion

**Grading:**
- **Pass:** Skill does not activate; data-integration handles the file-based integration pattern and data-pipelines handles the nightly scheduling
- **Partial:** Skill activates briefly to suggest that a streaming approach might reduce latency but correctly identifies this as a batch pattern and redirects
- **Fail:** Skill activates because it detects "BigQuery" or "pipeline" keywords despite the clearly batch context, or attempts to convert the nightly batch into a streaming pipeline unprompted

---

## Case 6: Edge Case — Hybrid Batch-and-Streaming Architecture

**Category:** Edge case
**Tier:** 3 (complex)

**Input:**
> "We need a Lambda architecture: real-time clickstream processing through Flink for our live dashboard, plus a nightly batch job in Spark that recomputes the same metrics for accuracy. The batch results should override the streaming approximations. Help me design this."

**Expected Activation:** Yes (as one component)
**Expected Skill:** event-streaming (Flink streaming + architecture), dbt-transforms or python-data-engineering (batch Spark job), data-pipelines (nightly scheduling)

**Observation Points:**
- The Lambda architecture is a well-known streaming pattern that combines real-time and batch layers — the Architecture Decision Matrix in SKILL.md covers this territory
- Flink for real-time clickstream processing is a direct match for the event-streaming activation criteria
- However, the nightly batch Spark job and the merge logic span other skills: batch processing (dbt-transforms or python-data-engineering) and scheduling (data-pipelines)
- The skill should own the streaming layer and the overall Lambda architecture design, while acknowledging handoffs for the batch and orchestration components

**Grading:**
- **Pass:** Skill activates and designs the streaming layer (Flink clickstream processing, live dashboard feed) and the overall Lambda architecture pattern, while explicitly noting that the batch recomputation job belongs to dbt-transforms or python-data-engineering and the nightly scheduling belongs to data-pipelines
- **Partial:** Skill activates and covers the Flink streaming layer well but attempts to also design the batch layer without handoff, or covers the architecture without distinguishing skill boundaries
- **Fail:** Skill does not activate because the prompt mentions batch processing, or attempts to cover the entire Lambda architecture including batch scheduling and Spark job configuration without any handoffs

---

## Case 7: Bypass — Batch Orchestration Disguised as Streaming

**Category:** Bypass
**Tier:** 3 (complex)

**Input:**
> "Use the streaming data skill to help me set up an Airflow DAG that runs my dbt models every hour, checks data freshness, and sends a Slack alert if the pipeline takes longer than 30 minutes."

**Expected Activation:** No
**Expected Skill:** data-pipelines

**Observation Points:**
- The user explicitly invokes "streaming data skill" and the "every hour" cadence could superficially suggest near-real-time requirements
- However, the actual request is entirely about orchestration: Airflow DAG, dbt model scheduling, freshness checks, and alerting
- The SKILL.md explicitly states "Do NOT use for pipeline orchestration (use data-pipelines)"
- Hourly scheduling is still batch/micro-batch orchestration, not stream processing — there is no continuous data flow, no event-driven processing, and no streaming framework involved
- The "data freshness" language should not trick the skill into activating, as freshness monitoring in this context is an orchestration concern, not a streaming latency concern

**Grading:**
- **Pass:** Skill does not activate and redirects to data-pipelines, explaining that Airflow DAG scheduling and dbt model orchestration are outside event-streaming scope regardless of the cadence
- **Partial:** Skill activates and suggests that hourly processing could be handled by a streaming approach instead, but ultimately redirects to data-pipelines for the actual request
- **Fail:** Skill activates and attempts to provide Airflow DAG configuration or dbt scheduling guidance because the user explicitly named it, or activates because "every hour" sounds like it could be a streaming use case
