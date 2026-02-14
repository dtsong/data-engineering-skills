#!/usr/bin/env python3
"""Check for explanatory prose patterns in procedure sections. WARN tier — always exits 0."""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import find_repo_root, is_excluded

PROSE_PATTERNS = [
    (re.compile(r"\bit is important to\b", re.IGNORECASE), "filler: 'it is important to' — just state the action"),
    (re.compile(r"\bit's important to\b", re.IGNORECASE), "filler: 'it's important to' — just state the action"),
    (re.compile(r"\byou should\b", re.IGNORECASE), "conversational: 'you should' — use imperative"),
    (re.compile(r"\byou may want to\b", re.IGNORECASE), "conversational: 'you may want to' — use imperative"),
    (re.compile(r"\byou might want to\b", re.IGNORECASE), "conversational: 'you might want to' — use imperative"),
    (re.compile(r"\bthis is because\b", re.IGNORECASE), "explanatory: 'this is because' — use 'X because Y' inline"),
    (re.compile(r"\bthe reason for this\b", re.IGNORECASE), "explanatory: 'the reason for this' — state directly"),
    (re.compile(r"\bbasically\b", re.IGNORECASE), "filler: 'basically' — adds zero information"),
    (re.compile(r"\bessentially\b", re.IGNORECASE), "filler: 'essentially' — adds zero information"),
    (re.compile(r"\bfundamentally\b", re.IGNORECASE), "filler: 'fundamentally' — adds zero information"),
    (re.compile(r"\bin other words\b", re.IGNORECASE), "filler: 'in other words' — just say it once clearly"),
    (re.compile(r"\bin order to\b", re.IGNORECASE), "verbose: 'in order to' — 'to' works identically"),
    (re.compile(r"\bkeep in mind that\b", re.IGNORECASE), "meta: 'keep in mind that' — convert to inline Note:"),
    (re.compile(r"\bplease note that\b", re.IGNORECASE), "meta: 'please note that' — convert to inline Note:"),
    (re.compile(r"\blet's\b", re.IGNORECASE), "conversational: 'let's' — use imperative"),
    (re.compile(r"\bwe can\b", re.IGNORECASE), "conversational: 'we can' — use imperative"),
    (re.compile(r"\bwe should\b", re.IGNORECASE), "conversational: 'we should' — use imperative"),
    (re.compile(r"\bfeel free to\b", re.IGNORECASE), "casual: 'feel free to' — remove entirely"),
    (re.compile(r"\bdon't hesitate to\b", re.IGNORECASE), "casual: 'don't hesitate to' — remove entirely"),
]

# Sections to skip (non-procedure content where prose is acceptable)
SKIP_SECTIONS = {
    "purpose", "context", "background", "notes", "description",
    "overview", "when to use", "don't use",
}


def get_current_section(lines, line_idx):
    """Find the nearest heading above this line."""
    for i in range(line_idx, -1, -1):
        line = lines[i].strip()
        match = re.match(r"^#{1,3}\s+(.+)", line)
        if match:
            return match.group(1).strip().lower()
    return ""


def should_skip_section(section_name):
    """Check if the current section should be skipped."""
    for skip in SKIP_SECTIONS:
        if skip in section_name:
            return True
    return False


def check_file(filepath, repo_root):
    """Check for prose patterns. Returns messages (warnings only)."""
    if is_excluded(filepath, repo_root):
        return []

    basename = os.path.basename(filepath)
    if basename != "SKILL.md" and "/references/" not in filepath:
        return []

    rel_path = os.path.relpath(filepath, repo_root)

    with open(filepath) as f:
        lines = f.readlines()

    messages = []
    for idx, line in enumerate(lines):
        section = get_current_section(lines, idx)
        if should_skip_section(section):
            continue
        for pattern, desc in PROSE_PATTERNS:
            if pattern.search(line):
                messages.append(
                    f"WARN: {rel_path}:{idx + 1} — {desc}"
                )

    return messages


def main():
    repo_root = find_repo_root()

    for filepath in sys.argv[1:]:
        filepath = os.path.abspath(filepath)
        messages = check_file(filepath, repo_root)
        for msg in messages:
            print(msg)

    # WARN tier — always exit 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
