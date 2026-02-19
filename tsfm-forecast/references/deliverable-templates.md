> **Part of:** [tsfm-forecast](../SKILL.md)

# Deliverable Templates for TSFM Forecast Reports

Templates for client-facing forecast deliverables. Load only in report mode (Step 7).

## Forecast Report Structure

Ordered sections for a complete client deliverable:

1. **Executive Summary** — horizon, model, key findings, confidence, recommended action
2. **Data Profile** — series length, frequency, gap count, outlier count, date range
3. **Model Selection Rationale** — chosen model, why it fits, alternatives considered
4. **Accuracy Results** — model vs. seasonal naive comparison table; Pass/Fail
5. **Forecast Output** — table or chart of point forecasts + prediction intervals
6. **Assumptions and Limitations** — standard disclaimers (always include)
7. **Next Steps** — scheduling recommendation, monitoring cadence, data improvement actions

---

## Executive Summary Template

```markdown
## Executive Summary

**Forecast horizon:** {horizon} {frequency} steps ({start_date} – {end_date})
**Model:** {model_name} ({model_version})
**Series forecasted:** {n_series} ({series_description})

### Key Findings

- Forecast predicts {direction} trend with {confidence_level} confidence.
- Point forecast at horizon end: **{final_value}** (90% interval: {lower} – {upper}).
- Model outperforms seasonal naive baseline: MASE = {mase_value} (target < 1.0). ✓

### Recommended Action

{recommended_action_text}

_Generated: {generation_date} | Model weights: {model_hf_id}_
```

---

## Accuracy Table Template

```markdown
## Accuracy Results

| Metric | {Model Name} | Seasonal Naive | Pass/Fail |
|--------|-------------|----------------|-----------|
| MASE   | {mase}      | 1.00 (baseline)| {✓ / ✗}  |
| SMAPE  | {smape}%    | {naive_smape}% | {✓ / ✗}  |
| RMSE   | {rmse}      | {naive_rmse}   | {✓ / ✗}  |
| Coverage (90%) | {coverage}% | N/A | {✓ / ✗} |

**Pass criteria:** MASE < 1.0 (beats seasonal naive); Coverage within ±5pp of nominal level.

**Test period:** {test_start} – {test_end} ({n_test_steps} steps, {n_horizons} rolling origins)
```

---

## Assumptions and Limitations

Include verbatim in every client deliverable:

```markdown
## Assumptions and Limitations

1. **Stationarity assumption:** The forecasting model assumes the statistical patterns (seasonality,
   trend, noise level) observed in the historical data persist into the forecast horizon.
   Structural breaks (e.g., market disruptions, product discontinuations) are not modeled.

2. **Training data recency:** Model weights were trained on public datasets and have a knowledge
   cutoff. The model has not been fine-tuned on your specific data. Performance may degrade on
   highly domain-specific series not represented in training data.

3. **Model weights version:** Forecasts were generated using {model_hf_id} as of {generation_date}.
   Updated model weights may produce different results. Pin model versions for reproducibility.

4. **Horizon reliability:** Forecast accuracy degrades with horizon length. Predictions beyond
   {reliable_horizon} steps should be treated as directional guidance only.

5. **External factors:** This model does not incorporate exogenous variables (promotions, holidays,
   macroeconomic signals) unless MOIRAI with covariates was used. Anomalous future events will
   not be reflected in the forecast.

6. **Zero-shot inference:** No fine-tuning was performed on your data. Fine-tuned models may
   significantly outperform these results on domain-specific series.
```
