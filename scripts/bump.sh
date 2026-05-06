#!/usr/bin/env bash
# Bump VERSION and sync README badge.
# Usage: scripts/bump.sh [major|minor|patch]   (default: patch)
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

part="${1:-patch}"
[[ -f VERSION ]] || { echo "VERSION file missing" >&2; exit 1; }

current=$(tr -d '[:space:]' < VERSION)
IFS=. read -r major minor patch <<< "$current"

case "$part" in
  major) major=$((major+1)); minor=0; patch=0 ;;
  minor) minor=$((minor+1)); patch=0 ;;
  patch) patch=$((patch+1)) ;;
  *) echo "usage: $0 [major|minor|patch]" >&2; exit 1 ;;
esac

new="${major}.${minor}.${patch}"
echo "$new" > VERSION

if [[ -f README.md ]]; then
  if sed --version >/dev/null 2>&1; then
    sed -i -E "s|version-[0-9]+\.[0-9]+\.[0-9]+-blue|version-${new}-blue|g" README.md
  else
    sed -i '' -E "s|version-[0-9]+\.[0-9]+\.[0-9]+-blue|version-${new}-blue|g" README.md
  fi
fi

echo "Bumped: $current -> $new"
