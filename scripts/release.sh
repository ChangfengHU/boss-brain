#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="$(tr -d '\r\n' < "$ROOT/VERSION")"
OUT="$ROOT/dist"

python3 -m unittest -v tests.test_boss
python3 -m py_compile plugins/boss-brain/scripts/boss.py scripts/install.py
bash -n install.sh uninstall.sh

if rg -l -g '!*.pyc' -e 'gh[pousr]_[A-Za-z0-9_]{20,}' -e 'github_pat_[A-Za-z0-9_]{20,}' "$ROOT" >/dev/null; then
  echo "secret-like token found; refusing release" >&2
  exit 1
fi

mkdir -p "$OUT"
git -C "$ROOT" archive --format=tar.gz --prefix="boss-brain-$VERSION/" -o "$OUT/boss-brain-$VERSION.tar.gz" HEAD
sha256sum "$OUT/boss-brain-$VERSION.tar.gz" > "$OUT/boss-brain-$VERSION.tar.gz.sha256"
echo "release artifacts written to $OUT"
