#!/usr/bin/env python3
"""Time-series profiler for TSFM model selection.

Reads CSV or Parquet files, extracts time-series statistics, detects gaps,
infers frequency, and recommends the most suitable foundation model.

# SECURITY: Reads local files only via DuckDB — no network access

Usage:
    python scripts/ts_profiler.py <input_path> <output_path> [OPTIONS]

Options:
    --timestamp-col TEXT   Name of timestamp column (auto-detect if omitted)
    --value-col TEXT       Name of value column (auto-detect if omitted)
    --id-col TEXT          Name of series identifier column (optional)
    --freq TEXT            Override frequency inference ('H', 'D', 'W', 'M')
    --include-sample N     Include N sample rows in output (Tier 2+ mode)

Dependencies:
    pip install duckdb pandas
    pip install scipy  # optional, for ADF stationarity test
"""

import argparse
import json
import os
import sys
from pathlib import Path

try:
    import duckdb
except ImportError:
    print("ERROR: duckdb is required. Install with: pip install duckdb", file=sys.stderr)
    sys.exit(1)

# scipy is optional — ADF test skipped if unavailable
try:
    from scipy import stats as _stats  # noqa: F401
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

# Frequency inference: map median delta (seconds) to pandas freq string
FREQ_THRESHOLDS = [
    (60 * 60 * 0.75, 60 * 60 * 1.5, "H"),         # ~1 hour
    (60 * 60 * 23, 60 * 60 * 25, "D"),              # ~1 day
    (60 * 60 * 24 * 6, 60 * 60 * 24 * 8, "W"),      # ~1 week
    (60 * 60 * 24 * 28, 60 * 60 * 24 * 33, "M"),    # ~1 month
]

# Minimum history requirements per model (in steps)
MODEL_MIN_HISTORY = {
    "TimesFM 2.5": 50,
    "Chronos-Bolt-Small": 20,
    "MOIRAI 2.0": 30,
    "Lag-Llama": 20,
}

# Maximum context window per model (in steps)
MODEL_MAX_CONTEXT = {
    "TimesFM 2.5": 16384,
    "Chronos-Bolt-Small": 2048,
    "MOIRAI 2.0": 5000,
    "Lag-Llama": 512,
}


def read_file(con: duckdb.DuckDBPyConnection, input_path: str) -> str:
    """Load CSV or Parquet into DuckDB and return the table name."""
    ext = Path(input_path).suffix.lower()
    if ext == ".csv":
        con.execute(f"CREATE TABLE ts_input AS SELECT * FROM read_csv_auto('{input_path}')")
    elif ext == ".parquet":
        con.execute(f"CREATE TABLE ts_input AS SELECT * FROM read_parquet('{input_path}')")
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported: .csv, .parquet")
    return "ts_input"


def detect_timestamp_columns(con: duckdb.DuckDBPyConnection, table: str) -> list[str]:
    """Find columns with TIMESTAMP, DATE type or date-like string patterns."""
    schema = con.execute(f"DESCRIBE {table}").fetchall()
    ts_cols = []

    for row in schema:
        col_name, col_type = row[0], row[1].upper()
        if any(t in col_type for t in ("TIMESTAMP", "DATE", "DATETIME")):
            ts_cols.append(col_name)

    if not ts_cols:
        # Check string columns for date-like values
        for row in schema:
            col_name, col_type = row[0], row[1].upper()
            if "VARCHAR" in col_type or "TEXT" in col_type:
                try:
                    result = con.execute(
                        f"""
                        SELECT count(*) FROM (
                            SELECT TRY_CAST("{col_name}" AS TIMESTAMP) AS parsed
                            FROM {table}
                            WHERE "{col_name}" IS NOT NULL
                            LIMIT 50
                        ) WHERE parsed IS NOT NULL
                        """
                    ).fetchone()
                    if result and result[0] >= 10:
                        ts_cols.append(col_name)
                except Exception:
                    continue

    return ts_cols


def infer_frequency(con: duckdb.DuckDBPyConnection, table: str, ts_col: str) -> str:
    """Infer time-series frequency from mode of consecutive timestamp deltas."""
    try:
        result = con.execute(
            f"""
            WITH ordered AS (
                SELECT TRY_CAST("{ts_col}" AS TIMESTAMP) AS ts
                FROM {table}
                WHERE "{ts_col}" IS NOT NULL
                ORDER BY ts
            ),
            deltas AS (
                SELECT
                    epoch(ts - LAG(ts) OVER (ORDER BY ts)) AS delta_seconds
                FROM ordered
            )
            SELECT delta_seconds, count(*) AS cnt
            FROM deltas
            WHERE delta_seconds IS NOT NULL AND delta_seconds > 0
            GROUP BY delta_seconds
            ORDER BY cnt DESC
            LIMIT 1
            """
        ).fetchone()
    except Exception:
        return "unknown"

    if result is None:
        return "unknown"

    median_delta = result[0]
    for low, high, freq in FREQ_THRESHOLDS:
        if low <= median_delta <= high:
            return freq

    # Sub-hourly
    if median_delta < 60 * 15:
        return "T"   # minutely
    if median_delta < 60 * 60:
        return "30T"  # sub-hourly

    return "unknown"


