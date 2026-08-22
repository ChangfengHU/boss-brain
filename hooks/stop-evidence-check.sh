#!/usr/bin/env bash
# project-brains Stop hook: three deterministic gates before ending a turn
# that produced fresh commits in a brain workspace. Loop-safe.
#   gate 1  evidence exists and is at least as new as the work commits
#   gate 2  newest evidence line carries a machine-readable "wiki" judgment
#   gate 4  .brain/STATE.md exists and is no older than the work commits
#   gate 3  .brain/ has no uncommitted writes (收口)
set -u

INPUT="$(cat 2>/dev/null || true)"
read -r CWD ACTIVE SID <<EOF
$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
  d=json.load(sys.stdin)
  print(d.get("cwd",""), str(d.get("stop_hook_active",False)).lower(), d.get("session_id","-"))
except Exception:
  print("", "false", "-")' 2>/dev/null)
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

# Session-scoped work window: prefer the baseline HEAD recorded at SessionStart, so a commit
# from a concurrent session in the same repo is never blamed on this one. The 12h window
# survives only as a fallback for sessions whose start predates the baseline mechanism.
RANGE=""
BASE_FILE="/tmp/project-brains/session-${SID}.head"
if [ -f "$BASE_FILE" ]; then
  read -r BASE_ROOT BASE_HEAD < "$BASE_FILE" || true
  if [ "$BASE_ROOT" = "$ROOT" ] && git -C "$ROOT" cat-file -e "${BASE_HEAD}^{commit}" 2>/dev/null; then
    RANGE="${BASE_HEAD}..HEAD"
    [ -z "$(git -C "$ROOT" rev-list "$RANGE" 2>/dev/null)" ] && exit 0   # this session committed nothing
  fi
fi
if [ -n "$RANGE" ]; then
  LAST_COMMIT_TS="$(git -C "$ROOT" log -1 --format=%ct "$RANGE" 2>/dev/null || true)"
else
  LAST_COMMIT_TS="$(git -C "$ROOT" log -1 --since=12.hours --format=%ct 2>/dev/null || true)"
fi
[ -n "$LAST_COMMIT_TS" ] || exit 0                   # no session commits → nothing to enforce

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
  if [ -n "$RANGE" ]; then SHORT="$(git -C "$ROOT" log --oneline "$RANGE" | head -5)"
  else SHORT="$(git -C "$ROOT" log --since=12.hours --oneline | head -5)"; fi
  block "project-brains 收工检查: 本工作空间有新 commit 但未落证据记录。请向 .brain/evidence.jsonl(或对应任务目录)追加一条含真实验证命令与 exit code、且带 wiki 判断字段的 JSON 证据,并向 .brain/dev-log/<今天日期>.md 追加一段人读记录,再结束回合。近期 commit:
$SHORT"
fi

# gate 2: wiki judgment must be explicit on the newest evidence line
if [ -n "$NEWEST" ] && ! tail -1 "$NEWEST" 2>/dev/null | grep -q '"wiki"'; then
  block "project-brains 收工检查: 最新证据缺少 wiki 判断字段。请回答必答题——本会话是否产生了 ①被用户纠正的认知 ②多轮试错才打通的方法 ③对外部系统的考古结论 之一?有则先沉淀 .brain/wiki/ 词条并在证据行补 \"wiki\":\"<slug>\";确实没有则补 \"wiki\":\"none\"。然后再结束回合。"
fi

# gate 4: 状态卡必须反映本会话的变化
# 为什么:boss 的 @项目名 注入读的就是这一页。过期的状态卡比没有状态卡更危险——
# 它会让下一个会话拿着错误认知自信地动手。
STATE="$ROOT/.brain/STATE.md"
if [ ! -f "$STATE" ]; then
  block "project-brains 收工检查: 本工作空间有新 commit 但没有状态卡 .brain/STATE.md。请写一页(定位/现状/下一步/阻塞/关键路径/雷区,≤1 页,写方法不写会过期的数字),再结束回合。这一页是换会话、换机器时别人唯一会读的东西。"
fi
ST_TS="$(stat -c %Y "$STATE" 2>/dev/null || stat -f %m "$STATE" 2>/dev/null || echo 0)"
ST_COMMIT_TS="$(git -C "$ROOT" log -1 --format=%ct -- .brain/STATE.md 2>/dev/null || echo 0)"
[ -n "$ST_COMMIT_TS" ] && [ "$ST_COMMIT_TS" -gt "$ST_TS" ] && ST_TS="$ST_COMMIT_TS"
if [ "$LAST_COMMIT_TS" -gt "$ST_TS" ]; then
  block "project-brains 收工检查: 本会话有新 commit,但状态卡 .brain/STATE.md 比它旧。请更新状态卡的「现状」与「下一步」——只改真变了的部分,别重写整页,再结束回合。"
fi

# gate 3: .brain writes must be committed (收口), not left dirty
if [ -n "$(git -C "$ROOT" status --porcelain -- .brain 2>/dev/null)" ]; then
  block "project-brains 收工检查: .brain/ 有未提交的写入。请把本会话的 brain 写入(证据/dev-log/wiki)并入本次任务 commit 或合成一个 docs(brain) commit(本机规范:commit 完立即 push),再结束回合。"
fi

exit 0
