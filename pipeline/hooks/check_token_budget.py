#!/usr/bin/env python3
"""Check word/token counts against budget targets. WARN tier — always exits 0."""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import (
    find_repo_root, load_budgets, classify_file,
    count_body_words, estimate_tokens, get_budget_for_type, is_excluded,
)


def check_file(filepath, repo_root, budgets):
    """Check a single file against its budget target. Returns message."""
    if is_excluded(filepath, repo_root):
        return None

    file_type = classify_file(filepath, repo_root)
    if file_type is None:
        return None

    rel_path = os.path.relpath(filepath, repo_root)

    # Check for per-skill override
    overrides = budgets.get("overrides", {})
    override_key = None
    for key in overrides:
        if rel_path.startswith(key) or rel_path == key:
            override_key = key
            break

    max_words, max_tokens = get_budget_for_type(file_type, budgets)
    if override_key and isinstance(overrides[override_key], dict):
        override = overrides[override_key]
        words_key = f"{file_type}_max_words"
        tokens_key = f"{file_type}_max_tokens"
        if words_key in override:
            max_words = override[words_key]
        if tokens_key in override:
            max_tokens = override[tokens_key]

    if max_words is None:
        return None

    word_count = count_body_words(filepath)
    est_tokens = estimate_tokens(word_count)

    threshold_90 = int(max_words * 0.9)

    if word_count > max_words:
        pct_over = ((word_count / max_words) - 1) * 100
        return (
            f"WARN: {rel_path} ({file_type}) — "
            f"{word_count} words (~{est_tokens} tokens), "
            f"target: {max_words} words ({max_tokens} tokens) "
            f"[+{pct_over:.0f}% over target]\n"
            f"  To document this override, add an entry to "
            f"pipeline/config/budgets.json with your rationale."
        )
    elif word_count >= threshold_90:
        headroom = max_words - word_count
        return (
            f"INFO: {rel_path} ({file_type}) — "
            f"{word_count} words (~{est_tokens} tokens), "
            f"target: {max_words} words — {headroom} words headroom remaining"
        )
    else:
        return (
            f"OK: {rel_path} ({file_type}) — "
            f"{word_count} words (~{est_tokens} tokens)"
        )


def main():
    repo_root = find_repo_root()
    budgets = load_budgets(repo_root)

    for filepath in sys.argv[1:]:
        filepath = os.path.abspath(filepath)
        msg = check_file(filepath, repo_root, budgets)
        if msg:
            print(msg)

    # WARN tier — always exit 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
