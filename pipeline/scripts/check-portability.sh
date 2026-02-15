#!/usr/bin/env bash
# Check for platform-specific references in skill files.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
WARNINGS=0

echo "=== Portability Check ==="
echo ""

# Patterns that suggest platform-specific content
PATTERNS=(
  '/usr/local/'
  '/home/'
  'C:\\'
  'brew install'
  'apt-get'
  'yum install'
  'winget'
  'choco install'
  '\.exe\b'
  '\.bat\b'
  'powershell'
)

for f in $(find "$ROOT" -name "SKILL.md" -not -path "*/pipeline/*" -not -path "*/node_modules/*"); do
  rel="$(realpath --relative-to="$ROOT" "$f" 2>/dev/null || echo "$f")"
  for pattern in "${PATTERNS[@]}"; do
    matches=$(grep -n -i "$pattern" "$f" 2>/dev/null || true)
    if [ -n "$matches" ]; then
      echo "WARN: $rel — platform-specific reference: $pattern"
      echo "$matches" | head -3 | sed 's/^/  /'
      WARNINGS=$((WARNINGS + 1))
    fi
  done
done

echo ""
if [ "$WARNINGS" -eq 0 ]; then
  echo "No portability issues found."
else
  echo "Found $WARNINGS portability warning(s)."
fi
