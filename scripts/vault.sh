#!/usr/bin/env bash
# project-brains secret vault: passphrase-encrypted secrets on Cloudflare R2.
#
#   vault.sh push <secrets-dir> <vault-url-base>   # encrypt + upload (needs R2_UPLOAD_URL/TOKEN)
#   vault.sh pull <secrets-dir> <vault-url-base>   # download + decrypt + chmod 600/700
#   vault.sh status <vault-url-base>               # show remote manifest (no secrets)
#
# Design: R2 stores ONLY ciphertext (AES-256-CBC, PBKDF2-SHA256 600k iters).
# The passphrase lives only in the user's head and is prompted silently.
# The vault URL is a pointer, safe to keep in a private repo doc.
set -euo pipefail

CMD="${1:?usage: vault.sh push|pull|status ...}"
ITER=600000

prompt_pass() { # $1=confirm(yes/no)
  read -rs -p "Vault passphrase: " P1 < /dev/tty; echo >&2
  if [ "$1" = yes ]; then
    read -rs -p "Confirm passphrase: " P2 < /dev/tty; echo >&2
    [ "$P1" = "$P2" ] || { echo "passphrase mismatch" >&2; exit 1; }
  fi
  printf '%s' "$P1"
}

case "$CMD" in
push)
  DIR="${2:?secrets dir}"; BASE="${3:?vault url base, e.g. https://skill.vyibc.com/suqu/vault}"
  : "${R2_UPLOAD_URL:?}"; : "${R2_UPLOAD_TOKEN:?}"
  [ -d "$DIR" ] || { echo "no such dir: $DIR" >&2; exit 1; }
  PASS="${VAULT_PASSPHRASE:-$(prompt_pass yes)}"
  T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
  tar -C "$(dirname "$DIR")" -czf "$T/plain.tgz" "$(basename "$DIR")"
  PASS_ENV="$PASS" openssl enc -aes-256-cbc -pbkdf2 -iter $ITER -salt \
    -in "$T/plain.tgz" -out "$T/secrets.enc" -pass env:PASS_ENV
  SHA="$(sha256sum "$T/secrets.enc" | awk '{print $1}')"
  printf 'updated=%s\nsha256=%s\nkdf=pbkdf2-sha256-iter%s\ncipher=aes-256-cbc\nfiles=%s\n' \
    "$(date -u +%FT%TZ)" "$SHA" "$ITER" \
    "$(ls "$DIR" | tr '\n' ',' )" > "$T/manifest.txt"
  path="${BASE#*//}"; path="${path#*/}"   # strip scheme+host → object path prefix
  domain="$(printf '%s' "$BASE" | sed -E 's#(https://[^/]+).*#\1#')"
  up() { curl -fsS "$R2_UPLOAD_URL" -H "Authorization: Bearer $R2_UPLOAD_TOKEN" \
          -F "file=@$1" -F "name=$2" -F "path=$path" -F "domain=$domain" >/dev/null; }
  up "$T/secrets.enc" "secrets.enc"
  up "$T/manifest.txt" "manifest.txt"
  echo "vault push ok: $BASE/secrets.enc (sha256 $SHA)"
  ;;
pull)
  DIR="${2:?secrets dir}"; BASE="${3:?vault url base}"
  PASS="${VAULT_PASSPHRASE:-$(prompt_pass no)}"
  T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
  curl -fsSL "$BASE/secrets.enc" -o "$T/secrets.enc"
  curl -fsSL "$BASE/manifest.txt" -o "$T/manifest.txt" || true
  if [ -f "$T/manifest.txt" ]; then
    want="$(sed -n 's/^sha256=//p' "$T/manifest.txt")"
    got="$(sha256sum "$T/secrets.enc" | awk '{print $1}')"
    [ -z "$want" ] || [ "$want" = "$got" ] || { echo "ciphertext sha mismatch" >&2; exit 1; }
  fi
  PASS_ENV="$PASS" openssl enc -d -aes-256-cbc -pbkdf2 -iter $ITER \
    -in "$T/secrets.enc" -out "$T/plain.tgz" -pass env:PASS_ENV \
    || { echo "decrypt failed (wrong passphrase?)" >&2; exit 1; }
  mkdir -p "$DIR"
  tar -C "$T" -xzf "$T/plain.tgz"
  cp -a "$T/$(basename "$DIR")/." "$DIR/"
  chmod 700 "$DIR"; find "$DIR" -type f -exec chmod 600 {} +
  echo "vault pull ok → $DIR (perms 700/600)"
  ;;
status)
  BASE="${2:?vault url base}"
  curl -fsSL "$BASE/manifest.txt"
  ;;
*) echo "unknown command: $CMD" >&2; exit 1 ;;
esac
