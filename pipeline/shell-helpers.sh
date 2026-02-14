#!/usr/bin/env bash
# Skill governance shell helpers
# Source this file: source pipeline/shell-helpers.sh

_skill_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

# Count words in a SKILL.md (excluding frontmatter)
skill-wc() {
  local file="${1:?Usage: skill-wc <SKILL.md>}"
  if [ ! -f "$file" ]; then
    echo "File not found: $file" >&2
    return 1
  fi
  python3 -c "
import sys
sys.path.insert(0, '$(_skill_repo_root)/pipeline/hooks')
from _utils import count_body_words, estimate_tokens, load_budgets
words = count_body_words('$file')
budgets = load_budgets('$(_skill_repo_root)')
tokens = estimate_tokens(words, budgets)
print(f'{words} words (~{tokens} tokens)')
"
}

# Run all governance checks on staged files
skill-check() {
  local root
  root="$(_skill_repo_root)"
  cd "$root" && pre-commit run --all-files
}

# Show budget report for all skills
skill-budget() {
  local root
  root="$(_skill_repo_root)"
  python3 "$root/pipeline/scripts/budget-report.py"
}

# Create a new standalone skill from template
skill-new() {
  local name="${1:?Usage: skill-new <skill-name>}"
  local root
  root="$(_skill_repo_root)"
  local template_dir="$root/pipeline/templates/standalone-skill"
  local target_dir="$root/$name"

  if [ -d "$target_dir" ]; then
    echo "Directory already exists: $target_dir" >&2
    return 1
  fi

  cp -r "$template_dir" "$target_dir"
  # Replace placeholder in SKILL.md
  sed -i '' "s/{{SKILL_NAME}}/$name/g" "$target_dir/SKILL.md" 2>/dev/null || \
    sed -i "s/{{SKILL_NAME}}/$name/g" "$target_dir/SKILL.md"
  echo "Created standalone skill: $target_dir"
  echo "Edit $target_dir/SKILL.md to get started."
}

# Create a new skill suite from template
skill-new-suite() {
  local name="${1:?Usage: skill-new-suite <suite-name>}"
  local root
  root="$(_skill_repo_root)"
  local template_dir="$root/pipeline/templates/skill-suite"
  local target_dir="$root/$name"

  if [ -d "$target_dir" ]; then
    echo "Directory already exists: $target_dir" >&2
    return 1
  fi

  cp -r "$template_dir" "$target_dir"
  # Replace placeholder in SKILL.md files
  find "$target_dir" -name "SKILL.md" -exec sh -c '
    sed -i "" "s/{{SUITE_NAME}}/'"$name"'/g" "$1" 2>/dev/null || \
    sed -i "s/{{SUITE_NAME}}/'"$name"'/g" "$1"
  ' _ {} \;
  echo "Created skill suite: $target_dir"
  echo "Edit $target_dir/SKILL.md (coordinator) to get started."
}

# Full governance audit — all checks + budget report
skill-audit() {
  local root
  root="$(_skill_repo_root)"
  echo "=== Skill Governance Audit ==="
  echo ""
  echo "--- Pre-commit checks ---"
  cd "$root" && pre-commit run --all-files
  local hook_status=$?
  echo ""
  echo "--- Budget Report ---"
  python3 "$root/pipeline/scripts/budget-report.py"
  echo ""
  echo "--- Structure Validation ---"
  bash "$root/pipeline/scripts/validate-structure.sh"
  echo ""
  if [ $hook_status -ne 0 ]; then
    echo "AUDIT RESULT: Issues found (see above)"
    return 1
  else
    echo "AUDIT RESULT: All checks passed"
    return 0
  fi
}
