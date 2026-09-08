# Boss Brain state

## Current state

Execution observability is implemented in source with opt-in session/project display
levels and a direct terminal event viewer. 140 tests and isolated native Codex
lifecycle passed. Shared installation pending; interactive inline systemMessage
rendering is not claimed. See docs/execution-observability.md and
dev-log/2026-09-08-observability.md. Existing defaults/core rules are preserved.

The user chose forward compatibility, not rollback. `43e77b9` adds explanatory
Chinese help and project-scoped receipt overrides on top of the accepted repairs.
Installed version is `0.1.0+codex.20260908033047`; source/cache equality and seven
installed/retired help, prompt and Stop entrypoints passed. The compatibility checklist in
`docs/requirements-preservation-audit.md` tracks evidence and remaining boundaries.

Preservation repair `9aa7f9d` supersedes the earlier broad v2 acceptance claim.
The twelve original user rules are restored verbatim in installed global directives.
Twelve audited implementation/compatibility findings were addressed; see
`docs/requirements-preservation-audit.md` for exact evidence, later receipt/startup
repairs and remaining behavior differences. Do not claim universal semantic parity.

Continuity protocol v2 is implemented and installed on the development host. The
Codex native plugin and global directives are configured; legacy fallback Codex
hooks are removed. Claude fallback files are installed but real Claude behavior
has not been accepted. Use `boss init --dry-run` to inspect other adopted projects;
this upgrade did not bulk-modify their documentation or business services.

## Verified behavior

- `43e77b9`: 131 tests passed. Detailed help explains purpose, scope, examples,
  expected results and recovery without executing examples. Native Codex explained
  project scope/recovery without changing settings or project entries. Project
  overrides preserve global defaults, context and guarded Stop; seven installed
  entries and installed help/override probes passed. Protected-file hashes unchanged.

- `4f2e368`: 122 deterministic tests passed. Added v2 daily-patrol/local-machine
  initialization checks and replayed four original Stop remediation journeys with
  v2 work bindings. Native Codex receipt/rules/multi-project/knowledge acceptance
  passed. Installation preserved both global directives, registry and config
  byte-for-byte; six actual new/retired prompt and Stop entrypoints passed.

- `9946caf`: 115 deterministic tests passed, including seven v2 receipt tests.
  Final source passed native Codex visible-receipt, original-rule, long-context,
  multi-project and resume/corrected-scope acceptance. The first receipt run also
  preserved the authorized knowledge-writeback journey. No shared reinstall occurred.

- Preservation suite: 108 tests passed, including 16 enabled-v2 preservation tests.
  Real isolated native Codex loaded original thinking/code rules without tools,
  read long multi-project state markers, resumed/corrected scope and persisted a
  confirmed decision. Installed source equality and four retired Stop entries passed.

- `93ff028`: user-confirmed task scope replacement, per-project context failure
  isolation and truthful partial initialization. All 92 deterministic tests passed.
  Real Codex observed corrected scope after resume, healthy context despite a
  damaged registered Brain, and a saved/resolved decision in a disposable project.
- Deterministic suite covers global rules, document mappings, multi-project tasks,
  read-only boundaries, durable knowledge reviews and native hook migration.
- Real isolated Codex journeys loaded global rules and two project contexts,
  retained a task constraint on resume, and saved a confirmed decision with file
  evidence without creating a business commit.
- Source commits: `89b2780`, `35b23d7`, `e10243e`, `8677bbc`; all pushed.

## Next action

Receipt/startup promotion is complete on this host. Keep the existing `changes`
receipt policy; it reports the first route and later routing/guidance changes, not
every identical prompt. New threads pick up the new plugin catalog; old executable
entrypoints were preserved and verified. Do not reinstall merely to answer questions.
Further fleet rollout and real platform acceptance require their own scope.

Users can ask `help boss` or run `boss help receipt` for detailed Chinese guidance.
Project receipt overrides use `boss receipt VALUE --project NAME`; `inherit` removes
the machine-local override. No project override was enabled on behalf of the user.
Whole-project plugin disabling remains separate and was not implemented or assumed.

Task scope corrections use `session bind --replace-projects` with the full revised
list and access level. Inspect per-project failures in initialization results or
`unavailable_projects` context traces; do not treat partial loading as full acceptance.

Live-session cache-pruning regression repaired in `1e695fd`: missing Hook resources
skip, and the installer preserves retired executable entrypoints. Both old Stop
entrypoints and installed missing-path guards were tested on the development host.
See `wiki/hook-migration.md`; use the installer for future upgrades so compatibility
restoration runs. This repair does not add project-specific plugin switches.

Use a new host thread to pick up revised skill definitions. For actual project
work, bind the user-confirmed task and capabilities with `session bind`; initialize
only its authorized owners. Track separate business work in its owning project.

## Remaining boundaries

Historical registry entries can be missing, non-Git or Git-ignored; do not change
their ownership/ignore rules automatically. Delegated `.brain-home` entries need
owner review. Semantic intent and knowledge correctness remain Agent responsibilities.
Real Claude/macOS/Windows acceptance and fleet-wide rollout are not claimed.
