#!/usr/bin/env bash
# project-brains one-liner installer (v0.5.2, release 20260807030900) — auto-generated, do not edit.
set -euo pipefail
ZIP_URL="https://skill.vyibc.com/project-brains/release/project-brains-20260807030900.zip"
ZIP_SHA256="6c2d998524ae4c2da7db1d1386cab123dc39d7ebd8fe3a78651d0c6b668a3c79"
D="$(mktemp -d)"; trap 'rm -rf "$D"' EXIT
echo "Downloading project-brains v0.5.2 ..."
curl -fsSL "$ZIP_URL" -o "$D/pb.zip"
echo "$ZIP_SHA256  $D/pb.zip" | sha256sum -c - >/dev/null || { echo "SHA256 mismatch, abort."; exit 1; }
mkdir -p "$HOME/.project-brains"
rm -rf "$HOME/.project-brains/src"
unzip -q "$D/pb.zip" -d "$D/x"
mv "$D/x/project-brains" "$HOME/.project-brains/src"
bash "$HOME/.project-brains/src/install.sh"
