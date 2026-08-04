#!/usr/bin/env bash
# Build + publish a project-brains release: zip (SHA256-pinned) + one-liner
# installer, uploaded to R2 (skill.vyibc.com) and persisted in git releases/current/.
# Requires: R2_UPLOAD_URL + R2_UPLOAD_TOKEN in env (source from control-plane secrets).
set -euo pipefail

SRC="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(cat "$SRC/VERSION")"
TS="$(date +%Y%m%d%H%M%S)"
NAME="project-brains-${TS}"
OUT="$SRC/releases/current"
TMP="$(mktemp -d)"
DOMAIN="https://skill.vyibc.com"

: "${R2_UPLOAD_URL:?missing}" ; : "${R2_UPLOAD_TOKEN:?missing}"

# 1. Stage distributable content (no .git, no .brain, no releases)
mkdir -p "$TMP/project-brains"
for f in README.md VERSION install.sh doctor.sh constitution skill hooks commands; do
  cp -r "$SRC/$f" "$TMP/project-brains/"
done
( cd "$TMP" && zip -qr "$NAME.zip" project-brains )
SHA="$(sha256sum "$TMP/$NAME.zip" | awk '{print $1}')"

# 2. Generate self-contained installer
ZIP_URL="$DOMAIN/project-brains/release/$NAME.zip"
cat > "$TMP/install-project-brains.sh" <<EOF
#!/usr/bin/env bash
# project-brains one-liner installer (v$VERSION, release $TS) — auto-generated, do not edit.
set -euo pipefail
ZIP_URL="$ZIP_URL"
ZIP_SHA256="$SHA"
D="\$(mktemp -d)"; trap 'rm -rf "\$D"' EXIT
echo "Downloading project-brains v$VERSION ..."
curl -fsSL "\$ZIP_URL" -o "\$D/pb.zip"
echo "\$ZIP_SHA256  \$D/pb.zip" | sha256sum -c - >/dev/null || { echo "SHA256 mismatch, abort."; exit 1; }
mkdir -p "\$HOME/.project-brains"
rm -rf "\$HOME/.project-brains/src"
unzip -q "\$D/pb.zip" -d "\$D/x"
mv "\$D/x/project-brains" "\$HOME/.project-brains/src"
bash "\$HOME/.project-brains/src/install.sh"
EOF

# 3. Upload zip + installer to R2
up() { # $1=file $2=name $3=path
  curl -fsS "$R2_UPLOAD_URL" -H "Authorization: Bearer $R2_UPLOAD_TOKEN" \
    -F "file=@$1" -F "name=$2" -F "path=$3" -F "domain=$DOMAIN" >/dev/null
}
up "$TMP/$NAME.zip" "$NAME.zip" "project-brains/release"
up "$TMP/install-project-brains.sh" "install-project-brains.sh" ""

# 4. Persist release in git (git is the durable authority; R2 is the CDN)
mkdir -p "$OUT"
rm -f "$OUT"/project-brains-*.zip
cp "$TMP/$NAME.zip" "$TMP/install-project-brains.sh" "$OUT/"
printf 'version=%s\nrelease=%s\nsha256=%s\nzip_url=%s\n' "$VERSION" "$TS" "$SHA" "$ZIP_URL" > "$OUT/manifest.txt"

echo "Released $NAME (sha256 $SHA)"
echo "Install: bash <(curl -fsSL \"$DOMAIN/install-project-brains.sh\")"
