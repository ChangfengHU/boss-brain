# Project memory schema

Project memory lives in `.brain/` inside the repository unless `.brain-home` points to a separate owner repository. Reuse an existing documentation system through links when practical; do not create a second source of truth.

Create files only when verified information exists:

- `STATE.md`: a short current-state card with status, next action, blockers, critical paths, and current hazards.
- `TASKS.md`: active/completed/deferred work. Mark inferred historical status as unconfirmed.
- `HANDOFF.md`: stable receiving protocol—what this is, assets and access locations, reading order, verification procedure, and hazards. Prefer commands for discovering current values over stale snapshots.
- `HANDOFF_ACCEPTANCE.md`: executable takeover checks with required/optional status.
- `capabilities.tsv`: tab-separated `provides|consumes`, stable capability id, interface location, and summary.
- `evidence.jsonl` or `tasks/*/evidence.jsonl`: one JSON object per materially verified work result. Include the commit, verification command/result, and a `wiki` judgment.
- `dev-log/YYYY-MM-DD.md`: concise narrative of work that produced commits.
- `conventions/`: project-specific rules and decisions.
- `wiki/index.md` plus topic files: expensive-to-recover lessons, rejected options with reasons, and verified external-system facts.
- `secrets/`: locations and recovery instructions only. Private secret values must remain ignored, permission-restricted, and outside documents.

Conflict priority is: observed running state, code/configuration, the user's latest explicit decision, then older records. Note unresolved contradictions rather than guessing.
