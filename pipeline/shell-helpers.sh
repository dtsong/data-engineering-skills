#!/bin/bash
# Skill governance shell helpers
# Source this in your shell profile: source /path/to/pipeline/shell-helpers.sh

_skill_repo_root() {
  git rev-parse --show-toplevel 2>/dev/null || pwd
}

# Quick word/token count
skill-wc() {
    local file="$1"
    if [ -z "$file" ]; then
        echo "Usage: skill-wc <SKILL.md or reference file>"
        return 1
    fi
    local words
    words=$(wc -w < "$file")
    local tokens=$(( words * 133 / 100 ))
    echo "$file: $words words (~$tokens tokens)"
}

# Run all checks on a specific skill
skill-check() {
    local skill_dir="$1"
    if [ -z "$skill_dir" ]; then
        echo "Usage: skill-check <skill-directory>"
        return 1
    fi
    find "$skill_dir" \( -name "SKILL.md" -o -path "*/references/*.md" \) \
        -not -path "*/eval-cases/*" -not -path "*/templates/*" | \
        xargs pre-commit run --files
}

# Budget check only
skill-budget() {
    pre-commit run skill-token-budget --files "$@"
}

# Create new standalone skill from template
skill-new() {
    local name="$1"
    local dest="${2:-$name}"
    if [ -z "$name" ]; then
        echo "Usage: skill-new <skill-name> [destination]"
        return 1
    fi
    local root
    root="$(_skill_repo_root)"
    local dest_path="$root/$dest"
    if [ -d "$dest_path" ]; then
        echo "Directory $dest_path already exists"
        return 1
    fi
    cp -r "$root/pipeline/templates/standalone-skill" "$dest_path"
    find "$dest_path" -type f -exec sed -i '' "s/SKILL_NAME/$name/g" {} + 2>/dev/null || \
        find "$dest_path" -type f -exec sed -i "s/SKILL_NAME/$name/g" {} +
    echo "Created skill scaffold at $dest_path"
    echo "Next: edit $dest_path/SKILL.md and run skill-check $dest_path"
}

# Create new skill suite from template
skill-new-suite() {
    local name="$1"
    local dest="${2:-$name}"
    if [ -z "$name" ]; then
        echo "Usage: skill-new-suite <suite-name> [destination]"
        return 1
    fi
    local root
    root="$(_skill_repo_root)"
    local dest_path="$root/$dest"
    if [ -d "$dest_path" ]; then
        echo "Directory $dest_path already exists"
        return 1
    fi
    cp -r "$root/pipeline/templates/skill-suite" "$dest_path"
    find "$dest_path" -type f -exec sed -i '' "s/SUITE_NAME/$name/g" {} + 2>/dev/null || \
        find "$dest_path" -type f -exec sed -i "s/SUITE_NAME/$name/g" {} +
    echo "Created skill suite scaffold at $dest_path"
}

# Full compliance audit
skill-audit() {
    echo "=== Skill Compliance Audit ==="
    echo ""
    echo "--- Hard Checks (structural integrity) ---"
    pre-commit run skill-frontmatter --all-files
    pre-commit run skill-references --all-files
    pre-commit run skill-isolation --all-files
    pre-commit run skill-context-load --all-files
    echo ""
    echo "--- Advisory Checks (quality guidance) ---"
    pre-commit run skill-token-budget --all-files
    pre-commit run skill-prose-check --all-files
    echo ""
    echo "=== Audit Complete ==="
}

# Show context load breakdown for a suite
skill-load() {
    local suite_dir="$1"
    if [ -z "$suite_dir" ]; then
        echo "Usage: skill-load <suite-directory>"
        return 1
    fi
    python3 "$(_skill_repo_root)/pipeline/hooks/check_context_load.py" \
        $(find "$suite_dir" \( -name "SKILL.md" -o -path "*/references/*.md" \) \
        -not -path "*/eval-cases/*")
}
