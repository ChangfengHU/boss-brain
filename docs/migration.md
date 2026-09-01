# Migration from Boss and Project Brains

Version `0.1.0` merges the runtimes without changing their ownership model:

- machine data remains under `~/.boss/`;
- project `.brain/` directories remain inside their repositories;
- Project Brains registry rows merge into `~/.boss/registry.tsv` by path;
- duplicate lifecycle hooks become one Boss Brain handler per event;
- token and credential files are never migrated;
- legacy directories are not deleted.

The installer stores timestamped backups under `~/.boss/backups/install-*`. Re-running installation is idempotent. Uninstall removes code and hook wiring while preserving data. Rollback restores the most recent backed-up Codex and Claude configuration.

Inspect migration without changing data:

```bash
boss migrate --dry-run
```
