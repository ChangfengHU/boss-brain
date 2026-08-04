#!/usr/bin/env bash
# project-brains one-liner installer (v0.2.1, release 20260804123833) — auto-generated, do not edit.
set -euo pipefail
ZIP_URL="https://skill.vyibc.com/project-brains/release/project-brains-20260804123833.zip"
ZIP_SHA256="99ad1db1b1c785e6fcf01b6c7a062a6cf5e9b436f324e2ee8ae1e857066366cb"
D="$(mktemp -d)"; trap 'rm -rf "$D"' EXIT
echo "Downloading project-brains v0.2.1 ..."
curl -fsSL "$ZIP_URL" -o "$D/pb.zip"
echo "$ZIP_SHA256  $D/pb.zip" | sha256sum -c - >/dev/null || { echo "SHA256 mismatch, abort."; exit 1; }
mkdir -p "$HOME/.project-brains"
rm -rf "$HOME/.project-brains/src"
unzip -q "$D/pb.zip" -d "$D/x"
mv "$D/x/project-brains" "$HOME/.project-brains/src"
bash "$HOME/.project-brains/src/install.sh"
