#!/usr/bin/env python3
"""Validate conventional commit message format."""

import re
import sys

VALID_TYPES = {
    "feat", "fix", "docs", "style", "refactor", "test",
    "chore", "ci", "perf", "build", "revert", "skill",
}

# type(optional-scope): lowercase description
COMMIT_PATTERN = re.compile(
    r"^(?P<type>[a-z]+)"
    r"(?:\((?P<scope>[a-z0-9_/.-]+)\))?"
    r":\s+"
    r"(?P<desc>[a-z].*)"
    r"$"
)


def validate_message(message):
    """Validate a commit message. Returns (passed, errors)."""
    lines = message.strip().split("\n")
    if not lines:
        return False, ["Empty commit message"]

    subject = lines[0].strip()
    errors = []

    # Allow merge commits
    if subject.startswith("Merge "):
        return True, []

    match = COMMIT_PATTERN.match(subject)
    if not match:
        errors.append(
            f"Subject line doesn't match conventional commit format.\n"
            f"  Got: '{subject}'\n"
            f"  Expected: type(scope): description\n"
            f"  Valid types: {', '.join(sorted(VALID_TYPES))}"
        )
        return False, errors

    commit_type = match.group("type")
    desc = match.group("desc")

    if commit_type not in VALID_TYPES:
        errors.append(
            f"Invalid commit type '{commit_type}'. "
            f"Valid types: {', '.join(sorted(VALID_TYPES))}"
        )

    if desc.endswith("."):
        errors.append("Description should not end with a period")

    if len(subject) > 100:
        errors.append(f"Subject line too long ({len(subject)} chars, max 100)")

    return len(errors) == 0, errors


def main():
    if len(sys.argv) < 2:
        print("Usage: check_commit_msg.py <commit-msg-file>")
        return 1

    with open(sys.argv[1]) as f:
        message = f.read()

    passed, errors = validate_message(message)
    if not passed:
        print("Commit message validation failed:")
        for error in errors:
            print(f"  {error}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