def detect_gaps(con: duckdb.DuckDBPyConnection, table: str, ts_col: str, freq: str) -> dict:
    """Count missing timesteps using a complete date spine via generate_series."""
    freq_interval_map = {
        "H": "INTERVAL 1 HOUR",
        "D": "INTERVAL 1 DAY",
        "W": "INTERVAL 7 DAYS",
        "M": "INTERVAL 1 MONTH",
        "T": "INTERVAL 1 MINUTE",
        "30T": "INTERVAL 30 MINUTES",
    }

    interval = freq_interval_map.get(freq)
    if interval is None:
        return {"gap_count": None, "gap_pct": None, "error": f"Cannot compute gaps for freq={freq}"}

    try:
        result = con.execute(
            f"""
            WITH ts_range AS (
                SELECT
                    MIN(TRY_CAST("{ts_col}" AS TIMESTAMP)) AS min_ts,
                    MAX(TRY_CAST("{ts_col}" AS TIMESTAMP)) AS max_ts
                FROM {table}
                WHERE "{ts_col}" IS NOT NULL
            ),
            spine AS (
                SELECT UNNEST(generate_series(min_ts, max_ts, {interval})) AS ds
                FROM ts_range
            ),
            actual AS (
                SELECT DISTINCT TRY_CAST("{ts_col}" AS TIMESTAMP) AS ds
                FROM {table}
                WHERE "{ts_col}" IS NOT NULL
            )
            SELECT
                count(*) AS spine_count,
                count(a.ds) AS actual_count,
                count(*) - count(a.ds) AS gap_count
            FROM spine s
            LEFT JOIN actual a ON s.ds = a.ds
            """
        ).fetchone()
    except Exception as exc:
        return {"gap_count": None, "gap_pct": None, "error": str(exc)}

    if result is None:
        return {"gap_count": 0, "gap_pct": 0.0}

    spine_count, actual_count, gap_count = result
    gap_pct = round(100.0 * gap_count / spine_count, 2) if spine_count > 0 else 0.0

    return {
        "gap_count": int(gap_count),
        "gap_pct": gap_pct,
        "spine_count": int(spine_count),
        "actual_count": int(actual_count),
    }


def profile_series(
    con: duckdb.DuckDBPyConnection,
    table: str,
    ts_col: str,
    val_col: str,
    id_col: str | None,
) -> dict:
    """Compute time-series statistics for the main series or across unique_ids."""
    try:
        stats = con.execute(
            f"""
            SELECT
                count(*) AS row_count,
                MIN(TRY_CAST("{ts_col}" AS TIMESTAMP)) AS min_date,
                MAX(TRY_CAST("{ts_col}" AS TIMESTAMP)) AS max_date,
                count(*) - count("{val_col}") AS null_count,
                round(100.0 * (count(*) - count("{val_col}")) / count(*), 2) AS null_pct,
                MIN(TRY_CAST("{val_col}" AS DOUBLE)) AS val_min,
                MAX(TRY_CAST("{val_col}" AS DOUBLE)) AS val_max,
                AVG(TRY_CAST("{val_col}" AS DOUBLE)) AS val_mean,
                STDDEV(TRY_CAST("{val_col}" AS DOUBLE)) AS val_std,
                sum(CASE WHEN TRY_CAST("{val_col}" AS DOUBLE) = 0 THEN 1 ELSE 0 END) AS zero_count
            FROM {table}
            """
        ).fetchone()
    except Exception as exc:
        return {"error": str(exc)}

    row_count, min_date, max_date, null_count, null_pct, val_min, val_max, val_mean, val_std, zero_count = stats

    n_series = 1
    if id_col:
        try:
            n_series = con.execute(f'SELECT count(DISTINCT "{id_col}") FROM {table}').fetchone()[0]
        except Exception:
            n_series = None

    zero_pct = round(100.0 * (zero_count or 0) / row_count, 2) if row_count else 0.0

    return {
        "row_count": int(row_count) if row_count else 0,
        "n_series": n_series,
        "date_range": {
            "start": str(min_date) if min_date else None,
            "end": str(max_date) if max_date else None,
        },
        "null_count": int(null_count) if null_count else 0,
        "null_pct": float(null_pct) if null_pct is not None else 0.0,
        "zero_pct": zero_pct,
        "value_stats": {
            "min": float(val_min) if val_min is not None else None,
            "max": float(val_max) if val_max is not None else None,
            "mean": round(float(val_mean), 4) if val_mean is not None else None,
            "std": round(float(val_std), 4) if val_std is not None else None,
        },
    }


