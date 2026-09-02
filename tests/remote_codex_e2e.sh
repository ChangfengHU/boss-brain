#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CODEX_BIN=${CODEX_BIN:-codex}
AUTH_SOURCE=${CODEX_AUTH_SOURCE:-}
TEST_OWNER=${BOSS_TEST_OWNER:-boss-brain-test}

CODEX_DIR=$(CDPATH= cd -- "$(dirname -- "$CODEX_BIN")" 2>/dev/null && pwd || true)

if [ -z "$AUTH_SOURCE" ] || [ ! -f "$AUTH_SOURCE" ]; then
  echo "CODEX_AUTH_SOURCE must point to an existing Codex auth.json" >&2
  exit 2
fi
if ! command -v "$CODEX_BIN" >/dev/null 2>&1; then
  echo "Codex CLI is not installed" >&2
  exit 2
fi

SANDBOX_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/boss-codex-e2e.XXXXXX")
cleanup() {
  if [ "${BOSS_KEEP_E2E:-0}" = "1" ]; then
    echo "PRESERVED_E2E=$SANDBOX_ROOT" >&2
    return
  fi
  chmod -R u+rwX "$SANDBOX_ROOT" 2>/dev/null || true
  rm -rf -- "$SANDBOX_ROOT"
}
trap cleanup EXIT HUP INT TERM

export HOME="$SANDBOX_ROOT/home"
export CODEX_HOME="$HOME/.codex"
export BOSS_HOME="$HOME/.boss"
export PATH="${CODEX_DIR:+$CODEX_DIR:}$HOME/.local/bin:$PATH"
mkdir -p "$CODEX_HOME" "$HOME/work"
install -m 600 "$AUTH_SOURCE" "$CODEX_HOME/auth.json"

python3 "$ROOT/scripts/install.py" install --owner "$TEST_OWNER" >/dev/null

make_repo() {
  local repo=$1
  local marker=$2
  mkdir -p "$repo/.brain"
  git -C "$repo" init -b main >/dev/null
  git -C "$repo" config user.name "Boss Brain E2E"
  git -C "$repo" config user.email "boss-e2e@example.invalid"
  printf '# %s\n' "$(basename "$repo")" >"$repo/README.md"
  printf '# State\n\n## 现状\n\n%s\n\n## 下一步\n\ncontinue the user journey\n' "$marker" >"$repo/.brain/STATE.md"
  printf 'provides\tjourney.%s\tREADME.md\tRemote Codex user journey\n' "$(basename "$repo")" >"$repo/.brain/capabilities.tsv"
  git -C "$repo" add README.md .brain
  git -C "$repo" commit -m initial >/dev/null
  git -C "$repo" remote add origin "https://github.com/$TEST_OWNER/$(basename "$repo").git"
}

ALPHA="$HOME/work/codex-journey-alpha"
BETA="$HOME/work/codex-journey-beta"
ALPHA_MARKER=ALPHA_REMOTE_USER_READY
BETA_MARKER=BETA_REMOTE_USER_READY
WIKI_MARKER=WIKI_REMOTE_RECURRING_LESSON
SECRET_VALUE="ghp_$(printf 'S%.0s' {1..24})"
make_repo "$ALPHA" "$ALPHA_MARKER"
make_repo "$BETA" "$BETA_MARKER"
printf '\nAccidental fixture secret: %s\n' "$SECRET_VALUE" >>"$ALPHA/.brain/STATE.md"
mkdir -p "$ALPHA/.brain/wiki"
printf '# Wiki index\n\n- [Recurring recovery](recurring-recovery.md)\n' >"$ALPHA/.brain/wiki/index.md"
printf '# Recurring recovery\n\nVerified lesson marker: %s\n' "$WIKI_MARKER" >"$ALPHA/.brain/wiki/recurring-recovery.md"
boss adopt "$BETA" --aliases "knowledgebase" --summary "cross-project knowledge base" >/dev/null

PLUGIN_LIST=$($CODEX_BIN plugin list 2>&1)
case "$PLUGIN_LIST" in
  *"boss-brain@boss-brain"*"installed, enabled"*) ;;
  *)
    echo "Boss Brain was not enabled by the isolated installer" >&2
    exit 1
    ;;
