# Architecture

## Product boundary

Boss Brain is a continuity substrate, not a mandatory planning or specification workflow.

```text
Agent session
    │ lifecycle hooks
    ▼
Boss (~/.boss) ── discovers/routes/audits ──► local Git projects
    │                                           │
    │ machine snapshot                           └── .brain (portable project memory)
    ▼
boss-<machine-id> Git repository

Vault MCP ◄── key references only ── Boss / project Brain
```

## Boss: machine scope

Boss owns the local registry, aliases, scan policy, session claims, audit results, cross-project capability view, and machine snapshot configuration. Its hooks are dependency-free, local-only, and bounded by short timeouts.

Discovery is conservative. Automatic registration requires a recent non-empty repository whose GitHub owner matches `~/.boss/owner`. Foreign, stale, empty, remote-less, and name-conflicting repositories remain candidates. Registration never writes project memory.

## Brain: project scope

Project truth lives inside `.brain/` and moves with the repository. Files are created only when facts exist. Typical records are `STATE.md`, `TASKS.md`, `HANDOFF.md`, `capabilities.tsv`, `evidence.jsonl`, `dev-log/`, `conventions/`, and `wiki/`.

The current request remains primary. Hooks inject compact private context; the agent does not repeat it or turn bookkeeping into an opening ceremony.

## Machine Brain

The first Boss session initializes a separate local Git repository named `boss-<machine-id>` by default; `boss machine init` can configure its name, path, and remote explicitly. Its generated allow-listed files contain system identity, project names and sanitized origins, aggregate capabilities, Vault references, and recovery instructions.

The snapshot excludes credentials and stages only managed files. `boss machine timer-install` installs an optional systemd user timer; each run rescans local repositories, refreshes the machine Brain, and pushes it. Remote creation remains explicit because it changes an external account.

## Recovery

A replacement machine clones its machine Brain, receives Vault bootstrap access through provisioning or a one-time channel, and runs `boss machine restore`. Projects are matched by sanitized origin URL rather than obsolete absolute paths. With `--clone`, missing repositories are recreated and their project `.brain/` directories resume continuity.