def compute_suitability(profile: dict, inferred_freq: str, gap_info: dict) -> dict[str, dict]:
    """Evaluate model suitability based on series profile."""
    row_count = profile.get("row_count", 0)
    null_pct = profile.get("null_pct", 0.0)
    zero_pct = profile.get("zero_pct", 0.0)
    n_series = profile.get("n_series", 1)
    gap_pct = gap_info.get("gap_pct") or 0.0

    suitability = {}

    for model, min_hist in MODEL_MIN_HISTORY.items():
        issues = []
        if row_count < min_hist:
            issues.append(f"Insufficient history ({row_count} steps; minimum {min_hist})")
        if null_pct > 30:
            issues.append(f"High null rate ({null_pct}%) — impute before inference")
        if gap_pct > 20 and model == "Chronos-Bolt-Small":
            issues.append(f"High gap rate ({gap_pct}%) — Chronos raises error on NaN; fill gaps first")
        if gap_pct > 20 and model == "Lag-Llama":
            issues.append(f"High gap rate ({gap_pct}%) — Lag-Llama requires imputed series")
        if n_series and n_series > 1 and model == "TimesFM 2.5":
            issues.append(f"Multi-series ({n_series} series) — TimesFM 2.5 requires looping per series")
        if inferred_freq == "unknown":
            issues.append("Could not infer frequency — specify --freq flag")

        suitability[model] = {
            "suitable": len(issues) == 0,
            "reason": "; ".join(issues) if issues else "No blockers detected",
        }

    return suitability


