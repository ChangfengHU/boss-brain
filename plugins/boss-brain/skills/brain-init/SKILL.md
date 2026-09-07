---
name: brain-init
description: Initialize or incrementally complete an explicitly selected existing project's Brain. Use when the user requests brain-init or project memory initialization; not for merely mentioning a project.
---

# Project Brain initialization

Use the installed `boss` CLI and the adjacent [Boss Brain initialization reference](../boss-brain/references/initialize.md). Read that reference completely before initializing. This entry replaces legacy Project Brains commands; do not call `.project-brains` shell scripts or copy credentials into project memory.

Resolve the actual Git owner, preserve existing work and `.brain-home`, then use `boss adopt PATH` and `boss brain-init PATH`. If global setup is missing, explain the scope of `boss init` before invoking it; use `--rules-only` when the user did not authorize initializing other adopted projects.

A successful CLI result means basic inventory exists, not that business facts are verified. Follow the reference to review code, relevant conversation and runtime evidence. Reuse documents declared in `.brain/manifest.json`; report gaps rather than generating empty histories. Commit and push only the task's authorized changes after validation.
