# Preservation is a separate migration acceptance gate

Verified during repair `9aa7f9d`; detailed findings and remaining differences are in
`docs/requirements-preservation-audit.md`.

The user's original twelve rules are a contract, not editable summary material.
Retain their original wording and distinguish later user-authorized additions.
The initializer rejects a template missing that core, and the preservation test
pins the original source digest. A future user-requested change needs an explicit
review of the corresponding baseline; do not change both template and test merely
to make a migration pass.

A function still present in the tree may have stopped running. The v2 Hook early
return bypassed legacy task selection/drift processing while old tests continued
to pass in legacy mode. Migration tests must enable the new mode and reuse old
user journeys, including resume from existing session metadata.

Budget project metadata and bodies separately. Truncating an entire project card
after a long state can erase tasks, constraints, indexes and capability relations.
Test tail markers, topic lengths, multiple projects and real host delivery; report
which sections were shortened. Never equate configured output size with actual
host receipt, or function existence with preserved behavior.

State facts are not instruction authority. Running code/configuration can prove
what exists, not authorize overriding the user's intended outcome or core rules.
Keep acceptance per requirement; identify unresolved behavior changes rather than
using a total passing test count as proof of complete preservation.

## User-visible behavior is an acceptance gate

The user explicitly wants forward compatibility, not a forced rollback tradeoff.
Listing a missing behavior as a known gap is not permission to remove it or call
the upgrade complete. Keep source acceptance separate from installed acceptance.

V2 receipt repair must test the actual rendered answer as well as Hook JSON.
Body deduplication and receipt policy are independent: `always` still needs a
receipt when the body is unchanged, while `off` and observe-only must suppress it.
Task projects and reference candidates must not be presented as the same ownership
class. Reserve space within the bounded context rather than allowing the receipt
to be silently truncated. A strict user output format still takes precedence.

## Verify the promoted runtime, not only source

`4f2e368` replays the original guarded/strict remediation journeys through real v2
work bindings. Use a synthetic GitHub identity and a separate local bare upstream
so push/record checks run end-to-end without writing a real remote repository.
Local startup patrol and machine initialization must not imply project work claims.

After an installer promotion, compare protected global directive, registry and
configuration bytes. Run `python3 -m tests.installed_hooks_e2e` to compare actual
source/distribution/cache files and invoke each retained prompt and Stop entrypoint
with disposable routing state. Merely seeing "installed" or preserving an old path
does not prove that the old session executes the repaired behavior. Six entries
passed this promotion, and protected-file hashes stayed identical.
