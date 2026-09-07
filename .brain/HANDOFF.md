# Receiving protocol

## Purpose

Boss Brain provides development rules and continuity across projects and capabilities.
It does not replace a user's business execution workflow or authorize extra mutations.

## Read order

Read README.md, .brain/STATE.md, .brain/TASKS.md and docs/continuity-v2.md. Follow the
manifest to locate authoritative records; docs/security.md governs secret handling.

## Runtime and access

The `boss` wrapper points at the installed distribution. Inspect `command -v boss`,
`boss explain --session ID --json` and `boss init --dry-run`. Use the configured local
marketplace CLI for native plugin reinstallation; never hand-edit marketplace entries.
Authentication for disposable Codex testing comes from an explicitly provided existing
auth file, copied only into a temporary restricted directory. No values belong in Git.

## Verification

Run `python3 -m unittest discover -s tests -q`, compile the Python entrypoints and
validate the plugin/skills. Run `tests/continuity_codex_e2e.py` with CODEX_AUTH_SOURCE;
set BOSS_TEST_KNOWLEDGE=1 to additionally verify Agent-driven decision persistence.
Initialization reports file configuration, not proof of host instruction loading.

## Hazards and recovery

Never overwrite outside managed rule blocks or operate on an uncertain project owner.
Installer backups live under the machine Boss runtime. Rollback refuses changed host
configuration instead of overwriting later edits. See wiki/hook-migration.md for the
native trust-table migration regression. Existing project memory must survive uninstall.
