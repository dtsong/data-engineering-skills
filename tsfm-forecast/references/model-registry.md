> **Part of:** [tsfm-forecast](../SKILL.md)

# TSFM Model Registry

Reference for detailed model comparison, hardware requirements, installation, and known limitations.

## Model Comparison Matrix

| Model | Org | Params | Context (tokens) | Variates | Output Type | HuggingFace ID |
|-------|-----|--------|-------------------|----------|-------------|----------------|
| TimesFM 2.5 | Google | 200M | 16K | Univariate | Point + quantile | `google/timesfm-2.5-200m-pytorch` |
| Chronos-Bolt | Amazon | 9M–710M | 2,048 | Uni + multivariate | Probabilistic (samples) | `amazon/chronos-bolt-small` / `-base` / `-large` |
| MOIRAI 2.0 | Salesforce | Small–Large | 5,000 | Multivariate + covariates | Quantile | `Salesforce/moirai-2.0-R-small` / `-base` / `-large` |
| Lag-Llama | Time-series-FM | ~50M | 512–2048 | Univariate | Distributional (NF) | `time-series-foundation-models/Lag-Llama` |

**Notes:**
- TimesFM 2.5: Best for long horizons with daily/weekly granularity; no covariate support.
- Chronos-Bolt: Quantized, fast; probabilistic via sample draws; `-small` fits CPU RAM.
- MOIRAI 2.0: Only model natively supporting external regressors (covariates).
- Lag-Llama: Normalizing flow output; strong for intermittent/sparse demand.

---

## Selection Decision Tree

```
Long horizon (>100 steps)?
  → Yes, univariate only → TimesFM 2.5

Need covariates/regressors?
  → Yes → MOIRAI 2.0

Need probabilistic output (prediction intervals)?
  → Yes, memory-constrained (CPU only) → Chronos-Bolt-Small
  → Yes, GPU available → Chronos-Bolt-Base or Lag-Llama

Intermittent/sparse demand (many zeros)?
  → Lag-Llama (normalizing flows handle zero-inflation better)

Cloud platform lock-in acceptable?
  → AWS SageMaker JumpStart → Chronos-Bolt
  → Google Vertex AI → TimesFM 2.5
  → Hugging Face Inference API → any model

Default (no strong signal):
  → Chronos-Bolt-Small (CPU-friendly, probabilistic, fast)
```

---

## Hardware Requirements

| Model | Min RAM (CPU) | GPU VRAM (min) | GPU VRAM (recommended) | Apple MPS |
|-------|--------------|----------------|------------------------|-----------|
| TimesFM 2.5 | 16 GB | 4 GB | 8 GB A100/H100 | Supported (MPS) |
| Chronos-Bolt-Small | 4 GB | < 1 GB | 2 GB | Supported |
| Chronos-Bolt-Base | 8 GB | 2 GB | 4 GB | Supported |
| Chronos-Bolt-Large | 16 GB | 4 GB | 8 GB | Supported |
| MOIRAI 2.0 Small | 8 GB | 2 GB | 4 GB | Partial (check version) |
| MOIRAI 2.0 Large | 32 GB | 8 GB | 16 GB | Limited |
| Lag-Llama | 8 GB | 2 GB | 4 GB | Supported (MPS device) |

**Apple MPS note:** Set `device = "mps"` on Apple Silicon. MOIRAI 2.0 large may fall back to CPU on MPS due to unsupported ops in some torch versions.

---

## Installation Commands

```bash
# TimesFM 2.5 (Google)
pip install timesfm torch  # requires torch >= 2.1

# Chronos-Bolt (Amazon)
pip install autogluon.timeseries  # includes Chronos-Bolt
# or lightweight:
pip install chronos-forecasting  # standalone HF-based install

# MOIRAI 2.0 (Salesforce)
pip install uni2ts  # Unified Training for Time Series

# Lag-Llama
pip install lag-llama
# or from HuggingFace:
pip install transformers torch
# then load checkpoint directly via HF Hub

# Common dependencies for all pipelines
pip install duckdb pandas pyarrow huggingface_hub
```

**Version pinning note:** Pin `torch` version to avoid CUDA driver conflicts. Add `torch==2.3.0` (or current stable) to requirements.txt with `--index-url` for platform-specific CUDA builds.

---

## Known Limitations

| Model | Context Hard Limit | Missing Value Behavior | Multi-Step Approach |
|-------|-------------------|----------------------|---------------------|
| TimesFM 2.5 | 16,384 steps — truncates silently if exceeded | Forward-fills NaN by default; explicit imputation recommended | Direct multi-horizon output (single call) |
| Chronos-Bolt | 2,048 steps | Raises error on NaN — impute before inference | Recursive or direct (configurable via `prediction_length`) |
| MOIRAI 2.0 | 5,000 steps | Accepts masked tokens for gaps; use `observed_mask` param | Direct multi-horizon output |
| Lag-Llama | 512 steps (rolling context window) | No NaN support — impute required | Recursive (one step ahead, repeated) |

**Structural break caveat:** None of these models retrain on your data. If the time series has a structural break (COVID-19 demand shift, product launch, pricing change), forecasts may be biased. Document the break date in deliverables and consider post-processing bias correction.
