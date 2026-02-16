#!/usr/bin/env python3
"""Sample extractor for consulting engagements.

Extracts a reviewable sample from source files for Tier 2+ access.

# SECURITY: Extracts sample data for consultant review before AI access

Usage:
    python scripts/sample_extractor.py <input_path> --sample-size 50 --output <dir> \
        [--strategy first|random|stratified] [--stratify-column COL] [--seed SEED]

Dependencies:
    pip install openpyxl chardet
"""

import argparse
import csv
import json
import os
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

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

# PII column name patterns (shared with schema_profiler.py)
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


def check_pii(column_name: str) -> bool:
    """Check if a column name matches PII patterns."""
    for pattern in PII_PATTERNS:
        if pattern.search(column_name):
            return True
    return False


def detect_encoding(file_path: str) -> str:
    """Detect file encoding using chardet."""
    with open(file_path, "rb") as f:
        raw = f.read(10000)
    result = chardet.detect(raw)
    return result.get("encoding", "utf-8") or "utf-8"


def read_csv_file(file_path: str) -> tuple:
    """Read CSV file, return headers and rows."""
    encoding = detect_encoding(file_path)
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
        rows = [row for row in reader]
    return headers, rows


def read_excel_file(file_path: str) -> tuple:
    """Read Excel file, return headers and rows."""
    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    sheet = wb.active
    all_rows = []
    for row in sheet.iter_rows(values_only=True):
        all_rows.append([str(v) if v is not None else "" for v in row])
    wb.close()
    if not all_rows:
        return [], []
    headers = all_rows[0]
    rows = all_rows[1:]
    return headers, rows


def sample_first(rows: list, n: int) -> list:
    """Return the first N rows."""
    return rows[:n]


def sample_random(rows: list, n: int, seed: int) -> list:
    """Return N random rows with reproducible seed."""
    rng = random.Random(seed)
    if n >= len(rows):
        return list(rows)
    return rng.sample(rows, n)


def sample_stratified(rows: list, headers: list, n: int, stratify_column: str, seed: int) -> list:
    """Return N rows stratified by a column value."""
    if stratify_column not in headers:
        print(
            f"ERROR: Stratify column '{stratify_column}' not found in headers: {headers}",
            file=sys.stderr,
        )
        sys.exit(1)

    col_idx = headers.index(stratify_column)
    groups = defaultdict(list)
    for row in rows:
        key = row[col_idx] if col_idx < len(row) else ""
        groups[key].append(row)

    rng = random.Random(seed)
    num_groups = len(groups)
    per_group = max(1, n // num_groups)
    remainder = n - (per_group * num_groups)

    sampled = []
    for group_key in sorted(groups.keys()):
        group_rows = groups[group_key]
        take = min(per_group, len(group_rows))
        sampled.extend(rng.sample(group_rows, take) if take < len(group_rows) else group_rows[:take])

    # Distribute remainder across groups that have more rows
    if remainder > 0:
        remaining_rows = []
        for group_key in sorted(groups.keys()):
            group_rows = groups[group_key]
            already_taken = min(per_group, len(group_rows))
            remaining_rows.extend(group_rows[already_taken:])
        if remaining_rows:
            extra = rng.sample(remaining_rows, min(remainder, len(remaining_rows)))
            sampled.extend(extra)

    return sampled[:n]


def main():
    parser = argparse.ArgumentParser(
        description="Sample extractor for consulting engagements. "
                    "Extracts a reviewable sample from source files for Tier 2+ access."
    )
    parser.add_argument("input_path", help="Path to input file (CSV or Excel)")
    parser.add_argument("--sample-size", type=int, default=50, help="Number of rows to sample (default: 50)")
    parser.add_argument("--output", required=True, help="Output directory for sample files")
    parser.add_argument(
        "--strategy",
        choices=["first", "random", "stratified"],
        default="first",
        help="Sampling strategy (default: first)",
    )
    parser.add_argument("--stratify-column", help="Column to stratify by (required if strategy=stratified)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")

    args = parser.parse_args()

    # Validate input
    if not os.path.isfile(args.input_path):
        print(f"ERROR: Input file not found: {args.input_path}", file=sys.stderr)
        sys.exit(1)

    if args.strategy == "stratified" and not args.stratify_column:
        print("ERROR: --stratify-column is required when strategy=stratified", file=sys.stderr)
        sys.exit(1)

    # Create output directory if needed
    os.makedirs(args.output, exist_ok=True)

    # Read input file
    ext = Path(args.input_path).suffix.lower()
    if ext == ".csv":
        headers, rows = read_csv_file(args.input_path)
    elif ext in (".xlsx", ".xls"):
        headers, rows = read_excel_file(args.input_path)
    else:
        print(f"ERROR: Unsupported file format: {ext}. Supported: .csv, .xlsx, .xls", file=sys.stderr)
        sys.exit(1)

    if not headers:
        print("ERROR: File has no headers or is empty.", file=sys.stderr)
        sys.exit(1)

    # Detect PII columns
    pii_columns = [h for h in headers if check_pii(h)]
    if pii_columns:
        print(f"WARNING: PII columns detected: {', '.join(pii_columns)}", file=sys.stderr)
        print("WARNING: Review sample output and mask PII before sharing.", file=sys.stderr)

    # Sample rows
    if args.strategy == "first":
        sampled = sample_first(rows, args.sample_size)
    elif args.strategy == "random":
        sampled = sample_random(rows, args.sample_size, args.seed)
    elif args.strategy == "stratified":
        sampled = sample_stratified(rows, headers, args.sample_size, args.stratify_column, args.seed)
    else:
        sampled = sample_first(rows, args.sample_size)

    # Write sample CSV
    base_name = Path(args.input_path).stem
    output_csv = os.path.join(args.output, f"{base_name}_sample.csv")
    try:
        with open(output_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            writer.writerows(sampled)
    except IOError as e:
        print(f"ERROR: Failed to write sample CSV: {e}", file=sys.stderr)
        sys.exit(1)

    # Write metadata JSON
    output_meta = os.path.join(args.output, f"{base_name}_sample_metadata.json")
    metadata = {
        "source_file": os.path.basename(args.input_path),
        "source_row_count": len(rows),
        "sample_size": len(sampled),
        "strategy": args.strategy,
        "seed": args.seed if args.strategy in ("random", "stratified") else None,
        "stratify_column": args.stratify_column if args.strategy == "stratified" else None,
        "pii_columns_detected": pii_columns,
        "output_file": os.path.basename(output_csv),
    }
    try:
        with open(output_meta, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
    except IOError as e:
        print(f"ERROR: Failed to write metadata JSON: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Sample extracted: {output_csv}")
    print(f"  Source rows: {len(rows)}")
    print(f"  Sample rows: {len(sampled)}")
    print(f"  Strategy: {args.strategy}")
    if pii_columns:
        print(f"  WARNING: PII columns detected: {', '.join(pii_columns)}")
    print(f"Metadata: {output_meta}")


if __name__ == "__main__":
    main()
