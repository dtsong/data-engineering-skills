#!/usr/bin/env python3
"""Check that specialist skills don't cross-reference each other."""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import find_repo_root, classify_file, is_excluded

# Match references to other skill directories
SKILL_DIR_PATTERN = re.compile(r"(?:^|[\s([\]])(\w+-skill)/", re.MULTILINE)


def find_all_skill_dirs(repo_root):
    """Find all top-level *-skill directories."""
    dirs = set()
    for entry in os.listdir(repo_root):
        if entry.endswith("-skill") and os.path.isdir(os.path.join(repo_root, entry)):
            dirs.add(entry)
    return dirs


def check_file(filepath, repo_root, skill_dirs):
    """Check for cross-skill references. Returns (passed, messages)."""
    if is_excluded(filepath, repo_root):
        return True, []

    file_type = classify_file(filepath, repo_root)
    if file_type not in ("specialist", "standalone"):
        return True, []

    rel_path = os.path.relpath(filepath, repo_root)

    # Determine which skill this file belongs to
    parts = rel_path.replace("\\", "/").split("/")
    own_skill = None
    for part in parts:
        if part.endswith("-skill"):
            own_skill = part
            break

    if own_skill is None:
        return True, []

    with open(filepath) as f:
        content = f.read()

    messages = []
    passed = True

    for match in SKILL_DIR_PATTERN.finditer(content):
        referenced_skill = match.group(1)
        if referenced_skill == own_skill:
            continue
        if referenced_skill not in skill_dirs:
            continue
        # shared-references is exempt
        if referenced_skill == "shared-references":
            continue

        messages.append(
            f"FAIL: {rel_path} — cross-references '{referenced_skill}/' "
            f"(use handoff protocol instead)"
        )
        passed = False

    if not messages:
        messages.append(f"OK: {rel_path} — no cross-skill references")

    return passed, messages


def main():
    repo_root = find_repo_root()
    skill_dirs = find_all_skill_dirs(repo_root)
    failed = False

    for filepath in sys.argv[1:]:
        filepath = os.path.abspath(filepath)
        passed, messages = check_file(filepath, repo_root, skill_dirs)
        for msg in messages:
            print(msg)
        if not passed:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
