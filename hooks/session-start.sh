#!/usr/bin/env bash
# project-brains SessionStart hook: workspace binding reminder / brain context loader.
# Reads Claude Code hook JSON on stdin, prints context to stdout (injected into session).
set -u

INPUT="$(cat 2>/dev/null || true)"
CWD="$(printf '%s' "$INPUT" | python3 -c 'import sys,json
try: print(json.load(sys.stdin).get("cwd",""))
except Exception: print("")' 2>/dev/null)"
[ -z "$CWD" ] && CWD="$PWD"

REGISTRY="$HOME/.project-brains/registry.tsv"

brain_dir=""
if [ -d "$CWD/.brain" ]; then
  brain_dir="$CWD/.brain"
elif [ -f "$CWD/.brain-home" ]; then
  home_ref="$(head -1 "$CWD/.brain-home" | tr -d '\r')"
  echo "[project-brains] 本项目的 brain 托管在别处: ${home_ref}。所有记录写到那边,本地不建 .brain/。"
  exit 0
fi

if [ -n "$brain_dir" ]; then
  echo "[project-brains] 工作空间: $CWD (已有 brain)"
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

# No brain here → workspace picker.
echo "[project-brains] 当前目录 $CWD 未绑定任何项目工作空间。"
echo "在开始开发类任务前,先问用户本次要开发哪个项目(纯问答/闲聊则无需问):"
if [ -s "$REGISTRY" ]; then
  echo "已登记项目:"
  awk -F'\t' '{printf "  - %s (%s)\n", $2, $1}' "$REGISTRY" | head -15
fi
echo "  - 或用户指定一个本地目录路径"
echo "  - 或用户指定一个 GitHub 仓库(clone 到 ~/projects/<名称>)"
echo "不要默认把当前目录当工作空间。细节见 project-brains skill。"
exit 0
