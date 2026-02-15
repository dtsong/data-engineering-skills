# streaming-data-skill — Navigation Eval Cases

Navigation evals test how the agent traverses the skill file tree during execution.
They are distinct from trigger evals (activation) and output evals (result correctness).

---

## Case 1: SKILL.md-sufficient — Architecture Decision

**Category:** SKILL.md-sufficient

**Input:**
> "We need sub-second latency for fraud detection on payment events. Should we use batch processing or streaming?"

**Expected Navigation:**
1. Read `streaming-data-skill/SKILL.md`
2. Stop — the Architecture Decision Matrix section answers this directly

**Should Read:** `SKILL.md` only
**Should NOT Read:** Any reference file

**Observation Points:**
- Agent locates the Architecture Decision Matrix in SKILL.md
- Agent does not open any `references/` file
- Agent provides an architecture recommendation citing SKILL.md content

**Grading:**
- **Pass:** Agent answers from SKILL.md without loading references
- **Partial:** Agent reads SKILL.md and one reference but answer comes from SKILL.md
- **Fail:** Agent reads multiple references or answers without consulting SKILL.md

---

## Case 2: Targeted Reference — Kafka Producer Config

**Category:** Targeted reference

**Input:**
> "Configure a Kafka producer for maximum durability with idempotent writes. Show me the exact config properties."

**Expected Navigation:**
1. Read `streaming-data-skill/SKILL.md`
2. Follow link to `references/kafka-deep-dive.md`
3. Stop — Kafka producer configuration details are in the Kafka reference

**Should Read:** `SKILL.md` → `references/kafka-deep-dive.md`
**Should NOT Read:** `references/flink-spark-streaming.md`, `references/warehouse-streaming-ingestion.md`, `references/stream-testing-patterns.md`

**Observation Points:**
- Agent reads SKILL.md and identifies the kafka-deep-dive reference link
- Agent follows exactly one reference link
- Agent does not speculatively read other references

**Grading:**
- **Pass:** Agent reads SKILL.md then kafka-deep-dive.md only
- **Partial:** Agent reads SKILL.md, kafka-deep-dive.md, and one additional reference
- **Fail:** Agent reads 3+ references or skips kafka-deep-dive.md

---

## Case 3: Cross-reference Resistance — Windowing Pattern

**Category:** Cross-reference resistance

**Input:**
> "I need to compute moving averages over user click events. Which windowing pattern should I use — tumbling, sliding, or session?"

**Expected Navigation:**
1. Read `streaming-data-skill/SKILL.md`
2. Stop — the Windowing Patterns section covers this directly

**Should Read:** `SKILL.md` only
**Should NOT Read:** `references/flink-spark-streaming.md` (tempting but unnecessary for windowing pattern selection)

**Observation Points:**
- Agent locates Windowing Patterns in SKILL.md
- Agent resists following the link to `references/flink-spark-streaming.md`
- Agent provides a windowing recommendation from SKILL.md content

**Grading:**
- **Pass:** Agent answers from SKILL.md Windowing Patterns without loading flink-spark-streaming.md
- **Partial:** Agent reads SKILL.md then flink-spark-streaming.md but answer only uses SKILL.md content
- **Fail:** Agent loads flink-spark-streaming.md and multiple other references

---

## Case 4: Shared Reference — Regulated Streaming Security

**Category:** Shared reference

**Input:**
> "We're HIPAA-regulated. Can the AI agent deploy Flink streaming jobs to production, or does that require human approval?"

**Expected Navigation:**
1. Read `streaming-data-skill/SKILL.md`
2. Follow Security Posture link to `../shared-references/data-engineering/security-compliance-patterns.md`
3. Stop — HIPAA deployment restrictions are in the shared security reference

**Should Read:** `SKILL.md` → `../shared-references/data-engineering/security-compliance-patterns.md`
**Should NOT Read:** `references/kafka-deep-dive.md`, `references/flink-spark-streaming.md`, or other skill-local references

**Observation Points:**
- Agent reads SKILL.md and identifies the security-compliance-patterns link
- Agent navigates to the shared reference (outside the skill directory)
- Agent does not confuse shared references with skill-local references

**Grading:**
- **Pass:** Agent reads SKILL.md then shared security reference only
- **Partial:** Agent reads SKILL.md, shared security reference, and one skill-local reference
- **Fail:** Agent skips the shared security reference or reads 3+ files total

---

## Case 5: Deep Reference — Snowpipe Streaming

**Category:** Deep reference

**Input:**
> "I need to stream JSON events into Snowflake with sub-minute latency. Should I use Snowpipe or Snowpipe Streaming? Show me the tradeoffs and setup."

**Expected Navigation:**
1. Read `streaming-data-skill/SKILL.md`
2. Follow Reference Files link to `references/warehouse-streaming-ingestion.md`
3. Read deeply into the warehouse streaming reference for Snowpipe patterns

**Should Read:** `SKILL.md` → `references/warehouse-streaming-ingestion.md`
**Should NOT Read:** `references/kafka-deep-dive.md`, `references/flink-spark-streaming.md`, `references/stream-testing-patterns.md`

**Observation Points:**
- Agent reads SKILL.md and follows the warehouse-streaming-ingestion reference link
- Agent reads warehouse-streaming-ingestion.md thoroughly (not just the first section)
- Agent provides Snowpipe vs Snowpipe Streaming comparison from the reference

**Grading:**
- **Pass:** Agent reads SKILL.md then warehouse-streaming-ingestion.md deeply, answer includes specific Snowpipe tradeoffs
- **Partial:** Agent reads correct files but answer only uses surface-level information
- **Fail:** Agent reads wrong reference or reads 3+ files
