# Critical knowledge synchronization

Project knowledge can become stale without a business-code commit. A user correcting an architecture/release relationship, or an Agent discovering a different development host, should initiate a knowledge review rather than silently disappear after the answer.

Prompt hooks detect a conservative set of correction/domain phrases and explicit memory requests. They create session-scoped pending metadata only when a Git cwd or explicit registered project establishes a candidate owner. No prompt body, generated fact or business document is persisted by the hook. The selected project is a candidate, not permission to write: cross-project discussions still require the Agent to verify ownership.

Verified Agent discoveries need the explicit channel (keyword detection cannot see tool conclusions):

```bash
boss knowledge flag --session SESSION --path /path/to/project --key release-experience-channel
boss knowledge list --session SESSION
boss knowledge resolve --session SESSION --id ID --status updated --file docs/architecture.md
```

Resolve `updated` requires a Markdown document within the target project with bytes different from the tracked-file baseline captured when flagged. `deferred` and `dismissed` preserve explicit dispositions. This is edit evidence, not semantic validation, commit linkage or proof of push; those remain Agent review and existing Git discipline. Preexisting untracked files have no captured baseline, so use tracked authoritative documents for strong evidence.

Pending reviews are injected on following prompts even when normal context matching suppresses output. Stop emits a nonblocking systemMessage; disabled sessions skip automatic detection, observe-only records without injection or reminders. No-write/analysis-only user instructions always override document maintenance. Metadata contains hashes, project path, fixed trigger labels and disposition only; discovery keys are hashed.

The Skill directs the Agent to verify facts vs decisions vs hypotheses, correct the original source document, resolve or report the gap. This closes the missing workflow, not autonomous factual learning. Durable cross-session project queues, semantic fact validation and authenticated host E2E of the reminder are not claimed. Resume using the same session preserves pending reviews.

Regression coverage: actual hook output without registry/context match, reminders on continuation and Stop, duplicate flags, session isolation, unchanged/out-of-project rejection, no-write deferral, modes, prompt privacy and ordinary question/unknown workspace suppression. Run `python3 -m unittest tests.test_knowledge_sync`.
