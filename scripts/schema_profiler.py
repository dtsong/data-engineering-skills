#!/usr/bin/env python3
"""Schema profiler for consulting engagements.

Reads Excel and CSV files, extracts column-level statistics and identifies
potential data quality issues.

# SECURITY: Reads local files only, no network access

Usage:
    python scripts/schema_profiler.py <input_path> <output_path> [--include-sample N]

Dependencies:
    pip install openpyxl chardet
"""

import argparse
import csv
import io
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

# Attempt imports with helpful error messages
try:
    import chardet
except ImportError:
    print("ERROR: chardet is required. Install with: pip install chardet", file=sys.stderr)
    sys.exit(1)

try:
    import openpyxl
except ImportError:
    print("ERROR: openpyxl is required. Install with: pip install openpyxl", file=sys.stderr)
    sys.exit(1)

# PII column name patterns
# SECURITY: Used to flag columns that may contain personally identifiable information
PII_PATTERNS = [
    re.compile(r"\bssn\b", re.IGNORECASE),
    re.compile(r"\bsocial.?security\b", re.IGNORECASE),
    re.compile(r"\bdob\b", re.IGNORECASE),
    re.compile(r"\bdate.?of.?birth\b", re.IGNORECASE),
    re.compile(r"\bemail\b", re.IGNORECASE),
    re.compile(r"\bphone\b", re.IGNORECASE),
    re.compile(r"\baddress\b", re.IGNORECASE),
    re.compile(r"\bzip.?code\b", re.IGNORECASE),
    re.compile(r"\bpassport\b", re.IGNORECASE),
    re.compile(r"\bdriver.?licen[sc]e\b", re.IGNORECASE),
]

# Date format patterns for inconsistency detection
DATE_PATTERNS = [
    (re.compile(r"^\d{4}-\d{2}-\d{2}$"), "YYYY-MM-DD"),
    (re.compile(r"^\d{2}/\d{2}/\d{4}$"), "MM/DD/YYYY"),
    (re.compile(r"^\d{2}-\d{2}-\d{4}$"), "MM-DD-YYYY"),
    (re.compile(r"^\d{2}\.\d{2}\.\d{4}$"), "DD.MM.YYYY"),
    (re.compile(r"^\d{4}/\d{2}/\d{2}$"), "YYYY/MM/DD"),
]


def detect_encoding(file_path: str) -> str:
    """Detect file encoding using chardet."""
    with open(file_path, "rb") as f:
        raw = f.read(10000)  # Read first 10KB for detection
    result = chardet.detect(raw)
    return result.get("encoding", "utf-8") or "utf-8"


def infer_type(value: str) -> str:
    """Infer the data type of a string value."""
    if value is None or str(value).strip() == "":
        return "null"
    val = str(value).strip()
    # Integer check
    try:
        int(val)
        return "integer"
    except (ValueError, OverflowError):
        pass
    # Float check
    try:
        float(val)
        return "float"
    except (ValueError, OverflowError):
        pass
    # Boolean check
    if val.lower() in ("true", "false", "yes", "no", "1", "0"):
        return "boolean"
    # Date check
    for pattern, _ in DATE_PATTERNS:
        if pattern.match(val):
            return "date"
    return "string"


def detect_date_formats(values: list) -> list:
    """Detect date format patterns present in a list of values."""
    formats_found = set()
    for val in values:
        if val is None:
            continue
        val_str = str(val).strip()
        for pattern, fmt_name in DATE_PATTERNS:
            if pattern.match(val_str):
                formats_found.add(fmt_name)
    return list(formats_found)


def check_pii(column_name: str) -> bool:
    """Check if a column name matches PII patterns."""
    for pattern in PII_PATTERNS:
        if pattern.search(column_name):
            return True
    return False


def profile_column(name: str, values: list, include_sample: int = 0) -> dict:
    """Profile a single column and return statistics."""
    total = len(values)
    non_null = [v for v in values if v is not None and str(v).strip() != ""]
    null_count = total - len(non_null)
    null_pct = round((null_count / total) * 100, 2) if total > 0 else 0.0

    str_values = [str(v).strip() for v in non_null]
    distinct_count = len(set(str_values)) if str_values else 0
    cardinality_ratio = round(distinct_count / total, 4) if total > 0 else 0.0

    lengths = [len(s) for s in str_values]
    min_length = min(lengths) if lengths else 0
    max_length = max(lengths) if lengths else 0

    # Infer types
    type_counts = Counter(infer_type(v) for v in non_null)
    inferred_type = type_counts.most_common(1)[0][0] if type_counts else "unknown"

    col_profile = {
        "name": name,
        "inferred_type": inferred_type,
        "null_count": null_count,
        "null_pct": null_pct,
        "distinct_count": distinct_count,
        "cardinality_ratio": cardinality_ratio,
        "min_length": min_length,
        "max_length": max_length,
    }

    if include_sample > 0 and str_values:
        col_profile["sample_values"] = str_values[:include_sample]

    return col_profile, type_counts


