#!/usr/bin/env bash
# project-brains doctor: verify installation state, per component, per tool.
set -u
FAIL=0
ok()   { printf 'PASS  %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; FAIL=1; }
skip() { printf 'SKIP  %s\n' "$1"; }

has_block() { grep -q 'project-brains:begin' "$1" 2>/dev/null; }

# shared runtime
[ -x "$HOME/.project-brains/hooks/session-start.sh" ] \
  && ok "runtime: hook 脚本存在且可执行" || bad "runtime: hook 脚本缺失/不可执行"
[ -f "$HOME/.project-brains/registry.tsv" ] \
  && ok "runtime: registry 存在" || bad "runtime: registry 缺失"

# hook script sanity: picker branch + brain branch
out="$(echo '{"cwd":"/nonexistent-dir-xyz"}' | "$HOME/.project-brains/hooks/session-start.sh" 2>/dev/null)"
echo "$out" | grep -q '未绑定任何项目工作空间' \
  && ok "hook: 无 brain 目录 → 输出工作空间选择提示" || bad "hook: picker 分支异常"

tmp="$(mktemp -d)"; mkdir -p "$tmp/.brain"
printf 't-1 测试任务 active\nt-2 另一个 active\n' > "$tmp/.brain/TASKS.md"
out="$(printf '{"cwd":"%s"}' "$tmp" | "$HOME/.project-brains/hooks/session-start.sh" 2>/dev/null)"
echo "$out" | grep -q '已有 brain' && echo "$out" | grep -q '不要自动挑' \
  && ok "hook: 有 brain + 多活跃任务 → 加载并提示选择" || bad "hook: brain 分支异常"
rm -rf "$tmp"

tmp="$(mktemp -d)"; mkdir -p "$tmp/.brain"
printf -- '- [ ] 待办一\n- [ ] 待办二\n- [x] 已完成的 active focus 段落\n' > "$tmp/.brain/TASKS.md"
out="$(printf '{"cwd":"%s"}' "$tmp" | "$HOME/.project-brains/hooks/session-start.sh" 2>/dev/null)"
echo "$out" | grep -q '活跃任务 2 个' && ! echo "$out" | grep -q '已完成的' \
  && ok "hook: checkbox 格式任务解析正确(不误匹配 active 字样)" || bad "hook: checkbox 格式解析错误"
rm -rf "$tmp"

# per tool
check_tool() { # $1=label $2=config $3=skills_dir(optional "")
  local label="$1" cfg="$2" skills="$3"
  if [ ! -e "$(dirname "$cfg")" ]; then skip "$label: 未安装该工具"; return; fi
  has_block "$cfg" && ok "$label: 宪法块存在 ($cfg)" || bad "$label: 宪法块缺失 ($cfg)"
  if [ -n "$skills" ]; then
    [ -f "$skills/project-brains/SKILL.md" ] \
      && ok "$label: skill 已安装" || bad "$label: skill 缺失"
  fi
}
check_tool "claude"   "$HOME/.claude/CLAUDE.md"           "$HOME/.claude/skills"
check_tool "codex"    "$HOME/.codex/AGENTS.md"            "$HOME/.codex/skills"
check_tool "opencode" "$HOME/.config/opencode/AGENTS.md"  "$HOME/.config/opencode/skills"
check_tool "pi-agent" "$HOME/.pi/agent/AGENTS.md"         "$HOME/.pi/agent/skills"

# commands
[ -f "$HOME/.claude/commands/handoff.md" ] && [ -f "$HOME/.claude/commands/takeover.md" ] \
  && ok "claude: /handoff /takeover 命令已安装" || bad "claude: 命令缺失"
[ ! -d "$HOME/.codex" ] || { [ -f "$HOME/.codex/prompts/takeover.md" ] \
  && ok "codex: /handoff /takeover 命令已安装" || bad "codex: 命令缺失"; }

# claude hook registration
if [ -f "$HOME/.claude/settings.json" ]; then
  python3 -c '
import json,sys,os
cfg=json.load(open(os.path.expanduser("~/.claude/settings.json")))
cmds=[h.get("command","") for e in cfg.get("hooks",{}).get("SessionStart",[]) for h in e.get("hooks",[])]
sys.exit(0 if any("project-brains" in c for c in cmds) else 1)' \
    && ok "claude: SessionStart hook 已注册" || bad "claude: SessionStart hook 未注册"
fi

exit $FAIL
