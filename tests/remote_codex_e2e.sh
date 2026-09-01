#!/usr/bin/env bash
set -euo pipefail

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CODEX_BIN=${CODEX_BIN:-codex}
AUTH_SOURCE=${CODEX_AUTH_SOURCE:-}
TEST_OWNER=${BOSS_TEST_OWNER:-boss-brain-test}

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
  chmod -R u+rwX "$SANDBOX_ROOT" 2>/dev/null || true
  rm -rf -- "$SANDBOX_ROOT"
}
trap cleanup EXIT HUP INT TERM

export HOME="$SANDBOX_ROOT/home"
export CODEX_HOME="$HOME/.codex"
export BOSS_HOME="$HOME/.boss"
export PATH="$HOME/.local/bin:$PATH"
mkdir -p "$CODEX_HOME" "$HOME/work"
install -m 600 "$AUTH_SOURCE" "$CODEX_HOME/auth.json"

python3 "$ROOT/scripts/install.py" install --owner "$TEST_OWNER" >/dev/null

REPO="$HOME/work/codex-e2e-repo"
mkdir -p "$REPO"
git -C "$REPO" init -b main >/dev/null
git -C "$REPO" config user.name "Boss Brain E2E"
git -C "$REPO" config user.email "boss-e2e@example.invalid"
git -C "$REPO" commit --allow-empty -m initial >/dev/null
git -C "$REPO" remote add origin "https://github.com/$TEST_OWNER/codex-e2e-repo.git"

PLUGIN_LIST=$($CODEX_BIN plugin list 2>&1)
case "$PLUGIN_LIST" in
  *"boss-brain@boss-brain"*"installed, enabled"*) ;;
  *)
    echo "Boss Brain was not enabled by the isolated installer" >&2
    exit 1
    ;;
esac

$CODEX_BIN exec \
  --ephemeral \
  --dangerously-bypass-hook-trust \
  --sandbox read-only \
  --cd "$REPO" \
  --json \
  "Reply only OK and do not call tools. Target @codex-e2e-repo" \
  >"$SANDBOX_ROOT/codex-events.jsonl"

python3 - "$HOME" <<'PY'
import json
from pathlib import Path
import sys

home = Path(sys.argv[1])
boss = home / ".boss"
context = json.loads((boss / "state" / "last-context.json").read_text(encoding="utf-8"))
assert context.get("mode") == "explicit", context
assert context.get("project") == "codex-e2e-repo", context
assert list((boss / "state" / "sessions").glob("*.json")), "SessionStart did not persist a session"
assert (boss / "state" / "audit.jsonl").is_file(), "Stop did not write an audit record"
assert any((path / ".git").exists() for path in home.glob("boss-*")), "machine Brain was not initialized"
registry = (boss / "registry.tsv").read_text(encoding="utf-8")
assert "codex-e2e-repo" in registry, "current repository was not registered"
print("PASS plugin-install")
print("PASS session-start")
print("PASS prompt-routing")
print("PASS stop-audit")
print("PASS machine-brain")
PY
