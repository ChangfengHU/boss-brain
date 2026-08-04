#!/usr/bin/env bash
# project-brains Stop hook: block ending the turn when fresh commits in the
# bound workspace have no evidence record yet. Deterministic, loop-safe.
set -u

INPUT="$(cat 2>/dev/null || true)"
read -r CWD ACTIVE <<EOF
$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
  d=json.load(sys.stdin)
  print(d.get("cwd",""), str(d.get("stop_hook_active",False)).lower())
except Exception:
  print("", "false")' 2>/dev/null)
EOF
[ "${ACTIVE:-false}" = "true" ] && exit 0   # already continued once; never loop
[ -n "${CWD:-}" ] || exit 0

ROOT="$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || true)"
[ -n "$ROOT" ] && [ -d "$ROOT/.brain" ] || exit 0   # not a brain workspace → no enforcement

# newest commit in the last 12h (this session's work window, conservative)
LAST_COMMIT_TS="$(git -C "$ROOT" log -1 --since=12.hours --format=%ct 2>/dev/null || true)"
[ -n "$LAST_COMMIT_TS" ] || exit 0                   # no recent commits → nothing to enforce

# newest evidence mtime across single-task and per-task layouts
EV_TS=0
for f in "$ROOT/.brain/evidence.jsonl" "$ROOT/.brain/tasks"/*/evidence.jsonl; do
  [ -f "$f" ] || continue
  t="$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo 0)"
  [ "$t" -gt "$EV_TS" ] && EV_TS="$t"
done

if [ "$LAST_COMMIT_TS" -gt "$EV_TS" ]; then
  SHORT="$(git -C "$ROOT" log --since=12.hours --oneline | head -5)"
  python3 - "$SHORT" <<'PY'
import json, sys
print(json.dumps({
  "decision": "block",
  "reason": "project-brains 收工检查: 本工作空间有新 commit 但未落证据记录。"
            "请向 .brain/evidence.jsonl(或对应任务目录)追加一条含真实验证命令与 exit code 的 JSON 证据,"
            "再结束回合。近期 commit:\n" + sys.argv[1]
}, ensure_ascii=False))
PY
  exit 0
fi
exit 0
