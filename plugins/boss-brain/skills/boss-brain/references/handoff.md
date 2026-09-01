# Handoff preparation and assessment

Use assessment mode for “show/review handoff” requests: remain read-only. Use preparation mode only when the user asks to make the project ready for handoff.

## Assessment mode

1. Locate `.brain/HANDOFF.md` or follow `.brain-home`.
2. Read the handoff, active tasks, wiki index, newest evidence, and acceptance contract if present.
3. Assess substantive coverage of: purpose, assets/access locations, reading order, verification, and hazards.
4. List unresolved TODOs, stale snapshot values, likely missing operational dependencies, and invalid read-only verification commands.
5. Scan documentation for secret-like values without printing matches. Report only file paths and remediation.
6. Give a readiness score and the concrete conditions blocking transfer. Make no edits, commits, or pushes.

## Preparation mode

1. If project memory is absent, follow [initialize.md](initialize.md) first.
2. Reconcile the full current conversation with repository reality. Put facts in their correct files, not all in `HANDOFF.md`.
3. Make the handoff stable: document how to discover changing values rather than recording transient hashes, versions, or deployment snapshots.
4. Create or update `HANDOFF_ACCEPTANCE.md` with exact commands, expected outcomes, required/optional status, safe side-effect notes, and credential prerequisites.
5. Execute every safe verification command. Mark unavailable destructive or externally mutating checks as `NOT_RUN` with the reason.
6. Ensure task status, evidence, wiki index, and Git state agree. Scan for secrets.
7. Commit the handoff changes and follow the repository's push policy. The project is “handoff ready” only when every required check passes and the receiving material is available where the recipient expects it.
