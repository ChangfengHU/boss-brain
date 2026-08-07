#!/usr/bin/env bash
# project-brains one-liner installer (v0.4.3, release 20260806230231) — auto-generated, do not edit.
set -euo pipefail
ZIP_URL="https://skill.vyibc.com/project-brains/release/project-brains-20260806230231.zip"
ZIP_SHA256="03dc4eb7b89ac069aa1149da8103ef5f9819e52f2ef18be21cf1c525f9ca2733"
D="$(mktemp -d)"; trap 'rm -rf "$D"' EXIT
echo "Downloading project-brains v0.4.3 ..."
curl -fsSL "$ZIP_URL" -o "$D/pb.zip"
echo "$ZIP_SHA256  $D/pb.zip" | sha256sum -c - >/dev/null || { echo "SHA256 mismatch, abort."; exit 1; }
mkdir -p "$HOME/.project-brains"
rm -rf "$HOME/.project-brains/src"
unzip -q "$D/pb.zip" -d "$D/x"
mv "$D/x/project-brains" "$HOME/.project-brains/src"
bash "$HOME/.project-brains/src/install.sh"
