# Context observability

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

- `changes` (default): show project/task routing changes, drift warnings, and selected Wiki/convention context; keep ordinary workspace startup silent.
- `always`: also show stable workspace and roster context.
- `off`: never request an automatic receipt; trace recording remains enabled.

Receipts contain project/task names and selected section labels only. They must not contain filesystem paths, raw injected context, prompts, or credentials. Examples:

```text
⚠ Boss：疑似涉及项目 llm-wiki，未切换、未加载其正文
⚠ Boss：疑似从任务 TASK-123 漂移到 TASK-208，未切换
↳ Boss：boss-brain · 注入 wiki
```

The Codex hook protocol supplies instructions rather than a native status component, so receipt rendering depends on the agent following the injected receipt instruction. Real-Codex acceptance tests verify this behavior; the per-session trace remains the authoritative record.

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
