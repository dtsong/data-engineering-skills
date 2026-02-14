#!/usr/bin/env bash
# Wrapper: run token budget check on all skill files.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

FILES=()
for f in $(find "$ROOT" -name "SKILL.md" -not -path "*/pipeline/*" -not -path "*/eval-cases/*" -not -path "*/node_modules/*" -not -path "*/.github/*"); do
  FILES+=("$f")
done

for f in $(find "$ROOT" -path "*/references/*.md" -not -path "*/pipeline/*" -not -path "*/eval-cases/*" -not -path "*/node_modules/*" -not -path "*/.github/*"); do
  FILES+=("$f")
done

if [ ${#FILES[@]} -eq 0 ]; then
  echo "No skill files found."
  exit 0
fi

python3 "$ROOT/pipeline/hooks/check_token_budget.py" "${FILES[@]}"
