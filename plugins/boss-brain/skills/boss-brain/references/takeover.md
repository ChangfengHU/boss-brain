# Take over a project

Only claim successful takeover after executable checks demonstrate it.

1. Locate `.brain/` or follow `.brain-home`.
2. Read `HANDOFF.md` fully, then its specified reading order, `TASKS.md`, `wiki/index.md`, and applicable conventions. Load individual wiki topics only as needed.
3. Confirm named credential files or providers exist and permissions are appropriate. Never output values. If access is absent, say exactly which owner or recovery channel is needed.
4. If `HANDOFF_ACCEPTANCE.md` exists, run its safe checks. Otherwise run the handoff verification commands and recommend adding a durable contract.
5. Record each result as `PASS`, `FAIL`, `BLOCKED`, or `NOT_RUN`. Include the redacted failure and the action needed to unblock it. Write a report under `.brain/handoff-reports/` only if the user requested an actual takeover, not a read-only review.
6. Correct documentation drift when reality is authoritative, while preserving stable discovery methods. Commit and follow the repository's push policy when files changed.
7. Report purpose, verified access, active tasks, corrected drift, and check results. Say “takeover complete” only when every required item passes; otherwise say “partial takeover” and name the blockers.
