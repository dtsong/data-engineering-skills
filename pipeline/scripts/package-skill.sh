#!/usr/bin/env bash
# Package a skill into a distributable archive.
set -euo pipefail

SKILL="${1:?Usage: package-skill.sh <skill-directory>}"
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
DIST="$ROOT/dist"

if [ ! -d "$ROOT/$SKILL" ]; then
  echo "Error: Skill directory not found: $ROOT/$SKILL" >&2
  exit 1
fi

if [ ! -f "$ROOT/$SKILL/SKILL.md" ]; then
  echo "Error: No SKILL.md in $SKILL" >&2
  exit 1
fi

# Read version from VERSION file or default
VERSION="$(cat "$ROOT/VERSION" 2>/dev/null || echo "0.0.0")"
VERSION="$(echo "$VERSION" | tr -d '[:space:]')"

mkdir -p "$DIST"

ARCHIVE="$DIST/${SKILL}-${VERSION}.tar.gz"

# Create archive excluding eval-cases and hidden files
tar -czf "$ARCHIVE" \
  -C "$ROOT" \
  --exclude="eval-cases" \
  --exclude=".*" \
  "$SKILL/"

echo "Packaged: $ARCHIVE"
echo "  Skill: $SKILL"
echo "  Version: $VERSION"
echo "  Size: $(du -h "$ARCHIVE" | cut -f1)"
