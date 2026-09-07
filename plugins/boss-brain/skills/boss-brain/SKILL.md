---
name: boss-brain
description: Maintain development rules and continuity across a session's projects and capabilities. Use for project-dependent development, confirmed decisions and lessons, initialization, context inspection, task recovery and handoff. Ordinary unrelated questions need no project writes.
---

# Boss Brain

Boss Brain is a background continuity layer, not a required workflow. Boss is machine-scoped at `~/.boss/`; Brain is project-scoped at `.brain/` and travels with its Git repository. Lifecycle hooks may inject project context before this skill is selected. Treat that context as private working memory: use it, but do not repeat it or announce that it was loaded.

## Default behavior

- Complete the user's task first. Memory updates are a closing action and must not interrupt ordinary work.
- Infer the workspace from the request, current Git root, or registry. Ask one short question only when the target truly cannot be determined.
- Read `.brain/wiki/index.md` before re-solving a difficult or recurring project problem. Load only relevant entries.
- One session can have several tasks and related projects. Preserve user-confirmed execution owners, rejected approaches and acceptance criteria across repository changes. A project mention or capability dependency is not authorization to modify it. Natural-language confirmation can change the task; `@task` is optional.
- After `boss init`, bind an agreed task with `boss session bind SESSION --task-id ID --goal "confirmed objective" --project NAME` (repeat `--project` and `--constraint`). Add `--access work` only when the user authorized changes; it claims the work baseline and initializes missing Brain entries. Read bindings do not authorize project writes. Use the host session ID; do not invent a second identity for the same session.
- Binding normally adds project associations. When the user corrects the task scope, use `--replace-projects` with the complete revised project list and access level; use `--replace-constraints` for revised constraints. This replaces only that task, not other tasks or past work audit records. A `partial` result means the task is bound but some Brain entries failed initialization; report the affected entries, not universal success.
- A missing Brain on an adopted GitHub project is automatically initialized when authorized work is bound. Use `boss brain-init PATH` to repair a missing entry. Initialization reports inventory, not verified business state. Check `.brain/manifest.json` for existing document locations; don't create duplicate task/log/handoff files.
- Ordinary Q&A is write-free. Once initialization enables critical knowledge capture, confirmed important decisions and verified lessons may be saved without a business-code commit. Explicit read-only, no-record and analysis-only instructions still prohibit project writes.
- Critical corrections are a separate knowledge-maintenance task when the user authorizes it: check architecture, operating rules, source-of-truth and release relationships against existing project documents even if no business commit was produced. A no-write instruction always takes precedence. Never turn an inference into a fact.
- When investigation or a confirmed user decision changes durable knowledge, use `boss knowledge flag --session SESSION --path PROJECT --key STABLE_ID --kind decision|lesson|fact --summary "verified concise conclusion" --source "relative document or sanitized evidence reference"`. Never store raw chat or credentials. Verify ownership first; a cross-project statement has one authoritative owner and references elsewhere. Pending reviews survive sessions; inspect them with `boss knowledge list --session SESSION` after binding the related project.
- Update the original authoritative document and remove contradictory claims, then resolve with `boss knowledge resolve --session <session-id> --id <id> --status updated --file <relative-markdown-path>`. Use `deferred` for intentionally postponed/no-write work or `dismissed` for a false positive. Report any remaining gap; changed bytes are evidence of an edit, not proof of semantic correctness or successful push.
- Never print, copy into documentation, or commit secret values. Record only credential names, locations, owners, and recovery methods.
- Do not create empty memory templates. Project memory grows from verified facts.
- Respect the configured policy: `quiet` records findings, `guarded` interrupts only for data-loss risks, and `strict` enforces continuity records too.
- Silent discovery may register qualified owned repositories, but scanning alone does not modify them. Explicit adoption after initialization also establishes a basic Brain. Preserve `.brain-home` ownership; delegated or inaccessible entries are reported as incomplete, not silently overwritten.
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
