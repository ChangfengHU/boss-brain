# Testing strategy

Boss Brain is ambient infrastructure. A failure may be invisible until a project is lost, so a successful command is not sufficient evidence. Tests assert observable state transitions: registry contents, injected-context metadata, audit records, Git commits, machine snapshots, exit codes, and secret absence.

The authoritative claim-to-evidence map is [capability-to-test coverage](coverage.md). Passing the suite does not upgrade `Partial`, `Not automated`, or `Not implemented` rows.

## Release layers

1. **Deterministic suite** — dependency-free unit and user-journey scenario tests in temporary HOME directories. These run on every push and pull request.
2. **Real Codex user journey** — installs the plugin into an isolated Codex home on a disposable remote host, asks ordinary, cross-project, low-confidence alias, and selective-Wiki questions, resumes the same session, checks the user-visible answers, and proves that `SessionStart`, `UserPromptSubmit`, and `Stop` produced their expected state without leaking secret values.
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

## User-visible journeys

The deterministic suite treats a workflow as complete only when the user can recover from the failure, not merely when a finding exists. It covers:

- ordinary workspace context and explicit cross-project routing without state mixing;
- low-confidence alias pointers that do not load or claim a project until the user explicitly selects it;
- a redacted context trace through `boss explain`, `boss explain --json`, and `boss explain --show`;
- checked-out Git worktree context and a two-second normal-hook latency budget;
- TASKS filtering/refresh, relation/capability routing, operational large-state capping, and non-eager Wiki/HANDOFF/conventions behavior;
- stable TASK IDs, explicit task switching, and natural-mention drift warnings;
- Wiki/conventions index diagnostics (broken, unsafe, duplicate, orphan, stale) and HANDOFF acceptance checks with a safe-command runner;
- duplicate prompt suppression plus resume/compact reinjection;
- a guarded unpushed-commit block that clears after the user pushes;
- a strict continuity block that clears after evidence, state, dev-log, and capability records are complete;
- successful machine-Brain push followed by clone/restore on a clean HOME;
- deletion detection, idempotent project recovery, corrupt inventory, and unavailable project remotes;
- install/rollback preservation of unrelated Codex and Claude configuration;
- actionable `projects`, `caps`, `risk`, and `doctor` output.

The remote Codex test additionally asserts the final assistant response. A passing run must use hook-provided context without tool calls, select the correct project marker, return a marker available only in the prompt-matched Wiki topic, preserve the active workspace across a low-confidence alias and `codex exec resume`, omit internal-context labels and paths from the final response, and keep secret-shaped fixture values out of both answers and JSONL events. Unrelated Codex Apps are disabled so external connectors cannot satisfy or interfere with these assertions.

## Commands

Deterministic suite:

```bash
python3 -m unittest -v tests.test_boss tests.test_resilience tests.test_user_journeys
python3 -m py_compile plugins/boss-brain/scripts/boss.py scripts/install.py
bash -n install.sh uninstall.sh tests/remote_codex_e2e.sh
```

Real Codex lifecycle on a disposable machine:

```bash
CODEX_AUTH_SOURCE=/secure/path/auth.json ./tests/remote_codex_e2e.sh
```

The lifecycle script creates a temporary HOME, copies `auth.json` with mode `0600`, installs Boss Brain, creates two synthetic owned Git repositories with distinct state and Wiki markers, runs ordinary, cross-project, selective-Wiki, low-confidence alias, and resumed read-only Codex turns, validates the final structured answers and event logs, asserts lifecycle state, and deletes the entire temporary directory through a trap. Set `BOSS_KEEP_E2E=1` only when a failed disposable run must be retained for event-level diagnosis.

## Release gate

A build is eligible for preview release only when the deterministic suite, plugin validator, skill validator, compile checks, shell syntax checks, and real Codex lifecycle test all pass. Fleet-wide production rollout additionally requires a successful canary timer/push/recovery cycle.

## Deliberately not claimed yet

The current suite does not prove interactive hook trust review, Claude Code behavior, macOS/Windows compatibility, creation against a real GitHub account, multi-day systemd stability, automatic semantic Wiki consolidation, or recovery from a real reclaimed machine. It does verify conservative semantic-overlap merge suggestions, explicit convention conflict diagnostics, and no-ID goal-drift warnings locally. Those remaining boundaries are explicit release limits rather than assumed coverage.
