# Task scope corrections and project failure isolation

Verified by `93ff028` and `tests/test_continuity_refinements.py`.

A task association list cannot be append-only: after the user corrects ownership,
the retired project would remain confirmed context. `session bind --replace-projects`
replaces that task's full project/access set, while preserving other tasks and old
work audit claims. The latter describe past changes, not future write authority.
Use the read set first, then add authorized work projects for mixed access levels.

Capability discovery visits registered projects beyond the current task. Catching
metadata failures only at the outer Hook boundary made one unrelated damaged
manifest erase all healthy context. Isolate capability and body/guidance reads by
project, retain the task goal and healthy bodies, and report unavailable names in
private context/trace. Reuse the capability inventory during one render rather than
rescanning every registered project for each selected body.

Initialization must validate selected project identity before global configuration
writes, preserve malformed manifests, and report each project's outcome. A bound
task with failed Brain initialization is partial, not a successful setup. Context
recovery is separate: after the source document is repaired, its changed fingerprint
must cause reinjection without silently changing task ownership.

Real isolated Codex acceptance includes a damaged registered project and a resumed
task-scope correction. Passing a single-project happy path cannot establish these
multi-project properties. Program checks still do not prove semantic ownership;
the Agent must use the user's confirmed scope.
