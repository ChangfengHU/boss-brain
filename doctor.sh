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
for c in handoff takeover brain-init handoff-show backfill; do
  [ -f "$HOME/.claude/commands/$c.md" ] || { bad "claude: 命令 $c 缺失"; continue; }
done
[ -f "$HOME/.claude/commands/handoff-show.md" ] && ok "claude: 五命令已安装(handoff/takeover/brain-init/handoff-show/backfill)"
[ ! -d "$HOME/.codex" ] || { [ -f "$HOME/.codex/prompts/handoff-show.md" ] \
  && ok "codex: 五命令已安装" || bad "codex: 命令缺失"; }
for sd in "$HOME/.codex/skills" "$HOME/.config/opencode/skills"; do
  [ -d "$(dirname "$sd")" ] || continue
  miss=0; for c in brain-init takeover handoff handoff-show backfill; do [ -f "$sd/$c/SKILL.md" ] || miss=1; done
  [ "$miss" -eq 0 ] && ok "$(basename "$(dirname "$sd")"): 五命令 skill 形态已安装" || bad "$(basename "$(dirname "$sd")"): 命令 skill 缺失"
done

# stop hook behavior (5 deterministic cases: 3 gates + pass + anti-loop)
sh="$HOME/.project-brains/hooks/stop-evidence-check.sh"
if [ -x "$sh" ]; then
  tr="$(mktemp -d)"; ( cd "$tr" && git init -q -b main && git config user.email t@t && git config user.name t \
    && mkdir .brain && echo x > f && git add f && git commit -q -m t )
  o1="$(printf '{"cwd":"%s","stop_hook_active":false}' "$tr" | "$sh")"
  printf '%s' "$o1" | grep -q '"decision": *"block"' && ok "stop-hook: 有 commit 无证据 → block" || bad "stop-hook: 未拦截"
  sleep 1; printf '{"summary":"t","wiki":"none"}\n' > "$tr/.brain/evidence.jsonl"
  o2="$(printf '{"cwd":"%s","stop_hook_active":false}' "$tr" | "$sh")"
  printf '%s' "$o2" | grep -q '未提交' && ok "stop-hook: .brain 脏 → block(收口闸)" || bad "stop-hook: 收口闸失效"
  ( cd "$tr" && git add .brain && git commit -q -m brain )
  o3="$(printf '{"cwd":"%s","stop_hook_active":false}' "$tr" | "$sh")"
  [ -z "$o3" ] && ok "stop-hook: 证据齐+wiki已判+已收口 → 放行" || bad "stop-hook: 误拦截 ($o3)"
  o4="$(printf '{"cwd":"%s","stop_hook_active":true}' "$tr" | "$sh")"
  [ -z "$o4" ] && ok "stop-hook: stop_hook_active → 防循环放行" || bad "stop-hook: 循环风险"
  sleep 1; printf '{"summary":"no-wiki-field"}\n' > "$tr/.brain/evidence.jsonl"
  ( cd "$tr" && git add .brain && git commit -q -m brain2 )
  o5="$(printf '{"cwd":"%s","stop_hook_active":false}' "$tr" | "$sh")"
  printf '%s' "$o5" | grep -q 'wiki' && ok "stop-hook: 证据缺 wiki 判断 → block(wiki闸)" || bad "stop-hook: wiki闸失效"
  rm -rf "$tr"
else
  bad "stop-hook: 脚本缺失"
fi

# codex lifecycle hooks
if [ -d "$HOME/.codex" ]; then
  grep -q 'project-brains:hooks:begin' "$HOME/.codex/config.toml" 2>/dev/null \
    && ok "codex: 生命周期 hooks 已注册 (config.toml managed block)" || bad "codex: hooks 块缺失"
  out="$(echo '{"cwd":"/nonexistent-xyz"}' | "$HOME/.project-brains/hooks/codex-session-start.sh" 2>/dev/null)"
  printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["hookSpecificOutput"]["hookEventName"]=="SessionStart" and d["hookSpecificOutput"]["additionalContext"]' 2>/dev/null \
    && ok "codex: SessionStart 包装脚本输出合法 JSON" || bad "codex: 包装脚本输出异常"
fi

# authoring guides ship with skill
for gd in "$HOME/.claude/skills/project-brains/guides" "$HOME/.codex/skills/project-brains/guides"; do
  [ -d "$(dirname "$(dirname "$(dirname "$gd")")")" ] || continue
  n=$(ls "$gd"/*.md 2>/dev/null | wc -l)
  [ "$n" -ge 4 ] && ok "$(echo "$gd" | cut -d/ -f3): 写作指南已分发 ($n 篇)" || bad "$(echo "$gd" | cut -d/ -f3): 写作指南缺失"
done

# vault tooling
[ -x "$HOME/.project-brains/vault.sh" ] && ok "vault: 工具已就位" || bad "vault: 工具缺失"

# pi extension
[ ! -d "$HOME/.pi/agent" ] || { [ -f "$HOME/.pi/agent/extensions/project-brains.ts" ] \
  && ok "pi-agent: TS extension 已安装" || bad "pi-agent: extension 缺失"; }

# claude hook registration
if [ -f "$HOME/.claude/settings.json" ]; then
  for ev in SessionStart Stop; do
    python3 -c '
import json,sys,os
cfg=json.load(open(os.path.expanduser("~/.claude/settings.json")))
cmds=[h.get("command","") for e in cfg.get("hooks",{}).get(sys.argv[1],[]) for h in e.get("hooks",[])]
sys.exit(0 if any("project-brains" in c for c in cmds) else 1)' "$ev" \
      && ok "claude: $ev hook 已注册" || bad "claude: $ev hook 未注册"
  done
fi

exit $FAIL