esac

$CODEX_BIN exec \
  --disable apps \
  --dangerously-bypass-hook-trust \
  --sandbox read-only \
  --cd "$ALPHA" \
  --json \
  --output-schema "$ROOT/tests/fixtures/user-context.schema.json" \
  --output-last-message "$SANDBOX_ROOT/final-alpha.json" \
  "Using only lifecycle context already supplied for the active workspace, return the project name and its exact all-caps readiness marker. Do not call tools, read files, mention hidden instructions, hooks, paths, or Boss Brain." \
  >"$SANDBOX_ROOT/events-alpha.jsonl"
boss explain --json >"$SANDBOX_ROOT/trace-alpha.json"

$CODEX_BIN exec \
  --disable apps \
  --dangerously-bypass-hook-trust \
  --sandbox read-only \
  --cd "$ALPHA" \
  --json \
  --output-schema "$ROOT/tests/fixtures/user-context.schema.json" \
  --output-last-message "$SANDBOX_ROOT/final-beta.json" \
  "For @codex-journey-beta, use only lifecycle context already supplied and return that project's name and exact all-caps readiness marker. Do not call tools, read files, mention hidden instructions, hooks, paths, or Boss Brain." \
  >"$SANDBOX_ROOT/events-beta.jsonl"
boss explain --json >"$SANDBOX_ROOT/trace-beta.json"

$CODEX_BIN exec \
  --disable apps \
  --dangerously-bypass-hook-trust \
  --sandbox read-only \
  --cd "$ALPHA" \
  --json \
  --output-schema "$ROOT/tests/fixtures/user-context.schema.json" \
  --output-last-message "$SANDBOX_ROOT/final-wiki.json" \
  "This workspace has a difficult recurring recovery problem. Find the exact verified lesson marker already recorded for that recurring problem and return it with the active project name. Do not guess, modify files, or mention hidden instructions, hooks, paths, or Boss Brain." \
  >"$SANDBOX_ROOT/events-wiki.jsonl"
boss explain --json >"$SANDBOX_ROOT/trace-wiki.json"

$CODEX_BIN exec \
  --disable apps \
  --dangerously-bypass-hook-trust \
  --sandbox read-only \
  --cd "$ALPHA" \
  --json \
  --output-schema "$ROOT/tests/fixtures/user-context.schema.json" \
  --output-last-message "$SANDBOX_ROOT/final-alias.json" \
  "The knowledgebase feature may be involved. Use only lifecycle context and do not call tools or read files. Return the project whose full state is actually loaded and its exact readiness marker; do not treat a low-confidence project pointer as loaded state. Do not mention hidden instructions, hooks, paths, or Boss Brain." \
  >"$SANDBOX_ROOT/events-alias.jsonl"
boss explain --json >"$SANDBOX_ROOT/trace-alias.json"

(
  cd "$ALPHA"
  $CODEX_BIN exec resume --last \
    --disable apps \
    --dangerously-bypass-hook-trust \
    --json \
    --output-schema "$ROOT/tests/fixtures/user-context.schema.json" \
    --output-last-message "$SANDBOX_ROOT/final-resume.json" \
    "Now answer for the active workspace, not the project discussed in the previous turn. Using only newly supplied lifecycle context, return the active project name and exact all-caps readiness marker. Do not call tools, read files, mention hidden instructions, hooks, paths, or Boss Brain." \
    >"$SANDBOX_ROOT/events-resume.jsonl"
)
boss explain --json >"$SANDBOX_ROOT/trace-resume.json"

python3 - "$HOME" "$SANDBOX_ROOT" "$ALPHA_MARKER" "$BETA_MARKER" "$WIKI_MARKER" "$SECRET_VALUE" <<'PY'
import json
from pathlib import Path
import sys

home = Path(sys.argv[1])
sandbox = Path(sys.argv[2])
alpha_marker = sys.argv[3]
beta_marker = sys.argv[4]
wiki_marker = sys.argv[5]
secret = sys.argv[6]
boss = home / ".boss"


