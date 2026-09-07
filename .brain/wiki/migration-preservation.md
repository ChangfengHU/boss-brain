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