def detect_issues(name: str, col_profile: dict, type_counts: Counter, values: list) -> list:
    """Detect data quality issues for a column."""
    issues = []

    # High null rate
    if col_profile["null_pct"] > 50:
        issues.append({
            "column": name,
            "issue_type": "high_null_rate",
            "severity": "critical",
            "detail": f"Null rate is {col_profile['null_pct']}% (>{50}% threshold)",
        })

    # Mixed types
    non_null_types = {k: v for k, v in type_counts.items() if k != "null"}
    if len(non_null_types) > 1:
        total_typed = sum(non_null_types.values())
        dominant_type = max(non_null_types, key=non_null_types.get)
        dominant_pct = (non_null_types[dominant_type] / total_typed) * 100
        if dominant_pct < 95:
            type_breakdown = ", ".join(f"{k}: {v}" for k, v in non_null_types.items())
            issues.append({
                "column": name,
                "issue_type": "mixed_types",
                "severity": "warning",
                "detail": f"Multiple types detected: {type_breakdown}",
            })

    # PII detection
    if check_pii(name):
        issues.append({
            "column": name,
            "issue_type": "pii_detected",
            "severity": "warning",
            "detail": f"Column name matches PII pattern: {name}",
        })

    # Date format inconsistency
    date_formats = detect_date_formats(values)
    if len(date_formats) > 1:
        issues.append({
            "column": name,
            "issue_type": "date_format_inconsistency",
            "severity": "warning",
            "detail": f"Multiple date formats detected: {', '.join(date_formats)}",
        })

    # Constant column
    if col_profile["distinct_count"] == 1 and col_profile["null_pct"] < 100:
        issues.append({
            "column": name,
            "issue_type": "constant_column",
            "severity": "info",
            "detail": "Column contains only one distinct value",
        })

    return issues


def read_csv(file_path: str) -> tuple:
    """Read a CSV file and return headers and rows."""
    encoding = detect_encoding(file_path)
    encoding_issue = encoding.lower() not in ("utf-8", "ascii", "utf-8-sig")

    with open(file_path, "r", encoding=encoding, errors="replace") as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
            delimiter = dialect.delimiter
        except csv.Error:
            delimiter = ","

        reader = csv.reader(f, delimiter=delimiter)
        headers = next(reader, [])
        rows = list(reader)

    metadata = {
        "filename": os.path.basename(file_path),
        "encoding": encoding,
        "row_count": len(rows),
        "column_count": len(headers),
        "delimiter": delimiter,
        "file_size_bytes": os.path.getsize(file_path),
    }

    if encoding_issue:
        metadata["encoding_warning"] = f"Non-UTF-8 encoding detected: {encoding}"

    return headers, rows, metadata


def read_excel(file_path: str) -> tuple:
    """Read an Excel file and return headers and rows."""
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    sheet = wb.active
    sheet_name = sheet.title

    all_rows = []
    for row in sheet.iter_rows(values_only=True):
        all_rows.append(list(row))

    wb.close()

    if not all_rows:
        return [], [], {"filename": os.path.basename(file_path), "row_count": 0, "column_count": 0}

    headers = [str(h) if h is not None else f"column_{i}" for i, h in enumerate(all_rows[0])]
    rows = all_rows[1:]

    metadata = {
        "filename": os.path.basename(file_path),
        "encoding": "xlsx",
        "row_count": len(rows),
        "column_count": len(headers),
        "sheet_name": sheet_name,
        "file_size_bytes": os.path.getsize(file_path),
    }

    return headers, rows, metadata


def profile_file(file_path: str, include_sample: int = 0) -> dict:
    """Profile a single file and return the complete profile."""
    ext = Path(file_path).suffix.lower()

    if ext == ".csv":
        headers, rows, metadata = read_csv(file_path)
    elif ext in (".xlsx", ".xls"):
        headers, rows, metadata = read_excel(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}. Supported: .csv, .xlsx, .xls")

    if not headers:
        return {"file_metadata": metadata, "columns": [], "issues": []}

    columns = []
    all_issues = []

    for col_idx, col_name in enumerate(headers):
        values = [row[col_idx] if col_idx < len(row) else None for row in rows]
        col_profile, type_counts = profile_column(col_name, values, include_sample)
        columns.append(col_profile)
        issues = detect_issues(col_name, col_profile, type_counts, values)
        all_issues.extend(issues)

    # Encoding issue at file level
    if metadata.get("encoding_warning"):
        all_issues.append({
            "column": None,
            "issue_type": "encoding_issue",
            "severity": "warning",
            "detail": metadata["encoding_warning"],
        })

    return {
        "file_metadata": metadata,
        "columns": columns,
        "issues": all_issues,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Schema profiler for consulting engagements. "
                    "Reads Excel and CSV files, extracts column-level statistics "
                    "and identifies potential data quality issues."
    )
    parser.add_argument("input_path", help="Path to input file (CSV or Excel)")
    parser.add_argument("output_path", help="Path for output JSON file")
    parser.add_argument(
        "--include-sample",
        type=int,
        default=0,
        metavar="N",
        help="Include N sample values per column (Tier 2+ mode)",
    )

    args = parser.parse_args()

    # Validate input file exists
    if not os.path.isfile(args.input_path):
        print(f"ERROR: Input file not found: {args.input_path}", file=sys.stderr)
        sys.exit(1)

    # Validate output directory exists
    output_dir = os.path.dirname(args.output_path)
    if output_dir and not os.path.isdir(output_dir):
        print(f"ERROR: Output directory does not exist: {output_dir}", file=sys.stderr)
        print(f"Create it with: mkdir -p {output_dir}", file=sys.stderr)
        sys.exit(1)

    try:
        result = profile_file(args.input_path, args.include_sample)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to profile file: {e}", file=sys.stderr)
        sys.exit(1)

    # Write output
    try:
        with open(args.output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Profile written to: {args.output_path}")
        print(f"  Rows: {result['file_metadata']['row_count']}")
        print(f"  Columns: {result['file_metadata']['column_count']}")
        print(f"  Issues found: {len(result['issues'])}")
    except IOError as e:
        print(f"ERROR: Failed to write output file: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
