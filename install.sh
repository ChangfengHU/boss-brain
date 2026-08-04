#!/usr/bin/env bash
# project-brains plugin installer v0.1.0
# Installs: ① constitution (always-on directives) into each detected tool's global
# config; ② SessionStart hook (Claude Code); ③ project-brains skill (lazy protocol).
# Idempotent: managed blocks are marker-wrapped and replaced on re-install.
set -euo pipefail

SRC="$(cd "$(dirname "$0")" && pwd)"
VERSION="$(cat "$SRC/VERSION" 2>/dev/null || echo dev)"
CONSTITUTION="$SRC/constitution/global-directives.md"
BEGIN='<!-- project-brains:begin (managed block, do not edit inside) -->'
END='<!-- project-brains:end -->'

say() { printf '%s\n' "$*"; }
REPORT=()

merge_block() { # $1=target file
  local target="$1" tmp
  mkdir -p "$(dirname "$target")"
  touch "$target"
  tmp="$(mktemp)"
  awk -v b="$BEGIN" -v e="$END" '
    $0==b {skip=1; next} $0==e {skip=0; next} !skip {print}
  ' "$target" >"$tmp"
  { cat "$tmp"; echo ""; echo "$BEGIN"; cat "$CONSTITUTION"; echo "$END"; } | \
    awk 'NF{blank=0} !NF{blank++} blank<2' >"$target"
  rm -f "$tmp"
}

install_skill() { # $1=skills dir
  mkdir -p "$1/project-brains"
  cp -r "$SRC/skill/project-brains/." "$1/project-brains/"
}

# ---------- shared runtime dir ----------
mkdir -p "$HOME/.project-brains/hooks"
touch "$HOME/.project-brains/registry.tsv"
cp "$SRC/hooks/session-start.sh" "$SRC/hooks/stop-evidence-check.sh" "$HOME/.project-brains/hooks/"
chmod +x "$HOME/.project-brains/hooks/"*.sh
cp "$SRC/scripts/vault.sh" "$HOME/.project-brains/vault.sh"
chmod +x "$HOME/.project-brains/vault.sh"
echo "$VERSION" > "$HOME/.project-brains/version"

install_commands() { # $1=commands dir
  mkdir -p "$1"
  cp "$SRC/commands/"*.md "$1/"
}

# ---------- Claude Code ----------
if [ -d "$HOME/.claude" ]; then
  merge_block "$HOME/.claude/CLAUDE.md"
  install_skill "$HOME/.claude/skills"
  install_commands "$HOME/.claude/commands"
  python3 - "$HOME/.claude/settings.json" "$HOME/.project-brains/hooks" <<'PY'
import json, sys, os
path, hookdir = sys.argv[1], sys.argv[2]
cfg = {}
if os.path.exists(path):
    with open(path) as f:
        cfg = json.load(f)
hooks = cfg.setdefault("hooks", {})
for event, script in [("SessionStart", "session-start.sh"),
                      ("Stop", "stop-evidence-check.sh")]:
    entries = hooks.setdefault(event, [])
    cmd = os.path.join(hookdir, script)
    if not any(h.get("command") == cmd
               for e in entries for h in e.get("hooks", [])):
        entries.append({"hooks": [{"type": "command", "command": cmd}]})
with open(path, "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
PY
  REPORT+=("claude   : 宪法 | skill | SessionStart+Stop hooks | /handoff /takeover /brain-init  [完整]")
else
  REPORT+=("claude   : 未检测到,跳过")
fi

# ---------- Codex ----------
if [ -d "$HOME/.codex" ]; then
  merge_block "$HOME/.codex/AGENTS.md"
  install_skill "$HOME/.codex/skills"
  install_commands "$HOME/.codex/prompts"
  REPORT+=("codex    : 宪法 ~/.codex/AGENTS.md | skill | /handoff /takeover  [降级: 无 hook,收工纪律靠宪法]")
else
  REPORT+=("codex    : 未检测到,跳过")
fi

# ---------- OpenCode ----------
if command -v opencode >/dev/null 2>&1 || [ -d "$HOME/.config/opencode" ]; then
  merge_block "$HOME/.config/opencode/AGENTS.md"
  install_skill "$HOME/.config/opencode/skills"
  REPORT+=("opencode : 宪法 ~/.config/opencode/AGENTS.md | skill  [降级: JS 插件 hook 在路线图]")
else
  REPORT+=("opencode : 未检测到,跳过(安装后重跑本脚本)")
fi

# ---------- pi-agent ----------
if [ -d "$HOME/.pi/agent" ]; then
  merge_block "$HOME/.pi/agent/AGENTS.md"
  install_skill "$HOME/.pi/agent/skills"
  mkdir -p "$HOME/.pi/agent/extensions"
  cp "$SRC/pi/project-brains.ts" "$HOME/.pi/agent/extensions/project-brains.ts"
  REPORT+=("pi-agent : 宪法 | skill | TS extension(session_start+before_agent_start)  [注入完整;严格类型检查通过,TUI 实跑待用户验证]")
else
  REPORT+=("pi-agent : 未检测到,跳过")
fi

# ---------- Gemini CLI (bonus) ----------
if [ -d "$HOME/.gemini" ]; then
  merge_block "$HOME/.gemini/GEMINI.md"
  REPORT+=("gemini   : 宪法 ~/.gemini/GEMINI.md  [降级: 无 hook]")
fi

say ""
say "project-brains v$VERSION 安装完成:"
for r in "${REPORT[@]}"; do say "  $r"; done
say ""
say "验证: bash $SRC/doctor.sh"
say "注意: hook 与宪法对新会话生效,当前已开的会话不受影响。"
