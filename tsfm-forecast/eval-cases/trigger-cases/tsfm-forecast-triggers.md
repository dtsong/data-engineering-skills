# tsfm-forecast -- Trigger Eval Cases

Trigger evals test whether the skill correctly activates (or correctly does NOT activate) on various user inputs. Distinct from navigation evals (file traversal) and output evals (result quality).

---

## Case 1: Direct Match -- TimesFM Pipeline for Daily Sales

**Category:** Direct match
**Tier:** 1 (simple)

**Input:**
> "Generate a TimesFM forecasting pipeline for my daily sales data"

**Expected Activation:** Yes
**Expected Skill:** tsfm-forecast

**Observation Points:**
- Prompt contains exact model name "TimesFM" and task keyword "forecasting pipeline"
- "Daily sales data" maps to demand forecasting use case in SKILL.md
- No competing skill handles TSFM model selection or inference code generation

**Grading:**
- **Pass:** Skill activates and classifies as Pipeline mode; selects TimesFM 2.5; offers to generate data prep + inference code
- **Partial:** Skill activates but jumps to code without confirming frequency (daily) and horizon length
- **Fail:** Skill does not activate; or python-data-engineering activates because it sees "Python pipeline"

---

## Case 2: Casual Phrasing -- Predict Next 12 Weeks

**Category:** Casual phrasing
**Tier:** 1 (simple)

**Input:**
> "I have 3 years of weekly sales history. Predict the next 12 weeks."

**Expected Activation:** Yes
**Expected Skill:** tsfm-forecast

**Observation Points:**
- No mention of a specific model name — keyword is "predict" with "weekly sales" and a fixed horizon
- "3 years of weekly history" = ~156 steps; sufficient for any TSFM model
- "12 weeks" horizon is explicit — skill should use this directly
- python-data-engineering could compete but "predict future values" + time-series context tips to tsfm-forecast

**Grading:**
- **Pass:** Skill activates, infers weekly frequency and 12-step horizon, recommends Chronos-Bolt-Small as default, and offers to generate pipeline code
- **Partial:** Skill activates but asks for model name instead of defaulting per Quick Reference table
- **Fail:** Skill does not activate; or python-data-engineering activates because it sees "Python" implied

---

## Case 3: Ambiguous -- Best Way to Forecast Monthly Revenue

**Category:** Ambiguous
**Tier:** 2 (medium)

**Input:**
> "What's the best way to forecast monthly revenue?"

**Expected Activation:** Conditional (ask clarifying question)
**Expected Skill:** tsfm-forecast (if foundation model approach confirmed)

**Observation Points:**
- "Forecast" with time context ("monthly") is a trigger signal, but no data volume, model preference, or tooling preference is given
- Could be answered with: statistical methods (ARIMA, ETS), ML-based approaches, or TSFM zero-shot
- Skill should clarify: "Are you looking for a zero-shot foundation model approach, or do you want to compare statistical and ML options?"
- If user confirms TSFM approach, skill activates fully

**Grading:**
- **Pass:** Skill activates with a clarifying question about approach preference before generating code; activates fully if TSFM is confirmed
- **Partial:** Skill activates but generates TSFM code without checking if foundation model approach is desired
- **Fail:** Skill does not activate; or python-data-engineering activates and provides only statistical/ML options

---

## Case 4: Negative -- Fine-Tune Transformer on Time-Series

**Category:** Negative
**Tier:** 2 (medium)

**Input:**
> "Fine-tune a transformer on my time-series data"

**Expected Activation:** No
**Expected Skill:** python-data-engineering

**Observation Points:**
- "Fine-tune" is explicitly out of scope per SKILL.md "Don't use for" section
- Even though time-series foundation models exist, this request is for training/fine-tuning, not zero-shot inference
- python-data-engineering covers custom model training and PyTorch/HuggingFace workflows
- tsfm-forecast's scope is zero-shot inference only

**Grading:**
- **Pass:** Skill does not activate; redirects to python-data-engineering for fine-tuning workflow; optionally notes that zero-shot TSFM inference (tsfm-forecast) is available if fine-tuning is not required
- **Partial:** Skill activates and attempts to explain fine-tuning but acknowledges it's out of scope
- **Fail:** Skill activates and attempts to generate fine-tuning code

---

## Case 5: Edge Case -- Multi-SKU Chronos with Dagster Scheduling

**Category:** Edge case
**Tier:** 3 (complex)

**Input:**
> "Forecast 50 product SKUs using Chronos, run on schedule with Dagster"

**Expected Activation:** Yes (with handoff)
**Expected Skill:** tsfm-forecast (primary), data-pipelines (handoff for scheduling)

**Observation Points:**
- "50 product SKUs" + "Chronos" maps to batch multi-series inference in tsfm-forecast
- "Run on schedule with Dagster" is explicitly in SKILL.md handoff block → data-pipelines
- Skill should handle the Chronos batch inference code and signal handoff to data-pipelines for Dagster scheduling
- This tests that the skill correctly scopes itself and doesn't attempt Dagster asset code

**Grading:**
- **Pass:** Skill activates and generates multi-series Chronos batch inference code; explicitly signals handoff to data-pipelines for Dagster scheduling; does NOT generate Dagster asset code
- **Partial:** Skill activates but attempts to generate Dagster asset code without loading data-pipelines skill
- **Fail:** data-pipelines activates first because of "Dagster" keyword; tsfm-forecast never activates

---

## Case 6: Bypass -- Kafka Consumer for Real-Time Price Data

**Category:** Bypass
**Tier:** 3 (complex)

**Input:**
> "Build a Kafka consumer for real-time price data"

**Expected Activation:** No
**Expected Skill:** event-streaming

**Observation Points:**
- "Kafka consumer" + "real-time" maps directly to event-streaming scope
- tsfm-forecast's "Don't use for" section explicitly excludes real-time/streaming forecasts
- "Price data" could superficially resemble a time-series workload, but real-time streaming is outside TSFM batch inference scope
- No foundation model inference is requested

**Grading:**
- **Pass:** Skill does not activate; event-streaming handles the Kafka consumer request
- **Partial:** Skill does not activate but mentions TSFM could be applied to batch price forecasting after streaming
- **Fail:** Skill activates because it sees "price data" and attempts to provide forecasting context for a streaming request

---

## Case 7: Profiler Trigger -- Profile Dataset for Model Selection

**Category:** Profiler trigger
**Tier:** 1 (simple)

**Input:**
> "Profile my time-series dataset to see which TSFM model is best"

**Expected Activation:** Yes (profile mode)
**Expected Skill:** tsfm-forecast

**Observation Points:**
- "Profile my time-series dataset" + "TSFM model" is an explicit profile mode trigger
- Skill should classify as Profile mode (Step 1) and recommend running `ts_profiler.py`
- Should provide the CLI invocation with appropriate flags
- duckdb skill could compete for "profile dataset" but "TSFM model" tips to tsfm-forecast

**Grading:**
- **Pass:** Skill activates in Profile mode; provides `ts_profiler.py` CLI command with input/output path placeholders; explains the JSON output fields including `recommended_model`
- **Partial:** Skill activates but jumps to model selection without mentioning ts_profiler.py
- **Fail:** duckdb skill activates and provides generic data profiling SQL without TSFM model recommendation
