# dbt-transforms — Navigation Eval Cases

Navigation evals test how the agent traverses the skill file tree during execution.
They are distinct from trigger evals (activation) and output evals (result correctness).

---

## Case 1: SKILL.md-sufficient — Materialization Decision

**Category:** SKILL.md-sufficient

**Input:**
> "I have a 50-million-row staging model that refreshes daily. What materialization should I use?"

**Expected Navigation:**
1. Read `dbt-transforms/SKILL.md`
2. Stop — the Materialization Decision Matrix section answers this directly

**Should Read:** `SKILL.md` only
**Should NOT Read:** Any reference file

**Observation Points:**
- Agent locates the Materialization Decision Matrix in SKILL.md
- Agent does not open any `references/` file
- Agent provides a materialization recommendation citing SKILL.md content

**Grading:**
- **Pass:** Agent answers from SKILL.md without loading references
- **Partial:** Agent reads SKILL.md and one reference but answer comes from SKILL.md
- **Fail:** Agent reads multiple references or answers without consulting SKILL.md

---

## Case 2: Targeted Reference — Microbatch Incremental

**Category:** Targeted reference

**Input:**
> "I need to implement microbatch incremental in dbt 1.9+ with a 3-day lookback window. Show me the pattern."

**Expected Navigation:**
1. Read `dbt-transforms/SKILL.md`
2. Follow link to `references/incremental-performance.md`
3. Stop — microbatch details are in the incremental performance reference

**Should Read:** `SKILL.md` → `references/incremental-performance.md`
**Should NOT Read:** `references/testing-quality.md`, `references/ci-cd-deployment.md`, `references/jinja-macros-packages.md`, `references/data-quality-observability.md`, `references/semantic-layer-governance.md`

**Observation Points:**
- Agent reads SKILL.md and identifies the incremental-performance reference link
- Agent follows exactly one reference link
- Agent does not speculatively read other references

**Grading:**
- **Pass:** Agent reads SKILL.md then incremental-performance.md only
- **Partial:** Agent reads SKILL.md, incremental-performance.md, and one additional reference
- **Fail:** Agent reads 3+ references or skips incremental-performance.md

---

## Case 3: Cross-reference Resistance — Staging Tests

**Category:** Cross-reference resistance

**Input:**
> "What tests should I add to my staging models?"

**Expected Navigation:**
1. Read `dbt-transforms/SKILL.md`
2. Stop — the Basic Testing Overview section covers staging model testing

**Should Read:** `SKILL.md` only
**Should NOT Read:** `references/testing-quality.md` (tempting but unnecessary for basic staging test guidance)

**Observation Points:**
- Agent locates Basic Testing Overview in SKILL.md
- Agent resists following the link to `references/testing-quality.md`
- Agent provides basic testing guidance (not-null, unique, accepted_values) from SKILL.md

**Grading:**
- **Pass:** Agent answers from SKILL.md Basic Testing Overview without loading testing-quality.md
- **Partial:** Agent reads SKILL.md then testing-quality.md but answer only uses SKILL.md content
- **Fail:** Agent loads testing-quality.md and multiple other references

---

## Case 4: Shared Reference — Production Credentials

**Category:** Shared reference

**Input:**
> "How should I configure profiles.yml for Snowflake production with proper credential security?"

**Expected Navigation:**
1. Read `dbt-transforms/SKILL.md`
2. Follow Security Posture link to `../shared-references/data-engineering/security-compliance-patterns.md`
3. Stop — credential management is in the shared security reference

**Should Read:** `SKILL.md` → `../shared-references/data-engineering/security-compliance-patterns.md`
**Should NOT Read:** `references/ci-cd-deployment.md`, `references/incremental-performance.md`, or other skill-local references

**Observation Points:**
- Agent reads SKILL.md and identifies the security-compliance-patterns link
- Agent navigates to the shared reference (outside the skill directory)
- Agent does not confuse shared references with skill-local references

**Grading:**
- **Pass:** Agent reads SKILL.md then shared security reference only
- **Partial:** Agent reads SKILL.md, shared security reference, and one skill-local reference
- **Fail:** Agent skips the shared security reference or reads 3+ files total

---

## Case 5: Deep Reference — Slim CI

**Category:** Deep reference

**Input:**
> "We have 500+ models and CI takes 30 minutes. How do I implement slim CI with state deferral?"

**Expected Navigation:**
1. Read `dbt-transforms/SKILL.md`
2. Follow Detailed Guides link to `references/ci-cd-deployment.md`
3. Read deeply into the CI/CD reference for slim CI patterns

**Should Read:** `SKILL.md` → `references/ci-cd-deployment.md`
**Should NOT Read:** `references/incremental-performance.md`, `references/testing-quality.md`, `references/jinja-macros-packages.md`, `references/data-quality-observability.md`, `references/semantic-layer-governance.md`

**Observation Points:**
- Agent reads SKILL.md and follows the CI/CD reference link
- Agent reads ci-cd-deployment.md thoroughly (not just the first section)
- Agent provides slim CI details (state:modified, deferral) from the reference

**Grading:**
- **Pass:** Agent reads SKILL.md then ci-cd-deployment.md deeply, answer includes specific slim CI patterns
- **Partial:** Agent reads correct files but answer only uses surface-level information
- **Fail:** Agent reads wrong reference or reads 3+ files
