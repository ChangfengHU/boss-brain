# Requirements preservation audit

## Scope and failure of the previous acceptance

Compared the user's twelve Project Brains v0.7.0 core rules, pre-v2 revision
`c5bf077`, the v2 implementation, installed global rules, and the legacy/v2 test
paths. This is a bounded migration audit, not a claim to have found every possible
defect in all historical releases or proved every future Agent decision correct.

The migration treated a shorter rewritten directive template as equivalent to the
user's original rules, without a clause-by-clause preservation gate. Enabling v2
also returned through a new Hook branch before legacy task/goal handling. Most
existing journey tests still exercised legacy mode; passing them did not prove
those behaviors survived enabling v2. The earlier completion claim was too broad.

## Findings addressed in this repair

| ID | Finding and impact | Repair / evidence |
| --- | --- | --- |
| R01 | Global rule replacement omitted or weakened first-principles reasoning, non-flattery, ambiguity handling, surgical edits and other explicit disciplines. | All twelve original clauses retained verbatim in the live template; fixed original-asset digest in the regression; initialization refuses templates missing the core text. Real native Codex retrieved original thinking/code rules without tools. |
| R02 | v2 bypassed stable `@task:ID` selection and task-drift warnings, including legacy session task state. | Reuse task records and drift messages through the multi-project path; migrate the selected legacy task as read context; reject completed/ambiguous targets and retain other contracts. |
| R03 | v2 bypassed free-form goal-drift scoring. | Reuse legacy goals, synonym/scoring logic and warnings; record candidate/score/evidence without switching the goal. |
| R04 | Applying a 1,300-character cap to the entire project body could remove tasks, indexes and capability relations after a long state. | Keep ownership/task/index/relation metadata ahead of separately budgeted bodies. Preserve the prior state-card limit rather than applying an additional whole-project cap. |
| R05 | An additional 1,200-character cap shortened already-bounded Wiki/convention selections; host configuration also advertised only 5,000 characters against v2's larger budget. | Remove the extra topic cap, retain selective routing and legacy topic limits, fairly share the total body budget, report truncated sections, and align the declared host allowance with the maximum v2 budget. Native long-state marker retrieval passed. |
| R06 | `session bind --access work --task-id ...` did not connect a matching project task to the Stop audit's task field. | Link an active matching task to its existing authorized work claim; preserve single-active-task initialization. |
| R07 | Without a work binding, Stop could establish its baseline after the work and then report no findings. | Report `baseline-missing` and an incomplete audit; do not invent a retrospective baseline. This gap is nonblocking, including strict read-only sessions. |
| R08 | Bare `@` no longer exposed the project roster inside a workspace. | Restore read-only roster access without changing task ownership. |
| R09 | Root-mapped state, Wiki and handoff documents were used by injection but some diagnostic commands still read hard-coded `.brain` paths. | Route project summary, risk, index diagnostics/fixes and handoff-file checks through declared document paths. Handoff acceptance-file location remains the established `.brain/HANDOFF_ACCEPTANCE.md` contract. |
| R10 | v2 did not update the default preview used by plain `boss explain --show`, and human-readable output omitted the project set. | Restore the default preview, project set, timestamp/content policy and section/truncation diagnostics. |
| R11 | Cross-session knowledge loading silently stopped at the first 100 filenames, including closed reviews, potentially hiding pending knowledge. | Remove the silent file-count truncation; regression places a pending review after 100 closed records. Very large queues still require latency acceptance. |
| R12 | Missing internal `continuity.py` failed before the existing Hook exception handler, despite the earlier missing-runtime compatibility claim. | Missing internal continuity module returns `{}` for Hook invocations; non-Hook commands still fail explicitly. Existing retired-entry compatibility remains. |

`tests/test_v2_preservation.py` provides sixteen focused tests for these contracts,
including malformed-template rejection, ambiguous cross-project task IDs, repaired
context bounds, no-write behavior and legacy-to-v2 transitions. The full suite
passed 108 tests. Plugin/skill validators and compilation passed. The extended
`continuity_codex_e2e.py` passed in an isolated **native-plugin** installation with
long state cards, two projects, resume, scope replacement, damaged-project
isolation, original global-rule retrieval and authorized knowledge persistence.

## Core rules versus later requested additions

