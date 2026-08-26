#!/usr/bin/env bash
# project-brains Stop hook: deterministic gates before ending a turn that produced
# fresh commits in a brain workspace. Loop-safe.
#   gate 1  evidence exists and is at least as new as the work commits
#   gate 2  newest evidence line carries a machine-readable "wiki" judgment
#   gate 4  .brain/STATE.md exists and is no older than the work commits
#   gate 5  .brain/capabilities.tsv exists and is not the untouched template
#   gate 3  .brain/ has no uncommitted writes (收口)
#   gate 3b 无工作 commit 的会话若写了 .brain(如「记下来」),同样必须收口
#
# 覆盖面(2026-08-25 r3):cwd 在仓内 → 查该仓;cwd 不在仓内(home 开场 @ 项目名干活的
# 旗舰工作流)→ 遍历本会话认领过的仓(boss-touched)逐个查——此前该场景五道 gate 全旁路。
# 认领判定:无本仓基线且未认领 → 放行(cd 路过别的会话的在途仓不背锅)。
# 拦截协议:stderr + exit 2 —— CC 与 codex 双端实测通吃(JSON decision 是 CC 专用,弃用)。
set -u

PB_STATE="${PB_STATE_DIR:-$HOME/.project-brains/state}"

INPUT="$(cat 2>/dev/null || true)"
# 逐行取字段:cwd 含空格时一次性 read 会错位 → 门禁静默关闭(二轮审计)
PARSED="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try:
  d=json.load(sys.stdin)
  print(d.get("cwd",""))
  print(str(d.get("stop_hook_active",False)).lower())
  print(d.get("session_id","nosid") or "nosid")
except Exception:
  print(); print("false"); print("nosid")' 2>/dev/null)"
CWD="$(printf '%s\n' "$PARSED" | sed -n 1p)"
ACTIVE="$(printf '%s\n' "$PARSED" | sed -n 2p)"
SID="$(printf '%s\n' "$PARSED" | sed -n 3p)"
[ "${ACTIVE:-false}" = "true" ] && exit 0   # already continued once; never loop
[ -n "${CWD:-}" ] || CWD="$PWD"

block() { # $1=reason → stderr + exit 2(双 agent 通用协议)
  printf '%s\n' "$1" >&2
  exit 2
}

