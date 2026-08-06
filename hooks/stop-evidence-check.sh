#!/usr/bin/env bash
# project-brains Stop hook: three deterministic gates before ending a turn
# that produced fresh commits in a brain workspace. Loop-safe.
#   gate 1  evidence exists and is at least as new as the work commits
#   gate 2  newest evidence line carries a machine-readable "wiki" judgment
#   gate 3  .brain/ has no uncommitted writes (收口)
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

block() { # $1=reason
  python3 - "$1" <<'PY'
import json, sys
print(json.dumps({"decision": "block", "reason": sys.argv[1]}, ensure_ascii=False))
PY
  exit 0
}

# newest commit in the last 12h (this session's work window, conservative)
LAST_COMMIT_TS="$(git -C "$ROOT" log -1 --since=12.hours --format=%ct 2>/dev/null || true)"
[ -n "$LAST_COMMIT_TS" ] || exit 0                   # no recent commits → nothing to enforce

# newest evidence: max of file mtimes and the last commit touching .brain
# (counting the .brain commit avoids re-blocking right after evidence is committed)
EV_TS=0; NEWEST=""
for f in "$ROOT/.brain/evidence.jsonl" "$ROOT/.brain/tasks"/*/evidence.jsonl; do
  [ -f "$f" ] || continue
  t="$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo 0)"
  if [ "$t" -gt "$EV_TS" ]; then EV_TS="$t"; NEWEST="$f"; fi
done
BRAIN_TS="$(git -C "$ROOT" log -1 --format=%ct -- .brain 2>/dev/null || echo 0)"
[ -n "$BRAIN_TS" ] && [ "$BRAIN_TS" -gt "$EV_TS" ] && EV_TS="$BRAIN_TS"

# gate 1: evidence freshness
if [ "$LAST_COMMIT_TS" -gt "$EV_TS" ]; then
  SHORT="$(git -C "$ROOT" log --since=12.hours --oneline | head -5)"
  block "project-brains 收工检查: 本工作空间有新 commit 但未落证据记录。请向 .brain/evidence.jsonl(或对应任务目录)追加一条含真实验证命令与 exit code、且带 wiki 判断字段的 JSON 证据,并向 .brain/dev-log/<今天日期>.md 追加一段人读记录,再结束回合。近期 commit:
$SHORT"
fi

# gate 2: wiki judgment must be explicit on the newest evidence line
if [ -n "$NEWEST" ] && ! tail -1 "$NEWEST" 2>/dev/null | grep -q '"wiki"'; then
  block "project-brains 收工检查: 最新证据缺少 wiki 判断字段。请回答必答题——本会话是否产生了 ①被用户纠正的认知 ②多轮试错才打通的方法 ③对外部系统的考古结论 之一?有则先沉淀 .brain/wiki/ 词条并在证据行补 \"wiki\":\"<slug>\";确实没有则补 \"wiki\":\"none\"。然后再结束回合。"
fi

# gate 3: .brain writes must be committed (收口), not left dirty
if [ -n "$(git -C "$ROOT" status --porcelain -- .brain 2>/dev/null)" ]; then
  block "project-brains 收工检查: .brain/ 有未提交的写入。请把本会话的 brain 写入(证据/dev-log/wiki)并入本次任务 commit 或合成一个 docs(brain) commit(本地即可,push 需用户同意),再结束回合。"
fi

exit 0
