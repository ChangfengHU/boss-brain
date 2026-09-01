# Historical backfill

Backfill is explicit archaeological repair. It must never masquerade as evidence captured when the work originally happened.

1. Use the requested commit range. Default to the latest 10 and cap a single batch at 50.
2. Collect commit ids already present in `evidence.jsonl` and task evidence files; skip duplicates.
3. Inspect each remaining commit's metadata, summary, and focused diff. Do not infer intent beyond the evidence.
4. Add only useful records:
   - a dated dev-log paragraph prefixed with “Backfill”;
   - a wiki topic only for an expensive lesson, repeated failure/root cause, or durable external-system fact, labeled with its source commit and lack of contemporaneous re-verification;
   - handoff changes only for durable structural changes;
   - evidence only when separately valuable, with `verify: "none"`, `exit: null`, and `backfill: true`.
5. Ask about incomprehensible commits instead of guessing. Never overwrite contemporaneous records with archaeological conclusions.
6. Validate formats, scan for secrets, commit as one focused documentation change, and follow the repository's push policy.
7. Report counts for dev-log additions, wiki topics, handoff changes, skipped commits, and unresolved questions.
