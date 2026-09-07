# Project memory schema

Project memory lives in `.brain/` inside the repository unless `.brain-home` points to a separate owner repository. Reuse an existing documentation system through links when practical; do not create a second source of truth.

Create files only when verified information exists:

- `manifest.json`: protocol version, normalized GitHub identity, content-review status and relative document locations. This basic inventory can be created automatically for authorized work on adopted projects; it is not a business-state verification. Paths must remain inside the owning repository. Existing `.brain-home` ownership requires separate review, not automatic reassignment.

- `STATE.md`: a short current-state card with status, next action, blockers, critical paths, and current hazards.
- `TASKS.md`: active/completed/deferred work. For drift protection, use stable IDs in active checkbox lines, for example `- [ ] [TASK-123] short title` or `- [ ] TASK-123: short title`; mark inferred historical status as unconfirmed.
- `HANDOFF.md`: stable receiving protocol—what this is, assets and access locations, reading order, verification procedure, and hazards. Prefer commands for discovering current values over stale snapshots.
- `HANDOFF_ACCEPTANCE.md`: executable takeover checks with required/optional status. Use lines such as `- [ ] REQUIRED SAFE \`python3 -m unittest\` => OK`; `--run` executes only the safe allow-list.
- `capabilities.tsv`: tab-separated `provides|consumes`, stable capability id, interface location, and summary.
- `evidence.jsonl` or `tasks/*/evidence.jsonl`: one JSON object per materially verified work result. Include the commit, verification command/result, and a `wiki` judgment.
- `dev-log/YYYY-MM-DD.md`: concise narrative of work that produced commits.
- `conventions/`: project-specific rules and decisions.
- `wiki/index.md` plus topic files: expensive-to-recover lessons, rejected options with reasons, and verified external-system facts.
- `secrets/`: locations and recovery instructions only. Private secret values must remain ignored, permission-restricted, and outside documents.

Separate facts from authority: observations and code/configuration establish what currently exists, not permission to override the user's requirements. The user's latest explicit decision controls the intended outcome and authorized changes; report any mismatch with current reality. Older records are historical evidence. Note unresolved contradictions rather than guessing.