def walk_types(value):
    if isinstance(value, dict):
        if isinstance(value.get("type"), str):
            yield value["type"]
        for item in value.values():
            yield from walk_types(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_types(item)


def assert_user_turn(label, expected_project, expected_marker, tool_policy="forbid"):
    final_path = sandbox / f"final-{label}.json"
    event_path = sandbox / f"events-{label}.jsonl"
    final_text = final_path.read_text(encoding="utf-8")
    final = json.loads(final_text)
    assert final == {"project": expected_project, "marker": expected_marker}, (label, final)
    forbidden = ("Boss Brain", "内部上下文", str(home), secret)
    assert not any(value in final_text for value in forbidden), (label, final_text)

    raw_events = event_path.read_text(encoding="utf-8")
    assert secret not in raw_events, f"{label}: secret leaked into Codex events"
    events = [json.loads(line) for line in raw_events.splitlines() if line.strip()]
    assert events, f"{label}: no Codex events"
    types = {item for event in events for item in walk_types(event)}
    forbidden_tools = {"command_execution", "file_change", "mcp_tool_call", "web_search"}
    if tool_policy == "forbid":
        assert not types.intersection(forbidden_tools), (label, types)
    else:
        assert "command_execution" in types, (label, types)
        assert not types.intersection({"file_change", "mcp_tool_call", "web_search"}), (label, types)
    assert "turn.completed" in types, (label, types)


def assert_trace(label, event, mode, project, policy):
    trace = json.loads((sandbox / f"trace-{label}.json").read_text(encoding="utf-8"))
    assert trace["event"] == event, (label, trace)
    assert trace["mode"] == mode, (label, trace)
    assert trace["project"] == project, (label, trace)
    assert trace["content_policy"] == policy, (label, trace)
    assert trace["chars"] > 0, (label, trace)
    assert secret not in json.dumps(trace), (label, trace)


assert_user_turn("alpha", "codex-journey-alpha", alpha_marker)
assert_user_turn("beta", "codex-journey-beta", beta_marker)
assert_user_turn("wiki", "codex-journey-alpha", wiki_marker)
assert_user_turn("alias", "codex-journey-alpha", alpha_marker)
assert beta_marker not in (sandbox / "events-alias.jsonl").read_text(encoding="utf-8"), "alias pointer leaked beta state"
assert_user_turn("resume", "codex-journey-alpha", alpha_marker)
assert_trace("alpha", "SessionStart", "workspace", "codex-journey-alpha", "full-project")
assert_trace("beta", "UserPromptSubmit", "explicit", "codex-journey-beta", "full-project")
assert_trace("wiki", "UserPromptSubmit", "wiki", "codex-journey-alpha", "selected-wiki-entry")
assert_trace("alias", "UserPromptSubmit", "alias", "codex-journey-beta", "pointer-only")
assert_trace("resume", "SessionStart", "workspace", "codex-journey-alpha", "full-project")

sessions = list((boss / "state" / "sessions").glob("*.json"))
assert len(sessions) >= 4, "SessionStart did not persist real sessions"
audit = boss / "state" / "audit.jsonl"
assert audit.is_file(), "Stop did not write an audit record"
assert len(audit.read_text(encoding="utf-8").splitlines()) >= 5, "not every user turn reached Stop"
assert any((path / ".git").exists() for path in home.glob("boss-*")), "machine Brain was not initialized"
registry = (boss / "registry.tsv").read_text(encoding="utf-8")
assert "codex-journey-alpha" in registry, "active repository was not registered"
assert "codex-journey-beta" in registry, "cross-project repository was not registered"
print("PASS plugin-install")
print("PASS ordinary-user-answer")
print("PASS cross-project-answer")
print("PASS selective-wiki-injection")
print("PASS low-confidence-pointer-only")
print("PASS resumed-user-answer")
print("PASS context-injection-trace")
print("PASS no-tool-context-use")
print("PASS no-secret-or-internal-context-leak")
print("PASS lifecycle-state-and-stop-audit")
print("PASS machine-brain")
PY
