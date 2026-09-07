# Boss Brain state

## Current state

Continuity protocol v2 is implemented and installed on the development host. The
Codex native plugin and global directives are configured; legacy fallback Codex
hooks are removed. Claude fallback files are installed but real Claude behavior
has not been accepted. Use `boss init --dry-run` to inspect other adopted projects;
this upgrade did not bulk-modify their documentation or business services.

## Verified behavior

- Deterministic suite covers global rules, document mappings, multi-project tasks,
  read-only boundaries, durable knowledge reviews and native hook migration.
- Real isolated Codex journeys loaded global rules and two project contexts,
  retained a task constraint on resume, and saved a confirmed decision with file
  evidence without creating a business commit.
- Source commits: `89b2780`, `35b23d7`, `e10243e`, `8677bbc`; all pushed.

## Next action

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
