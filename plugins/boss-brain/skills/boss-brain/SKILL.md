---
name: boss-brain
description: Ambient project continuity for coding agents. Use implicitly when a request depends on an existing project's state, conventions, cross-project relationships, or safe end-of-session handling; use explicitly when the user asks to list/adopt projects, inspect loaded context, initialize project memory, prepare or inspect a handoff, take over a project, or backfill historical records.
---

# Boss Brain

Boss Brain is a background continuity layer, not a required workflow. Boss is machine-scoped at `~/.boss/`; Brain is project-scoped at `.brain/` and travels with its Git repository. Lifecycle hooks may inject project context before this skill is selected. Treat that context as private working memory: use it, but do not repeat it or announce that it was loaded.

## Default behavior

- Complete the user's task first. Memory updates are a closing action and must not interrupt ordinary work.
- Infer the workspace from the request, current Git root, or registry. Ask one short question only when the target truly cannot be determined.
- Read `.brain/wiki/index.md` before re-solving a difficult or recurring project problem. Load only relevant entries.
- When `.brain/TASKS.md` uses stable IDs such as `- [ ] [TASK-123] ...`, keep the session on its selected task. A natural mention of another task is a drift warning; switch only after the user explicitly uses `@task:TASK-123`.
- Make no `.brain/` writes during pure Q&A or read-only work.
- Critical corrections are a separate knowledge-maintenance task when the user authorizes it: check architecture, operating rules, source-of-truth and release relationships against existing project documents even if no business commit was produced. A no-write instruction always takes precedence. Never turn an inference into a fact.
- When verified investigation changes durable project knowledge, run `boss knowledge flag --session <session-id> --path <owning-project> --key <stable-discovery-id>`. Do not rely only on user-prompt keyword detection. Inspect pending items with `boss knowledge list --session <session-id>`. Verify the owning project before editing; session goals must not become unrelated project goals.
- Update the original authoritative document and remove contradictory claims, then resolve with `boss knowledge resolve --session <session-id> --id <id> --status updated --file <relative-markdown-path>`. Use `deferred` for intentionally postponed/no-write work or `dismissed` for a false positive. Report any remaining gap; changed bytes are evidence of an edit, not proof of semantic correctness or successful push.
- Never print, copy into documentation, or commit secret values. Record only credential names, locations, owners, and recovery methods.
- Do not create empty memory templates. Project memory grows from verified facts.
- Respect the configured policy: `quiet` records findings, `guarded` interrupts only for data-loss risks, and `strict` enforces continuity records too.
- Let Boss silently register active, non-empty GitHub repositories owned by the configured `~/.boss/owner`. Registration never creates an empty project Brain.
- Store credential values through the available Vault MCP. Write only the Vault key name, purpose, and recovery instructions into Boss or Brain files.

## Natural project work

When code or project state changes, follow the repository's own instructions first. If a commit is produced, keep the minimal continuity records already used by that repository consistent, then push when the repository policy requires it. Never claim another concurrent session's changes.

Use `boss projects`, `boss status`, `boss caps`, and `boss risk` only when the user asks for a portfolio view or when it directly resolves the current task. Use `boss explain` when the user asks what context was loaded. Use `boss scan --adopt` for an explicit immediate patrol.
Use `boss wiki check`, `boss conventions check`, and `boss handoff check` when the user asks whether project memory or takeover material is complete; add `--fix` or `--run` only when that mutation or command execution is explicitly requested.

Machine recovery lives in a separate `boss-<machine-id>` Git repository. Use `boss machine init`, `boss machine sync --push`, and `boss machine restore` only when the user asks to configure, synchronize, or recover a machine. The generated repository contains inventory and Vault references, never credentials.

## Explicit lifecycle operations

These operations are deliberately user-triggered because they can create or substantially edit project memory:

- Initialize or adopt an existing project: read [references/initialize.md](references/initialize.md).
- Prepare or assess a handoff: read [references/handoff.md](references/handoff.md).
- Take over a project: read [references/takeover.md](references/takeover.md).
- Backfill historical commits: read [references/backfill.md](references/backfill.md).

For memory file meanings and minimum schemas, read [references/brain-schema.md](references/brain-schema.md). Do not load lifecycle references unless the matching operation is requested.
