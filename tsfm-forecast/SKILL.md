---
name: tsfm-forecast
description: "Use this skill when generating time-series forecasting pipelines using foundation models. Covers TimesFM, Chronos, MOIRAI, and Lag-Llama model selection, DuckDB-based preprocessing code, Python inference generation, backtesting harnesses, multi-model comparison, and client forecast deliverables. Common phrases: \"time-series forecast\", \"demand forecasting\", \"TimesFM\", \"Chronos\", \"predict future values\", \"zero-shot forecast\". Do NOT use for ML model training or fine-tuning (use python-data-engineering), real-time/streaming forecasts (use event-streaming), or pipeline scheduling (use data-pipelines)."
model:
  preferred: sonnet
  acceptable: [sonnet, opus]
  minimum: sonnet
  allow_downgrade: false
  reasoning_demand: medium
version: 0.1.0
---

# TSFM Forecast Skill

Generates Python + DuckDB forecasting pipeline code using foundation models. Produces runnable code for local execution; does NOT run models.

## When to Use This Skill

**Activate when:** Generating zero-shot time-series forecasting pipelines, selecting between TimesFM / Chronos / MOIRAI / Lag-Llama, preparing time-series data with DuckDB, building backtesting harnesses, comparing model accuracy, or producing client forecast deliverables.

**Don't use for:**
- ML model training or fine-tuning → use `python-data-engineering`
- Real-time or streaming forecasts → use `event-streaming`
- Scheduling or orchestrating forecast jobs → use `data-pipelines`
- Loading raw files into DuckDB without forecasting intent → use `duckdb`

## Scope Constraints

- Generates code only — does not execute models, run inference, or access data files.
- Local execution model: all generated code targets the user's machine; no cloud deployment scaffolding unless explicitly requested.
- Security tier default: Tier 1 (schema/metadata only). User must explicitly elevate to Tier 2 (sample data) or Tier 3 (full data access).
- Reference files loaded one at a time — never pre-load multiple references simultaneously.
- No cross-references to other specialist skills; use handoff protocol for adjacent work.

## Model Routing

| reasoning_demand | preferred | acceptable | minimum |
|-----------------|-----------|------------|---------|
| medium | Sonnet | Sonnet, Opus | Sonnet |

## Core Principles

1. **Code-only** — Generate self-contained, runnable Python + DuckDB code. Never execute models or read actual data.
2. **Foundation-model-first** — Default to zero-shot TSFM inference; only recommend fine-tuning when dataset is large and domain is highly specialized.
3. **DuckDB-native** — Use DuckDB SQL for all data preparation, gap detection, resampling, and export steps.
4. **Evaluation-driven** — Always include a seasonal naive baseline and MASE metric; a model that doesn't beat naive doesn't justify deployment.
5. **Handoff-ready** — Generate outputs (`forecasts.parquet`) in standardized shape so downstream skills (data-pipelines, client-delivery) can consume them directly.

## Model Selection Quick Reference

| Signal | Recommended Model | Why |
|--------|-------------------|-----|
| Long horizon (>100 steps), univariate | TimesFM 2.5 | 16K context window, direct multi-horizon |
| Need prediction intervals, CPU-only | Chronos-Bolt-Small | Probabilistic, < 1 GB VRAM, fast |
| Multivariate + external regressors | MOIRAI 2.0 | Only TSFM with native covariate support |
| Intermittent/sparse demand (many zeros) | Lag-Llama | Normalizing flow handles zero-inflation |

**Load [model-registry.md](references/model-registry.md)** for: full matrix, hardware requirements, installation commands, and known limitations.

## Procedure

> **Progress checklist** (tick off as you complete each step):
> - [ ] 1. Classify request mode
> - [ ] 2. Select model
> - [ ] 3. Generate data prep code
> - [ ] 4. Generate inference code
> - [ ] 5. Generate evaluation code (if eval/comparison mode)
> - [ ] 6. Generate deliverable (if report mode)

> **Compaction recovery:** If context is compressed mid-procedure, re-read this SKILL.md to restore context. Check which checklist items are complete, then resume from the next unchecked step.

### Step 1 — Classify request mode

Determine which mode applies before generating any code:

- **Pipeline mode**: User wants end-to-end forecast code (data prep → inference → output). Default mode.
- **Eval/comparison mode**: User wants to compare models or backtest accuracy. Add evaluation step.
- **Report mode**: User wants a client-ready deliverable. Add deliverable step after evaluation.
- **Profile mode**: User wants to assess data before selecting a model. Run ts_profiler.py recommendation first.

### Step 2 — Select model

Use the Quick Reference table above for default selection. Ask if ambiguous:
- How many series? (1 → any model; 50+ → Chronos or MOIRAI for batch efficiency)
- Need prediction intervals? (yes → Chronos or Lag-Llama)
- Any external regressors (promotions, holidays)? (yes → MOIRAI 2.0)
- Hardware constraints? (CPU-only → Chronos-Bolt-Small)

