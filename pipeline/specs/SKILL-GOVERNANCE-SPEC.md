# Skill Governance Specification v1.1

## Overview

This specification defines the standards, patterns, and enforcement mechanisms
for authoring, validating, and deploying AI agent skills. It applies to skills
targeting Claude Code, OpenAI Codex, and any SKILL.md-compatible agent platform.

This document is the **single source of truth**. All pipeline scripts, hooks,
and tooling derive their rules from this spec.

### Changes from v1.0

- Per-file token budgets reclassified from hard limits to **guideline targets**
- Suite context load ceiling remains the **only hard budget limit**
- Pre-commit budget checks changed from blocking to **warning**
- Added guidance on when to exceed budgets and how to document it
- Rebalanced enforcement to prioritize structural integrity over compression
- Added quality-over-compression principle to writing rules

---

## 1. Core Principles

### 1.1 The Optimization Hierarchy

When authoring skills, these priorities apply in order. Higher priorities
override lower ones when they conflict.

1. **Output quality** — The skill produces correct, useful results
2. **Structural integrity** — Progressive loading, isolation, and handoff contracts
3. **Token efficiency** — Minimize instruction and execution token cost
4. **Compression** — Keep individual files compact

Most of the real token savings come from #2 (not loading multiple specialists)
and #3 (smart tool usage, targeted reading, structured handoffs). Aggressive
compression (#4) delivers diminishing returns and can degrade #1 if it removes
context that helps the agent make good decisions.

### 1.2 Budget Philosophy

**Guideline targets** set a reasonable default size for each file type. They
prevent unbounded growth and encourage structural discipline (extracting
checklists to reference files, moving logic to scripts). Exceeding a guideline
is acceptable when the extra content demonstrably improves agent performance.

**The context load ceiling** is the one hard limit. It caps the maximum tokens
of skill instructions present in the agent's context window at any point during
execution. This is the constraint that directly protects reasoning capacity.

**The distinction matters.** A specialist skill at 2,200 words that includes
edge case reasoning and produces better results is preferable to one squeezed
to 1,500 words that loses critical context. But three such skills loaded
simultaneously at 6,600 words would crowd out code and reasoning — which is
why the ceiling exists.

---

## 2. Skill Architecture

### 2.1 Progressive Loading Model

```
Layer 1: Coordinator          Always in context        Target: ≤800 tokens
          ↓ routes to
Layer 2: Specialist Skill     Loaded on demand          Target: ≤2,000 tokens
          ↓ references
Layer 3: Reference Files      Loaded within a step     Target: ≤1,500 tokens

Hard ceiling on simultaneous load: ≤5,500 tokens
```

**Rules:**
- Only one Layer 2 skill is loaded at a time
- Layer 3 files are loaded conditionally within a procedure step
- Eval cases and templates are never loaded during execution

### 2.2 Skill Types and Budget Targets

| Type | Description | Target | Warn At | Hard Limit |
|------|-------------|--------|---------|------------|
| **Coordinator** | Routes to specialists. Has a `skills/` subdirectory. | ≤800 tokens (~600 words) | >800 tokens | None (ceiling applies) |
| **Specialist** | Full procedure for one task type. Inside `skills/`. | ≤2,000 tokens (~1,500 words) | >2,000 tokens | None (ceiling applies) |
| **Standalone** | Single-purpose skill, no suite. | ≤2,000 tokens (~1,500 words) | >2,000 tokens | None (ceiling applies) |
| **Reference** | Checklist, lookup table, or pattern library. | ≤1,500 tokens (~1,100 words) | >1,500 tokens | None (ceiling applies) |
| **Suite ceiling** | Coordinator + largest specialist + largest reference | — | — | **≤5,500 tokens** |

Token estimation: `tokens ≈ words × 1.33`

### 2.3 When to Exceed a Target

Exceeding a per-file target is acceptable when:

- The extra content is **contextual reasoning** that helps the agent understand
  *why* a step matters, not just *what* to do — and removing it degrades output quality
- The content is **edge case handling** that prevents common failure modes you've
  observed in eval runs
- The content is **examples of good vs bad output** that calibrate the agent's judgment
- The file has been through eval iterations and the current length reflects what's
  needed for consistent performance

When exceeding a target, document it in `pipeline/config/budgets.json`:

```json
{
  "overrides": {
    "skills/frontend-qa/skills/ui-bug-investigator": {
      "specialist_max_words": 1800,
      "reason": "Diagnostic branching logic + edge case notes for hydration mismatches. Eval pass rate dropped from 85% to 60% when compressed to 1500 words."
    }
  }
}
```

### 2.4 Directory Structures

**Skill Suite:**
```
suite-name/
├── SKILL.md                        # Coordinator (Layer 1)
├── skills/
│   └── specialist-name/
│       ├── SKILL.md                # Specialist (Layer 2)
│       └── references/             # Reference files (Layer 3)
│           └── checklist.md
├── scripts/                        # Executable automation
├── templates/                      # Output templates
└── eval-cases/                     # Never loaded during execution
    ├── evals.json
    └── cases/
```

**Standalone Skill:**
```
skill-name/
├── SKILL.md                        # Combined (Layer 1+2)
├── references/
├── scripts/
└── eval-cases/
```

### 2.5 Isolation Rules (Hard — Always Enforced)

- Specialist skills must NOT reference other specialists' SKILL.md or reference files
- Inter-skill data passes through the coordinator's handoff protocol as structured data
- Eval cases must NOT reside inside skill directories that could be auto-loaded
- Scripts are executed, not read into context

---

## 3. File Format Standards

### 3.1 SKILL.md Frontmatter

Required fields:
```yaml
---
name: skill-name          # Kebab-case identifier
description: >            # Trigger description — when to use, what it does
  Comprehensive description with specific trigger phrases.
  Be slightly pushy about when to use this skill.
---
```

Optional fields:
```yaml
model_tier: mechanical|analytical|reasoning
version: 1.0.0
```

No other frontmatter fields are permitted.

### 3.2 Coordinator SKILL.md Structure

Must contain exactly five elements, nothing else:

1. **Purpose** — One sentence
2. **Classification logic** — Decision tree or conditional block
3. **Skill registry** — Table: name, path, one-line purpose, model tier
4. **Load directive** — "Read ONLY the relevant specialist SKILL.md"
5. **Handoff protocol** — What structured data passes between skills

### 3.3 Specialist SKILL.md Structure

```markdown
---
name: ...
description: ...
---

# Skill Name

## Inputs
[3-5 lines. Required vs optional marked.]

## Procedure
[Numbered steps. Imperative by default. Contextual reasoning where it
improves agent decisions. Reference file loads as explicit steps.]

## Output Format
[One compact example. Variations annotated inline.]

## Handoff
[2-3 lines. Structured data only, no raw files.]

## References
[Table: path, load condition, content summary.]
```

### 3.4 Reference File Structure

- No preamble, meta-instructions, or conclusions
- One item per line
- Organized under short category headers
- Table of contents for files >100 lines

---

## 4. Writing Rules

### 4.1 The Quality-Over-Compression Principle

The goal of writing rules is **information density**, not minimum word count.
Every sentence should earn its place, but earning a place means either:

- Instructing a specific action (imperative step)
- Providing context that improves the agent's decision quality
- Preventing a known failure mode with a targeted note

The test is not "can this be shorter?" but "if I remove this, does the agent
perform worse?" When you've observed through evals that a piece of context
improves results, it belongs in the skill regardless of word count impact.

### 4.2 Procedure Sections

- **Default to imperative sentences.** "Read the file. Check for `use client`. Record the result."
- **Add contextual reasoning when it affects decisions.** "Resolve barrel exports
  to source files — barrel exports via index.ts mask the real file path, which
  breaks downstream analysis if you stop at the re-export layer." The second half
  of this sentence costs 25 words but prevents a common failure mode.
- **Inline conditionals for branching.** "If X → do A. Otherwise → do B."
- **One example per output format.** No redundant schema descriptions alongside examples.
- **Notes for edge cases.** "Note: components using `usePathname` are always client
  components even if their file lacks `use client` — the hook forces the boundary."

### 4.3 What to Cut vs What to Keep

**Always cut:**
| Pattern | Why It's Wasteful |
|---------|-------------------|
| "It is important to..." | Preamble — just state the action |
| "Basically / essentially / fundamentally" | Filler — adds zero information |
| "In order to" | Verbose — "to" works identically |
| "Keep in mind that..." / "Please note that..." | Meta-instruction — convert to inline Note: |
| "Let's / we can / we should" | Conversational — use imperative |
| "Feel free to" / "Don't hesitate to" | Casual — remove entirely |
| Schema described in prose AND shown as example | Duplication — keep only the example |

**Keep when it improves agent decisions:**
| Pattern | Why It Earns Its Place |
|---------|------------------------|
| "X because Y" in a procedure step | Agent understands consequences of skipping |
| Edge case notes ("Note: watch for Z") | Prevents known failure modes |
| Short good-vs-bad examples | Calibrates agent judgment on ambiguous cases |
| "Stop here if X — this is the root cause" | Early termination saves tokens downstream |
| Fallback instructions ("If A fails, try B") | Prevents dead-end states |

### 4.4 Model Tier Annotations

| Tier | Use Case | Examples |
|------|----------|---------|
| `mechanical` | Deterministic tracing, file ops, pattern matching | File scanning, format conversion |
| `analytical` | Classification, multi-factor decisions | Bug triage, component mapping |
| `reasoning` | Complex debugging, architectural decisions | Root cause analysis, design review |

---

## 5. Engineering Patterns

Patterns to embed in skills for quality, efficiency, and tool intelligence.
These patterns typically deliver more token savings during execution than
compressing the skill instructions themselves.

### 5.1 Quality Patterns

| ID | Pattern | When to Use |
|----|---------|-------------|
| Q1 | **Pre-flight context gathering** — Read project config before acting | Code generation, modification skills |
| Q2 | **Convention mirroring** — Read exemplar files, match style | Code generation skills |
| Q3 | **Output contracts** — Checkable conditions the output must satisfy | Skills whose output feeds other skills |
| Q4 | **Self-verification loop** — Check own work before presenting | All skills producing actionable output |
| Q5 | **Confidence signaling** — Rate findings HIGH/MEDIUM/LOW | Diagnostic, analytical skills |
| Q6 | **Negative space documentation** — Report what was checked and ruled out | Diagnostic, audit, review skills |

### 5.2 Efficiency Patterns (High Token Impact)

| ID | Pattern | Typical Savings |
|----|---------|-----------------|
| E1 | **Targeted file reading** — Read sections, not whole files | 500-2,000 tokens/file |
| E2 | **Progressive detail** — Shallow scan, then deep dive on relevant items | 1,000-5,000 tokens/run |
| E3 | **Output token discipline** — Diffs not files, no problem restatement | 500-3,000 tokens/response |
| E4 | **Structured handoffs** — JSON between skills, not prose | 200-800 tokens/handoff |
| E5 | **Early termination** — Exit when the answer is clear | 1,000-10,000 tokens/run |
| E6 | **Cache-friendly ordering** — Stable context prefix for KV-cache hits | Latency reduction |

### 5.3 Tool Intelligence Patterns

| ID | Pattern | Typical Savings |
|----|---------|-----------------|
| T1 | **Tool selection heuristics** — Right tool for each job | 100-500 tokens/operation |
| T2 | **Batched tool calls** — One call, many operations | 200-1,000 tokens/batch |
| T3 | **Pre-flight validation** — Cheap checks before expensive operations | 1,000-5,000 tokens on failed runs |
| T4 | **Fallback chains** — Plan B, C, D for tool failures | Eliminates dead-end user round-trips |
| T5 | **Output parsing discipline** — Filter tool output at source | 500-5,000 tokens/command |
| T6 | **Capability detection** — Detect available tools before planning | Prevents wasted procedure branches |
| T7 | **Incremental verification** — Verify per change, not at end | Cheaper failure isolation |

### 5.4 Composition Matrix

| Skill Type | Must Have | Should Have | Consider |
|------------|-----------|-------------|----------|
| Code Generation | Q1, Q2, Q3, T1 | Q4, E1, E3 | E6 |
| Diagnosis | E2, E5, Q5, Q6 | T2, T4, T5 | E3 |
| Fix & Verify | T3, T7, T4, T6 | Q4, E3 | T2 |
| Analysis/Mapping | E1, T2, T1, Q3 | E2, E4 | E6 |
| Test Generation | Q1, Q2, T6, Q4 | Q3, T4 | E3 |
| Coordinator | E4, E5, T6 | E3 | — |

**Key insight**: Patterns E1-E5 and T1-T5 typically save more tokens during
skill execution than any amount of SKILL.md compression. Prioritize embedding
these patterns over squeezing word count.

---

## 6. Refactoring Patterns

When a file significantly exceeds its target, apply in order:

1. **Extract checklists** — Move >10 items to `references/`. Savings: 300-800 tokens.
2. **Cut filler** — Remove patterns from the "Always cut" table (§4.3). Savings: 200-500 tokens.
3. **Deduplicate output specs** — Keep only the example. Savings: 150-400 tokens.
4. **Script mechanical work** — Move deterministic logic to scripts. Variable savings.
5. **Decompose** — Split into two specialists with coordinator. Last resort.

**Do NOT cut:**
- Contextual reasoning that prevents known failure modes
- Edge case notes validated by eval results
- Examples that calibrate agent judgment
- Fallback instructions that prevent dead-end states

When refactoring, re-run eval cases to confirm the refactored version performs
at least as well as the original. If eval pass rate drops, the cut removed
necessary content — restore it and document the override.

---

## 7. Eval Case Standards

### 7.1 Case Structure

```markdown
# Eval Case: [Name]

## Metadata
- Case ID, Tier (1-3), Route/Input, Estimated components

## Input
[JSON block with the skill's input parameters]

## Expected Output
[Concrete, checkable expectations — tables, trees, specific values]

## Grading Rubric

### Must Pass (eval fails if wrong)
- [ ] [Specific, verifiable assertion]

### Should Pass (partial credit)
- [ ] [Secondary assertion]

### Bonus
- [ ] [Nice-to-have assertion]
```

### 7.2 Case Selection

- 5-7 cases per skill
- Tiered: 1-2 simple, 2-3 medium, 1-2 complex
- Must collectively cover all key scenarios for the skill's domain
- Include a "Raw Trace Log" section for traceability

### 7.3 Using Evals to Justify Budgets

Eval results are the arbiter of budget decisions. When a skill exceeds its
target, the process is:

1. Run evals at the current (over-target) length → record pass rate
2. Refactor to target length using the patterns in §6
3. Run evals again → compare pass rate
4. If pass rate holds → keep the shorter version
5. If pass rate drops → restore the longer version, document the override with the eval data

This makes budget decisions empirical rather than arbitrary.

---

## 8. Enforcement Tiers

### 8.1 Tier Classification

Every rule in this spec belongs to one of three enforcement tiers:

| Tier | Behavior | Purpose |
|------|----------|---------|
| **Hard** | Blocks commit and merge | Prevents structural breakage |
| **Warn** | Visible warning, does not block | Encourages best practices |
| **Info** | Reported in analysis, no warning | Awareness and tracking |

### 8.2 Rule-to-Tier Mapping

| Rule | Tier | Rationale |
|------|------|-----------|
| Frontmatter has required fields | **Hard** | Skill won't trigger without name + description |
| Referenced files exist on disk | **Hard** | Agent will fail at runtime if reference is missing |
| No cross-specialist references | **Hard** | Violates isolation, causes instruction blending |
| Suite context load ≤ ceiling | **Hard** | Directly protects reasoning capacity |
| Eval cases outside skill directories | **Hard** | Prevents accidental context pollution |
| Scripts are executable | **Hard** | Agent will fail at runtime otherwise |
| Per-file token budget exceeded | **Warn** | Guideline — may be justified by quality needs |
| Prose patterns in procedure sections | **Warn** | Suggests tightening, but context may be valuable |
| Near budget (>90% of target) | **Info** | Awareness that headroom is shrinking |
| Unknown frontmatter fields | **Info** | Might indicate platform-specific additions |
| Commit message format | **Hard** | Enables changelog generation and filtered diffs |

### 8.3 Pipeline Requirements

**Pre-Commit Hooks (Local, <2s):**

| Hook | Tier | What It Checks |
|------|------|----------------|
| `skill-frontmatter` | Hard | YAML structure, required fields |
| `skill-references` | Hard | Referenced files exist on disk |
| `skill-isolation` | Hard | No cross-specialist references |
| `skill-context-load` | Hard | Suite worst-case ≤ ceiling |
| `skill-token-budget` | Warn | Word/token counts vs targets |
| `skill-prose-check` | Warn | Explanatory prose in procedures |
| `skill-commit-msg` | Hard | Conventional commit format |

**CI Stage 1: Lint & Validate (Every Push, <30s)**
- Same checks as pre-commit, run as safety net for `--no-verify` bypasses
- Generate budget report as step summary on PRs

**CI Stage 2: Static Analysis (PRs, <2min)**
- Pattern compliance analysis
- Portability check (Claude Code + Codex)
- Context load report with per-suite breakdown
- Post analysis as PR comment

**CI Stage 3: Eval Execution (Merge / Manual, <30min)**
- Run eval cases against skills
- Grade against rubrics
- Detect regressions against stored baselines
- Upload results as artifacts

**CI Stage 4: Publish (Release Tags)**
- Package changed skills
- Create release
- Sync to target locations

### 8.4 Commit Message Convention

```
skill(name): description          — new skill or major change
skill-fix(name): description      — bug fix
skill-ref(name): description      — refactor (no behavior change)
skill-eval(name): description     — eval case changes
skill-docs(name): description     — documentation only
chore(pipeline): description      — pipeline/tooling changes
```

---

## 9. Cross-Platform Compatibility

### 9.1 Shared Elements (No Adaptation Needed)

- SKILL.md body content (procedures, checklists, decision trees)
- Reference files
- Scripts (bash/python)
- Directory structure and organization
- Eval cases and grading criteria
- Token budgets and progressive loading architecture

### 9.2 Platform-Specific Adaptations

| Element | Claude Code | Codex |
|---------|-------------|-------|
| Project instructions | `CLAUDE.md` | `AGENTS.md` |
| Skill metadata UI | Frontmatter only | `agents/openai.yaml` |
| Explicit invocation | Via description trigger | `$skill-name` or `/skills` |
| Implicit invocation control | Always on | `allow_implicit_invocation` in yaml |
| Model routing | Haiku / Sonnet / Opus | Codex-Spark / GPT-5.x-Codex |

### 9.3 Portability Rules

- Use generic language ("project instructions file") or note both filenames
- Avoid platform-specific tool syntax in SKILL.md bodies
- Use `python3` not `python` in scripts
- Keep `agents/openai.yaml` as an optional addition, not a requirement

---

## Appendix A: Quick Reference Card

```
┌──────────────────────────────────────────────────────────┐
│            SKILL GOVERNANCE v1.1 QUICK REFERENCE         │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  PRIORITY ORDER                                           │
│  1. Output quality  2. Structure  3. Efficiency  4. Size  │
│                                                           │
│  BUDGET TARGETS (guidelines — warn, don't block)          │
│  Coordinator ................. ≤800 tokens (~600 words)   │
│  Specialist / Standalone ..... ≤2,000 tokens (~1,500 w)   │
│  Reference ................... ≤1,500 tokens (~1,100 w)   │
│                                                           │
│  HARD LIMIT (the only one that blocks)                    │
│  Suite context load ceiling .. ≤5,500 tokens              │
│                                                           │
│  ALWAYS ENFORCED (structural integrity)                   │
│  ✓ Valid frontmatter with name + description              │
│  ✓ All referenced files exist on disk                     │
│  ✓ No cross-specialist references                         │
│  ✓ Eval cases outside skill directories                   │
│  ✓ Suite context load under ceiling                       │
│                                                           │
│  WRITING GUIDANCE                                         │
│  ✓ Imperative steps as default                            │
│  ✓ Add "because X" when it prevents failures              │
│  ✓ Edge case notes when validated by evals                │
│  ✗ Cut filler: "basically", "in order to", "it is        │
│    important to"                                          │
│  ✗ Don't cut: reasoning that prevents known failures      │
│                                                           │
│  BUDGET DISPUTES                                          │
│  Run evals at both lengths. Eval pass rate decides.       │
│  Document overrides with evidence in budgets.json.        │
│                                                           │
│  ENFORCEMENT TIERS                                        │
│  Hard = blocks commit  |  Warn = visible warning          │
│  Info = reported only  |  See §8.2 for full mapping       │
│                                                           │
└──────────────────────────────────────────────────────────┘
```

---

## Appendix B: Budget Configuration Schema

```json
{
  "coordinator_max_words": 600,
  "coordinator_max_tokens": 800,
  "specialist_max_words": 1500,
  "specialist_max_tokens": 2000,
  "reference_max_words": 1100,
  "reference_max_tokens": 1500,
  "standalone_max_words": 1500,
  "standalone_max_tokens": 2000,
  "max_simultaneous_tokens": 5500,
  "overrides": {
    "skills/path/to/specific-skill": {
      "specialist_max_words": 1800,
      "reason": "Documented justification with eval data"
    }
  }
}
```
