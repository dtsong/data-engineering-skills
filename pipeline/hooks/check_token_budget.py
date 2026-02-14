#!/usr/bin/env python3
"""Check word/token counts against budgets per file type."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import (
    find_repo_root, load_budgets, classify_file,
    count_body_words, estimate_tokens, get_budget_for_type, is_excluded,
)


def check_file(filepath, repo_root, budgets):
    """Check a single file against its budget. Returns (passed, message)."""
    if is_excluded(filepath, repo_root):
        return True, None

    file_type = classify_file(filepath, repo_root)
    if file_type is None:
        return True, None

    # Check for per-file override
    rel_path = os.path.relpath(filepath, repo_root)
    overrides = budgets.get("overrides", {})
    if rel_path in overrides:
        max_tokens = overrides[rel_path].get("max_tokens") if isinstance(overrides[rel_path], dict) else overrides[rel_path]
        word_count = count_body_words(filepath)
        est_tokens = estimate_tokens(word_count, budgets)
        if est_tokens > max_tokens:
            return False, (
                f"FAIL: {rel_path} ({file_type}, override) — "
                f"{word_count} words, ~{est_tokens} tokens "
                f"(max: {max_tokens} tokens)"
            )
        return True, None

    max_words, max_tokens = get_budget_for_type(file_type, budgets)
    if max_words is None:
        return True, None

    word_count = count_body_words(filepath)
    est_tokens = estimate_tokens(word_count, budgets)

    if word_count > max_words or est_tokens > max_tokens:
        pct_over = ((word_count / max_words) - 1) * 100 if max_words else 0
        return False, (
            f"FAIL: {rel_path} ({file_type}) — "
            f"{word_count} words (~{est_tokens} tokens), "
            f"budget: {max_words} words ({max_tokens} tokens) "
            f"[{pct_over:+.0f}% over]"
        )

    return True, (
        f"OK: {rel_path} ({file_type}) — "
        f"{word_count} words (~{est_tokens} tokens)"
    )


def main():
    repo_root = find_repo_root()
    budgets = load_budgets(repo_root)
    failed = False

    for filepath in sys.argv[1:]:
        filepath = os.path.abspath(filepath)
        passed, msg = check_file(filepath, repo_root, budgets)
        if msg:
            print(msg)
        if not passed:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
