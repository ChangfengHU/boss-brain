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
