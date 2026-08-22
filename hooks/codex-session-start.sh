#!/usr/bin/env bash
# project-brains SessionStart hook — codex flavor.
# codex requires strict JSON output; wrap the shared plain-text hook in
# {"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":...}}.
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
INPUT="$(cat 2>/dev/null || true)"
TEXT="$(printf '%s' "$INPUT" | "$DIR/session-start.sh" 2>/dev/null || true)"
[ -n "$TEXT" ] || exit 0
printf '%s' "$TEXT" | python3 -c 'import json,sys
print(json.dumps({"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":sys.stdin.read()}},ensure_ascii=False))'
