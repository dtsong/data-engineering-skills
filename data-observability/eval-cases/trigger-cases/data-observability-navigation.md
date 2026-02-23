# data-observability -- Navigation Eval Cases

Navigation evals test which reference files get loaded during a conversation. Correct navigation means the right file is loaded at the right time — and no unnecessary files are pre-loaded. Distinct from trigger evals (activation) and output evals (result quality).

---

## Case 1: SKILL.md Sufficient -- Simple Observability Pillar Question

**Category:** SKILL.md-sufficient
**Tier:** 1 (simple)

**Input:**
> "What are the five pillars of data observability and which should I prioritize?"

**Expected Skill Activated:** data-observability
**Expected Files Loaded:** SKILL.md only

**Observation Points:**
- "Five pillars" maps directly to the Five Pillars table in SKILL.md
- SKILL.md contains the pillar definitions, tool support, and severity levels — no reference detail needed
- Prioritization advice (freshness > volume > schema > distribution > lineage) is derivable from the severity column
- Loading any reference file here would violate the "one reference at a time" rule without justification

**Grading:**
- **Pass:** Skill answers from SKILL.md Five Pillars table only; recommends prioritizing freshness and volume first; does NOT load any reference files
- **Partial:** Skill answers correctly but preemptively loads freshness-monitoring.md to show an example
- **Fail:** Skill loads multiple reference files to answer a question already covered by the Five Pillars table; or provides pillar definitions that contradict the SKILL.md table

---

## Case 2: Reference Target -- Dagster Alerting Setup

**Category:** Reference target
**Tier:** 2 (medium)

**Input:**
> "Set up Slack alerting for my Dagster data pipeline using freshness policies"

**Expected Skill Activated:** data-observability
**Expected Files Loaded:** SKILL.md + alerting-patterns.md (Step 4)

**Observation Points:**
- "Slack alerting" + "Dagster" + "freshness policies" maps to alerting-patterns.md (Dagster alerting section)
- Only alerting-patterns.md should be loaded — not freshness-monitoring.md
- freshness-monitoring.md covers dbt source freshness and SQL queries, not Dagster freshness policies
- This tests single-reference precision: exactly one reference loaded, correctly targeted

**Grading:**
- **Pass:** Skill loads alerting-patterns.md only; provides Dagster FreshnessPolicy configuration and Slack sensor setup; unloads after answering
- **Partial:** Skill loads alerting-patterns.md but also preemptively loads freshness-monitoring.md because the query mentions "freshness"
- **Fail:** Skill answers from SKILL.md without loading alerting-patterns.md (missing Dagster-specific code); or loads multiple references simultaneously

---

## Case 3: Sequential Load -- Full Observability Setup

**Category:** Sequential procedure
**Tier:** 3 (complex)

**Input:**
> "Set up complete data observability for my dbt project: freshness monitoring, volume anomaly detection, and Slack alerting for all critical sources."

**Expected Skill Activated:** data-observability (full-stack mode)
**Expected Files Loaded:** SKILL.md -> freshness-monitoring.md (Step 3) -> volume-anomaly-detection.md (Step 3) -> alerting-patterns.md (Step 4)

**Observation Points:**
- "Complete data observability" with three explicit pillars activates full-stack mode (Steps 3-4)
- References must be loaded sequentially, not simultaneously
- Peak load at any single point: SKILL.md (~1,800 tokens) + one reference (~1,400 tokens) is within 5,500 ceiling
- After generating freshness config from freshness-monitoring.md, that file should be unloaded before loading volume-anomaly-detection.md
- After generating volume config, volume-anomaly-detection.md should be unloaded before loading alerting-patterns.md
- incident-response.md should NOT be loaded — no incident workflow was requested

**Grading:**
- **Pass:** Skill follows 3-reference sequential load pattern; generates dbt freshness YAML, volume anomaly SQL, and Slack alerting config in distinct steps; never holds more than one reference simultaneously
- **Partial:** Skill loads two references simultaneously (e.g., freshness-monitoring + volume-anomaly-detection at once) but produces correct configs
- **Fail:** Skill loads all three references simultaneously; or skips volume anomaly detection despite being explicitly requested; or loads incident-response.md when no incident workflow was requested

---

## Case 4: Conditional Load -- Incident Response Only

**Category:** Conditional load
**Tier:** 2 (medium)

**Input:**
> "Create an incident response workflow for when our data pipelines fail. Include communication templates and a postmortem template."

**Expected Skill Activated:** data-observability (incident mode)
**Expected Files Loaded:** SKILL.md -> incident-response.md (Step 5 only)

**Observation Points:**
- "Incident response workflow" triggers incident mode — skill should skip directly to Step 5
- incident-response.md should ONLY be loaded at Step 5 — not earlier in the procedure
- This tests that the conditional load rule is respected: incident-response.md is not pre-loaded at skill activation
- "Communication templates" and "postmortem template" are both in incident-response.md — no other reference needed
- Loading freshness-monitoring.md or alerting-patterns.md here would be redundant and wasteful

**Grading:**
- **Pass:** Skill loads incident-response.md only at Step 5; generates incident classification criteria, triage workflow, communication templates (initial/update/resolution), and postmortem template; does NOT load freshness-monitoring, volume-anomaly-detection, or alerting-patterns
- **Partial:** Skill loads incident-response.md but also loads alerting-patterns.md because it associates "pipeline fail" with alerting
- **Fail:** incident-response.md is never loaded; skill generates incident workflow from memory without the standardized templates; or multiple references are loaded simultaneously
