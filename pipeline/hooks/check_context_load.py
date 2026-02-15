#!/usr/bin/env python3
"""Check suite worst-case context load against ceiling. HARD tier."""

import sys
import os
import glob as globmod

sys.path.insert(0, os.path.dirname(__file__))
from _utils import (
    find_repo_root, load_budgets, classify_file,
    count_body_words, estimate_tokens, is_excluded,
)


def find_suites(repo_root):
    """Find skill suites (directories with skills/ subdirectory)."""
    suites = []
    for entry in os.listdir(repo_root):
        full_path = os.path.join(repo_root, entry)
        if not os.path.isdir(full_path):
            continue
        skill_md = os.path.join(full_path, "SKILL.md")
        skills_dir = os.path.join(full_path, "skills")
        if os.path.isfile(skill_md) and os.path.isdir(skills_dir):
            suites.append(full_path)
    return suites


def find_standalone_skills(repo_root):
    """Find standalone skills (SKILL.md without sibling skills/ dir)."""
    standalones = []
    for entry in os.listdir(repo_root):
        full_path = os.path.join(repo_root, entry)
        if not os.path.isdir(full_path):
            continue
        if is_excluded(full_path, repo_root):
            continue
        skill_md = os.path.join(full_path, "SKILL.md")
        skills_dir = os.path.join(full_path, "skills")
        if os.path.isfile(skill_md) and not os.path.isdir(skills_dir):
            standalones.append(full_path)
    return standalones


def check_suite(suite_path, repo_root, budgets):
    """Check context load for a suite. Returns (passed, message)."""
    max_load = budgets.get("max_simultaneous_tokens", 5500)
    suite_name = os.path.basename(suite_path)

    # Coordinator tokens
    coord_md = os.path.join(suite_path, "SKILL.md")
    coord_words = count_body_words(coord_md)
    coord_tokens = estimate_tokens(coord_words)

    # Find largest specialist
    skills_dir = os.path.join(suite_path, "skills")
    max_spec_tokens = 0
    max_spec_name = ""
    for spec_dir in os.listdir(skills_dir):
        spec_md = os.path.join(skills_dir, spec_dir, "SKILL.md")
        if os.path.isfile(spec_md):
            words = count_body_words(spec_md)
            tokens = estimate_tokens(words)
            if tokens > max_spec_tokens:
                max_spec_tokens = tokens
                max_spec_name = spec_dir

    # Find largest reference
    max_ref_tokens = 0
    max_ref_name = ""
    refs_pattern = os.path.join(suite_path, "**", "references", "*.md")
    for ref_path in globmod.glob(refs_pattern, recursive=True):
        words = count_body_words(ref_path)
        tokens = estimate_tokens(words)
        if tokens > max_ref_tokens:
            max_ref_tokens = tokens
            max_ref_name = os.path.basename(ref_path)

    total = coord_tokens + max_spec_tokens + max_ref_tokens

    detail = (
        f"{suite_name}: coordinator({coord_tokens}) + "
        f"specialist/{max_spec_name}({max_spec_tokens}) + "
        f"reference/{max_ref_name}({max_ref_tokens}) = {total} tokens"
    )

    if total > max_load:
        return False, (
            f"FAIL: {detail} (ceiling: {max_load})\n"
            f"  Reduce the largest specialist or extract content to a "
            f"conditionally-loaded reference file."
        )
    return True, f"OK: {detail} (ceiling: {max_load})"


def check_standalone(skill_path, repo_root, budgets):
    """Check context load for a standalone skill."""
    max_load = budgets.get("max_simultaneous_tokens", 5500)
    skill_name = os.path.basename(skill_path)

    skill_md = os.path.join(skill_path, "SKILL.md")
    words = count_body_words(skill_md)
    tokens = estimate_tokens(words)

    # Include largest reference if any
    max_ref_tokens = 0
    max_ref_name = ""
    refs_dir = os.path.join(skill_path, "references")
    if os.path.isdir(refs_dir):
        for ref_file in os.listdir(refs_dir):
            if ref_file.endswith(".md"):
                ref_path = os.path.join(refs_dir, ref_file)
                ref_words = count_body_words(ref_path)
                ref_tokens = estimate_tokens(ref_words)
                if ref_tokens > max_ref_tokens:
                    max_ref_tokens = ref_tokens
                    max_ref_name = ref_file

    total = tokens + max_ref_tokens

    if max_ref_tokens:
        detail = (
            f"{skill_name}: SKILL.md({tokens}) + "
            f"reference/{max_ref_name}({max_ref_tokens}) = {total} tokens"
        )
    else:
        detail = f"{skill_name}: SKILL.md({tokens}) = {total} tokens"

    if total > max_load:
        return False, (
            f"FAIL: {detail} (ceiling: {max_load})\n"
            f"  Reduce the largest specialist or extract content to a "
            f"conditionally-loaded reference file."
        )
    return True, f"OK: {detail} (ceiling: {max_load})"


def main():
    repo_root = find_repo_root()
    budgets = load_budgets(repo_root)
    failed = False

    # Check suites
    for suite_path in find_suites(repo_root):
        passed, msg = check_suite(suite_path, repo_root, budgets)
        print(msg)
        if not passed:
            failed = True

    # Check standalone skills
    for skill_path in find_standalone_skills(repo_root):
        passed, msg = check_standalone(skill_path, repo_root, budgets)
        print(msg)
        if not passed:
            failed = True

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
