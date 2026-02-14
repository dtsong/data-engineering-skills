#!/usr/bin/env bash
# Validate skill directory structure and frontmatter existence.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
ERRORS=0

echo "=== Structure Validation ==="
echo ""

# Check each skill directory
for skill_dir in "$ROOT"/*-skill; do
  [ -d "$skill_dir" ] || continue
  name="$(basename "$skill_dir")"

  # Must have SKILL.md
  if [ ! -f "$skill_dir/SKILL.md" ]; then
    echo "FAIL: $name/ — missing SKILL.md"
    ERRORS=$((ERRORS + 1))
    continue
  fi

  # SKILL.md must have frontmatter
  if ! head -1 "$skill_dir/SKILL.md" | grep -q "^---$"; then
    echo "FAIL: $name/SKILL.md — missing YAML frontmatter"
    ERRORS=$((ERRORS + 1))
  else
    echo "OK: $name/SKILL.md — structure valid"
  fi

  # Check references directory if it exists
  if [ -d "$skill_dir/references" ]; then
    ref_count=$(find "$skill_dir/references" -name "*.md" | wc -l | tr -d ' ')
    echo "  -> $name/references/ — $ref_count reference file(s)"
  fi
done

echo ""
# Check pipeline structure
for dir in pipeline/hooks pipeline/scripts pipeline/config pipeline/specs; do
  if [ -d "$ROOT/$dir" ]; then
    echo "OK: $dir/ exists"
  else
    echo "FAIL: $dir/ missing"
    ERRORS=$((ERRORS + 1))
  fi
done

echo ""
if [ "$ERRORS" -eq 0 ]; then
  echo "Structure validation passed."
else
  echo "Structure validation found $ERRORS error(s)."
  exit 1
fi