The original core file remains unchanged. The installed global block includes it
verbatim, then labels the later user-requested multi-project/critical-knowledge
extension separately. Development logs and commit evidence retain their original
discipline; the later explicit request allows verified decisions/lessons in
project conventions/Wiki without a business-code commit. Ordinary Q&A and explicit
no-write/no-record requests remain write-free. No requirements-interrogation mode
was added. Existing outside-block custom rules remain protected.

An inherited skill reference also mixed factual evidence priority with authority,
placing the user's decision after observed state/code in a single list. It now
distinguishes what currently exists from what the user authorizes or wants; running
code cannot authorize discarding user requirements. This wording existed before
v2 and is not presented as a newly introduced code deletion.

## Differences not silently declared equivalent

- The installed v2 runtime still lacks automatic user-visible routing receipts.
  Following the user's compatibility correction, the current source reconnects
  bounded receipts to the multi-project path without reverting v2. It preserves
  off/changes/always policies, distinguishes task owners from reference projects,
  and separates receipt delivery from body deduplication. See `tests/test_v2_receipts.py`
  and `BOSS_TEST_RECEIPT=1` in the native Codex journey. Source acceptance is not
  shared-runtime deployment; full legacy parity is still not claimed.
- Legacy SessionStart called patrol and automatic machine-Brain initialization.
  v2 registers the current qualified workspace, while explicit scan/machine CLI
  workflows remain. Full-home automatic patrol/machine initialization is not
  claimed restored; lifecycle scope and latency need explicit acceptance.
- v2 can retrieve relevant guidance from multiple mention/capability candidates;
  the legacy alias path supplied only a pointer. Candidate retrieval is read-only
  and not a work claim. This is a multi-project behavior change, not identical
  routing under a new name.

## Remaining limits

No semantic guarantee that an Agent always obeys every rule, always identifies
important knowledge, or never misinterprets project ownership. No all-project or
fleet-wide initialization, real Claude/Windows/macOS acceptance, unlimited context,
or automatic Git persistence inside hooks. Baseline absence is reported, not
reconstructed. Existing strict/data-loss checks are not blanket-disabled.

Future migrations must review both clause preservation and enabled-path user
journeys. Compare the actual installed rule text and Hook outputs, not merely
function existence, template markers, process exit codes or aggregate test counts.

## Compatibility release checklist

This checklist separates existing evidence from remaining work. Passing the receipt repair
does not close other rows. Preserve the old baseline `c5bf077` and the original twelve rules;
do not delete new features or user data to make a comparison pass.

| User-visible contract | Evidence / current disposition | Remaining release gate |
| --- | --- | --- |
| Original twelve global rules | `test_all_original_core_rules_survive_global_migration`; native rule retrieval | No guarantee of every future semantic decision |
| Project identification feedback | `test_v2_receipts.py`; optional native visible-answer assertion | Shared installed runtime not updated |
| Task switch and drift | Enabled-v2 preservation tests plus receipt task-switch test | Natural-language false positives remain possible |
| Context, long state and Wiki/conventions | Enabled-v2 preservation and native long-marker journey | Bounded selective retrieval, not full-history loading |
| Multiple task owners and corrected scope | `test_continuity_refinements.py`; native resume/correction | Agent must verify intended ownership |
| Knowledge reminders and durable writeback | v2 cross-session tests; native decision persistence | Lexical candidates and changed bytes do not establish truth |
| Development logs, push and Stop | Existing strict/guarded journeys; v2 baseline/task-link tests | Full strict remediation journey still needs explicit enabled-v2 replay |
| Handoff and Wiki/convention checks | Existing CLI journeys plus v2 mapped-document checks | Actual takeover remains Agent-driven |
| Session switches and isolation | New enabled-v2 receipt mode tests plus existing control journeys | Project-level switch was never implemented |
| Missing Hook resources and old cache paths | Compatibility suite and prior retired-entry checks | Recheck installed entrypoints before any promotion |
| Startup full-home patrol and machine initialization | Explicit commands retained; v2 startup bypass remains | Restore/validate lifecycle behavior; cannot declare equivalent |
| Machine snapshot/restore | Existing explicit CLI journeys | Real timer longevity and reclaimed-host recovery not accepted |
| Multiple-candidate retrieval | v2 intentionally retrieves more than old alias-only pointers | Documented behavior change, not identical legacy routing |
| Claude / Windows / macOS | No real-host acceptance | Do not claim accepted support |

The user's desired outcome is forward compatibility, not a forced choice between old and new
features. A known behavioral gap must be tracked as an unresolved release gate, not renamed
an optimization or silently accepted because it appears in this document.
