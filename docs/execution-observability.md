# Execution observability

This is an opt-in, local CLI observation layer, separate from the existing receipt
and continuity policy. It does not automatically write development logs or Wiki.

## User commands

```sh
boss display detail --session SESSION
boss events --session SESSION --follow --detail
boss display off --session SESSION
boss display inherit --session SESSION
boss display summary --project PROJECT
boss help display
boss help events
```

Without a value, `display` queries its explicit scope. Session overrides win over
project overrides; otherwise the most detailed grounded task/workspace project
setting applies to that session event. Incidental capability matches cannot enable
logging. Default is `off`; changing a project switch does not modify its repository.
No setting is changed by installation or help. Disabled/observe-only session modes
still suppress Hook output. `off` stops new observations, not normal continuity, and
does not delete existing history. `inherit` removes only the selected override.

## What is proven

- `context_body` is the actual returned Hook additionalContext, after redaction;
  detail mode retains it. Duplicate context is not reconstructed as a new injection.
- Context metadata includes state/Wiki/convention retrieval paths and reasons,
  budget truncation and duplicate suppression. The returned body includes task
  contract and routing metadata; this is not a copy of every file on disk.
- dev-log, Wiki, TASKS and HANDOFF use the manifest's authoritative paths. Hash
  differences identify observed file changes, including uncommitted records.
  They do **not** identify which concurrent Agent wrote them or prove correctness.
- First observation establishes a baseline; it does not invent earlier activity.
  Unchanged observations say so. Pending/resolved knowledge reviews are reported.
- Stop events include the actual audit findings and block/no-block decision.
  HEAD/upstream/ahead are local Git evidence, **not a network-confirmed push receipt**.
  Hooks never fetch, push, contact Vault or SSH into another machine.

Observation is bounded: at most eight repositories, 128 Markdown files per category,
256 KiB per file, 1 MiB total content hashing and a soft two-second snapshot budget.
Skipped files/projects are marked. Slow Git subprocesses have one-second timeouts.
Per-session event history retains the latest 40 events under the Boss state directory,
mode 0600. `events --json` is newline-delimited JSON; `--follow` prints new records
directly to the terminal and exits with Ctrl-C. It neither replays Hooks nor calls a model.

## Host rendering boundary

Hooks also submit a redacted `systemMessage`. This means **display requested**, not
**display confirmed**. Native Codex lifecycle acceptance proves prompt/Stop execution
and the independent CLI viewer; it does not prove that every interactive CLI/App
renders that field inline. The viewer is the reliable fallback, not a claim that the
full automatic inline requirement is finished. No instruction asks the assistant to
fabricate or paraphrase execution receipts in place of events.

The official configuration reference does not establish an inline display guarantee:
https://learn.chatgpt.com/docs/config-file/config-reference
Real behavior must be accepted on each targeted host, not inferred from a JSON field.

## Compatibility and remote paths

The original twelve core rules, receipt commands, policies and lifecycle results
remain. Missing optional observation code or damaged display configuration preserves
the original Hook context/decision and emits only a fixed diagnostic. Display failure
does not turn a genuine guarded/strict block into success.

A `remote` registry entry with no local directory is now reported as remotely owned
and not locally loaded. It no longer suggests initializing that path on this machine.
Existing registry host information remains in the summary; this change does not
introduce a new machine-qualified registry schema or automatically load remote Brain.

Local directives appended outside managed blocks (Vault-first, media cleanup and
84-only auto-parse work) must be preserved by installation. They are **not** claimed
as fleet-wide/plugin-distributed enforcement by this observability release.
