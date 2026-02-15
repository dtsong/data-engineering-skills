#!/usr/bin/env python3
"""Compare eval results against baselines.

Placeholder — will be implemented when eval baselines are established.
"""

import json
import os
import sys


def main():
    root = os.environ.get("REPO_ROOT") or os.popen(
        "git rev-parse --show-toplevel 2>/dev/null"
    ).read().strip() or os.getcwd()

    results_dir = os.path.join(root, "eval-results")
    baselines_dir = os.path.join(root, "eval-baselines")

    if not os.path.isdir(results_dir):
        print("No eval-results/ directory found. Skipping regression check.")
        return 0

    if not os.path.isdir(baselines_dir):
        print("No eval-baselines/ directory found. Skipping regression check.")
        print("Run evaluations and save baselines to enable regression detection.")
        return 0

    print("=== Regression Check ===")
    print()
    print("Placeholder: regression checking will be implemented when baselines exist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
