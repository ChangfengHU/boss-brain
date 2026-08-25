#!/usr/bin/env bash
# project-brains Stop hook: three deterministic gates before ending a turn
# that produced fresh commits in a brain workspace. Loop-safe.
#   gate 1  evidence exists and is at least as new as the work commits
#   gate 2  newest evidence line carries a machine-readable "wiki" judgment
#   gate 4  .brain/STATE.md exists and is no older than the work commits
#   gate 5  .brain/capabilities.tsv exists and is not the untouched template
#   gate 3  .brain/ has no uncommitted writes (收口)
#   gate 3b 无工作 commit 的会话若写了 .brain(如「记下来」),同样必须收口——
#           纯问答会话不 commit 词条就等于没记(2026-08-23 真实测出的盲区)
set -u

INPUT="$(cat 2>/dev/null || true)"
# 逐行取字段,不用空格分隔的一次性 read:cwd 含空格会错位 → ROOT 解析失败 → 门禁静默关闭
# (2026-08-25 二轮审计实测;session-start.sh 一直是逐字段解析,此处对齐)
PARSED="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
  d=json.load(sys.stdin)
  print(d.get("cwd",""))
  print(str(d.get("stop_hook_active",False)).lower())
  print(d.get("session_id","-") or "-")
except Exception:
  print(); print("false"); print("-")' 2>/dev/null)"
CWD="$(printf '%s\n' "$PARSED" | sed -n 1p)"
ACTIVE="$(printf '%s\n' "$PARSED" | sed -n 2p)"
SID="$(printf '%s\n' "$PARSED" | sed -n 3p)"
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

# gate 3b:会话没有工作 commit 时的唯一检查——.brain 写入也必须收口。
# 「记下来」在纯问答会话里只写文件不 commit,词条留在工作区,机器一坏等于没记。
brain_dirty_or_exit() {
  if [ -n "$(git -C "$ROOT" status --porcelain -- .brain 2>/dev/null)" ]; then
    block "project-brains 收工检查: 本会话没有工作 commit,但 .brain/ 有未提交写入(如「记下来」的 wiki 词条)。不 commit 就等于没记——请合成一个 docs(brain) commit(本机规范:commit 完立即 push),再结束回合。"
  fi
  exit 0
}

# Session-scoped work window: prefer the baseline HEAD recorded at SessionStart, so a commit
# from a concurrent session in the same repo is never blamed on this one. The 12h window
# survives only as a fallback for sessions whose start predates the baseline mechanism.
RANGE=""
BASE_FILE="/tmp/project-brains/session-${SID}.head"
if [ -f "$BASE_FILE" ]; then
  # 格式是 "ROOT HEAD"(printf '%s %s'):ROOT 可能含空格,HEAD 必是最后一个字段
  BASE_LINE="$(head -1 "$BASE_FILE" 2>/dev/null || true)"
  BASE_HEAD="${BASE_LINE##* }"; BASE_ROOT="${BASE_LINE% *}"
  if [ "$BASE_ROOT" = "$ROOT" ] && git -C "$ROOT" cat-file -e "${BASE_HEAD}^{commit}" 2>/dev/null; then
    RANGE="${BASE_HEAD}..HEAD"
    [ -z "$(git -C "$ROOT" rev-list "$RANGE" 2>/dev/null)" ] && brain_dirty_or_exit   # 本会话没提交 → 只查 .brain 收口
  fi
fi
# 追责基准 = 本会话是否落了 .brain 之外的"工作改动"。纯 .brain 提交(收口词条/证据)
# 是记账不是工作,不该反过来要求为它再举证——否则收口本身会触发新一轮拦截。
# 2026-08-25 二轮收洞:不能用 `log -1 -- pathspec` 判(git 历史简化会把 merge 藏掉、
# 返回被合分支的旧时间戳,gate1/gate4 双穿透)。改为:基线树 vs HEAD 树的 diff 说了算,
# 时间戳取范围内最新提交(不带 pathspec,免疫简化)。
if [ -n "$RANGE" ]; then
  if [ -n "$(git -C "$ROOT" diff --name-only "$BASE_HEAD" HEAD -- . ':(exclude).brain' 2>/dev/null | head -1)" ]; then
    LAST_COMMIT_TS="$(git -C "$ROOT" log -1 --format=%ct "$RANGE" 2>/dev/null || true)"
  else
    LAST_COMMIT_TS=""
  fi
else
  # 12h 兜底窗(仅无基线的老会话走到):--full-history 尽量少被简化,尽力而为
  LAST_COMMIT_TS="$(git -C "$ROOT" log -1 --full-history --since=12.hours --format=%ct -- . ':(exclude).brain' 2>/dev/null || true)"
fi
[ -n "$LAST_COMMIT_TS" ] || brain_dirty_or_exit      # 12h 内无 commit → 只查 .brain 收口

# newest evidence: max of file mtimes and the last commit touching the evidence files
# (counting that commit avoids re-blocking right after evidence is committed).
# 2026-08-25 收洞:此前这里数的是"最后一个碰 .brain 的 commit"——只提交一次 STATE.md
# 就能把 EV_TS 顶到最新,工作 commit 可以零证据溜过 gate1。只认证据文件本身的 commit。
EV_TS=0; NEWEST=""
for f in "$ROOT/.brain/evidence.jsonl" "$ROOT/.brain/tasks"/*/evidence.jsonl; do
  [ -f "$f" ] || continue
  t="$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo 0)"
  if [ "$t" -gt "$EV_TS" ]; then EV_TS="$t"; NEWEST="$f"; fi
done
BRAIN_TS="$(git -C "$ROOT" log -1 --format=%ct -- .brain/evidence.jsonl '.brain/tasks/*/evidence.jsonl' 2>/dev/null || echo 0)"
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

# gate 5: 能力声明必须存在且不是原样模板
# 为什么:boss 的能力图(/boss-caps)从各项目自己的声明推导,不写这一份,
# 跨项目改动的影响就看不见。端点多为 URL/MCP 名,真伪查不了,只把守「有没有、改没改」。
CAPS="$ROOT/.brain/capabilities.tsv"
if [ ! -f "$CAPS" ]; then
  block "project-brains 收工检查: 本工作空间没有能力声明 .brain/capabilities.tsv。请写一份(4 列制表符:方向/能力id/端点或位置/一句话;模板在 boss 的 templates/capabilities.tsv)——确实没有对外接口就只留表头注释。boss 的能力图靠各项目自己的声明推导,缺了这一份,跨项目改动影响就看不见。写完并入 brain commit,再结束回合。"
fi
if grep -q '这里换成真的' "$CAPS" 2>/dev/null; then
  block "project-brains 收工检查: .brain/capabilities.tsv 还是没改过的模板(含「这里换成真的」占位)。请换成本项目真实的 provides/consumes 声明,再结束回合。"
fi

# gate 3: .brain writes must be committed (收口), not left dirty
if [ -n "$(git -C "$ROOT" status --porcelain -- .brain 2>/dev/null)" ]; then
  block "project-brains 收工检查: .brain/ 有未提交的写入。请把本会话的 brain 写入(证据/dev-log/wiki)并入本次任务 commit 或合成一个 docs(brain) commit(本机规范:commit 完立即 push),再结束回合。"
fi

exit 0
