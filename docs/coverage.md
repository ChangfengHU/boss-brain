# Capability-to-test coverage

Passing test counts are not a product-completeness claim. A capability is called verified only when a test asserts its observable user outcome. `Partial` means an important boundary remains; `Not automated` and `Not implemented` are release limits, not implied coverage.

| Product behavior | Status | Automated evidence | Remaining boundary |
| --- | --- | --- | --- |
| Owned, active repository discovery | Verified | `test_scan_adopts_only_owned_active_repo_without_creating_brain` | Real large-home patrol performance |
| Foreign, stale, empty, malformed, colliding repositories | Verified | discovery and resilience tests | Filesystem permission-denied trees |
| Concurrent registry updates and stale/live locks | Verified | concurrency and lock recovery tests | Multi-host shared filesystem is unsupported |
| Workspace context injection | Verified locally and with real Codex | normal workspace tests; remote ordinary-user answer | Interactive hook trust review |
| Roster injection outside a Git workspace | Verified | `test_roster_lists_projects_without_eagerly_loading_project_bodies` | Very large registries beyond display cap |
| Explicit `@project` routing | Verified locally and with real Codex | cross-project tests; remote cross-project answer | Ambiguous aliases with equal length |
| Low-confidence alias pointer | Verified locally and with real Codex | `test_low_confidence_alias_is_pointer_only_until_user_is_explicit`; remote pointer-only turn | Natural-language false-positive corpus remains small |
| Duplicate suppression and resume/compact reinjection | Verified | duplicate/resume test; remote resumed answer | Long multi-day session history |
| Context observability | Verified locally and with real Codex | session-isolated append-only traces, project/task transitions, suppression reasons, `boss explain --session`, redacted preview, and automatic receipt journey | Hook receipts rely on agent rendering because Codex has no native plugin status component |
| Secret redaction in hook output, final answer, events, and preview | Verified for known token shapes | resilience, preview, and remote user tests | General semantic secret detection is not claimed |
| `STATE.md` injection and large-card capping | Verified | workspace and large-state tests | Invalid encodings are replacement-decoded, not rejected |
| `TASKS.md` active checkbox and legacy `active` parsing | Verified | current/complete/limit/refresh and legacy tests | There is no task state machine or task ID integrity yet |
| Cross-project relations and capability peers | Verified | relations/capability injection test | Interface availability is not actively probed |
| Wiki index routing and selective topic injection | Verified locally and with real Codex | startup/body separation, multi-topic dedupe, cross-project scoping, path containment, and remote unique-marker answer without tools | Matching remains index-title/token based; consolidation is still human-reviewed |
| Wiki index maintenance, path safety, duplicate/orphan/stale checks | Verified locally | `boss wiki check` diagnostics and `--fix` journey; inverted-index semantic candidates with high-frequency fan-out protection | Candidate generation avoids normal all-pairs scans, but automatic consolidation and lesson merging remain unimplemented |
| HANDOFF and HANDOFF_ACCEPTANCE workflows | Verified locally | `boss handoff check` static contract plus safe command execution journey | Interactive takeover remains skill-driven |
| Conventions selection and index checks | Verified locally | prompt-matched injection; unresolved conflict blocking; deterministic `supersedes`, scope, and priority resolution | Same-scope/same-priority conflicts intentionally require human resolution |
| Stable task-ID drift detection | Verified locally | task ID selection, natural-mention warning, explicit `@task:ID` switch, completed-task rejection, and explain trace | Free-form goal drift without a stable task ID remains outside the model |
| Free-form goal-level drift detection | Verified locally | legacy no-ID active goals, bilingual n-grams/synonym normalization, scored warning evidence, and pointer-only explain trace | This is explainable lexical semantics, not an embedding/LLM classifier; it does not infer or rewrite task IDs |
| Project-target drift prevention | Partial | alias pointer does not claim or load; explicit target does | Concurrent multi-agent task ownership is not modeled |
| Evidence must reference latest work commit | Verified | strict and stale-evidence tests | Evidence command/result schema is not fully validated |
| Wiki judgment required in evidence | Verified as a field gate | strict missing-then-present judgment test | Judgment truthfulness cannot be inferred automatically |
| Current-session dev-log required | Verified | strict completion and preexisting-dev-log rejection | Narrative quality and commit linkage are not validated |
| Uncommitted Brain records block guarded/strict completion | Verified | dirty-Brain test | Files outside `.brain/` remain normal Git responsibility |
| quiet / guarded / strict policy behavior | Verified | policy and user-recovery tests | Real interactive Stop remediation remains model-dependent |
| Machine Brain initialization and stable sync | Verified | machine snapshot tests | Real timer longevity |
| Successful Machine Brain push | Verified locally and by GitHub canary | machine push/restore journey; Vault-backed create/push/delete canary | Token rotation and least-privilege policy remain operational responsibilities |
| Missing/deleted project detection and clone recovery | Verified with local Git remote | explicit delete, MISSING status, restore, idempotency test | Uncommitted files are unrecoverable by design |
| Corrupt inventory and unavailable project remote | Verified | corrupt/unavailable restore test | Interrupted partial clone and disk-full faults |
| Clean replacement-machine restore | Verified in isolated HOME | clean-machine restore journey | Real reclaimed host with Vault bootstrap |
| GitHub repository creation command path | Verified locally and by GitHub canary | fake-`gh` contract plus real create/push/delete canary; process-only askpass and no repository credential persistence | Canary must be repeated after credential or GitHub policy changes |
| systemd timer generation and enable failure | Partial | interval and fake-controller tests | Multi-day live timer/push canary |
| Vault reference containment | Verified for accepted/rejected shapes | Vault and snapshot security tests | Real Vault outage behavior |
| Install/update/uninstall/rollback preservation | Verified in isolated HOME | installer and rollback tests | Interactive existing-plugin trust UX |
| Claude Code lifecycle | Out of scope | Not tested by project decision | Not a release target for this work |
| macOS and Windows | Out of scope | None | Not release targets for this work |

## Required reporting rule

Release and handoff reports must name the covered rows and list every remaining `Partial`, `Not automated`, and `Not implemented` row that is relevant to the claim. “All tests pass” means only that the enumerated suite passed.
