#!/usr/bin/env bash
# project-brains one-liner installer (v0.3.9, release 20260806014602) — auto-generated, do not edit.
set -euo pipefail
ZIP_URL="https://skill.vyibc.com/project-brains/release/project-brains-20260806014602.zip"
ZIP_SHA256="dcc6f864c891d28cf06b242d7e7f1f26bea40d20af14063ffbf03bdf6751b4b3"
D="$(mktemp -d)"; trap 'rm -rf "$D"' EXIT
echo "Downloading project-brains v0.3.9 ..."
curl -fsSL "$ZIP_URL" -o "$D/pb.zip"
echo "$ZIP_SHA256  $D/pb.zip" | sha256sum -c - >/dev/null || { echo "SHA256 mismatch, abort."; exit 1; }
mkdir -p "$HOME/.project-brains"
rm -rf "$HOME/.project-brains/src"
unzip -q "$D/pb.zip" -d "$D/x"
mv "$D/x/project-brains" "$HOME/.project-brains/src"
bash "$HOME/.project-brains/src/install.sh"