def recommend_model(suitability: dict, profile: dict, inferred_freq: str) -> tuple[str, str]:
    """Select the best model based on suitability scores and profile signals."""
    suitable_models = [m for m, s in suitability.items() if s["suitable"]]

    if not suitable_models:
        return "none", "No suitable model — resolve blockers listed in model_suitability"

    zero_pct = profile.get("zero_pct", 0.0)
    row_count = profile.get("row_count", 0)

    # Sparse/intermittent demand → Lag-Llama
    if zero_pct > 30 and "Lag-Llama" in suitable_models:
        return "Lag-Llama", f"High zero rate ({zero_pct}%) suggests intermittent demand; Lag-Llama handles sparse series"

    # Long history → TimesFM for maximum context utilization
    if row_count > 500 and "TimesFM 2.5" in suitable_models:
        return "TimesFM 2.5", f"Large context ({row_count} steps); TimesFM 2.5 leverages full 16K context window"

    # Default: Chronos-Bolt-Small (CPU-friendly, probabilistic)
    if "Chronos-Bolt-Small" in suitable_models:
        return "Chronos-Bolt-Small", "Default choice: probabilistic, CPU-friendly, fast inference"

    return suitable_models[0], "First suitable model"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Time-series profiler for TSFM model selection. "
                    "Reads CSV or Parquet files and outputs a JSON profile with "
                    "model suitability ratings."
    )
    parser.add_argument("input_path", help="Path to input file (CSV or Parquet)")
    parser.add_argument("output_path", help="Path for output JSON file")
    parser.add_argument("--timestamp-col", default=None, help="Name of timestamp column (auto-detect if omitted)")
    parser.add_argument("--value-col", default=None, help="Name of value/target column (auto-detect if omitted)")
    parser.add_argument("--id-col", default=None, help="Name of series identifier column (optional)")
    parser.add_argument("--freq", default=None, help="Override frequency inference (H, D, W, M)")
    parser.add_argument(
        "--include-sample",
        type=int,
        default=0,
        metavar="N",
        help="Include N sample rows in output (Tier 2+ mode)",
    )

    args = parser.parse_args()

    # Validate input file
    if not os.path.isfile(args.input_path):
        print(f"ERROR: Input file not found: {args.input_path}", file=sys.stderr)
        sys.exit(1)

    # Validate output directory
    output_dir = os.path.dirname(args.output_path)
    if output_dir and not os.path.isdir(output_dir):
        print(f"ERROR: Output directory does not exist: {output_dir}", file=sys.stderr)
        print(f"Create it with: mkdir -p {output_dir}", file=sys.stderr)
        sys.exit(1)

    # Validate user-provided paths don't contain dangerous patterns
    for path_arg in [args.input_path, args.output_path]:
        if any(c in path_arg for c in ["..", "~", "$", "`", ";", "&", "|"]):
            print(f"ERROR: Invalid characters in path: {path_arg}", file=sys.stderr)
            sys.exit(1)

    try:
        con = duckdb.connect(":memory:")
        table = read_file(con, args.input_path)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"ERROR: Failed to read file: {exc}", file=sys.stderr)
        sys.exit(1)

    # Detect timestamp column
    ts_col = args.timestamp_col
    if ts_col is None:
        detected_ts_cols = detect_timestamp_columns(con, table)
        if not detected_ts_cols:
            print("ERROR: No timestamp column detected. Use --timestamp-col to specify one.", file=sys.stderr)
            sys.exit(1)
        ts_col = detected_ts_cols[0]
        if len(detected_ts_cols) > 1:
            print(f"INFO: Multiple timestamp columns found: {detected_ts_cols}. Using: {ts_col}", file=sys.stderr)

    # Detect value column (first numeric column that is not the timestamp)
    val_col = args.value_col
    if val_col is None:
        schema = con.execute(f"DESCRIBE {table}").fetchall()
        numeric_cols = [
            row[0] for row in schema
            if any(t in row[1].upper() for t in ("INTEGER", "BIGINT", "DOUBLE", "FLOAT", "DECIMAL", "HUGEINT"))
            and row[0] != ts_col
        ]
        if not numeric_cols:
            print("ERROR: No numeric value column detected. Use --value-col to specify one.", file=sys.stderr)
            sys.exit(1)
        val_col = numeric_cols[0]
        print(f"INFO: Using value column: {val_col}", file=sys.stderr)

    # File metadata
    file_metadata = {
        "filename": os.path.basename(args.input_path),
        "file_size_bytes": os.path.getsize(args.input_path),
        "format": Path(args.input_path).suffix.lower().lstrip("."),
        "timestamp_col": ts_col,
        "value_col": val_col,
        "id_col": args.id_col,
    }

    # Infer frequency
    inferred_freq = args.freq or infer_frequency(con, table, ts_col)

    # Profile series
    ts_profile = profile_series(con, table, ts_col, val_col, args.id_col)
    ts_profile["inferred_freq"] = inferred_freq
    ts_profile["freq_source"] = "user" if args.freq else "inferred"

    # Detect gaps
    gap_info = detect_gaps(con, table, ts_col, inferred_freq)
    ts_profile["gaps"] = gap_info

    # Model suitability
    model_suitability = compute_suitability(ts_profile, inferred_freq, gap_info)

    # Issues list
    issues = []
    if ts_profile.get("null_pct", 0) > 10:
        issues.append({"type": "warning", "message": f"Null rate {ts_profile['null_pct']}% — consider imputation"})
    if gap_info.get("gap_pct") and gap_info["gap_pct"] > 5:
        issues.append({"type": "warning", "message": f"Gap rate {gap_info['gap_pct']}% — fill gaps before inference"})
    if ts_profile.get("row_count", 0) < 30:
        issues.append({"type": "blocker", "message": "Fewer than 30 data points — insufficient for reliable forecasting"})
    if inferred_freq == "unknown":
        issues.append({"type": "warning", "message": "Could not infer frequency — use --freq flag"})

    # Recommendation
    recommended_model, recommendation_reason = recommend_model(model_suitability, ts_profile, inferred_freq)

    # Assemble output
    result: dict = {
        "file_metadata": file_metadata,
        "time_series_profile": ts_profile,
        "model_suitability": model_suitability,
        "issues": issues,
        "recommended_model": recommended_model,
        "recommended_model_reason": recommendation_reason,
    }

    # Optional sample (Tier 2+ mode)
    if args.include_sample > 0:
        try:
            sample_rows = con.execute(
                f"""
                SELECT * FROM {table}
                ORDER BY TRY_CAST("{ts_col}" AS TIMESTAMP)
                LIMIT {args.include_sample}
                """
            ).fetchdf().to_dict(orient="records")
            result["sample_rows"] = sample_rows
        except Exception as exc:
            result["sample_rows_error"] = str(exc)

    con.close()

    # Write output
    try:
        with open(args.output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False, default=str)
        print(f"Profile written to: {args.output_path}")
        print(f"  Rows: {ts_profile.get('row_count', 'unknown')}")
        print(f"  Inferred frequency: {inferred_freq}")
        print(f"  Gaps: {gap_info.get('gap_count', 'unknown')} ({gap_info.get('gap_pct', '?')}%)")
        print(f"  Recommended model: {recommended_model}")
        if issues:
            print(f"  Issues: {len(issues)}")
    except OSError as exc:
        print(f"ERROR: Failed to write output file: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
