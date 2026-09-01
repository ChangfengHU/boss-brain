# Security and privacy

Boss Brain treats agent hooks and skills as trusted local code. Review a release before installation.

- No installer, plugin file, machine Brain, project document, log, or response may contain credential values.
- Vault values are retrieved only when needed. Durable files store key names, purposes, owners, and recovery procedures.
- A replacement machine needs a separately provisioned Vault bootstrap credential; it never comes from Git.
- Lifecycle hooks make no network calls. Network synchronization is an explicit CLI or timer action.
- Machine snapshots use an allow-list of generated files and sanitize credential-bearing Git remotes.
- Automatic discovery scans bounded local roots and never initializes foreign repositories.
- Session claims prevent one session from treating another session's work as its own.
- Installer edits are backed up; legacy data and every `.brain/` directory are preserved.

Before release, scan both the working tree and Git history. Revoke any credential that has ever appeared in chat, a remote URL, a commit, or an installer—even if later deleted.

Never open a public issue containing a live secret.
