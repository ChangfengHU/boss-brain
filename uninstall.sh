#!/usr/bin/env bash
set -euo pipefail

VERSION="${BOSS_VERSION:-v0.1.0}"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
TEMP_DIR=""

cleanup() {
  if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
    find "$TEMP_DIR" -depth -mindepth 1 -delete 2>/dev/null || true
    rmdir "$TEMP_DIR" 2>/dev/null || true
  fi
}
trap cleanup EXIT

if [ ! -f "$SOURCE_DIR/scripts/install.py" ]; then
  command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 1; }
  TEMP_DIR="$(mktemp -d)"
  git clone --quiet --depth 1 --branch "$VERSION" https://github.com/ChangfengHU/boss-brain.git "$TEMP_DIR/source"
  SOURCE_DIR="$TEMP_DIR/source"
fi

exec python3 "$SOURCE_DIR/scripts/install.py" uninstall "$@"
