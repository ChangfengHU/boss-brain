# Native Hook migration and trust-table preservation

Verified while upgrading continuity protocol v2; implementation fix: `35b23d7`.

Native Codex trust-table names contain `plugin-name:hooks/...`. A cleanup function
that removes every line containing the managed marker can delete their table headers
while leaving repeated `trusted_hash` keys, corrupting TOML. Matching a substring is
not sufficient to identify a managed hook block.

Recognize explicit comment-delimited ranges and separately inspect executable hook
entries. Preserve native trust tables. Also handle partially migrated fallback entries
whose comment markers are absent, using the known runtime executable path.

An existing native marketplace pointing at the verified local source should be
reinstalled directly. If native reinstallation fails, do not silently append fallback
hooks while leaving the native plugin enabled. Back up first and verify one handler
per event after migration. The regression fixture must contain native trust tables
and fallback hooks together; a fresh empty config does not exercise this failure.

Validation: `test_hook_cleanup_preserves_native_trust_tables_and_removes_fallback`
plus actual development-host native reinstall. No credential values are involved.

## Live sessions retain retired cache commands

The v2 upgrade missed a lifecycle case: native reinstallation can remove an old
cache while an already-running session still holds its absolute Hook command.
Fresh-session acceptance does not test that command. This caused a real missing
`scripts/boss.py` Stop failure; repair is implemented in `1e695fd`.

Native and fallback commands now return `{}` successfully when their script or
Python interpreter is missing. Healthy handlers retain their output and exit code;
this is not a blanket bypass of configured policy checks. Windows guards are
included but have not been executed on a Windows host.

The installer remembers verified cache versions before native reinstallation and
restores missing executable-only bridges afterward, even when the native CLI fails.
Bridges forward to the stable distribution and skip when that runtime is absent.
They never recreate plugin manifests or overwrite an existing cached module. For
an older, already-pruned version not in inventory, use the explicitly reported
version with `python3 scripts/install.py repair-hooks --version VERSION`.

Regression: `tests/test_hook_compatibility.py` covers missing files/interpreters,
preserved handler results, retired-cache forwarding, partial installation failure,
existing-file preservation and unsafe paths. Real-host validation ran Stop through
both retained old entrypoints and exercised missing-path guards in the installed
native manifest. Future plugin updates should go through this installer; an
out-of-band cache deletion cannot restore an old unguarded command by itself.
