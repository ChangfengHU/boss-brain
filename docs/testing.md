# Testing strategy

Boss Brain is ambient infrastructure. A failure may be invisible until a project is lost, so a successful command is not sufficient evidence. Tests assert observable state transitions: registry contents, injected-context metadata, audit records, Git commits, machine snapshots, exit codes, and secret absence.

## Release layers

1. **Deterministic suite** — dependency-free unit and scenario tests in temporary HOME directories. These run on every push and pull request.
2. **Real Codex lifecycle** — installs the plugin into an isolated Codex home on a disposable remote host, starts `codex exec`, and proves that `SessionStart`, `UserPromptSubmit`, and `Stop` produced their expected state.
3. **Canary operations** — before a fleet rollout, run a real timer and remote push against a dedicated non-production Git repository for at least one full interval.

## Covered scenarios

| Area | Normal case | Failure or edge case |
| --- | --- | --- |
| Discovery | owned active repository is adopted | foreign, stale, empty, name-conflicting, Unicode/space paths, malformed scan configuration |
| Registry | atomic registration | twelve concurrent scans, live lock timeout, stale lock recovery, TSV injection rejection |
| Codex hooks | real plugin install and three lifecycle events | malformed hook input, Stop recursion guard, duplicate prompt suppression |
| Brain context | state/tasks/capabilities routing | secret-shaped Brain content is redacted before hook output |
| Stop policy | quiet recording, guarded data-loss block, strict continuity block | missing upstream, unpushed commit, missing evidence/state/dev-log |
| Machine Brain | initialize, stable sync, restore | contaminated registry refusal, credentialed-origin sanitization, unavailable push remote |
| Vault references | key-name-only record | secret-like values in key, project, or purpose fields |
| Timer | interval validation and unit generation | systemd enable failure through an isolated fake controller |
| Installer | install/update/uninstall and legacy migration | malformed legacy settings, idempotent install, preservation of unrelated config |

## Commands

Deterministic suite:

```bash
python3 -m unittest -v tests.test_boss tests.test_resilience
python3 -m py_compile plugins/boss-brain/scripts/boss.py scripts/install.py
bash -n install.sh uninstall.sh tests/remote_codex_e2e.sh
```

Real Codex lifecycle on a disposable machine:

```bash
CODEX_AUTH_SOURCE=/secure/path/auth.json ./tests/remote_codex_e2e.sh
```

The lifecycle script creates a temporary HOME, copies `auth.json` with mode `0600`, installs Boss Brain, creates a synthetic owned Git repository, runs one read-only Codex turn, asserts five outcomes, and deletes the entire temporary directory through a trap.

## Release gate

A build is eligible for preview release only when the deterministic suite, plugin validator, skill validator, compile checks, shell syntax checks, and real Codex lifecycle test all pass. Fleet-wide production rollout additionally requires a successful canary timer/push/recovery cycle.

## Deliberately not claimed yet

The current suite does not prove Claude Code behavior, macOS/Windows compatibility, GitHub repository creation, multi-day systemd stability, or recovery from a real reclaimed machine. Those remain explicit release boundaries rather than assumed coverage.
