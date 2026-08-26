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
echo "$out" | grep -q '未绑定项目工作空间' && echo "$out" | grep -q '不要向用户复述' \
  && ok "hook: 无 brain 目录 → 静默背景信息(不指令打断)" || bad "hook: picker 分支异常"
# 静默闸(反向断言):hook 一旦重新出现指令式打断措辞就 FAIL
echo "$out" | grep -qE '先问用户本次要开发哪个项目|在开始开发类任务前' \
  && bad "hook: 仍含喧宾夺主的指令式措辞" || ok "hook: 无指令式打断措辞(静默闸)"

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

# stop hook behavior(与 0.7.0 语义对齐:认领判定需要基线/touched,拦截协议 = stderr + exit 2;
# 探针自带 session_id 与基线夹具,状态目录隔离到临时 PB_STATE_DIR,不碰真会话状态)
sh="$HOME/.project-brains/hooks/stop-evidence-check.sh"
if [ -x "$sh" ]; then
  tr="$(mktemp -d)"; export PB_STATE_DIR="$tr/state"; mkdir -p "$PB_STATE_DIR"
  DSID="doctor-$$"
  ( cd "$tr" && git init -q -b main && git config user.email t@t && git config user.name t \
    && mkdir .brain && printf '# 卡\n## 现状\nx\n## 下一步\n1. x\n' > .brain/STATE.md \
    && printf 'provides\tdoc.thing\t-\t探针夹具\n' > .brain/capabilities.tsv \
    && git add -A && git commit -q -m init )
  printf '%s %s\n' "$tr" "$(git -C "$tr" rev-parse HEAD)" > "$PB_STATE_DIR/session-$DSID.head"
  ( cd "$tr" && echo work > f && git add f && git commit -q -m work )
  probe() { printf '{"cwd":"%s","stop_hook_active":%s,"session_id":"%s"}' "$tr" "$2" "$DSID" | "$sh" 2>&1; }
  o1="$(probe x false)"; rc=$?
  { [ "$rc" -ne 0 ] && printf '%s' "$o1" | grep -q '收工检查'; } && ok "stop-hook: 有 commit 无证据 → 拦截" || bad "stop-hook: 未拦截"
  sleep 1; printf '{"summary":"t","verify":"cmd → ok","exit":0,"wiki":"none"}\n' > "$tr/.brain/evidence.jsonl"
  touch "$tr/.brain/STATE.md"
  o2="$(probe x false)"; rc=$?
  { [ "$rc" -ne 0 ] && printf '%s' "$o2" | grep -q '未提交'; } && ok "stop-hook: .brain 脏 → 拦截(收口闸)" || bad "stop-hook: 收口闸失效"
  ( cd "$tr" && touch .brain/STATE.md && git add .brain && git commit -q -m brain )
  o3="$(probe x false)"; rc=$?
  { [ "$rc" -eq 0 ] && [ -z "$o3" ]; } && ok "stop-hook: 证据齐+已收口 → 放行" || bad "stop-hook: 误拦截 ($o3)"
  o4="$(probe x true)"; rc=$?
  [ "$rc" -eq 0 ] && ok "stop-hook: stop_hook_active → 防循环放行" || bad "stop-hook: 循环风险"
  sleep 1; printf '{"summary":"no-wiki-field"}\n' > "$tr/.brain/evidence.jsonl"
  ( cd "$tr" && touch .brain/STATE.md && git add .brain && git commit -q -m brain2 )
  o5="$(probe x false)"; rc=$?
  { [ "$rc" -ne 0 ] && printf '%s' "$o5" | grep -q 'wiki'; } && ok "stop-hook: 证据缺 wiki 判断 → 拦截(wiki闸)" || bad "stop-hook: wiki闸失效"
  unset PB_STATE_DIR; rm -rf "$tr"
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

# skill reference integrity: every guides/*.md a SKILL.md tells the model to read must exist
# next to it after install (P0: installed topology must match skill text).
for sd in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.config/opencode/skills"; do
  [ -d "$sd" ] || continue
  miss=""
  for sk in "$sd"/*/SKILL.md; do
    [ -f "$sk" ] || continue
    for r in $(grep -o 'guides/[a-z-]*\.md' "$sk" 2>/dev/null | sort -u); do
      [ -f "$(dirname "$sk")/$r" ] || miss="$miss $(basename "$(dirname "$sk")")/$r"
    done
  done
  [ -z "$miss" ] && ok "$(basename "$(dirname "$sd")"): skill 引用的 guides 全部真实存在" \
                 || bad "$(basename "$(dirname "$sd")"): skill 引用缺失:$miss"
done

# ledger lint (账本体检): a green install check must not vouch for a dirty ledger.
# Validates the repo this doctor runs from, when it has a brain.
if [ -f ".brain/evidence.jsonl" ]; then
  python3 - <<'PY'; [ $? -eq 0 ] && ok "账本: evidence 全部合法 JSON 且 commit 指针可解析" || bad "账本: evidence 存在坏行/断链/pending 指针"
import json,subprocess,sys
bad=0
for i,l in enumerate(open(".brain/evidence.jsonl",encoding="utf-8"),1):
    if not l.strip(): continue
    try: e=json.loads(l)
    except Exception: print(f"  行{i}: 非法 JSON"); bad=1; continue
    c=str(e.get("commit",""))
    if c in ("","pending"): print(f"  行{i}: commit 指针缺失/pending"); bad=1; continue
    if subprocess.run(["git","cat-file","-e",c+"^{commit}"],capture_output=True).returncode:
        print(f"  行{i}: commit {c} 不存在"); bad=1
sys.exit(bad)
PY
  if [ -d ".brain/wiki" ]; then
    python3 - <<'PY'; [ $? -eq 0 ] && ok "账本: 证据引用的 wiki 词条全部存在" || bad "账本: 证据引用了不存在的 wiki 词条"
import json,os,sys
bad=0
for i,l in enumerate(open(".brain/evidence.jsonl",encoding="utf-8"),1):
    if not l.strip(): continue
    try: w=str(json.loads(l).get("wiki",""))
    except Exception: continue
    if w and w not in ("none","") and not os.path.exists(f".brain/wiki/{w}.md"):
        print(f"  行{i}: wiki 词条 {w}.md 不存在"); bad=1
sys.exit(bad)
PY
  fi
fi

# vault + wiki-sync tooling
[ -x "$HOME/.project-brains/wiki-sync.sh" ] && ok "wiki-sync: 中央同步工具已就位" || bad "wiki-sync: 工具缺失"
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
