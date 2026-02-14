#!/usr/bin/env python3
"""Check that specialist skills don't cross-reference siblings. HARD tier."""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import find_repo_root, classify_file, is_excluded


def find_sibling_specialists(filepath, repo_root):
    """Find sibling specialist directories for a specialist skill."""
    rel_path = os.path.relpath(filepath, repo_root).replace("\\", "/")
    parts = rel_path.split("/")

    # Find the skills/ directory in the path
    skills_idx = None
    for i, part in enumerate(parts):
        if part == "skills":
            skills_idx = i
            break

    if skills_idx is None or skills_idx + 1 >= len(parts):
        return set(), None

    own_specialist = parts[skills_idx + 1]
    skills_dir = os.path.join(repo_root, *parts[:skills_idx + 1])

    siblings = set()
    if os.path.isdir(skills_dir):
        for entry in os.listdir(skills_dir):
            if entry != own_specialist and os.path.isdir(os.path.join(skills_dir, entry)):
                siblings.add(entry)

    return siblings, own_specialist


def check_file(filepath, repo_root):
    """Check for cross-specialist references. Returns (passed, messages)."""
    if is_excluded(filepath, repo_root):
        return True, []

    file_type = classify_file(filepath, repo_root)
    if file_type != "specialist":
        return True, []

    rel_path = os.path.relpath(filepath, repo_root)
    siblings, own_name = find_sibling_specialists(filepath, repo_root)

    if not siblings:
        return True, [f"OK: {rel_path} — no sibling specialists to check"]

    with open(filepath) as f:
        lines = f.readlines()

    messages = []
    passed = True

    for line_num, line in enumerate(lines, 1):
        for sibling in siblings:
            # Check for references to sibling's SKILL.md or reference files
            patterns = [
                f"{sibling}/SKILL.md",
                f"{sibling}/references/",
                f"skills/{sibling}",
            ]
            for pattern in patterns:
                if pattern in line:
                    messages.append(
                        f"FAIL: {rel_path}:{line_num} — "
                        f"cross-references sibling specialist '{sibling}' "
                        f"(source: {own_name}, target: {sibling}). "
                        f"Use handoff protocol instead."
                    )
                    passed = False
                    break

    if not messages:
        messages.append(f"OK: {rel_path} — no cross-specialist references")

    return passed, messages


def find_all_skill_dirs(repo_root):
    """Find all top-level *-skill directories (for standalone isolation check)."""
    dirs = set()
    for entry in os.listdir(repo_root):
        if entry.endswith("-skill") and os.path.isdir(os.path.join(repo_root, entry)):
            dirs.add(entry)
    return dirs


def check_standalone_file(filepath, repo_root, skill_dirs):
    """Check standalone skills for cross-skill references."""
    if is_excluded(filepath, repo_root):
        return True, []

    file_type = classify_file(filepath, repo_root)
    if file_type != "standalone":
        return True, []

    rel_path = os.path.relpath(filepath, repo_root)
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

    skill_ref_pattern = re.compile(r"(?:^|[\s([\]])(\w+-skill)/", re.MULTILINE)
    for match in skill_ref_pattern.finditer(content):
        referenced = match.group(1)
        if referenced == own_skill or referenced == "shared-references":
            continue
        if referenced in skill_dirs:
            messages.append(
                f"FAIL: {rel_path} — cross-references '{referenced}/' "
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
        file_type = classify_file(filepath, repo_root)

        if file_type == "specialist":
            passed, messages = check_file(filepath, repo_root)
        elif file_type == "standalone":
            passed, messages = check_standalone_file(filepath, repo_root, skill_dirs)
        else:
            continue

        for msg in messages:
            print(msg)
        if not passed:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
