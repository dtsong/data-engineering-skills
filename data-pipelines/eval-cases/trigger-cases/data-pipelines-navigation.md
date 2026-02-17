# data-pipelines — Navigation Eval Cases

Navigation evals test how the agent traverses the skill file tree during execution.
They are distinct from trigger evals (activation) and output evals (result correctness).

---

## Case 1: SKILL.md-sufficient — Orchestrator Selection

**Category:** SKILL.md-sufficient

**Input:**
> "We're building a greenfield data platform with dbt and DLT. Should we use Dagster or Airflow as our orchestrator?"

**Expected Navigation:**
1. Read `data-pipelines/SKILL.md`
2. Stop — the Orchestrator Decision Matrix section answers this directly

**Should Read:** `SKILL.md` only
**Should NOT Read:** Any reference file

**Observation Points:**
- Agent locates the Orchestrator Decision Matrix in SKILL.md
- Agent does not open any `references/` file
- Agent provides an orchestrator recommendation citing SKILL.md content

**Grading:**
- **Pass:** Agent answers from SKILL.md without loading references
- **Partial:** Agent reads SKILL.md and one reference but answer comes from SKILL.md
- **Fail:** Agent reads multiple references or answers without consulting SKILL.md

---

## Case 2: Targeted Reference — dagster-dbt Integration

**Category:** Targeted reference

**Input:**
> "How do I integrate my dbt models as Dagster assets using dagster-dbt? Show me the setup pattern."

**Expected Navigation:**
1. Read `data-pipelines/SKILL.md`
2. Follow link to `references/dagster-integrations.md`
3. Stop — dagster-dbt integration patterns are in the integrations reference

**Should Read:** `SKILL.md` → `references/dagster-integrations.md`
**Should NOT Read:** `references/dagster-patterns.md`, `references/airflow-patterns.md`, `references/embedded-orchestration.md`

**Observation Points:**
- Agent reads SKILL.md and identifies the dagster-integrations reference link
- Agent follows exactly one reference link (integrations, not patterns)
- Agent does not speculatively read dagster-patterns.md

**Grading:**
- **Pass:** Agent reads SKILL.md then dagster-integrations.md only
- **Partial:** Agent reads SKILL.md, dagster-integrations.md, and one additional reference
- **Fail:** Agent reads 3+ references or reads dagster-patterns.md instead of dagster-integrations.md

---

## Case 3: Cross-reference Resistance — Retry Logic

**Category:** Cross-reference resistance

**Input:**
> "How do I add exponential backoff retry to a Dagster asset?"

**Expected Navigation:**
1. Read `data-pipelines/SKILL.md`
2. Stop — the Common Patterns > Retry Strategy section covers this directly

**Should Read:** `SKILL.md` only
**Should NOT Read:** `references/dagster-patterns.md` (tempting but unnecessary for basic retry configuration)

**Observation Points:**
- Agent locates Common Patterns > Retry Strategy in SKILL.md
- Agent resists following the link to `references/dagster-patterns.md`
- Agent provides retry configuration from SKILL.md content

**Grading:**
- **Pass:** Agent answers from SKILL.md Retry Strategy without loading dagster-patterns.md
- **Partial:** Agent reads SKILL.md then dagster-patterns.md but answer only uses SKILL.md content
- **Fail:** Agent loads dagster-patterns.md and multiple other references

---

## Case 4: Shared Reference — Production Credentials

**Category:** Shared reference

**Input:**
> "How should I configure Dagster EnvVar resources for warehouse credentials in production? What's the secure pattern?"

**Expected Navigation:**
1. Read `data-pipelines/SKILL.md`
2. Follow Security Posture link to `../shared-references/data-engineering/security-compliance-patterns.md`
3. Stop — credential management patterns are in the shared security reference

**Should Read:** `SKILL.md` → `../shared-references/data-engineering/security-compliance-patterns.md`
**Should NOT Read:** `references/dagster-patterns.md`, `references/dagster-integrations.md`, or other skill-local references

**Observation Points:**
- Agent reads SKILL.md and identifies the security-compliance-patterns link
- Agent navigates to the shared reference (outside the skill directory)
- Agent does not confuse shared references with skill-local references

**Grading:**
- **Pass:** Agent reads SKILL.md then shared security reference only
- **Partial:** Agent reads SKILL.md, shared security reference, and one skill-local reference
- **Fail:** Agent skips the shared security reference or reads 3+ files total

---

## Case 5: Deep Reference — Airflow Dynamic Tasks

**Category:** Deep reference

**Input:**
> "We process data for 50 customers. I need parallel per-customer processing in Airflow 2.5+ using dynamic task mapping. Show me the pattern."

**Expected Navigation:**
1. Read `data-pipelines/SKILL.md`
2. Follow Reference Files link to `references/airflow-patterns.md`
3. Read deeply into the Airflow reference for dynamic task mapping patterns

**Should Read:** `SKILL.md` → `references/airflow-patterns.md`
**Should NOT Read:** `references/dagster-patterns.md`, `references/dagster-integrations.md`, `references/embedded-orchestration.md`

**Observation Points:**
- Agent reads SKILL.md and follows the airflow-patterns reference link
- Agent reads airflow-patterns.md thoroughly (not just the first section)
- Agent provides dynamic task mapping patterns from the reference

**Grading:**
- **Pass:** Agent reads SKILL.md then airflow-patterns.md deeply, answer includes specific dynamic task mapping code
- **Partial:** Agent reads correct files but answer only uses surface-level information
- **Fail:** Agent reads wrong reference (Dagster instead of Airflow) or reads 3+ files
