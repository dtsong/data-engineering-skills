#!/usr/bin/env python3
"""Validate YAML frontmatter in SKILL.md files."""

import re
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from _utils import find_repo_root, is_excluded

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

REQUIRED_FIELDS = {"name", "description"}
RECOGNIZED_FIELDS = {"name", "description", "license", "metadata"}
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
MIN_DESCRIPTION_WORDS = 10


def parse_frontmatter_regex(content):
    """Fallback frontmatter parser using regex."""
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None
    fm = {}
    for line in match.group(1).split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith(" ") and not line.startswith("-"):
            key, _, value = line.partition(":")
            fm[key.strip()] = value.strip()
    return fm


def parse_frontmatter(content):
    """Parse YAML frontmatter from file content."""
    if not content.startswith("---"):
        return None

    end = content.find("---", 3)
    if end == -1:
        return None

    fm_text = content[3:end]

    if HAS_YAML:
        try:
            return yaml.safe_load(fm_text) or {}
        except yaml.YAMLError:
            return None

    return parse_frontmatter_regex(content)


def check_file(filepath, repo_root):
    """Validate frontmatter for a single file. Returns (passed, messages)."""
    if is_excluded(filepath, repo_root):
        return True, []

    if os.path.basename(filepath) != "SKILL.md":
        return True, []

    rel_path = os.path.relpath(filepath, repo_root)

    with open(filepath) as f:
        content = f.read()

    fm = parse_frontmatter(content)
    if fm is None:
        return False, [f"FAIL: {rel_path} — missing or invalid YAML frontmatter"]

    messages = []
    passed = True

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in fm:
            messages.append(f"FAIL: {rel_path} — missing required field '{field}'")
            passed = False

    # Validate name format
    name = fm.get("name", "")
    if name and not NAME_PATTERN.match(str(name)):
        messages.append(
            f"FAIL: {rel_path} — 'name' must be kebab-case "
            f"(got '{name}')"
        )
        passed = False

    # Validate description length
    desc = fm.get("description", "")
    if desc:
        word_count = len(str(desc).split())
        if word_count < MIN_DESCRIPTION_WORDS:
            messages.append(
                f"FAIL: {rel_path} — 'description' must be at least "
                f"{MIN_DESCRIPTION_WORDS} words (got {word_count})"
            )
            passed = False

    # Warn on unrecognized fields
    extra_fields = set(fm.keys()) - RECOGNIZED_FIELDS
    if extra_fields:
        messages.append(
            f"WARN: {rel_path} — unrecognized frontmatter fields: "
            f"{', '.join(sorted(extra_fields))}"
        )

    if not messages and passed:
        messages.append(f"OK: {rel_path} — frontmatter valid")

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
