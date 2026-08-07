#!/usr/bin/env bash
# project-brains one-liner installer (v0.5.0, release 20260807000245) — auto-generated, do not edit.
set -euo pipefail
ZIP_URL="https://skill.vyibc.com/project-brains/release/project-brains-20260807000245.zip"
ZIP_SHA256="e10913c1c29a3df33ef9a6b189440b8ed3b0c3105add3bedc28c3d0afa40b05e"
D="$(mktemp -d)"; trap 'rm -rf "$D"' EXIT
echo "Downloading project-brains v0.5.0 ..."
curl -fsSL "$ZIP_URL" -o "$D/pb.zip"
echo "$ZIP_SHA256  $D/pb.zip" | sha256sum -c - >/dev/null || { echo "SHA256 mismatch, abort."; exit 1; }
mkdir -p "$HOME/.project-brains"
rm -rf "$HOME/.project-brains/src"
unzip -q "$D/pb.zip" -d "$D/x"
mv "$D/x/project-brains" "$HOME/.project-brains/src"
bash "$HOME/.project-brains/src/install.sh"
