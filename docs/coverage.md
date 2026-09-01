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
| Context observability | Verified | `boss explain`, `--json`, and redacted `--show` tests; remote context trace | No graphical UI yet |
| Secret redaction in hook output, final answer, events, and preview | Verified for known token shapes | resilience, preview, and remote user tests | General semantic secret detection is not claimed |
| `STATE.md` injection and large-card capping | Verified | workspace and large-state tests | Invalid encodings are replacement-decoded, not rejected |
| `TASKS.md` active checkbox and legacy `active` parsing | Verified | current/complete/limit/refresh and legacy tests | There is no task state machine or task ID integrity yet |
| Cross-project relations and capability peers | Verified | relations/capability injection test | Interface availability is not actively probed |
| Wiki index routing and selective topic injection | Verified locally and with real Codex | startup/body separation, multi-topic dedupe, cross-project scoping, path containment, and remote unique-marker answer without tools | Matching is index-title/token based, not semantic retrieval |
| Wiki consolidation, index maintenance, deduplication, and staleness | Not implemented | None | Planned optional Brain Evolution layer |
| HANDOFF and HANDOFF_ACCEPTANCE workflows | Not automated | None | Skill-driven assessment/preparation needs dedicated acceptance fixtures |
| Conventions selection and enforcement | Not automated | None | No runtime selector or validator exists |
| Goal-level task-drift detection | Not implemented | None | Sessions track repositories and commit baselines, not user goals or task IDs |
| Project-target drift prevention | Partial | alias pointer does not claim or load; explicit target does | Concurrent multi-agent task ownership is not modeled |
| Evidence must reference latest work commit | Verified | strict and stale-evidence tests | Evidence command/result schema is not fully validated |
| Wiki judgment required in evidence | Verified as a field gate | strict missing-then-present judgment test | Judgment truthfulness cannot be inferred automatically |
| Current-session dev-log required | Verified | strict completion and preexisting-dev-log rejection | Narrative quality and commit linkage are not validated |
| Uncommitted Brain records block guarded/strict completion | Verified | dirty-Brain test | Files outside `.brain/` remain normal Git responsibility |
| quiet / guarded / strict policy behavior | Verified | policy and user-recovery tests | Real interactive Stop remediation remains model-dependent |
| Machine Brain initialization and stable sync | Verified | machine snapshot tests | Real timer longevity |
| Successful Machine Brain push | Verified with local Git remote | machine push/restore journey | Real GitHub authentication and permissions |
| Missing/deleted project detection and clone recovery | Verified with local Git remote | explicit delete, MISSING status, restore, idempotency test | Uncommitted files are unrecoverable by design |
| Corrupt inventory and unavailable project remote | Verified | corrupt/unavailable restore test | Interrupted partial clone and disk-full faults |
| Clean replacement-machine restore | Verified in isolated HOME | clean-machine restore journey | Real reclaimed host with Vault bootstrap |
| GitHub repository creation | Not automated | None | Requires a disposable authenticated GitHub account |
| systemd timer generation and enable failure | Partial | interval and fake-controller tests | Multi-day live timer/push canary |
| Vault reference containment | Verified for accepted/rejected shapes | Vault and snapshot security tests | Real Vault outage behavior |
| Install/update/uninstall/rollback preservation | Verified in isolated HOME | installer and rollback tests | Interactive existing-plugin trust UX |
| Claude Code lifecycle | Not automated | Manifest consistency only | Real Claude session required |
| macOS and Windows | Not automated | None | Platform runners required |

## Required reporting rule

Release and handoff reports must name the covered rows and list every remaining `Partial`, `Not automated`, and `Not implemented` row that is relevant to the claim. “All tests pass” means only that the enumerated suite passed.
