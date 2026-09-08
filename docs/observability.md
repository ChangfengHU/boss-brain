# Context observability

After `boss init`, protocol v2 emits multi-project selection traces. The receipt repair
reconnects user-visible feedback without reverting multi-project context. It is installed and
entrypoint-verified on the development host; this does not imply fleet-wide deployment.
Use `boss explain --session ID --json`/`--show` for project sets, task and bounded context.

Boss records routing decisions per session so an incorrect decision is observable even when no context was injected. The trace is append-only JSONL under the Boss runtime state and contains redacted metadata, never the original prompt or secret values.

## Observation points

| Point | Recorded decision |
| --- | --- |
| Session start | workspace project, active task, initial sections |
| Project routing | project before, candidate, selected project, decision and reason |
| Task routing | task before, candidate, selected task, decision and reason |
| Legacy goal routing | candidate goal, score and matched token evidence |
| Knowledge routing | Wiki or convention mode and selected section |
| Injection | performed/suppressed, content policy, sections and character count |
| Suppression | no registry, invalid/completed task, low-confidence goal, no match, duplicate, or unrecognized reference |
| Stop | redacted continuity and data-loss findings in the existing audit stream |

Each session owns `traces/<session>.jsonl` and `previews/<session>.txt`. The compatibility files `last-context.json` and `last-context-preview.txt` remain, but session-specific diagnosis must use `boss explain --session ID` to avoid cross-session ambiguity.

## User-visible receipts

`boss receipt` controls automatic receipts:

- `changes` (default in repaired v2): show the first user-prompt route, then changes to project/task routing, drift warnings or selected Wiki/convention guidance. SessionStart alone does not consume a visible receipt.
- `always`: request a receipt on every user prompt even if the context body is deduplicated.
- `off`: never request an automatic receipt; trace recording remains enabled.

V2 distinguishes task projects from read-only reference candidates. Without a bound task it
labels the workspace or explicit reference instead of inventing task ownership. Selection
does not grant write authority. Strict user output formats and explicit no-extra-text requests
take precedence. The retained legacy path uses its original mode-based receipt policy.

Receipts contain project/task names and selected section labels only. They must not contain filesystem paths, raw injected context, prompts, or credentials. V2 example:

```text
↳ Boss：任务项目 workflow；参考项目 browser · PUBLISH
```

Legacy examples:

```text
⚠ Boss：疑似涉及项目 llm-wiki，未切换、未加载其正文
⚠ Boss：疑似从任务 TASK-123 漂移到 TASK-208，未切换
↳ Boss：boss-brain · 注入 wiki
```

The Codex hook protocol supplies instructions rather than a native status component, so receipt rendering depends on the agent following the injected receipt instruction. Real-Codex acceptance tests verify this behavior; the per-session trace remains the authoritative record.

### Project receipt overrides (v2)

`boss receipt --project NAME` queries an adopted project's override and effective value.
Adding `always`, `changes` or `off` writes only that project's machine-local override;
`inherit` removes it. Names, aliases and registered paths resolve through the registry;
unknown or ambiguous projects are refused. Legacy mode refuses this option explicitly.
The file is `~/.boss/project-receipts.json`, written atomically under a lock. It does not
travel with project Git data or change the global setting. A project override therefore
also applies to other sessions that actually reference that project on this machine.

In a mixed-project receipt, `off` projects are omitted from the visible project list and
guidance labels, while their actual context remains available. If any remaining associated
project uses `always`, emit every prompt; otherwise use `changes`. No visible projects means
no receipt. Session disabled/observe-only still wins. This is not a whole-project plugin
disable switch; it must not bypass knowledge or Stop safeguards.

Malformed/symlinked override files are not overwritten by the CLI. Hooks suppress receipts
and report `receipt.error` while retaining normal context. Diagnose with explicit help and
`boss explain`; do not silently reset the configuration to make an error disappear.

`last_context.receipt` records the policy and whether the current output requests a receipt.
`injection` describes context-body delivery, while `chars` and `sha256` describe the Hook's
constructed output including any receipt. Observe-only mode still suppresses host delivery.
`startup_unavailable` identifies failed local patrol/machine services independently of
project metadata failures. These failures must not erase otherwise healthy context.
`receipt.policy` remains the global default; `receipt.projects` records each associated
project's effective setting, and `receipt.error` reports an unreadable override configuration.

## Help requests

`boss help` and a bare `boss` show the Chinese overview. `boss help COMMAND SUBCOMMAND`
shows explanatory guidance plus the actual parser's arguments. The exact conversational
forms `help boss`, `boss help` and `boss 帮助` (optionally followed by an English command
topic) enter a read-only help Hook path before routing or knowledge capture. Repeated help
is not lost to context deduplication. Disabled/observe-only sessions still suppress Hook
output; an Agent may explicitly run the read-only CLI when the user asks for help.

## Session controls

Each session can independently use one of three modes:

- `enabled`: normal routing, injection, receipts, trace, and Stop policy.
- `observe-only`: record routing and Stop diagnostics without injecting context, displaying receipts, or blocking Stop.
- `disabled`: skip routing, injection, trace, and Stop auditing for that session.

Natural-language requests containing “本会话禁用 Boss Brain”, “本会话只观察”, or “本会话恢复 Boss Brain” update only the current session. The equivalent diagnostic interface is:

```bash
boss session mode SESSION_ID disabled
boss session mode SESSION_ID observe-only
boss session mode SESSION_ID enabled
```

Controls are stored separately from session routing state so a disabled session can be resumed without first running its normal hooks.

## Diagnosis

```bash
boss explain --session SESSION_ID --json
boss explain --session SESSION_ID --history
boss explain --session SESSION_ID --show
```

The history records both positive injections and negative decisions. It does not claim semantic intent understanding: project aliases and legacy goals retain their conservative matching boundaries.
