# Initialize or adopt a project

Only run this workflow when the user explicitly asks to initialize, adopt, or bring an existing project under Boss Brain.

1. Resolve the Git root. If `.brain/` already exists, inspect it and fill only real gaps; never rebuild or overwrite it. If `.brain-home` exists, operate in the pointed owner repository.
2. Establish success criteria and inspect three evidence sources:
   - repository: README, focused docs, recent Git history, CI/deploy/test configuration;
   - conversation: durable goals, responsibilities, confirmed decisions, rejected options, active/finished/deferred tasks, blockers, hazards, and acceptance criteria;
   - reality: available commands, services, paths, and credential locations without exposing credential values.
3. Classify verified facts using [brain-schema.md](brain-schema.md). Reuse the repository's existing durable documents where they already serve the purpose. Do not generate empty placeholders.
4. Identify operational dependencies by name and location. Do not copy credentials into the plugin, registry, logs, or documentation. If recovery is missing, report the risk and ask the user where the credential should be recovered from.
5. Use `boss adopt <path> --name <name>` and `boss brain-init <path>` to establish the registered inventory and document map. `boss init` enables protocol v2 and initializes all already-adopted GitHub projects; `--rules-only` excludes project writes and `--dry-run` previews without enabling anything. Initialization must not use obsolete `.project-brains` scripts. Check `.brain/manifest.json` and reuse its document locations. Missing business facts remain `needs-review`; never infer successful deployment or completed tasks from Git metadata. Choose aliases specific enough to avoid incidental matches.
6. Run the project's real validation commands. Review memory for secret-like values before committing.
7. Report coverage for goal, progress, conventions, assets, credential locations/recovery, historical decisions, blockers, and next action. Mark missing facts explicitly.

Initialization must not change application code unless the user separately asks for that work.
