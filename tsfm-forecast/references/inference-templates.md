> **Part of:** [tsfm-forecast](../SKILL.md)

# Inference Templates for TSFM Models

One compact Python template per model. All templates output a standardized DataFrame:
`unique_id | ds | y_hat | y_hat_lower | y_hat_upper`

---

## TimesFM 2.5

```python
import pandas as pd
import numpy as np
import timesfm

def run_timesfm(
    df: pd.DataFrame,
    horizon: int,
    freq: str = "D",
    quantile_levels: list[float] = [0.1, 0.5, 0.9],
) -> pd.DataFrame:
    """Zero-shot forecast with TimesFM 2.5.

    Args:
        df: DataFrame with columns [unique_id, ds, y]. ds must be datetime.
        horizon: Number of future steps to forecast.
        freq: Pandas-compatible frequency string ('D', 'W', 'M', 'H').
        quantile_levels: Quantile levels for output intervals.

    Returns:
        Standardized forecast DataFrame.
    """
    tfm = timesfm.TimesFm(
        hparams=timesfm.TimesFmHparams(
            backend="pytorch",
            per_core_batch_size=32,
            horizon_len=horizon,
        ),
        checkpoint=timesfm.TimesFmCheckpoint(
            huggingface_repo_id="google/timesfm-2.5-200m-pytorch"
        ),
    )

    results = []
    for uid, group in df.groupby("unique_id"):
        group = group.sort_values("ds")
        context = group["y"].values.astype(float)

        point_forecast, quantile_forecast = tfm.forecast(
            inputs=[context],
            freq=[freq],
            quantile_levels=quantile_levels,
        )

        last_date = group["ds"].iloc[-1]
        future_dates = pd.date_range(start=last_date, periods=horizon + 1, freq=freq)[1:]

        median_idx = quantile_levels.index(0.5) if 0.5 in quantile_levels else 0
        q10_idx = quantile_levels.index(0.1) if 0.1 in quantile_levels else None
        q90_idx = quantile_levels.index(0.9) if 0.9 in quantile_levels else None

        for i, date in enumerate(future_dates):
            results.append({
                "unique_id": uid,
                "ds": date,
                "y_hat": float(quantile_forecast[0][i][median_idx]),
                "y_hat_lower": float(quantile_forecast[0][i][q10_idx]) if q10_idx is not None else np.nan,
                "y_hat_upper": float(quantile_forecast[0][i][q90_idx]) if q90_idx is not None else np.nan,
            })

    return pd.DataFrame(results)
```

---

## Chronos-Bolt

```python
import pandas as pd
import numpy as np
import torch
from chronos import ChronosPipeline

def run_chronos(
    df: pd.DataFrame,
    horizon: int,
    model_size: str = "small",
    n_samples: int = 20,
    freq: str = "D",
) -> pd.DataFrame:
    """Zero-shot forecast with Chronos-Bolt.

    Args:
        df: DataFrame with [unique_id, ds, y].
        horizon: Forecast steps.
        model_size: 'small' (CPU-friendly), 'base', or 'large'.
        n_samples: Number of sample draws for probabilistic output.
        freq: Pandas frequency string for future dates.

    Returns:
        Standardized forecast DataFrame.
    """
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    pipeline = ChronosPipeline.from_pretrained(
        f"amazon/chronos-bolt-{model_size}",
        device_map=device,
        torch_dtype=torch.bfloat16,
    )

    results = []
    for uid, group in df.groupby("unique_id"):
        group = group.sort_values("ds")
        context = torch.tensor(group["y"].values, dtype=torch.float32)

        # Chronos returns (n_series, n_samples, horizon)
        forecast_samples = pipeline.predict(
            context=context.unsqueeze(0),
            prediction_length=horizon,
            num_samples=n_samples,
        ).squeeze(0).numpy()  # shape: (n_samples, horizon)

        last_date = group["ds"].iloc[-1]
        future_dates = pd.date_range(start=last_date, periods=horizon + 1, freq=freq)[1:]

        for i, date in enumerate(future_dates):
            step_samples = forecast_samples[:, i]
            results.append({
                "unique_id": uid,
                "ds": date,
                "y_hat": float(np.median(step_samples)),
                "y_hat_lower": float(np.percentile(step_samples, 10)),
                "y_hat_upper": float(np.percentile(step_samples, 90)),
            })

    return pd.DataFrame(results)
```

---

## MOIRAI 2.0

