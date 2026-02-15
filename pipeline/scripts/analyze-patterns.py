#!/usr/bin/env python3
"""Analyze skill files for prose patterns, duplication, and inline checklists."""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))
from _utils import find_repo_root, is_excluded


def find_skill_files(repo_root):
    """Find all SKILL.md and reference files."""
    files = []
    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for f in filenames:
            full = os.path.join(dirpath, f)
            if is_excluded(full, repo_root):
                continue
            if f == "SKILL.md" or (f.endswith(".md") and "/references/" in full):
                files.append(full)
    return files


def check_inline_checklists(content, rel_path):
    """Flag checklists with >10 items that should be in references."""
    issues = []
    lines = content.split("\n")
    checklist_count = 0
    checklist_start = 0

    for i, line in enumerate(lines):
        if re.match(r"^\s*[-*]\s+\[[ x]\]", line) or re.match(r"^\s*\d+\.\s+", line):
            if checklist_count == 0:
                checklist_start = i + 1
            checklist_count += 1
        else:
            if checklist_count > 10:
                issues.append(
                    f"WARN: {rel_path}:{checklist_start} — "
                    f"inline checklist has {checklist_count} items "
                    f"(consider moving to references/)"
                )
            checklist_count = 0

    if checklist_count > 10:
        issues.append(
            f"WARN: {rel_path}:{checklist_start} — "
            f"inline checklist has {checklist_count} items "
            f"(consider moving to references/)"
        )

    return issues


def check_duplication(files, repo_root):
    """Detect duplicate paragraphs across files."""
    issues = []
    paragraphs = {}

    for filepath in files:
        rel_path = os.path.relpath(filepath, repo_root)
        with open(filepath) as f:
            content = f.read()

        # Split into paragraphs (blocks separated by blank lines)
        for para in re.split(r"\n\s*\n", content):
            para = para.strip()
            if len(para.split()) < 20:
                continue
            if para in paragraphs:
                issues.append(
                    f"WARN: Duplicate paragraph in {rel_path} "
                    f"and {paragraphs[para]}"
                )
            else:
                paragraphs[para] = rel_path

    return issues


def main():
    repo_root = find_repo_root()
    files = find_skill_files(repo_root)

    print("=== Pattern Analysis ===")
    print()

    all_issues = []

    for filepath in files:
        rel_path = os.path.relpath(filepath, repo_root)
        with open(filepath) as f:
            content = f.read()
        all_issues.extend(check_inline_checklists(content, rel_path))

    all_issues.extend(check_duplication(files, repo_root))

    if all_issues:
        for issue in all_issues:
            print(issue)
        print()
        print(f"Found {len(all_issues)} pattern issue(s).")
    else:
        print("No pattern issues found.")


if __name__ == "__main__":
    main()
