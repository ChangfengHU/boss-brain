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
# 项目名以 boss 登记表为单一事实来源(session-start 同款优先级),brain 自家两列表只做兜底
SOURCE=""
for REG in "$HOME/.boss/registry.tsv" "$HOME/.project-brains/registry.tsv"; do
  [ -f "$REG" ] || continue
  SOURCE="$(awk -F'\t' -v r="$ROOT" '$0 !~ /^#/ && $1 == r {print $2; exit}' "$REG")"
  [ -n "$SOURCE" ] && break
done
[ -n "$SOURCE" ] || SOURCE="$(basename "$ROOT")"
QUEUE="$HOME/.project-brains/wiki-sync-queue"

src_for() { # $1=md file path → 该文件所属项目的名字(按路径反查登记表,兜底 basename)
  local root="${1%/.brain/wiki/*}" s=""
  for reg in "$HOME/.boss/registry.tsv" "$HOME/.project-brains/registry.tsv"; do
    [ -f "$reg" ] || continue
    s="$(awk -F'\t' -v r="$root" '$0 !~ /^#/ && $1 == r {print $2; exit}' "$reg")"
    [ -n "$s" ] && break
  done
  printf '%s' "${s:-$(basename "$root")}"
}

push_one() { # $1=md file path → 0 ok / 1 fail / 2 skipped
  # source 按文件自身路径定,不用当前项目的 SOURCE:队列里可能躺着别的项目的失败词条,
  # 用当前项目名会"冒名顶替"、再被同 slug 覆盖(2026-08-25 二轮审计)。
  local f="$1" slug title src idx
  slug="$(basename "$f" .md)"
  case "$slug" in index|log) return 2;; esac
  head -5 "$f" | grep -q '^sync: *false' && return 2
  # leak guard: never ship anything that smells like a secret/asset credential
  if grep -qE 'cfk_[A-Za-z0-9]{20,}|BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{30,}|(password|passwd|secret) *[:=] *[^ ]{8,}' "$f"; then
    echo "  SKIP(防泄闸) $slug" >&2; return 2
  fi
  src="$(src_for "$f")"
  title="$(grep -m1 '^# ' "$f" | sed 's/^# //')"
  [ -n "$title" ] || title="$slug"
  local hook=""
  idx="$(dirname "$f")/index.md"
  [ -f "$idx" ] && hook="$(grep -m1 -- "$slug" "$idx" | sed 's/.*— *//' | head -c 120)"
  SLUG="$slug" TITLE="$title" HOOK="$hook" SRC="$src" F="$f" python3 - <<'PY'
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
# retry queued files first。三条纪律(2026-08-25 审计):
#   ①队列先去重——此前失败一次追加一行,重试与主循环还会双推;
#   ②本项目 wiki 目录下的文件跳过重试(主循环马上会推,同轮不推两遍);
#   ③rc=2(index/防泄闸这类永久跳过)直接出队,不再无限滞留。
if [ -f "$QUEUE" ]; then
  sort -u "$QUEUE" -o "$QUEUE" 2>/dev/null || true
  TMPQ="$(mktemp)"; while IFS= read -r qf; do
    [ -f "$qf" ] || continue
    case "$qf" in "$ROOT/.brain/wiki/"*) continue;; esac
    push_one "$qf"; rc=$?
    case $rc in 0) OK=$((OK+1));; 2) : ;; *) echo "$qf" >> "$TMPQ";; esac
  done < "$QUEUE"
  mv "$TMPQ" "$QUEUE"
fi
for f in "$ROOT/.brain/wiki/"*.md; do
  [ -f "$f" ] || continue
  push_one "$f"; rc=$?
  case $rc in 0) OK=$((OK+1));; 2) SKIP=$((SKIP+1));;
    *) FAIL=$((FAIL+1)); grep -qxF "$f" "$QUEUE" 2>/dev/null || echo "$f" >> "$QUEUE";; esac
done
[ -s "$QUEUE" ] || rm -f "$QUEUE" 2>/dev/null
echo "[wiki-sync] $SOURCE: 推送 $OK,跳过 $SKIP,失败入队 $FAIL"
exit 0
