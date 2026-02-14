"""Shared utilities for skill governance pre-commit hooks."""

import json
import os
import re
import subprocess


def find_repo_root():
    """Find the git repository root directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return os.getcwd()


def load_budgets(repo_root=None):
    """Load budget configuration from pipeline/config/budgets.json."""
    if repo_root is None:
        repo_root = find_repo_root()
    config_path = os.path.join(repo_root, "pipeline", "config", "budgets.json")
    with open(config_path) as f:
        return json.load(f)


def classify_file(filepath, repo_root=None):
    """Classify a file as coordinator, specialist, standalone, or reference.

    Returns one of: 'coordinator', 'specialist', 'standalone', 'reference', None
    """
    if repo_root is None:
        repo_root = find_repo_root()

    rel_path = os.path.relpath(filepath, repo_root)

    # Excluded paths
    excluded = ("pipeline/", "eval-cases/", "node_modules/", ".github/")
    for exc in excluded:
        if rel_path.startswith(exc):
            return None

    # Reference files
    if "/references/" in rel_path or rel_path.startswith("references/"):
        return "reference"

    basename = os.path.basename(filepath)
    if basename != "SKILL.md":
        return None

    parent_dir = os.path.dirname(filepath)

    # Coordinator: SKILL.md with sibling skills/ directory
    skills_sibling = os.path.join(parent_dir, "skills")
    if os.path.isdir(skills_sibling):
        return "coordinator"

    # Specialist: SKILL.md inside a skills/ directory
    parts = rel_path.replace("\\", "/").split("/")
    if "skills" in parts:
        return "specialist"

    # Standalone
    return "standalone"


def count_body_words(filepath):
    """Count words in a markdown file, excluding YAML frontmatter."""
    with open(filepath) as f:
        content = f.read()

    # Strip YAML frontmatter
    if content.startswith("---"):
        end = content.find("---", 3)
        if end != -1:
            content = content[end + 3:]

    # Count words
    words = content.split()
    return len(words)


def estimate_tokens(word_count, budgets=None):
    """Estimate token count from word count using configured multiplier."""
    if budgets is None:
        budgets = load_budgets()
    multiplier = budgets.get("token_multiplier", 1.33)
    return int(word_count * multiplier)


def get_budget_for_type(file_type, budgets=None):
    """Get max_words and max_tokens for a file classification type."""
    if budgets is None:
        budgets = load_budgets()

    budget_map = {
        "coordinator": ("coordinator_max_words", "coordinator_max_tokens"),
        "specialist": ("specialist_max_words", "specialist_max_tokens"),
        "standalone": ("standalone_max_words", "standalone_max_tokens"),
        "reference": ("reference_max_words", "reference_max_tokens"),
    }

    if file_type not in budget_map:
        return None, None

    words_key, tokens_key = budget_map[file_type]
    return budgets.get(words_key), budgets.get(tokens_key)


def is_excluded(filepath, repo_root=None):
    """Check if a filepath is in an excluded directory."""
    if repo_root is None:
        repo_root = find_repo_root()
    rel_path = os.path.relpath(filepath, repo_root)
    excluded = ("pipeline/", "eval-cases/", "node_modules/", ".github/")
    for exc in excluded:
        if rel_path.startswith(exc):
            return True
    return False
