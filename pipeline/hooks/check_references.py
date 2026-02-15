#!/usr/bin/env python3
"""Check that referenced files exist on disk. HARD tier."""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import find_repo_root, is_excluded

# Match various reference patterns to local files
REFERENCE_PATTERNS = [
    # Markdown links to local .md files (not URLs)
    re.compile(r"\[.*?\]\((?!https?://|#)(.*?\.md)\)"),
    # Read `path` patterns
    re.compile(r"Read\s+`([^`]+\.\w+)`"),
    # Load `path` patterns
    re.compile(r"Load\s+`([^`]+\.\w+)`"),
    # at `path.md` patterns
    re.compile(r"at\s+`([^`]+\.md)`"),
    # references/*.md and scripts/*.* patterns in tables/lists
    re.compile(r"`(references/[^`]+\.md)`"),
    re.compile(r"`(scripts/[^`]+\.\w+)`"),
]


def check_file(filepath, repo_root):
    """Check all local references in a file. Returns (passed, messages)."""
    if is_excluded(filepath, repo_root):
        return True, []

    rel_path = os.path.relpath(filepath, repo_root)

    with open(filepath) as f:
        content = f.read()

    lines = content.split("\n")
    messages = []
    passed = True
    file_dir = os.path.dirname(filepath)
    seen = set()

    for line_num, line in enumerate(lines, 1):
        for pattern in REFERENCE_PATTERNS:
            for match in pattern.finditer(line):
                ref = match.group(1)
                # Skip absolute paths and URLs
                if ref.startswith("/") or "://" in ref:
                    continue
                # Deduplicate
                if ref in seen:
                    continue
                seen.add(ref)
                # Resolve relative to the file's directory
                ref_path = os.path.normpath(os.path.join(file_dir, ref))
                if not os.path.exists(ref_path):
                    messages.append(
                        f"FAIL: {rel_path}:{line_num} — "
                        f"references '{ref}' which does not exist"
                    )
                    passed = False

    if not messages:
        messages.append(f"OK: {rel_path} — all references valid")

    return passed, messages


def main():
    repo_root = find_repo_root()
    failed = False

    for filepath in sys.argv[1:]:
        filepath = os.path.abspath(filepath)
        passed, messages = check_file(filepath, repo_root)
        for msg in messages:
            print(msg)
        if not passed:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
