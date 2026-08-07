#!/usr/bin/env bash
# project-brains wiki-sync: push local .brain/wiki entries to the central llm-wiki.
# Deterministic write-path (no judgment): entry quality was already gated at ingest time.
# Usage: wiki-sync.sh [project-root]   (default: git root of cwd)
# Config: ~/.project-brains/wiki-sync.env  (WIKI_SYNC_URL, WIKI_SYNC_TOKEN). Absent → silent no-op.
set -u
ENVF="$HOME/.project-brains/wiki-sync.env"
[ -f "$ENVF" ] || exit 0
# shellcheck disable=SC1090
set -a; . "$ENVF"; set +a
[ -n "${WIKI_SYNC_URL:-}" ] && [ -n "${WIKI_SYNC_TOKEN:-}" ] || exit 0

ROOT="${1:-$(git rev-parse --show-toplevel 2>/dev/null)}"
[ -n "$ROOT" ] && [ -d "$ROOT/.brain/wiki" ] || exit 0
SOURCE="$(grep -P "^$(printf '%s' "$ROOT")\t" "$HOME/.project-brains/registry.tsv" 2>/dev/null | head -1 | cut -f2)"
[ -n "$SOURCE" ] || SOURCE="$(basename "$ROOT")"
QUEUE="$HOME/.project-brains/wiki-sync-queue"

push_one() { # $1=md file path → 0 ok / 1 fail / 2 skipped
  local f="$1" slug title
  slug="$(basename "$f" .md)"
  case "$slug" in index|log) return 2;; esac
  head -5 "$f" | grep -q '^sync: *false' && return 2
  # leak guard: never ship anything that smells like a secret/asset credential
  if grep -qE 'cfk_[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{30,}|(password|passwd|secret) *[:=] *[^ ]{8,}' "$f"; then
    echo "  SKIP(防泄闸) $slug" >&2; return 2
  fi
  title="$(grep -m1 '^# ' "$f" | sed 's/^# //')"
  [ -n "$title" ] || title="$slug"
  local hook=""
  [ -f "$ROOT/.brain/wiki/index.md" ] && hook="$(grep -m1 -- "$slug" "$ROOT/.brain/wiki/index.md" | sed 's/.*— *//' | head -c 120)"
  SLUG="$slug" TITLE="$title" HOOK="$hook" SRC="$SOURCE" F="$f" python3 - <<'PY'
import json,os,sys,urllib.request,datetime
body=json.dumps({"source":os.environ["SRC"],"slug":os.environ["SLUG"],"title":os.environ["TITLE"],
  "hook":os.environ["HOOK"],"tags":[],"date":datetime.date.fromtimestamp(os.path.getmtime(os.environ["F"])).isoformat(),
  "md":open(os.environ["F"]).read()}).encode()
req=urllib.request.Request(os.environ["WIKI_SYNC_URL"].rstrip("/")+"/api/ingest",data=body,
  headers={"Content-Type":"application/json","Authorization":"Bearer "+os.environ["WIKI_SYNC_TOKEN"],"User-Agent":"project-brains-wiki-sync/1.0"},method="POST")
try:
    r=json.load(urllib.request.urlopen(req,timeout=15))
    sys.exit(0 if r.get("ok") else 1)
except Exception:
    sys.exit(1)
PY
}

OK=0; FAIL=0; SKIP=0
# retry queued files first
if [ -f "$QUEUE" ]; then
  TMPQ="$(mktemp)"; while IFS= read -r qf; do
    [ -f "$qf" ] || continue
    if push_one "$qf"; then OK=$((OK+1)); else echo "$qf" >> "$TMPQ"; fi
  done < "$QUEUE"
  mv "$TMPQ" "$QUEUE"; [ -s "$QUEUE" ] || rm -f "$QUEUE"
fi
for f in "$ROOT/.brain/wiki/"*.md; do
  [ -f "$f" ] || continue
  push_one "$f"; rc=$?
  case $rc in 0) OK=$((OK+1));; 2) SKIP=$((SKIP+1));;
    *) FAIL=$((FAIL+1)); echo "$f" >> "$QUEUE";; esac
done
echo "[wiki-sync] $SOURCE: 推送 $OK,跳过 $SKIP,失败入队 $FAIL"
exit 0
