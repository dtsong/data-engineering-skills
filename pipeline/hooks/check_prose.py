#!/usr/bin/env python3
"""Check for explanatory prose patterns in procedure sections (warning only)."""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import find_repo_root, is_excluded

PROSE_PATTERNS = [
    (re.compile(r"^\s*This is because\b", re.IGNORECASE), "starts with 'This is because...'"),
    (re.compile(r"^\s*The reason for\b", re.IGNORECASE), "starts with 'The reason for...'"),
    (re.compile(r"^\s*Note that\b", re.IGNORECASE), "starts with 'Note that...'"),
    (re.compile(r"should be done\b", re.IGNORECASE), "passive voice ('should be done')"),
    (re.compile(r"needs to be\b", re.IGNORECASE), "passive voice ('needs to be')"),
]


def in_procedure_section(lines, line_idx):
    """Heuristic: check if a line is inside a procedure/steps section."""
    for i in range(line_idx, -1, -1):
        line = lines[i].strip()
        if re.match(r"^#{1,3}\s+", line):
            heading_lower = line.lower()
            return any(kw in heading_lower for kw in [
                "procedure", "steps", "process", "workflow", "how to",
                "instructions", "implementation",
            ])
    return False


def check_file(filepath, repo_root):
    """Check for prose patterns. Returns messages (warnings only)."""
    if is_excluded(filepath, repo_root):
        return []

    if not os.path.basename(filepath) == "SKILL.md":
        return []

    rel_path = os.path.relpath(filepath, repo_root)

    with open(filepath) as f:
        lines = f.readlines()

    messages = []
    for idx, line in enumerate(lines):
        if not in_procedure_section(lines, idx):
            continue
        for pattern, desc in PROSE_PATTERNS:
            if pattern.search(line):
                messages.append(
                    f"WARN: {rel_path}:{idx + 1} — prose pattern: {desc}"
                )

    return messages


def main():
    repo_root = find_repo_root()

    for filepath in sys.argv[1:]:
        filepath = os.path.abspath(filepath)
        messages = check_file(filepath, repo_root)
        for msg in messages:
            print(msg)

    # Always exit 0 — warnings only
    return 0


if __name__ == "__main__":
    sys.exit(main())
