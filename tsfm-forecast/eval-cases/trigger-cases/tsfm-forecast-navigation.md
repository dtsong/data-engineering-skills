# tsfm-forecast -- Navigation Eval Cases

Navigation evals test which reference files get loaded during a conversation. Correct navigation means the right file is loaded at the right time — and no unnecessary files are pre-loaded. Distinct from trigger evals (activation) and output evals (result quality).

---

## Case 1: SKILL.md Sufficient -- Quick Model Selection

**Category:** SKILL.md-sufficient
**Tier:** 1 (simple)

**Input:**
> "I have daily demand data with prediction intervals needed. Which TSFM model should I use?"

**Expected Skill Activated:** tsfm-forecast
**Expected Files Loaded:** SKILL.md only

**Observation Points:**
- "Prediction intervals needed" + "daily" maps directly to the Quick Reference table in SKILL.md
- Chronos-Bolt-Small is the clear answer from the Quick Reference (probabilistic output)
- No edge case requires the full model-registry detail (hardware requirements, installation, limitations)
- Loading model-registry.md here would violate the "one reference at a time" rule without justification

**Grading:**
- **Pass:** Skill answers from SKILL.md Quick Reference table only; recommends Chronos-Bolt-Small; does NOT load model-registry.md
- **Partial:** Skill answers correctly but preemptively loads model-registry.md to show hardware requirements
- **Fail:** Skill loads model-registry.md to answer a question already covered by the Quick Reference table; or provides wrong model recommendation

---

## Case 2: model-registry Target -- Hardware Requirements Question

**Category:** model-registry target
**Tier:** 2 (medium)

**Input:**
> "What GPU VRAM does MOIRAI 2.0 Large need, and how do I install it?"

**Expected Skill Activated:** tsfm-forecast
**Expected Files Loaded:** SKILL.md + model-registry.md (Step 2)

**Observation Points:**
- "GPU VRAM" and "install" are not in SKILL.md; they require model-registry.md
- Only model-registry.md should be loaded — not data-prep-patterns or inference-templates
- Loading inference-templates here would be premature and violate the context ceiling rule
- This tests single-reference precision: exactly one reference loaded, correctly targeted

**Grading:**
- **Pass:** Skill loads model-registry.md only; provides MOIRAI 2.0 Large VRAM requirements (8 GB min / 16 GB recommended) and `pip install uni2ts` command; unloads after answering
- **Partial:** Skill loads model-registry.md but also preemptively loads inference-templates.md
- **Fail:** Skill answers from SKILL.md without loading model-registry.md (incorrect VRAM values); or loads multiple references simultaneously

---

## Case 3: Sequential Load -- Full Pipeline with Evaluation

**Category:** Sequential procedure
**Tier:** 3 (complex)

**Input:**
> "Generate a complete Chronos forecasting pipeline for weekly sales data, including backtesting against seasonal naive."

**Expected Skill Activated:** tsfm-forecast (eval/comparison mode)
**Expected Files Loaded:** SKILL.md → data-prep-patterns.md (Step 3) → inference-templates.md (Step 4) → evaluation-metrics.md (Step 5)

**Observation Points:**
- "Including backtesting against seasonal naive" activates eval/comparison mode (Steps 3–5)
- References must be loaded sequentially, not simultaneously
- Peak load at any single point: SKILL.md (~1,600 tokens) + one reference (~1,300 tokens) ≤ 5,500 ceiling ✓
- After generating data-prep code from data-prep-patterns.md, that file should be unloaded before loading inference-templates.md
- After generating inference code, inference-templates.md should be unloaded before loading evaluation-metrics.md

**Grading:**
- **Pass:** Skill follows 3-reference sequential load pattern; generates DuckDB prep SQL, Chronos inference code, MASE/SMAPE evaluation code in distinct steps; never holds more than one reference simultaneously
- **Partial:** Skill loads two references simultaneously (e.g., data-prep-patterns + inference-templates at once) but produces correct code
- **Fail:** Skill loads all three references simultaneously; or skips the evaluation step despite "backtesting" being explicitly requested; or loads deliverable-templates.md when report mode was not requested

---

## Case 4: Conditional Deliverable -- Client Report Request

**Category:** Conditional deliverable
**Tier:** 2 (medium)

**Input:**
> "Generate a client-ready forecast report for this TimesFM pipeline we've been building."

**Expected Skill Activated:** tsfm-forecast (report mode)
**Expected Files Loaded:** SKILL.md → deliverable-templates.md (Step 6 only)

**Observation Points:**
- "Client-ready forecast report" triggers report mode (Step 6 / Procedure Step 6)
- deliverable-templates.md should ONLY be loaded at Step 6 — not earlier in the procedure
- This tests that the conditional load rule is respected: deliverable-templates is not pre-loaded at skill activation
- Previous pipeline steps (data prep, inference, evaluation) are assumed already completed based on conversation context
- Loading inference-templates.md or evaluation-metrics.md here would be redundant and wasteful

**Grading:**
- **Pass:** Skill loads deliverable-templates.md only at Step 6; generates executive summary markdown, accuracy table, and assumptions/limitations section; does NOT reload data-prep-patterns or inference-templates
- **Partial:** Skill loads deliverable-templates.md but also redundantly loads evaluation-metrics.md to regenerate accuracy numbers
- **Fail:** deliverable-templates.md is never loaded; skill generates report from memory without the standardized templates; or multiple references are loaded simultaneously
