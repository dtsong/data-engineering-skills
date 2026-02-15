#!/usr/bin/env python3
"""Per-suite context load breakdown."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))
from _utils import find_repo_root, load_budgets, count_body_words, estimate_tokens


def analyze_skill_dir(skill_path, repo_root, budgets):
    """Analyze context load for a single skill directory."""
    name = os.path.basename(skill_path)
    skill_md = os.path.join(skill_path, "SKILL.md")

    if not os.path.isfile(skill_md):
        return None

    words = count_body_words(skill_md)
    tokens = estimate_tokens(words)

    result = {
        "name": name,
        "skill_md_words": words,
        "skill_md_tokens": tokens,
        "references": [],
        "specialists": [],
    }

    # Check for references
    refs_dir = os.path.join(skill_path, "references")
    if os.path.isdir(refs_dir):
        for ref_file in sorted(os.listdir(refs_dir)):
            if ref_file.endswith(".md"):
                ref_path = os.path.join(refs_dir, ref_file)
                ref_words = count_body_words(ref_path)
                ref_tokens = estimate_tokens(ref_words)
                result["references"].append({
                    "name": ref_file,
                    "words": ref_words,
                    "tokens": ref_tokens,
                })

    # Check for specialists (suite)
    skills_dir = os.path.join(skill_path, "skills")
    if os.path.isdir(skills_dir):
        for spec_dir in sorted(os.listdir(skills_dir)):
            spec_md = os.path.join(skills_dir, spec_dir, "SKILL.md")
            if os.path.isfile(spec_md):
                spec_words = count_body_words(spec_md)
                spec_tokens = estimate_tokens(spec_words)
                result["specialists"].append({
                    "name": spec_dir,
                    "words": spec_words,
                    "tokens": spec_tokens,
                })

    return result


def main():
    repo_root = find_repo_root()
    budgets = load_budgets(repo_root)
    max_load = budgets.get("max_simultaneous_tokens", 5000)

    print("=== Context Load Analysis ===")
    print()
    print(f"Maximum simultaneous context: {max_load} tokens")
    print()

    for entry in sorted(os.listdir(repo_root)):
        skill_path = os.path.join(repo_root, entry)
        if not os.path.isdir(skill_path) or not entry.endswith("-skill"):
            continue

        result = analyze_skill_dir(skill_path, repo_root, budgets)
        if result is None:
            continue

        is_suite = len(result["specialists"]) > 0
        kind = "suite" if is_suite else "standalone"

        print(f"### {result['name']} ({kind})")
        print(f"  SKILL.md: {result['skill_md_words']} words (~{result['skill_md_tokens']} tokens)")

        if result["references"]:
            print("  References:")
            for ref in result["references"]:
                print(f"    - {ref['name']}: {ref['words']} words (~{ref['tokens']} tokens)")

        if result["specialists"]:
            print("  Specialists:")
            for spec in result["specialists"]:
                print(f"    - {spec['name']}: {spec['words']} words (~{spec['tokens']} tokens)")

        # Calculate worst case
        max_ref = max((r["tokens"] for r in result["references"]), default=0)
        max_spec = max((s["tokens"] for s in result["specialists"]), default=0)

        if is_suite:
            total = result["skill_md_tokens"] + max_spec + max_ref
        else:
            total = result["skill_md_tokens"] + max_ref

        status = "OVER" if total > max_load else "OK"
        print(f"  Worst-case load: {total} tokens [{status}]")
        print()


if __name__ == "__main__":
    main()