check_workspace() { # $1=仓库根;干净则 return 0,有债则 block(exit 2)
  local ROOT="$1"
  [ -n "$ROOT" ] && [ -d "$ROOT/.brain" ] || return 0

  # gate 3b:会话没有工作 commit 时的唯一检查——.brain 写入也必须收口。
  brain_dirty_check() {
    if [ -n "$(git -C "$ROOT" status --porcelain -- .brain 2>/dev/null)" ]; then
      block "project-brains 收工检查: 本会话没有工作 commit,但 $ROOT/.brain 有未提交写入(如「记下来」的 wiki 词条)。不 commit 就等于没记——请合成一个 docs(brain) commit(本机规范:commit 完立即 push),再结束回合。"
    fi
    return 0
  }

  # Session-scoped work window: baseline HEAD recorded at SessionStart.
  local RANGE="" BASE_LINE BASE_HEAD BASE_ROOT
  local BASE_FILE="$PB_STATE/session-${SID}.head"
  if [ -f "$BASE_FILE" ]; then
    # 格式 "ROOT HEAD":ROOT 可含空格,HEAD 必是最后一个字段
    BASE_LINE="$(head -1 "$BASE_FILE" 2>/dev/null || true)"
    BASE_HEAD="${BASE_LINE##* }"; BASE_ROOT="${BASE_LINE% *}"
    if [ "$BASE_ROOT" = "$ROOT" ] && git -C "$ROOT" cat-file -e "${BASE_HEAD}^{commit}" 2>/dev/null; then
      RANGE="${BASE_HEAD}..HEAD"
      if [ -z "$(git -C "$ROOT" rev-list "$RANGE" 2>/dev/null)" ]; then
        brain_dirty_check; return 0     # 本会话没提交 → 只查 .brain 收口
      fi
    fi
  fi

  # 认领判定:没有本仓基线 = 会话不是在这里开场的。只有本会话 @ 认领过它才用
  # 兜底窗审计;否则多半是 cd 路过别的会话的在途仓——谁的仓谁负责,放行。
  if [ -z "$RANGE" ]; then
    grep -qxF "$ROOT" "$PB_STATE/boss-touched-${SID}" 2>/dev/null || return 0
  fi

  # 工作判据:基线树 vs HEAD 树的 diff(不用 log -1 -- pathspec:git 历史简化会把
  # merge 藏掉、返回被合分支旧时间戳,gate1/gate4 双穿透——二轮收洞)。
  local LAST_COMMIT_TS
  if [ -n "$RANGE" ]; then
    if [ -n "$(git -C "$ROOT" diff --name-only "$BASE_HEAD" HEAD -- . ':(exclude).brain' 2>/dev/null | head -1)" ]; then
      LAST_COMMIT_TS="$(git -C "$ROOT" log -1 --format=%ct "$RANGE" 2>/dev/null || true)"
    else
      LAST_COMMIT_TS=""
    fi
  else
    LAST_COMMIT_TS="$(git -C "$ROOT" log -1 --full-history --since=12.hours --format=%ct -- . ':(exclude).brain' 2>/dev/null || true)"
  fi
  if [ -z "$LAST_COMMIT_TS" ]; then
    brain_dirty_check; return 0
  fi

  # newest evidence: file mtimes + last commit touching the evidence files
  # (只认证据文件的 commit:STATE-only 提交顶不掉时间戳——二轮收洞)
  local EV_TS=0 NEWEST="" t BRAIN_TS f
  for f in "$ROOT/.brain/evidence.jsonl" "$ROOT/.brain/tasks"/*/evidence.jsonl; do
    [ -f "$f" ] || continue
    t="$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo 0)"
    if [ "$t" -gt "$EV_TS" ]; then EV_TS="$t"; NEWEST="$f"; fi
  done
  BRAIN_TS="$(git -C "$ROOT" log -1 --format=%ct -- .brain/evidence.jsonl '.brain/tasks/*/evidence.jsonl' 2>/dev/null || echo 0)"
  [ -n "$BRAIN_TS" ] && [ "$BRAIN_TS" -gt "$EV_TS" ] && EV_TS="$BRAIN_TS"

  # gate 1: evidence freshness
  if [ "$LAST_COMMIT_TS" -gt "$EV_TS" ]; then
    local SHORT
    if [ -n "$RANGE" ]; then SHORT="$(git -C "$ROOT" log --oneline "$RANGE" | head -5)"
    else SHORT="$(git -C "$ROOT" log --since=12.hours --oneline | head -5)"; fi
    block "project-brains 收工检查: 工作空间 $ROOT 有新 commit 但未落证据记录。请向 .brain/evidence.jsonl(或对应任务目录)追加一条 JSON 证据(示例:{\"date\":\"今天\",\"task\":\"…\",\"summary\":\"…\",\"verify\":\"真实验证命令 → 结果\",\"exit\":0,\"wiki\":\"none\"};wiki 字段见下一关,确实没有教训就写 none),并向 .brain/dev-log/<今天日期>.md 追加一段人读记录。
收工完整清单(一次做完,别等逐关拦):①证据行(含 wiki 判断字段)②dev-log ③状态卡「现状/下一步」刷新 ④能力声明(仅首次)⑤.brain 收口 commit 并 push(游离 HEAD 上先切回分支)。
若下面这些 commit 不是本会话做的——同一仓库可能有并行会话在写——不要代写证据、不要代推送,向用户说明即可。近期 commit:
$SHORT"
  fi

  # gate 2: wiki judgment must be explicit on the newest evidence line
  if [ -n "$NEWEST" ] && ! tail -1 "$NEWEST" 2>/dev/null | grep -q '"wiki"'; then
    block "project-brains 收工检查: $ROOT 最新证据缺少 wiki 判断字段。请回答必答题——本会话是否产生了 ①被用户纠正的认知 ②多轮试错才打通的方法 ③对外部系统的考古结论 之一?有则先沉淀 .brain/wiki/ 词条并在证据行补 \"wiki\":\"<词条文件名,如 douyin-image-403>\";确实没有则补 \"wiki\":\"none\"。然后再结束回合。"
  fi

  # gate 4: 状态卡必须反映本会话的变化(boss 的 @项目名 注入读的就是这一页)
  local STATE="$ROOT/.brain/STATE.md" ST_TS ST_COMMIT_TS
  if [ ! -f "$STATE" ]; then
    block "project-brains 收工检查: 工作空间 $ROOT 有新 commit 但没有状态卡 .brain/STATE.md。请写一页(定位/现状/下一步/阻塞/关键路径/雷区,≤1 页,写方法不写会过期的数字),再结束回合。这一页是换会话、换机器时别人唯一会读的东西。"
  fi
  ST_TS="$(stat -c %Y "$STATE" 2>/dev/null || stat -f %m "$STATE" 2>/dev/null || echo 0)"
  ST_COMMIT_TS="$(git -C "$ROOT" log -1 --format=%ct -- .brain/STATE.md 2>/dev/null || echo 0)"
  [ -n "$ST_COMMIT_TS" ] && [ "$ST_COMMIT_TS" -gt "$ST_TS" ] && ST_TS="$ST_COMMIT_TS"
  if [ "$LAST_COMMIT_TS" -gt "$ST_TS" ]; then
    block "project-brains 收工检查: $ROOT 有本会话的新 commit,但状态卡 .brain/STATE.md 比它旧。请更新状态卡的「现状」与「下一步」——只改真变了的部分,别重写整页,再结束回合。"
  fi

  # gate 5: 能力声明必须存在且不是原样模板(boss 能力图的地基;只把守有没有、改没改)
  local CAPS="$ROOT/.brain/capabilities.tsv"
  if [ ! -f "$CAPS" ]; then
    block "project-brains 收工检查: 工作空间 $ROOT 没有能力声明 .brain/capabilities.tsv。请写一份(4 列制表符:方向/能力id/端点或位置/一句话;模板在 ~/.boss/templates/capabilities.tsv,注释自带示例)——确实没有对外接口就只留表头注释。boss 的能力图靠各项目自己的声明推导,缺了这一份,跨项目改动影响就看不见。写完并入 brain commit,再结束回合。"
  fi
  if grep -q '这里换成真的' "$CAPS" 2>/dev/null; then
    block "project-brains 收工检查: $ROOT/.brain/capabilities.tsv 还是没改过的模板(含「这里换成真的」占位)。请换成本项目真实的 provides/consumes 声明,再结束回合。"
  fi

  # gate 3: .brain writes must be committed (收口), not left dirty
  if [ -n "$(git -C "$ROOT" status --porcelain -- .brain 2>/dev/null)" ]; then
    block "project-brains 收工检查: $ROOT/.brain 有未提交的写入。请把本会话的 brain 写入(证据/dev-log/wiki)并入本次任务 commit 或合成一个 docs(brain) commit(本机规范:commit 完立即 push),再结束回合。"
  fi
  return 0
}

CWD_ROOT="$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || true)"
if [ -n "$CWD_ROOT" ]; then
  check_workspace "$CWD_ROOT"
else
  # 旗舰工作流:home 开场、@项目名 进仓干活——cwd 不在仓里,但认领过的仓照样要收工
  TOUCHF="$PB_STATE/boss-touched-${SID}"
  if [ -f "$TOUCHF" ]; then
    while IFS= read -r p; do
      [ -n "$p" ] && [ -d "$p/.brain" ] || continue
      check_workspace "$p"
    done < "$TOUCHF"
  fi
fi
exit 0
