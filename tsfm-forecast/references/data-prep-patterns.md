> **Part of:** [tsfm-forecast](../SKILL.md)

# Data Preparation Patterns for TSFM Forecasting

DuckDB SQL patterns for preparing time-series data for foundation model inference.

## Timestamp Normalization

Parse inconsistent formats and create a unified `ds` column (TSFM convention):

```sql
-- Normalize mixed timestamp formats to UTC timestamp
CREATE OR REPLACE TABLE ts_normalized AS
SELECT
    unique_id,
    -- strptime handles multiple format attempts via COALESCE
    COALESCE(
        TRY_STRPTIME(ts_raw, '%Y-%m-%d %H:%M:%S'),
        TRY_STRPTIME(ts_raw, '%m/%d/%Y %H:%M'),
        TRY_STRPTIME(ts_raw, '%Y-%m-%d'),
        TRY_CAST(ts_raw AS TIMESTAMP)
    )::TIMESTAMPTZ AT TIME ZONE 'UTC' AS ds,
    value AS y
FROM raw_data
WHERE ts_raw IS NOT NULL;
```

**Column naming convention:** All TSFM models expect:
- `ds` — timestamp (datetime64[ns] in pandas, TIMESTAMP in DuckDB)
- `y` — target value (float)
- `unique_id` — series identifier (string); use `'series_0'` for single-series

---

## Gap Detection and Filling

Detect missing timesteps before inference — gaps cause silent forecast drift:

```sql
-- Generate complete date spine and identify gaps
WITH date_spine AS (
    SELECT UNNEST(
        generate_series(
            (SELECT MIN(ds) FROM ts_normalized),
            (SELECT MAX(ds) FROM ts_normalized),
            INTERVAL '1 day'  -- adjust to target frequency
        )
    ) AS ds
),
joined AS (
    SELECT
        s.ds,
        n.unique_id,
        n.y,
        CASE WHEN n.ds IS NULL THEN true ELSE false END AS is_gap
    FROM date_spine s
    LEFT JOIN ts_normalized n ON s.ds = n.ds
)
SELECT ds, unique_id, y, is_gap FROM joined ORDER BY ds;
```

**Count missing steps:**
```sql
SELECT
    count(*) FILTER (WHERE is_gap) AS gap_count,
    count(*) AS total_steps,
    round(100.0 * count(*) FILTER (WHERE is_gap) / count(*), 2) AS gap_pct
FROM (-- above joined query --)
```

---

## Resampling to Target Frequency

Aggregate sub-daily data to the target forecast frequency:

```sql
-- Resample to daily frequency
CREATE OR REPLACE TABLE ts_daily AS
SELECT
    unique_id,
    date_trunc('day', ds)::DATE AS ds,
    -- Use SUM for demand/volume, AVG for price/rate
    SUM(y) AS y
FROM ts_normalized
GROUP BY unique_id, date_trunc('day', ds)
ORDER BY unique_id, ds;

-- Resample to weekly (Monday anchor)
CREATE OR REPLACE TABLE ts_weekly AS
SELECT
    unique_id,
    date_trunc('week', ds)::DATE AS ds,
    SUM(y) AS y
FROM ts_normalized
GROUP BY unique_id, date_trunc('week', ds)
ORDER BY unique_id, ds;
```

**Frequency guide:**
- Demand/sales → `SUM`
- Price, rate, inventory level → `AVG`
- Max capacity, peak load → `MAX`

---

## Null and Outlier Handling

Fill gaps and flag anomalies before inference:

```sql
-- Forward-fill nulls using lag-based interpolation
CREATE OR REPLACE TABLE ts_filled AS
SELECT
    unique_id,
    ds,
    COALESCE(
        y,
        LAG(y IGNORE NULLS) OVER (PARTITION BY unique_id ORDER BY ds),
        0.0  -- fallback to zero if no prior value
    ) AS y
FROM ts_with_gaps
ORDER BY unique_id, ds;

-- Z-score outlier flagging (flag > 3 sigma)
CREATE OR REPLACE TABLE ts_flagged AS
SELECT
    unique_id,
    ds,
    y,
    AVG(y) OVER (PARTITION BY unique_id) AS y_mean,
    STDDEV(y) OVER (PARTITION BY unique_id) AS y_std,
    ABS(y - AVG(y) OVER (PARTITION BY unique_id))
        / NULLIF(STDDEV(y) OVER (PARTITION BY unique_id), 0) AS z_score,
    ABS(y - AVG(y) OVER (PARTITION BY unique_id))
        / NULLIF(STDDEV(y) OVER (PARTITION BY unique_id), 0) > 3 AS is_outlier
FROM ts_filled;
```

---

## Parquet Export for Model Ingestion

Export to Parquet with TSFM-standard column names:

```sql
-- Export single series
COPY (
    SELECT unique_id, ds, y
    FROM ts_filled
    ORDER BY unique_id, ds
) TO 'output/ts_ready.parquet' (FORMAT PARQUET);

-- Export with quantile history (for evaluation backtesting)
COPY (
    SELECT
        unique_id,
        ds,
        y,
        ROW_NUMBER() OVER (PARTITION BY unique_id ORDER BY ds) AS step_idx
    FROM ts_filled
) TO 'output/ts_ready_indexed.parquet' (FORMAT PARQUET);
```

**Load back for inspection:**
```sql
SELECT * FROM read_parquet('output/ts_ready.parquet') LIMIT 5;
```

---

## Multi-Series Batch Preparation

Prepare multiple series (e.g., product SKUs) with `unique_id`:

```sql
-- Combine multiple series from separate tables
CREATE OR REPLACE TABLE ts_batch AS
SELECT 'sku_a' AS unique_id, ds, quantity AS y FROM sales_sku_a
UNION ALL
SELECT 'sku_b' AS unique_id, ds, quantity AS y FROM sales_sku_b
UNION ALL
SELECT 'sku_c' AS unique_id, ds, quantity AS y FROM sales_sku_c
ORDER BY unique_id, ds;

-- Verify all series have same frequency
SELECT
    unique_id,
    count(*) AS n_steps,
    MIN(ds) AS start_date,
    MAX(ds) AS end_date,
    MODE() WITHIN GROUP (ORDER BY ds - LAG(ds) OVER (PARTITION BY unique_id ORDER BY ds)) AS modal_interval
FROM ts_batch
GROUP BY unique_id;

-- Export batch for TSFM inference
COPY (SELECT * FROM ts_batch ORDER BY unique_id, ds)
TO 'output/ts_batch.parquet' (FORMAT PARQUET);
```

**Batch inference note:** Chronos-Bolt and MOIRAI support batch inference across `unique_id`s in a single call. TimesFM 2.5 requires looping per series unless using the batched API endpoint.
