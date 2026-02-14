#!/usr/bin/env python3
"""Check that referenced files exist on disk."""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import find_repo_root, is_excluded

# Match markdown links to local files (not URLs)
LOCAL_LINK_PATTERN = re.compile(
    r"\[.*?\]\((?!https?://|#)(.*?\.md)\)"
)


def check_file(filepath, repo_root):
    """Check all local references in a file. Returns (passed, messages)."""
    if is_excluded(filepath, repo_root):
        return True, []

    rel_path = os.path.relpath(filepath, repo_root)

    with open(filepath) as f:
        content = f.read()

    messages = []
    passed = True
    file_dir = os.path.dirname(filepath)

    for match in LOCAL_LINK_PATTERN.finditer(content):
        ref = match.group(1)
        # Resolve relative to the file's directory
        ref_path = os.path.normpath(os.path.join(file_dir, ref))
        if not os.path.exists(ref_path):
            messages.append(
                f"FAIL: {rel_path} — references '{ref}' which does not exist"
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