Load **[model-registry.md](references/model-registry.md)** if user needs detailed comparison or hardware guidance.

### Step 3 — Generate data preparation code

Load **[data-prep-patterns.md](references/data-prep-patterns.md)** and generate DuckDB SQL for:

1. Timestamp normalization → `ds` column (UTC, datetime64)
2. Gap detection → report missing step count before filling
3. Resampling to target frequency (SUM for demand, AVG for rate)
4. Null/outlier handling (forward-fill + z-score flagging)
5. Parquet export → `output/ts_ready.parquet` with `unique_id | ds | y` schema

Always confirm `unique_id`, `ds`, `y` column names match source data or generate a rename step.

### Step 4 — Generate inference code

Load **[inference-templates.md](references/inference-templates.md)** and generate Python code for the selected model:

1. Imports and model loading (with device detection: CUDA → MPS → CPU)
2. Context window setup (load from `output/ts_ready.parquet` via pandas)
3. `forecast()` call with horizon and quantile levels
4. Output normalization to standard shape: `unique_id | ds | y_hat | y_hat_lower | y_hat_upper`
5. Export → `output/forecasts.parquet`

Unload inference-templates.md after generating code before loading evaluation-metrics.md.

### Step 5 — Generate evaluation code (eval/comparison mode only)

Load **[evaluation-metrics.md](references/evaluation-metrics.md)** and generate:

1. Temporal train/test split (test window = horizon × 3)
2. Seasonal naive baseline for the target frequency
3. MASE, SMAPE, RMSE calculation
4. Coverage rate if model outputs prediction intervals
5. Pass/Fail determination: MASE < 1.0 = beats naive

Unload evaluation-metrics.md after generating code.

### Step 6 — Generate deliverable (report mode only)

Load **[deliverable-templates.md](references/deliverable-templates.md)** and generate:

1. Markdown report structure with metric placeholders
2. Executive summary with forecast findings
3. Accuracy comparison table (model vs. seasonal naive)
4. Assumptions and limitations section (include verbatim)

## Security Posture

# SECURITY: This skill generates code for local execution only. No network calls, credential access, or data file reads are performed by Claude. Generated scripts read local files via DuckDB — validate file paths before execution.

See [Security & Compliance Patterns](../shared-references/data-engineering/security-compliance-patterns.md) for the full framework.
See [Consulting Security Tier Model](../shared-references/data-engineering/security-tier-model.md) for tier definitions.

| Capability | Tier 1 (Default) | Tier 2 (Sampled) | Tier 3 (Full Access) |
|------------|-----------------|-------------------|---------------------|
| Data profiling | Column types / shape only | Stats on sample | Full profiling |
| Data prep code | Generate SQL (not execute) | Execute on samples | Execute on full data |
| Inference code | Generate only | Generate + run on samples | Generate + run on full data |
| Deliverables | Template with placeholders | Populated from samples | Fully populated |

### Input Sanitization

When user provides file paths for `ts_profiler.py` or data prep scripts:
- Validate path exists and is within the working directory before use in generated code.
- Reject paths containing `..`, `~`, environment variables, or shell metacharacters.
- Never interpolate user-provided strings directly into shell commands.

## Reference Files

Reference files loaded on demand — one at a time:

- **[model-registry.md](references/model-registry.md)** — Full model comparison matrix, hardware requirements, installation commands, known limitations. Load at Step 2 if Quick Reference is insufficient.
- **[data-prep-patterns.md](references/data-prep-patterns.md)** — DuckDB SQL patterns for timestamp normalization, gap detection, resampling, null handling, Parquet export. Load at Step 3.
- **[inference-templates.md](references/inference-templates.md)** — Python inference code for TimesFM, Chronos, MOIRAI, Lag-Llama, output normalization. Load at Step 4.
- **[evaluation-metrics.md](references/evaluation-metrics.md)** — Backtesting protocol, MASE/SMAPE/RMSE/CRPS formulas, naive baseline, evaluation code patterns. Load at Step 5 (eval/comparison mode only).
- **[deliverable-templates.md](references/deliverable-templates.md)** — Executive summary, accuracy table, assumptions and limitations templates. Load at Step 6 (report mode only).

## Handoffs

- **Scheduling generated forecasts** → [data-pipelines](../data-pipelines/SKILL.md) (Dagster assets or Airflow DAGs wrapping inference scripts)
- **Client engagement setup** → [client-delivery](../client-delivery/SKILL.md) (engagement scaffolding, security tier selection, client handoff)
- **DuckDB data preparation** → [duckdb](../duckdb/SKILL.md) (local data exploration, file ingestion, profiling before forecasting)
