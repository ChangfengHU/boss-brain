# BOSS-OBSERVE — opt-in execution events

User requested a dedicated sub-agent for Boss CLI visibility while the main session
continues disk cleanup and auto-parse publishing. Work is confined to Boss Brain.

Implemented session/project `display` and a direct `events` viewer/follower, actual
Hook context recording, retrieval provenance, document byte-change observations,
knowledge status and Stop/Git evidence. Defaults and original receipts are unchanged.
Remote-only missing paths no longer prompt local initialization. Credential handling
was checked against Vault `service:github`; no values are stored in project files.

Verification before shared installation:

- 140 deterministic tests passed, including all prior 131 and 9 observation tests.
- Isolated native Codex passed actual prompt/Stop recording, context-marker/viewer,
  original core rules, multi-project context, resume/corrected scope and damaged Brain isolation.
- Plugin validator passed. No new package dependencies or business repository copies.

Limits: systemMessage requests host display; interactive inline rendering has not
been verified. Independent terminal viewer is proven, not a replacement claim for
that unfinished requirement. File changes do not identify authors; local tracking
refs do not prove live GitHub state. Remote Brain fetch and fleet rollout are not added.
See `docs/execution-observability.md` for exact retention, limits and scope.
