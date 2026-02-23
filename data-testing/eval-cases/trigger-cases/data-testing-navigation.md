# data-testing -- Navigation Eval Cases

Navigation evals test which reference files get loaded during a conversation. Correct navigation means the right file is loaded at the right time — and no unnecessary files are pre-loaded. Distinct from trigger evals (activation) and output evals (result quality).

---

## Case 1: SKILL.md Sufficient -- Simple Testing Layer Question

**Category:** SKILL.md-sufficient
**Tier:** 1 (simple)

**Input:**
> "What kinds of data tests should I have at the staging layer vs the marts layer?"

**Expected Skill Activated:** data-testing
**Expected Files Loaded:** SKILL.md only

**Observation Points:**
- "Staging layer vs marts layer" maps directly to the Testing Layers table in SKILL.md
- Staging = schema tests (unique, not_null, accepted_values); Marts = schema + aggregate reconciliation + custom business rules
- Coverage targets are in the SKILL.md Core Principles (100% PK, 80%+ column on marts)
- No edge case requires reference file detail — the Testing Layers table and Core Principles are sufficient
- Loading dbt-testing-strategy.md here would violate the "one reference at a time" rule without justification

**Grading:**
- **Pass:** Skill answers from SKILL.md Testing Layers table and Core Principles only; explains staging vs marts test expectations; does NOT load dbt-testing-strategy.md
- **Partial:** Skill answers correctly but preemptively loads dbt-testing-strategy.md to show YAML examples
- **Fail:** Skill loads dbt-testing-strategy.md to answer a question already covered by the Testing Layers table; or provides incorrect layer recommendations

---

## Case 2: Reference Target -- dbt CI/CD Test Integration

**Category:** dbt-testing-strategy target
**Tier:** 2 (medium)

**Input:**
> "How do I set up slim CI test selection in dbt so only changed models get tested?"

**Expected Skill Activated:** data-testing
**Expected Files Loaded:** SKILL.md + dbt-testing-strategy.md (Step 2/3)

**Observation Points:**
- "Slim CI" and "changed models" are not in SKILL.md; they require dbt-testing-strategy.md CI/CD Integration section
- Only dbt-testing-strategy.md should be loaded — not pipeline-validation or sql-assertion-patterns
- Loading sql-assertion-patterns.md here would be irrelevant and violate the context ceiling rule
- This tests single-reference precision: exactly one reference loaded, correctly targeted

**Grading:**
- **Pass:** Skill loads dbt-testing-strategy.md only; provides `dbt build --select state:modified+` command with `--state` flag explanation; explains CI pipeline steps; unloads after answering
- **Partial:** Skill loads dbt-testing-strategy.md but also preemptively loads pipeline-validation.md
- **Fail:** Skill answers from SKILL.md without loading dbt-testing-strategy.md (missing slim CI commands); or loads multiple references simultaneously

---

## Case 3: Sequential Load -- Full Testing Strategy with SQL Assertions and Deliverable

**Category:** Sequential procedure
**Tier:** 3 (complex)

**Input:**
> "Design a complete testing strategy for our data warehouse migration. I need SQL assertions for reconciliation, dbt tests for the new models, and a test report we can share with the client."

**Expected Skill Activated:** data-testing (deliverable mode)
**Expected Files Loaded:** SKILL.md → dbt-testing-strategy.md (Step 3) → sql-assertion-patterns.md (Step 3) → test-as-deliverable.md (Step 5)

**Observation Points:**
- "SQL assertions for reconciliation" requires sql-assertion-patterns.md
- "dbt tests for the new models" requires dbt-testing-strategy.md
- "Test report for client" triggers Deliverable mode and requires test-as-deliverable.md at Step 5
- References must be loaded sequentially, not simultaneously
- Peak load at any single point: SKILL.md (~1,800 tokens) + one reference (~1,400 tokens) is within 5,500 ceiling
- After generating dbt tests from dbt-testing-strategy.md, that file should be unloaded before loading sql-assertion-patterns.md
- After generating SQL assertions, sql-assertion-patterns.md should be unloaded before loading test-as-deliverable.md
- pipeline-validation.md should NOT be loaded unless the user asks about DuckDB validation or row hashing

**Grading:**
- **Pass:** Skill follows 3-reference sequential load pattern; generates dbt test YAML, SQL reconciliation assertions, and client test report in distinct steps; never holds more than one reference simultaneously
- **Partial:** Skill loads two references simultaneously (e.g., dbt-testing-strategy + sql-assertion-patterns at once) but produces correct output
- **Fail:** Skill loads all three references simultaneously; or skips the deliverable step despite "test report for client" being explicitly requested; or loads pipeline-validation.md when it was not requested

---

## Case 4: Conditional Deliverable -- Package Tests for Client Handoff

**Category:** Conditional deliverable
**Tier:** 2 (medium)

**Input:**
> "Package our test results into a client scorecard with coverage metrics."

**Expected Skill Activated:** data-testing (deliverable mode)
**Expected Files Loaded:** SKILL.md → test-as-deliverable.md (Step 5 only)

**Observation Points:**
- "Client scorecard" + "coverage metrics" triggers Deliverable mode (Step 5)
- test-as-deliverable.md should ONLY be loaded at Step 5 — not earlier in the procedure
- This tests that the conditional load rule is respected: test-as-deliverable is not pre-loaded at skill activation
- Previous testing steps (strategy, assertions, validation) are assumed already completed based on conversation context
- Loading dbt-testing-strategy.md or sql-assertion-patterns.md here would be redundant and wasteful

**Grading:**
- **Pass:** Skill loads test-as-deliverable.md only at Step 5; generates client scorecard with coverage metrics, pass/fail summary, and failure review lists; does NOT reload dbt-testing-strategy or sql-assertion-patterns
- **Partial:** Skill loads test-as-deliverable.md but also redundantly loads dbt-testing-strategy.md to regenerate test counts
- **Fail:** test-as-deliverable.md is never loaded; skill generates scorecard from memory without the standardized templates; or multiple references are loaded simultaneously

---

## Case 5: Pipeline Validation Target -- DuckDB Row Hash Comparison

**Category:** pipeline-validation target
**Tier:** 2 (medium)

**Input:**
> "I need to verify that re-running my pipeline produces identical output. How do I compare the two runs?"

**Expected Skill Activated:** data-testing
**Expected Files Loaded:** SKILL.md + pipeline-validation.md (Step 3)

**Observation Points:**
- "Re-running pipeline produces identical output" maps to idempotency validation — row hash comparison in pipeline-validation.md
- Only pipeline-validation.md should be loaded — not dbt-testing-strategy or sql-assertion-patterns
- "Compare the two runs" is the key signal for row hash comparison, not sum reconciliation (which is in sql-assertion-patterns)
- This tests that the skill distinguishes between pipeline idempotency (pipeline-validation) and data reconciliation (sql-assertion-patterns)

**Grading:**
- **Pass:** Skill loads pipeline-validation.md only; provides row hash comparison pattern using `md5(row_to_json(...))` and `EXCEPT` query; explains idempotency verification approach; unloads after answering
- **Partial:** Skill loads pipeline-validation.md but also loads sql-assertion-patterns.md for sum reconciliation
- **Fail:** Skill loads sql-assertion-patterns.md instead of pipeline-validation.md; or answers from SKILL.md without loading any reference (missing hash comparison SQL)
