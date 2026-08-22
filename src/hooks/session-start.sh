#!/usr/bin/env bash
# project-brains SessionStart hook: workspace binding reminder / brain context loader.
# Reads Claude Code hook JSON on stdin, prints context to stdout (injected into session).
set -u

INPUT="$(cat 2>/dev/null || true)"
CWD="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("cwd",""))
except Exception: print("")' 2>/dev/null)"
[ -z "$CWD" ] && CWD="$PWD"

# 单一事实来源:boss 装了就用 boss 的登记表(5 列,带 kind),否则退回自己的。
# 两份表并存会分叉——boss 纳管的新项目开场看不到,这是踩过的坑。
REGISTRY="$HOME/.boss/registry.tsv"
[ -s "$REGISTRY" ] || REGISTRY="$HOME/.project-brains/registry.tsv"

# Brain root resolution (single scheme, mirrored by stop hook): cwd → git toplevel → .brain.
# Starting from /project/src/deep must still find /project/.brain.
ROOT="$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || true)"
[ -z "$ROOT" ] && ROOT="$CWD"
brain_dir=""
if [ -d "$ROOT/.brain" ]; then
  brain_dir="$ROOT/.brain"; CWD="$ROOT"
elif [ -f "$ROOT/.brain-home" ]; then
  home_ref="$(head -1 "$ROOT/.brain-home" | tr -d '\r')"
  echo "[project-brains] 本项目的 brain 托管在别处: ${home_ref}。所有记录写到那边,本地不建 .brain/。"
  exit 0
fi

# Session baseline: record HEAD so the stop hook audits exactly this session's commits,
# not "anything in the last 12h" (which misfires across concurrent sessions).
SID="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("session_id",""))
except Exception: print("")' 2>/dev/null)"
if [ -n "$SID" ] && [ -n "$ROOT" ] && git -C "$ROOT" rev-parse HEAD >/dev/null 2>&1; then
  mkdir -p /tmp/project-brains
  printf '%s %s\n' "$ROOT" "$(git -C "$ROOT" rev-parse HEAD)" > "/tmp/project-brains/session-$SID.head" 2>/dev/null || true
fi

if [ -n "$brain_dir" ]; then
  echo "[project-brains 背景信息,静默使用:不要向用户复述,不要因此改变用户当前任务的优先级]"
  echo "工作空间: $CWD (已有 brain)"
  if [ -f "$brain_dir/TASKS.md" ]; then
    # Two supported formats: markdown checkbox "- [ ] ..." and status suffix "... active".
    if grep -q '^- \[ \]' "$brain_dir/TASKS.md" 2>/dev/null; then
      pattern='^- \[ \]'
    else
      pattern=' active$'
    fi
    active="$(grep -cE "$pattern" "$brain_dir/TASKS.md" 2>/dev/null || echo 0)"
    echo "活跃任务 ${active} 个 (.brain/TASKS.md):"
    grep -E "$pattern" "$brain_dir/TASKS.md" 2>/dev/null | head -10
    if [ "${active:-0}" -gt 1 ]; then
      echo "提示: 多个活跃任务。用户只说\"继续\"时,列出清单让用户选,不要自动挑。"
    fi
  fi
  echo "接手前先读 .brain/HANDOFF.md;遇到难题先查 .brain/wiki/index.md(若存在)。"
  exit 0
fi

# No brain here → quiet registry hint. Facts only, never an instruction to interrupt the user.
echo "[project-brains 背景信息,静默使用:不要向用户复述,不要主动提起本段或建议运行任何 brain 命令]"
echo "当前目录 $CWD 未绑定项目工作空间。"
if [ -s "$REGISTRY" ]; then
  echo "本机已登记项目(仅供你推断用户指的是哪个,不要念给用户听):"
  awk -F'\t' '$0 !~ /^#/ && NF {printf "  - %s [%s] (%s)\n", $2, ($5==""?"local":$5), $1}' "$REGISTRY" | head -15
fi
echo "用户请求已指明项目/目录就直接照做;真的无法推断落在哪个项目时,才问一句。纯问答无需过问。"
exit 0
