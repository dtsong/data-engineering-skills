> **Part of:** [tsfm-forecast](../SKILL.md)

# Evaluation Metrics for TSFM Forecasting

Backtesting protocol, point and probabilistic metrics, naive baselines, and evaluation code patterns.

## Backtesting Protocol

**Rule:** Always use temporal train/test split — never random shuffle for time series.

```
|------ training context ------|--- test window ---|
                                ^                   ^
                           cutoff_date          end_date
```

- **Test window** = horizon × 3 (minimum); e.g., 12-week horizon → 36-week test window
- **Rolling origin** (optional): slide cutoff forward by `horizon` steps, average metrics across origins
- **Never** use `sklearn.model_selection.train_test_split` on time-series data

```python
import pandas as pd

def temporal_split(df: pd.DataFrame, horizon: int, test_multiplier: int = 3):
    """Temporal train/test split for time-series evaluation."""
    df = df.sort_values("ds")
    cutoff = df["ds"].iloc[-(horizon * test_multiplier)]
    train = df[df["ds"] < cutoff].copy()
    test = df[df["ds"] >= cutoff].copy()
    return train, test, cutoff
```

---

## Point Forecast Metrics

### MASE — Mean Absolute Scaled Error (primary)

Scale-independent; compares model to seasonal naive baseline:

```
MASE = MAE(model) / MAE(seasonal_naive_in_sample)
```

```python
import numpy as np

def mase(y_true: np.ndarray, y_pred: np.ndarray, y_train: np.ndarray, season: int = 1) -> float:
    """MASE: MAE scaled by in-sample seasonal naive MAE. Values < 1.0 beat naive."""
    naive_errors = np.abs(y_train[season:] - y_train[:-season])
    scale = np.mean(naive_errors)
    if scale == 0:
        return float("nan")
    return float(np.mean(np.abs(y_true - y_pred)) / scale)
```

**Interpret:** MASE < 1.0 means model outperforms seasonal naive. Target < 0.8 for deployment.

### SMAPE — Symmetric Mean Absolute Percentage Error

```python
def smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """SMAPE as percentage. Bounded [0, 200]. Undefined when both true and pred = 0."""
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2
    mask = denom > 0
    return float(100.0 * np.mean(np.abs(y_true[mask] - y_pred[mask]) / denom[mask]))
```

### RMSE — Root Mean Squared Error

```python
def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
```

---

## Probabilistic Forecast Metrics

Use when model outputs prediction intervals or sample draws (Chronos, Lag-Llama, MOIRAI).

### CRPS — Continuous Ranked Probability Score

Measures sharpness + calibration of forecast distribution:

```python
def crps_empirical(y_true: float, samples: np.ndarray) -> float:
    """CRPS from ensemble samples. Lower = better. 0 = perfect."""
    n = len(samples)
    term1 = np.mean(np.abs(samples - y_true))
    term2 = np.mean(np.abs(samples[:, None] - samples[None, :])) / 2
    return float(term1 - term2)
```

### WQL — Weighted Quantile Loss (aka Pinball Loss)

```python
def wql(y_true: np.ndarray, y_quantiles: dict[float, np.ndarray]) -> float:
    """WQL across multiple quantile levels. y_quantiles: {0.1: preds, 0.5: preds, 0.9: preds}"""
    losses = []
    for q, y_q in y_quantiles.items():
        error = y_true - y_q
        loss = np.where(error >= 0, q * error, (q - 1) * error)
        losses.append(np.mean(loss))
    return float(np.mean(losses))
```

### Coverage Rate

Empirical coverage of prediction intervals:

```python
def coverage_rate(y_true: np.ndarray, y_lower: np.ndarray, y_upper: np.ndarray) -> float:
    """Fraction of actuals within [lower, upper]. Target: matches nominal level (e.g., 0.9)."""
    return float(np.mean((y_true >= y_lower) & (y_true <= y_upper)))
```

---

## Naive Baseline Construction

**Model must beat seasonal naive to justify TSFM deployment.**

Seasonal naive formula: `ŷ_{t+h} = y_{t+h-m}` where `m` = seasonal period.

```python
def seasonal_naive_forecast(y_train: np.ndarray, horizon: int, season: int) -> np.ndarray:
    """Seasonal naive: repeat last full season for the forecast horizon."""
    last_season = y_train[-season:]
    reps = (horizon // season) + 1
    return np.tile(last_season, reps)[:horizon]

# Season guide:
# Daily data → season = 7 (weekly pattern)
# Weekly data → season = 52 (yearly pattern)
# Monthly data → season = 12
# Hourly data → season = 24 (daily) or 168 (weekly)
```

---

## Evaluation Code Patterns

### Full Evaluation Function

```python
def evaluate_forecast(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_train: np.ndarray,
    season: int,
    y_lower: np.ndarray = None,
    y_upper: np.ndarray = None,
) -> dict:
    """Return metrics dict for a single series forecast."""
    metrics = {
        "mase": mase(y_true, y_pred, y_train, season),
        "smape": smape(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "n_test": len(y_true),
    }
    if y_lower is not None and y_upper is not None:
        metrics["coverage_90"] = coverage_rate(y_true, y_lower, y_upper)
    baseline = seasonal_naive_forecast(y_train, len(y_true), season)
    metrics["baseline_mase"] = 1.0  # by definition
    metrics["baseline_smape"] = smape(y_true, baseline)
    metrics["beats_naive"] = metrics["mase"] < 1.0
    return metrics
```

### DuckDB Query: Assemble Actuals for Evaluation

```sql
-- Join forecasts with actuals for metric calculation
SELECT
    f.unique_id,
    f.ds,
    f.y_hat,
    f.y_hat_lower,
    f.y_hat_upper,
    a.y AS y_actual
FROM read_parquet('output/forecasts.parquet') f
LEFT JOIN read_parquet('output/ts_ready.parquet') a
    ON f.unique_id = a.unique_id AND f.ds = a.ds
WHERE a.y IS NOT NULL  -- only evaluate where actuals exist
ORDER BY f.unique_id, f.ds;
```
