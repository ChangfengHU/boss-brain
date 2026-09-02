# Boss Brain

Boss Brain is an ambient control and continuity layer for coding agents.

- **Boss belongs to a machine.** It discovers and registers active Git repositories, routes project context, maps capabilities, and maintains a portable machine inventory under `~/.boss/`.
- **Brain belongs to a project.** A project's `.brain/` travels with its Git repository and preserves current state, tasks, decisions, lessons, capabilities, evidence, and handoff instructions.
- **Vault holds secrets.** Boss and Brain store Vault key names and recovery instructions, never credential values.
- **Git provides continuity.** A `boss-<machine-id>` repository records the recoverable machine inventory so a replacement machine can resume management.

The product is deliberately different from workflow-first systems. Users keep working normally; Boss Brain loads useful context in the background and interrupts only when the configured policy requires it.

## Status

Version `0.1.0` is the first integrated release for Codex and Claude Code. It provides one runtime, one registry, one set of lifecycle hooks, portable project brains, and machine-brain snapshot/recovery commands. The deterministic suite covers normal behavior, concurrency, malformed state, secret containment, unavailable remotes, and timer failures; a separate disposable-host test drives a real authenticated Codex session through all three lifecycle hooks.

## Install

From a checked-out release:

```bash
./install.sh --owner YOUR_GITHUB_OWNER
```

After `v0.1.0` is published:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ChangfengHU/boss-brain/v0.1.0/install.sh) --owner YOUR_GITHUB_OWNER
```

The installer preserves existing `~/.boss/`, project `.brain/` directories, and legacy Project Brains data. It backs up agent configuration before replacing duplicate legacy hooks. It never copies token files.

## Everyday behavior

On session start, Boss performs a daily local patrol and silently registers repositories that are non-empty, recently active, owned by the GitHub account in `~/.boss/owner`, and not name-conflicting. It also initializes the local machine Brain once. Registration does not create an empty project `.brain/`; new project brains grow only from verified information.

Useful explicit commands:

```bash
boss projects
boss scan --adopt
boss status
boss caps
boss risk
boss explain
boss explain --show
boss explain --session SESSION_ID --history
boss receipt changes
boss wiki check
boss conventions check
boss handoff check --run
boss policy quiet|guarded|strict
boss machine init --name boss-MACHINE
boss machine init --name boss-IP --create-remote --timer
boss machine sync --push
boss machine timer-install
boss machine restore /path/to/boss-machine --clone
boss vault-ref service:github --purpose "repository access"
boss doctor
```

`quiet` records findings without blocking. `guarded` blocks only data-loss risks such as unpushed commits. `strict` also enforces project continuity records.

## Data layout

```text
~/.boss/                    machine runtime, registry, policy, audit state
~/boss-<machine-id>/        portable machine Brain Git repository
~/project/.brain/           portable project Brain
```

See [architecture](docs/architecture.md), [security](docs/security.md), [migration](docs/migration.md), and the [Brain Evolution roadmap](docs/brain-evolution.md).

## Testing

Run the deterministic and user-journey suite with:

```bash
python3 -m unittest -v tests.test_boss tests.test_resilience tests.test_user_journeys
```

The authenticated Codex user-journey test must run on a disposable host and copies login state only into a temporary directory that is deleted on exit:

```bash
CODEX_AUTH_SOURCE=/secure/path/auth.json ./tests/remote_codex_e2e.sh
```

See [testing strategy](docs/testing.md) and the [capability-to-test coverage map](docs/coverage.md) for explicit evidence and remaining boundaries.

## Uninstall and rollback

```bash
python3 ~/.boss/distribution/scripts/install.py uninstall
python3 ~/.boss/distribution/scripts/install.py rollback
```

Uninstall removes plugin code and hooks while preserving `~/.boss` data and every project `.brain/`. Rollback restores the most recent pre-install agent configuration backup.

## License

MIT
