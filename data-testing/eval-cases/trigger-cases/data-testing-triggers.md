# data-testing -- Trigger Eval Cases

Trigger evals test whether the skill correctly activates (or correctly does NOT activate) on various user inputs. Distinct from navigation evals (file traversal) and output evals (result quality).

---

## Case 1: Direct Match -- Data Quality Tests for dbt Project

**Category:** Direct match
**Tier:** 1 (simple)

**Input:**
> "Write data quality tests for my dbt project"

**Expected Activation:** Yes
**Expected Skill:** data-testing

**Observation Points:**
- Prompt contains exact phrase "data quality tests" and context keyword "dbt project"
- Maps directly to SKILL.md description: "data testing strategy", "data quality tests"
- No competing skill handles standalone data testing strategy — dbt-transforms handles model authoring, not test strategy
- Skill should classify as Implementation mode (Step 1) and default to dbt testing layer

**Grading:**
- **Pass:** Skill activates and classifies as Implementation mode; asks about model layer (staging/intermediate/marts) and existing test coverage before generating test YAML
- **Partial:** Skill activates but generates generic tests without asking about project structure or layer
- **Fail:** Skill does not activate; or dbt-transforms activates because it sees "dbt project"

---

## Case 2: Casual Phrasing -- How to Know Pipeline Output Is Correct

**Category:** Casual phrasing
**Tier:** 1 (simple)

**Input:**
> "How do I know my pipeline output is correct?"

**Expected Activation:** Yes
**Expected Skill:** data-testing

**Observation Points:**
- No mention of specific tools or frameworks — keyword is "pipeline output" with "correct" implying validation
- "Know my pipeline output is correct" maps to Validation mode in SKILL.md
- duckdb skill could compete for "pipeline" but validation intent tips to data-testing
- Skill should recommend testing layers and offer to generate validation queries

**Grading:**
- **Pass:** Skill activates, classifies as Validation mode, recommends appropriate testing layers (aggregate reconciliation + row-level checks), offers to generate SQL assertions
- **Partial:** Skill activates but provides only high-level advice without offering specific test patterns
- **Fail:** Skill does not activate; or duckdb activates because it sees "pipeline" as a general data query context

---

## Case 3: Ambiguous -- Add Tests to My Data Model

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "Add tests to my data model"

**Expected Activation:** Conditional (ask clarifying question)
**Expected Skill:** data-testing (if standalone test strategy confirmed); dbt-transforms (if tests are part of model authoring)

**Observation Points:**
- "Add tests" with "data model" could be either standalone test strategy or inline model tests
- If user is building a new dbt model and wants tests embedded in the YAML, dbt-transforms is more appropriate
- If user has existing models and wants a testing strategy layered on top, data-testing is correct
- Skill should clarify: "Are you adding tests to an existing project, or building a new model with tests included?"

**Grading:**
- **Pass:** Skill activates with a clarifying question about whether this is test strategy for existing models vs inline tests for new models; activates fully if standalone testing is confirmed
- **Partial:** Skill activates and assumes standalone test strategy without checking if user is mid-model authoring
- **Fail:** dbt-transforms activates and embeds tests in model YAML without considering standalone test strategy; or neither skill activates

---

## Case 4: Negative -- Unit Tests for Python ETL Script

**Category:** Negative
**Tier:** 2 (medium)

**Input:**
> "Write unit tests for my Python ETL script"

**Expected Activation:** No
**Expected Skill:** python-data-engineering

**Observation Points:**
- "Unit tests" + "Python ETL script" is software testing, not data quality testing
- data-testing covers SQL assertions and data quality checks, not pytest-style unit tests for Python code
- python-data-engineering handles Python scripting, testing frameworks, and ETL logic
- "ETL" could superficially match data testing, but "unit tests" + "Python" is the distinguishing signal

**Grading:**
- **Pass:** Skill does not activate; redirects to python-data-engineering for pytest-based unit testing; optionally notes that data-testing is available for data quality assertions on the ETL output
- **Partial:** Skill activates and attempts to provide data quality tests instead of Python unit tests
- **Fail:** Skill activates and generates SQL assertions when the user clearly wants pytest-style Python tests

---

## Case 5: Edge Case -- Test Report for Client Delivery

**Category:** Edge case
**Tier:** 3 (complex)

**Input:**
> "Generate a test report for client delivery"

**Expected Activation:** Yes (with handoff)
**Expected Skill:** data-testing (primary), client-delivery (handoff for packaging)

**Observation Points:**
- "Test report" maps to Deliverable mode in SKILL.md (Step 5)
- "Client delivery" signals handoff to client-delivery skill for engagement scaffolding
- Skill should handle test report generation (scorecard, coverage metrics, failure summary) and signal handoff to client-delivery for final packaging
- This tests that the skill correctly scopes itself and doesn't attempt full client engagement scaffolding

**Grading:**
- **Pass:** Skill activates in Deliverable mode; generates test summary report, coverage scorecard, and failure review; explicitly signals handoff to client-delivery for final client packaging; does NOT generate engagement scaffolding
- **Partial:** Skill activates but attempts to generate full client delivery documentation without handoff to client-delivery
- **Fail:** client-delivery activates first because of "client delivery" keyword; data-testing never activates for the test report

---

## Case 6: Bypass -- Set Up Dagster Asset Checks

**Category:** Bypass
**Tier:** 3 (complex)

**Input:**
> "Set up Dagster asset checks"

**Expected Activation:** No
**Expected Skill:** data-pipelines

**Observation Points:**
- "Dagster asset checks" is pipeline orchestration functionality, not data testing strategy
- data-testing's "Don't use for" section explicitly excludes pipeline scheduling
- Dagster asset checks are scheduling-layer concerns handled by data-pipelines
- "Asset checks" could superficially resemble data quality testing, but the Dagster context tips to data-pipelines

**Grading:**
- **Pass:** Skill does not activate; data-pipelines handles the Dagster asset check configuration
- **Partial:** Skill does not activate but mentions data-testing could provide the SQL assertions that Dagster asset checks execute
- **Fail:** Skill activates because it sees "checks" and attempts to generate dbt tests instead of Dagster asset checks

---

## Case 7: Negative -- Monitor Data Freshness in Production

**Category:** Negative
**Tier:** 2 (medium)

**Input:**
> "Monitor data freshness in production"

**Expected Activation:** No
**Expected Skill:** data-observability

**Observation Points:**
- "Monitor" + "production" + "data freshness" maps directly to observability, not testing
- data-testing's "Don't use for" section explicitly excludes production monitoring and alerting
- data-observability handles freshness SLAs, anomaly detection, and production alerting
- "Data freshness" could superficially resemble a data quality check, but "monitor" + "production" is the distinguishing signal

**Grading:**
- **Pass:** Skill does not activate; redirects to data-observability for production freshness monitoring; optionally notes that data-testing can provide freshness assertions for CI/dev environments
- **Partial:** Skill activates and provides freshness checks suitable for CI but not production monitoring
- **Fail:** Skill activates and generates dbt freshness tests as if they were production monitoring
