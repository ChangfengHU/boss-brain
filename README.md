# Boss Brain

Boss Brain is an ambient control and continuity layer for coding agents.

- **Boss belongs to a machine.** It discovers and registers active Git repositories, routes project context, maps capabilities, and maintains a portable machine inventory under `~/.boss/`.
- **Brain belongs to a project.** A project's `.brain/` travels with its Git repository and preserves current state, tasks, decisions, lessons, capabilities, evidence, and handoff instructions.
- **Vault holds secrets.** Boss and Brain store Vault key names and recovery instructions, never credential values.
- **Git provides continuity.** A `boss-<machine-id>` repository records the recoverable machine inventory so a replacement machine can resume management.

The product is deliberately different from workflow-first systems. Users keep working normally; Boss Brain loads useful context in the background and interrupts only when the configured policy requires it.

## Continuity protocol v2

The current development upgrade adds managed global directives, real project initialization,
multi-project task context and durable knowledge reviews. Existing installations remain in
legacy routing mode until initialized; installation alone does not rewrite project memory.

```bash
boss init --dry-run
boss init                         # rules + already-adopted GitHub projects
boss init --rules-only            # rules and v2 policy; no project writes
boss adopt /path/to/project
boss brain-init /path/to/project
boss session bind SESSION --task-id TASK-1 --goal "confirmed outcome" \
  --project workflow --project browser --constraint "workflow owns execution" --access work
```

`boss init` preserves custom global instructions outside its managed block. Unknown/edited
blocks require review, not forced replacement. Project manifests reuse existing task, log
and handoff documents; inventory is explicitly not verified business knowledge. Discovery
and read-only context do not initialize projects; binding authorized work does.

One session may retain several tasks and associated capabilities/projects. Context selection
is read-only, bounded and source-labeled; it is not a write grant. Confirmed important decisions
and lessons can be saved by the Agent without business-code changes, with an explicit no-write
request taking precedence. See [protocol and migration details](docs/continuity-v2.md).

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

In legacy mode, session start performs a daily local patrol and initializes the local machine
Brain once. Enabled v2 currently registers the qualified current workspace instead; full-home
startup patrol and automatic machine initialization remain migration gaps, not equivalent
behavior. Explicit scan/machine commands remain available. Discovery alone does not create a
project `.brain/`; authorized v2 work bindings initialize basic entries.

The source receipt repair restores visible v2 project/task feedback; it has not yet been
promoted to the shared installed runtime. See [observability](docs/observability.md) for
`changes`/`always`/`off` behavior and [compatibility audit](docs/requirements-preservation-audit.md)
for remaining release gates.

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
boss session mode SESSION_ID disabled
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
boss knowledge list --session SESSION_ID
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
python3 -m unittest -v tests.test_boss tests.test_resilience tests.test_user_journeys tests.test_knowledge_sync
python3 -m unittest tests.test_continuity_v2
```

The authenticated Codex user-journey test must run on a disposable host and copies login state only into a temporary directory that is deleted on exit:

```bash
CODEX_AUTH_SOURCE=/secure/path/auth.json ./tests/remote_codex_e2e.sh
CODEX_AUTH_SOURCE=/secure/path/auth.json python3 tests/continuity_codex_e2e.py
```

See [testing strategy](docs/testing.md) and the [capability-to-test coverage map](docs/coverage.md) for explicit evidence and remaining boundaries.

Critical architecture/operating corrections can produce knowledge reviews even without a
business commit: legacy reviews are session-scoped; v2 additionally stores project-owned
reviews across sessions. Verified tool discoveries use an explicit flag; existing project
documents are updated only within user authorization. See [knowledge synchronization](docs/knowledge-sync.md)
for commands, no-write behavior, and verification limits.

## Uninstall and rollback

```bash
python3 ~/.boss/distribution/scripts/install.py uninstall
python3 ~/.boss/distribution/scripts/install.py rollback
```

Uninstall removes plugin code and hooks while preserving `~/.boss` data and every project `.brain/`. Rollback restores the most recent pre-install agent configuration backup.

## License

MIT
