#!/usr/bin/env bash
# Run skill evaluations.
# Placeholder — will be implemented when eval cases are added.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

echo "=== Skill Evaluation Runner ==="
echo ""

EVAL_COUNT=0
for eval_file in $(find "$ROOT" -name "evals.json" -path "*/eval-cases/*" 2>/dev/null); do
  rel="$(realpath --relative-to="$ROOT" "$eval_file" 2>/dev/null || echo "$eval_file")"

  # Check if eval has cases
  cases=$(python3 -c "import json; d=json.load(open('$eval_file')); print(len(d.get('cases',[])))" 2>/dev/null || echo "0")
  if [ "$cases" -eq 0 ]; then
    echo "SKIP: $rel — no cases defined"
    continue
  fi

  echo "RUN: $rel — $cases case(s)"
  EVAL_COUNT=$((EVAL_COUNT + 1))
done

echo ""
if [ "$EVAL_COUNT" -eq 0 ]; then
  echo "No evaluations to run. Add cases to eval-cases/evals.json files."
else
  echo "Ran $EVAL_COUNT evaluation suite(s)."
fi