```python
import pandas as pd
import numpy as np
import torch
from einops import rearrange
from uni2ts.model.moirai import MoiraiForecast, MoiraiModule

def run_moirai(
    df: pd.DataFrame,
    horizon: int,
    model_size: str = "small",
    patch_size: int = 16,
    num_samples: int = 20,
    freq: str = "D",
) -> pd.DataFrame:
    """Zero-shot forecast with MOIRAI 2.0.

    Args:
        df: DataFrame with [unique_id, ds, y]. Supports multivariate if multiple unique_ids share same ds.
        horizon: Forecast steps.
        model_size: 'small', 'base', or 'large'.
        patch_size: Patch size for tokenization (8, 16, 32, 64 or 'auto').
        num_samples: Sample draws for probabilistic output.
        freq: Pandas frequency string.

    Returns:
        Standardized forecast DataFrame.
    """
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = MoiraiForecast(
        module=MoiraiModule.from_pretrained(f"Salesforce/moirai-2.0-R-{model_size}"),
        prediction_length=horizon,
        context_length=min(len(df) // df["unique_id"].nunique(), 2000),
        patch_size=patch_size,
        num_samples=num_samples,
        target_dim=1,
        feat_dynamic_real_dim=0,
        past_feat_dynamic_real_dim=0,
    ).to(device)

    results = []
    for uid, group in df.groupby("unique_id"):
        group = group.sort_values("ds")
        context = torch.tensor(group["y"].values, dtype=torch.float32).unsqueeze(0).unsqueeze(-1).to(device)

        with torch.no_grad():
            samples = model(past_target=context, past_observed_values=torch.ones_like(context))
        # samples shape: (1, num_samples, horizon, 1)
        samples_np = samples.squeeze(0).squeeze(-1).cpu().numpy()  # (num_samples, horizon)

        last_date = group["ds"].iloc[-1]
        future_dates = pd.date_range(start=last_date, periods=horizon + 1, freq=freq)[1:]

        for i, date in enumerate(future_dates):
            step_samples = samples_np[:, i]
            results.append({
                "unique_id": uid,
                "ds": date,
                "y_hat": float(np.median(step_samples)),
                "y_hat_lower": float(np.percentile(step_samples, 10)),
                "y_hat_upper": float(np.percentile(step_samples, 90)),
            })

    return pd.DataFrame(results)
```

---

## Lag-Llama

```python
import pandas as pd
import numpy as np
import torch
from huggingface_hub import hf_hub_download
from lag_llama.gluon.estimator import LagLlamaEstimator

def run_lag_llama(
    df: pd.DataFrame,
    horizon: int,
    num_samples: int = 20,
    freq: str = "D",
    context_length: int = 32,
) -> pd.DataFrame:
    """Zero-shot forecast with Lag-Llama.

    Args:
        df: DataFrame with [unique_id, ds, y].
        horizon: Forecast steps.
        num_samples: Distributional samples for intervals.
        freq: GluonTS-compatible freq string ('D', 'W', 'M', '1H').
        context_length: Steps of history to condition on (max ~512).

    Returns:
        Standardized forecast DataFrame.
    """
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"

    ckpt_path = hf_hub_download(
        repo_id="time-series-foundation-models/Lag-Llama",
        filename="lag-llama.ckpt",
    )
    estimator = LagLlamaEstimator(
        ckpt_path=ckpt_path,
        prediction_length=horizon,
        context_length=context_length,
        n_layer=32,
        n_embd_per_head=32,
        n_head=16,
        num_parallel_samples=num_samples,
        device=device,
    )
    lightning_module = estimator.train_model().to(device)

    from gluonts.dataset.common import ListDataset
    results = []
    for uid, group in df.groupby("unique_id"):
        group = group.sort_values("ds")
        dataset = ListDataset(
            [{"start": group["ds"].iloc[0], "target": group["y"].values}],
            freq=freq,
        )
        predictor = estimator.create_predictor(
            transformation=estimator.create_transformation(),
            trained_network=lightning_module,
        )
        forecasts = list(predictor.predict(dataset))
        fc = forecasts[0]
        future_dates = pd.date_range(start=group["ds"].iloc[-1], periods=horizon + 1, freq=freq)[1:]

        for i, date in enumerate(future_dates):
            step_samples = fc.samples[:, i]
            results.append({
                "unique_id": uid,
                "ds": date,
                "y_hat": float(np.median(step_samples)),
                "y_hat_lower": float(np.percentile(step_samples, 10)),
                "y_hat_upper": float(np.percentile(step_samples, 90)),
            })

    return pd.DataFrame(results)
```

---

## Output Normalization

Standardize any model output to the unified forecast shape:

```python
def normalize_forecast_output(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure forecast DataFrame has the standard 5-column shape.

    Required columns: unique_id (str), ds (datetime64[ns]), y_hat (float),
                      y_hat_lower (float), y_hat_upper (float).
    """
    required = {"unique_id", "ds", "y_hat"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Forecast DataFrame missing required columns: {missing}")

    if "y_hat_lower" not in df.columns:
        df["y_hat_lower"] = float("nan")
    if "y_hat_upper" not in df.columns:
        df["y_hat_upper"] = float("nan")

    df["ds"] = pd.to_datetime(df["ds"])
    df["unique_id"] = df["unique_id"].astype(str)
    df["y_hat"] = df["y_hat"].astype(float)

    return df[["unique_id", "ds", "y_hat", "y_hat_lower", "y_hat_upper"]].sort_values(["unique_id", "ds"])
```
