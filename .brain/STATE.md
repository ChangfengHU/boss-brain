# Boss Brain state

## Current state

The user chose forward compatibility, not rollback. Source receipt repair `9946caf`
passed isolated acceptance and has NOT replaced the shared installed runtime. Do not
claim that existing sessions already display the repaired receipt. The compatibility
checklist in `docs/requirements-preservation-audit.md` tracks remaining release gates.

Preservation repair `9aa7f9d` supersedes the earlier broad v2 acceptance claim.
The twelve original user rules are restored verbatim in installed global directives.
Twelve audited implementation/compatibility findings were addressed; see
`docs/requirements-preservation-audit.md` for exact evidence and un-restored legacy
receipt/patrol behavior. Do not call all legacy behavior fully preserved.

Continuity protocol v2 is implemented and installed on the development host. The
Codex native plugin and global directives are configured; legacy fallback Codex
hooks are removed. Claude fallback files are installed but real Claude behavior
has not been accepted. Use `boss init --dry-run` to inspect other adopted projects;
this upgrade did not bulk-modify their documentation or business services.

## Verified behavior

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

Review a controlled promotion of the accepted source receipt repair that
preserves live Hook entrypoints. Do not automatically reinstall as a side effect
of answering plugin questions. Startup patrol/machine initialization and broader
compatibility acceptance remain open; do not represent receipts alone as full parity.

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
