# Continuity protocol v2

## Installation and initialization

Installation refreshes the plugin runtime and both standalone skill entries. The source
marketplace remains the existing local Boss Brain marketplace. Reinstall with its CLI after
changing the Codex cachebuster. Start a new host thread to discover changed skill definitions;
a running thread can explicitly read the new instructions, but must not claim automatic reload.

`boss init --dry-run` is read-only. `boss init` merges the shipped directive block into the
Codex global AGENTS.md and, when Claude is present, CLAUDE.md, enables v2 continuity and
initializes registered GitHub projects. `--rules-only` excludes projects; repeated `--project`
restricts initialization to registered paths. It does not scan and mutate every GitHub checkout.

Directive writes retain outside text byte-for-byte and store a private pre-image before edits.
The known Project Brains v0.7.0 block is migrated; unrecognized/edited blocks, duplicate markers
and symlinks fail closed. Repeated init is idempotent. Installed block hashes are checked before
uninstall/restore. Restoring rules preserves later outside edits; configuration rollback refuses
post-install config changes instead of overwriting them. Backups and project memory remain.

The CLI reports file configuration, not proof the host loaded instructions. Real host acceptance
must observe global rules and lifecycle context in a new/resumed session.

## Project entries

`boss adopt` establishes a basic entry when v2 is enabled. `boss brain-init PATH` requires an
already-adopted Git root. `boss init` can repair all registered projects. `session bind --access work`
performs the same initialization as part of the Agent's explicitly authorized work setup.
Hooks never initialize on SessionStart, scanning, ambiguous mentions or read-only requests.

The manifest contains schema 2, normalized GitHub identity, content status `needs-review`,
relative document mappings and an explicit review gap. Existing Brain documents take precedence,
then existing root-level documents, then new Brain paths. Only manifest and a truthful inventory
state are created; no fabricated task/log/wiki history. No commit or network push happens inside
hooks or initializer; the Agent persists only its own authorized files using normal Git discipline.

Document paths must resolve inside the owning repo. Ignored Brain files, malformed manifests,
identity changes and unsafe symlinks are refused. `.brain-home` is reported as delegated and kept;
the Agent must verify the owner repository before continuing. Git worktrees remain separate
working copies; initialization never changes branches or tries to synchronize their uncommitted files.

## Multi-project tasks and context

`session bind` records a user-confirmed task with repeated project and constraint arguments.
Read bindings only provide context; work bindings establish commit baselines and initialization.
Adding another task keeps the previous task. `--replace-constraints` is for an explicitly confirmed
revision, not a silent conflict-resolution mechanism. The Skill accepts natural-language intent;
the CLI records the Agent's interpretation and cannot verify that interpretation itself.

The prompt hook combines the focused task, cwd, explicit references, mentioned projects and
one-hop matching capability providers/consumers. Mentioned/dependent projects are candidates,
not write claims. Confirmed/workspace states are bounded; relevant conventions and wiki may
both be injected. Other tasks remain in the session but do not automatically load all their files.
Selection retains at most six project bodies within a configurable character budget (default 10,000).
Remaining candidate names are pointers. Content fingerprints suppress duplicates; SessionStart,
resume and compact reinject even an unchanged fingerprint. Facts still need live verification.

V2 trace data includes project sets, focused task, content digest and actual output size. It
does not emit legacy single-project switch receipts. `boss explain --session ID --json` and
`--show` expose diagnosis on explicit request. Missing/unsafe metadata degrades with a warning,
not a fabricated successful load. Hooks remain local-only.

## Critical knowledge

After verifying a conclusion and owner, the Agent flags a concise summary, kind and source:

```bash
boss knowledge flag --session SESSION --path PROJECT --key execution-owner \
  --kind decision --summary "The workflow owns execution" --source docs/architecture.md
boss knowledge list --session SESSION
boss knowledge resolve --session SESSION --id ID --status updated --file docs/architecture.md
```

Update the authoritative document, not a second contradictory copy. Confirmed knowledge does
not require a business-code commit; ordinary Q&A remains write-free and explicit no-record wins.
Do not save raw chat or secrets. Program hooks only identify candidates; they never invent prose.
An ambiguous multi-project correction must be assigned by the Agent, not by the first alias.

Private per-project reviews live outside expiring session caches. A new session bound to the
same project can retrieve the summary/source and resolve it. Resolution uses a lock and rejects
already-resolved reviews and unchanged/outside documents. This proves changed bytes, not semantic
truth or a successful commit/push. Git persistence remains separately verified by the Agent.

## Acceptance and limits

Run the full deterministic suite (`python3 -m unittest discover -s tests -q`), plugin/skill
validators and `tests/continuity_codex_e2e.py`. The real Codex test uses temporary projects and
restricted copied auth, verifies global directive loading, multi-project context, a retained
constraint after auxiliary-workspace resume, tool-free retrieval and all relevant lifecycle traces.
It never modifies business services or publishes external artifacts.

Not claimed: automatic semantic truth validation, zero intent drift, auto-generated complete
historical records, automatic Git pushes from hooks, transparent remote `.brain-home` editing,
or real Claude/macOS/Windows acceptance. Capability retrieval is deterministic lexical matching,
not a vector search service. Background capture after the final reply is not assumed: the Agent
saves before replying or reports the pending item/failure.
