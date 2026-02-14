#!/usr/bin/env python3
"""Generate markdown budget report for all skills."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))
from _utils import (
    find_repo_root, load_budgets, classify_file,
    count_body_words, estimate_tokens, get_budget_for_type,
)


def collect_files(repo_root):
    """Collect all governed files."""
    files = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in (
            ".git", "node_modules", "pipeline", ".github",
        )]
        rel_dir = os.path.relpath(dirpath, repo_root)
        if rel_dir.startswith("eval-cases"):
            continue
        for f in filenames:
            full = os.path.join(dirpath, f)
            if f == "SKILL.md" or (f.endswith(".md") and "/references/" in full):
                files.append(full)
    return sorted(files)


def main():
    repo_root = find_repo_root()
    budgets = load_budgets(repo_root)
    files = collect_files(repo_root)

    rows = []
    for filepath in files:
        file_type = classify_file(filepath, repo_root)
        if file_type is None:
            continue

        rel_path = os.path.relpath(filepath, repo_root)
        words = count_body_words(filepath)
        tokens = estimate_tokens(words, budgets)
        max_words, max_tokens = get_budget_for_type(file_type, budgets)

        if max_words and words > max_words:
            pct = ((words / max_words) - 1) * 100
            status = f"OVER (+{pct:.0f}%)"
        else:
            status = "OK"

        rows.append((rel_path, file_type, words, tokens, max_words or 0, max_tokens or 0, status))

    # Markdown table
    print("## Skill Budget Report")
    print()
    print("| File | Type | Words | ~Tokens | Budget (words) | Budget (tokens) | Status |")
    print("|------|------|------:|--------:|---------------:|----------------:|--------|")
    for rel_path, file_type, words, tokens, max_w, max_t, status in rows:
        print(f"| {rel_path} | {file_type} | {words} | {tokens} | {max_w} | {max_t} | {status} |")

    print()

    # Summary
    over = sum(1 for r in rows if "OVER" in r[6])
    ok = sum(1 for r in rows if r[6] == "OK")
    print(f"**{ok}** file(s) within budget, **{over}** file(s) over budget.")


if __name__ == "__main__":
    main()
