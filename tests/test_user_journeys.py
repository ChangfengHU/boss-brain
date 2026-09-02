from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOSS = ROOT / "plugins" / "boss-brain" / "scripts" / "boss.py"
INSTALLER = ROOT / "scripts" / "install.py"


def run(
    args: list[str],
    *,
    env: dict[str, str],
    cwd: Path | None = None,
    stdin: str = "",
    timeout: int = 30,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd or ROOT,
        env=env,
        input=stdin,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def make_repo(path: Path, marker: str, *, remote: Path | None = None) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "main")
    git(path, "config", "user.name", "Journey Test")
    git(path, "config", "user.email", "journey@example.invalid")
    brain = path / ".brain"
    brain.mkdir()
    (path / "README.md").write_text(f"# {path.name}\n", encoding="utf-8")
    (brain / "STATE.md").write_text(
        f"# State\n\n## 现状\n\n{marker}\n\n## 下一步\n\ncontinue safely\n",
        encoding="utf-8",
    )
    (brain / "capabilities.tsv").write_text(
        f"provides\tjourney.{path.name}\tREADME.md\t{path.name} journey capability\n",
        encoding="utf-8",
    )
    git(path, "add", "README.md", ".brain")
    git(path, "commit", "-m", "initial")
    if remote is None:
        git(path, "remote", "add", "origin", f"https://github.com/me/{path.name}.git")
    else:
        subprocess.run(
            ["git", "init", "--bare", "--initial-branch=main", str(remote)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        git(path, "remote", "add", "origin", remote.as_uri())
        git(path, "push", "-u", "origin", "main")
    return path


class UserJourneyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.home = Path(self.temporary.name)
        self.boss_home = self.home / ".boss"
        self.boss_home.mkdir()
        (self.boss_home / "owner").write_text("me\n", encoding="utf-8")
        self.env = os.environ.copy()
        self.env.update({
            "HOME": str(self.home),
            "BOSS_HOME": str(self.boss_home),
            "BOSS_SKIP_PLUGIN_CLI": "1",
        })

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def boss(
        self,
        *args: str,
        cwd: Path | None = None,
        payload: dict | None = None,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return run(
            ["python3", str(BOSS), *args],
            env=env or self.env,
            cwd=cwd,
            stdin=json.dumps(payload) if payload is not None else "",
        )

    def test_normal_workspace_and_cross_project_context_do_not_mix(self) -> None:
        alpha = make_repo(self.home / "work" / "alpha", "ALPHA_USER_READY")
        make_repo(self.home / "work" / "beta", "BETA_USER_READY")
        self.assertEqual(self.boss("scan", "--adopt").returncode, 0)

        started = self.boss(
            "hook",
            "session-start",
            payload={"session_id": "route", "cwd": str(alpha), "source": "startup"},
        )
        workspace = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("ALPHA_USER_READY", workspace)
        self.assertNotIn("BETA_USER_READY", workspace)

        routed = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "route", "prompt": "请检查 @beta 的当前状态"},
        )
        context = json.loads(routed.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("BETA_USER_READY", context)
        self.assertNotIn("ALPHA_USER_READY", context)

        unrelated = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "route", "prompt": "解释一下二分查找"},
        )
        self.assertEqual(unrelated.stdout, "")

    def test_roster_lists_projects_without_eagerly_loading_project_bodies(self) -> None:
        make_repo(self.home / "work" / "alpha", "ALPHA_ROSTER_PRIVATE")
        make_repo(self.home / "work" / "beta", "BETA_ROSTER_PRIVATE")
        self.assertEqual(self.boss("scan", "--adopt").returncode, 0)
        started = self.boss(
            "hook",
            "session-start",
            payload={"session_id": "roster", "cwd": str(self.home), "source": "startup"},
        )
        context = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("alpha", context)
        self.assertIn("beta", context)
        self.assertNotIn("ALPHA_ROSTER_PRIVATE", context)
        self.assertNotIn("BETA_ROSTER_PRIVATE", context)
        trace = json.loads(self.boss("explain", "--json").stdout)
        self.assertEqual(trace["mode"], "roster")
        self.assertEqual(trace["content_policy"], "project-index")
        self.assertEqual(trace["sections"], ["project-index"])

    def test_low_confidence_alias_is_pointer_only_until_user_is_explicit(self) -> None:
        alpha = make_repo(self.home / "work" / "alpha", "ALPHA_STAYS_ACTIVE")
        wiki = make_repo(self.home / "work" / "llm-wiki", "WIKI_PRIVATE_STATE")
        self.assertEqual(self.boss("adopt", str(alpha), "--summary", "active workspace").returncode, 0)
        self.assertEqual(
            self.boss(
                "adopt",
                str(wiki),
                "--aliases",
                "wiki,知识库",
                "--summary",
                "technical knowledge base",
            ).returncode,
            0,
        )
        self.boss(
            "hook",
            "session-start",
            payload={"session_id": "drift", "cwd": str(alpha), "source": "startup"},
        )

        hinted = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "drift", "prompt": "wiki 的功能是不是还在"},
        )
        hint = json.loads(hinted.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("低置信度项目指针", hint)
        self.assertIn(str(wiki), hint)
        self.assertNotIn("WIKI_PRIVATE_STATE", hint)
        trace = json.loads(self.boss("explain", "--json").stdout)
        self.assertEqual(trace["event"], "UserPromptSubmit")
        self.assertEqual(trace["mode"], "alias")
        self.assertEqual(trace["confidence"], "low")
        self.assertEqual(trace["content_policy"], "pointer-only")
        self.assertEqual(trace["sections"], ["pointer"])
        preview = self.boss("explain", "--show").stdout
        self.assertIn("redacted context preview", preview)
        self.assertNotIn("WIKI_PRIVATE_STATE", preview)
        session = json.loads((self.boss_home / "state" / "sessions" / "drift.json").read_text(encoding="utf-8"))
        self.assertEqual(set(session["roots"]), {str(alpha.resolve())})

        explicit = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "drift", "prompt": "明确查看 @llm-wiki"},
        )
        loaded = json.loads(explicit.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("WIKI_PRIVATE_STATE", loaded)
        explicit_trace = json.loads(self.boss("explain", "--json").stdout)
        self.assertEqual(explicit_trace["mode"], "explicit")
        self.assertEqual(explicit_trace["confidence"], "high")
        self.assertEqual(explicit_trace["content_policy"], "full-project")
        self.assertIn("state", explicit_trace["sections"])
        session = json.loads((self.boss_home / "state" / "sessions" / "drift.json").read_text(encoding="utf-8"))
        self.assertEqual(set(session["roots"]), {str(alpha.resolve()), str(wiki.resolve())})

    def test_tasks_context_excludes_completed_items_and_refreshes_after_change(self) -> None:
        repo = make_repo(self.home / "work" / "tasks", "TASK_CONTEXT_READY")
        tasks = repo / ".brain" / "TASKS.md"
        lines = ["# Tasks", "", "- [x] completed-task"]
        lines.extend(f"- [ ] active-task-{index:02d}" for index in range(1, 12))
        lines.append("legacy-task active")
        tasks.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertEqual(self.boss("adopt", str(repo), "--summary", "task context").returncode, 0)
        started = self.boss(
            "hook",
            "session-start",
            payload={"session_id": "tasks", "cwd": str(repo), "source": "startup"},
        )
        context = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("active-task-01", context)
        self.assertIn("active-task-10", context)
        self.assertNotIn("active-task-11", context)
        self.assertNotIn("completed-task", context)
        self.assertNotIn("legacy-task", context)
        self.assertIn("tasks", json.loads(self.boss("explain", "--json").stdout)["sections"])

        tasks.write_text("# Tasks\n\n- [ ] switched-task\n", encoding="utf-8")
        refreshed = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "tasks", "prompt": "明确刷新 @tasks"},
        )
        refreshed_context = json.loads(refreshed.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("switched-task", refreshed_context)
        self.assertNotIn("active-task-01", refreshed_context)

    def test_legacy_active_task_lines_are_supported_without_checkboxes(self) -> None:
        repo = make_repo(self.home / "work" / "legacy-tasks", "LEGACY_TASKS_READY")
        (repo / ".brain" / "TASKS.md").write_text(
            "# Tasks\n\nlegacy-one active\nlegacy-two completed\nlegacy-three active\n",
            encoding="utf-8",
        )
        self.assertEqual(self.boss("adopt", str(repo), "--summary", "legacy tasks").returncode, 0)
        started = self.boss(
            "hook",
            "session-start",
            payload={"session_id": "legacy-tasks", "cwd": str(repo), "source": "startup"},
        )
        context = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("legacy-one active", context)
        self.assertIn("legacy-three active", context)
        self.assertNotIn("legacy-two completed", context)

    def test_relations_and_capability_peers_are_injected_for_the_target_only(self) -> None:
        alpha = make_repo(self.home / "work" / "alpha", "ALPHA_RELATION_READY")
        beta = make_repo(self.home / "work" / "beta", "BETA_RELATION_PRIVATE")
        (alpha / ".brain" / "capabilities.tsv").write_text(
            "provides\tshared.contract\tapi.md\tShared provider\n",
            encoding="utf-8",
        )
        (beta / ".brain" / "capabilities.tsv").write_text(
            "consumes\tshared.contract\tclient.md\tShared consumer\n",
            encoding="utf-8",
        )
        self.assertEqual(self.boss("adopt", str(alpha), "--summary", "provider").returncode, 0)
        self.assertEqual(self.boss("adopt", str(beta), "--summary", "consumer").returncode, 0)
        (self.boss_home / "relations.md").write_text(
            "| source | target | relation |\n| alpha | beta | RELATION_CONTRACT |\n",
            encoding="utf-8",
        )
        started = self.boss(
            "hook",
            "session-start",
            payload={"session_id": "relations", "cwd": str(alpha), "source": "startup"},
        )
        context = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("RELATION_CONTRACT", context)
        self.assertIn("shared.contract 被使用：beta", context)
        self.assertNotIn("BETA_RELATION_PRIVATE", context)
        sections = json.loads(self.boss("explain", "--json").stdout)["sections"]
        self.assertIn("relations", sections)
        self.assertIn("capabilities", sections)

    def test_wiki_content_is_not_eagerly_injected_into_ordinary_context(self) -> None:
        repo = make_repo(self.home / "work" / "wiki-scope", "WIKI_SCOPE_READY")
        wiki = repo / ".brain" / "wiki"
        wiki.mkdir()
        (wiki / "index.md").write_text(
            "# Wiki\n\n- [Recurring recovery](recurring-recovery.md)\n",
            encoding="utf-8",
        )
        (wiki / "recurring-recovery.md").write_text("PRIVATE_WIKI_LESSON\n", encoding="utf-8")
        (repo / ".brain" / "HANDOFF.md").write_text("PRIVATE_HANDOFF_DETAIL\n", encoding="utf-8")
        conventions = repo / ".brain" / "conventions"
        conventions.mkdir()
        (conventions / "index.md").write_text(
            "# Conventions\n\n- [Deployment coding](deployment-coding.md)\n",
            encoding="utf-8",
        )
        (conventions / "rules.md").write_text("PRIVATE_CONVENTION_DETAIL\n", encoding="utf-8")
        (conventions / "deployment-coding.md").write_text("PRIVATE_DEPLOYMENT_CONVENTION\n", encoding="utf-8")
        self.assertEqual(self.boss("adopt", str(repo), "--summary", "wiki scope").returncode, 0)
        started = self.boss(
            "hook",
            "session-start",
            payload={"session_id": "wiki-scope", "cwd": str(repo), "source": "startup"},
        )
        context = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("WIKI_SCOPE_READY", context)
        self.assertNotIn("PRIVATE_WIKI_LESSON", context)
        self.assertNotIn("PRIVATE_HANDOFF_DETAIL", context)
        self.assertNotIn("PRIVATE_CONVENTION_DETAIL", context)
        self.assertNotIn("PRIVATE_DEPLOYMENT_CONVENTION", context)
        self.assertIn(str(wiki / "index.md"), context)
        self.assertIn("只加载相关条目", context)
        self.assertIn("本地只读命令", context)
        self.assertIn(str(conventions / "index.md"), context)
        self.assertIn("wiki-index", json.loads(self.boss("explain", "--json").stdout)["sections"])

        repeated_name = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "wiki-scope", "prompt": "wiki-scope 的恢复经验是什么"},
        )
        self.assertEqual(repeated_name.stdout, "")
        trace = json.loads(self.boss("explain", "--json").stdout)
        self.assertEqual(trace["mode"], "workspace")
        self.assertEqual(trace["content_policy"], "full-project")

        selected = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "wiki-scope", "prompt": "This difficult recurring recovery problem happened again"},
        )
        selected_context = json.loads(selected.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("PRIVATE_WIKI_LESSON", selected_context)
        self.assertNotIn("PRIVATE_HANDOFF_DETAIL", selected_context)
        self.assertNotIn("PRIVATE_CONVENTION_DETAIL", selected_context)
        selected_trace = json.loads(self.boss("explain", "--json").stdout)
        self.assertEqual(selected_trace["mode"], "wiki")
        self.assertEqual(selected_trace["confidence"], "matched")
        self.assertEqual(selected_trace["content_policy"], "selected-wiki-entry")
        self.assertEqual(selected_trace["sections"], ["wiki"])

        convention = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "wiki-scope", "prompt": "Review the deployment coding convention"},
        )
        convention_context = json.loads(convention.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("PRIVATE_DEPLOYMENT_CONVENTION", convention_context)
        self.assertNotIn("PRIVATE_WIKI_LESSON", convention_context)
        convention_trace = json.loads(self.boss("explain", "--json").stdout)
        self.assertEqual(convention_trace["mode"], "conventions")
        self.assertEqual(convention_trace["content_policy"], "selected-convention-entry")

    def test_wiki_selection_is_scoped_deduplicated_and_path_safe(self) -> None:
        alpha = make_repo(self.home / "work" / "alpha-wiki", "ALPHA_WIKI_STATE")
        beta = make_repo(self.home / "work" / "beta-wiki", "BETA_WIKI_STATE")
        for repo, prefix in ((alpha, "ALPHA"), (beta, "BETA")):
            wiki = repo / ".brain" / "wiki"
            wiki.mkdir()
            (wiki / "index.md").write_text(
                "# Wiki\n\n"
                "- [Recurring recovery](recurring-recovery.md)\n"
                "- [Deployment rollback](deployment-rollback.md)\n"
                "- [Unsafe escape](../../outside.md)\n",
                encoding="utf-8",
            )
            (wiki / "recurring-recovery.md").write_text(f"{prefix}_RECOVERY_ONLY\n", encoding="utf-8")
            (wiki / "deployment-rollback.md").write_text(f"{prefix}_DEPLOY_ONLY\n", encoding="utf-8")
            (repo / "outside.md").write_text(f"{prefix}_OUTSIDE_MUST_NOT_LOAD\n", encoding="utf-8")
            self.assertEqual(self.boss("adopt", str(repo), "--summary", f"{prefix} wiki").returncode, 0)

        self.boss(
            "hook",
            "session-start",
            payload={"session_id": "wiki-routing", "cwd": str(alpha), "source": "startup"},
        )
        recovery = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "wiki-routing", "prompt": "Recurring recovery failed again"},
        )
        recovery_context = json.loads(recovery.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("ALPHA_RECOVERY_ONLY", recovery_context)
        self.assertNotIn("ALPHA_DEPLOY_ONLY", recovery_context)
        self.assertNotIn("BETA_RECOVERY_ONLY", recovery_context)

        duplicate = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "wiki-routing", "prompt": "Recurring recovery failed again"},
        )
        self.assertEqual(duplicate.stdout, "")

        deployment = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "wiki-routing", "prompt": "Need the deployment rollback lesson"},
        )
        deployment_context = json.loads(deployment.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("ALPHA_DEPLOY_ONLY", deployment_context)
        self.assertNotIn("ALPHA_RECOVERY_ONLY", deployment_context)

        cross_project = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "wiki-routing", "prompt": "Use @beta-wiki recurring recovery"},
        )
        cross_context = json.loads(cross_project.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("BETA_RECOVERY_ONLY", cross_context)
        self.assertNotIn("ALPHA_RECOVERY_ONLY", cross_context)

        unsafe = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "wiki-routing", "prompt": "Use @alpha-wiki unsafe escape"},
        )
        unsafe_context = json.loads(unsafe.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertNotIn("ALPHA_OUTSIDE_MUST_NOT_LOAD", unsafe_context)

    def test_large_state_is_capped_to_operational_sections(self) -> None:
        repo = make_repo(self.home / "work" / "large-state", "LARGE_STATE_READY")
        state = repo / ".brain" / "STATE.md"
        state.write_text(
            "# State\n\n## Background\n\n"
            + ("IRRELEVANT_HISTORY " * 500)
            + "\n\n## 现状\n\nCURRENT_OPERATIONAL_MARKER\n"
            + "\n## 下一步\n\nNEXT_OPERATIONAL_MARKER\n"
            + "\n## 阻塞\n\nBLOCK_OPERATIONAL_MARKER\n",
            encoding="utf-8",
        )
        self.assertEqual(self.boss("adopt", str(repo), "--summary", "large state").returncode, 0)
        started = self.boss(
            "hook",
            "session-start",
            payload={"session_id": "large-state", "cwd": str(repo), "source": "startup"},
        )
        context = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("CURRENT_OPERATIONAL_MARKER", context)
        self.assertIn("NEXT_OPERATIONAL_MARKER", context)
        self.assertIn("BLOCK_OPERATIONAL_MARKER", context)
        self.assertIn("状态卡过长", context)
        self.assertLess(len(context), 5000)

    def test_context_preview_is_persisted_redacted(self) -> None:
        repo = make_repo(self.home / "work" / "redacted-preview", "PREVIEW_READY")
        secret = "ghp_" + "Z" * 24
        state = repo / ".brain" / "STATE.md"
        state.write_text(state.read_text(encoding="utf-8") + f"\naccidental {secret}\n", encoding="utf-8")
        self.assertEqual(self.boss("adopt", str(repo), "--summary", "redaction").returncode, 0)
        self.boss(
            "hook",
            "session-start",
            payload={"session_id": "preview", "cwd": str(repo), "source": "startup"},
        )
        shown = self.boss("explain", "--show").stdout
        self.assertIn("[REDACTED_SECRET]", shown)
        self.assertNotIn(secret, shown)
        persisted = (self.boss_home / "state" / "last-context-preview.txt")
        self.assertEqual(persisted.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(secret, persisted.read_text(encoding="utf-8"))

    def test_duplicate_prompt_is_quiet_but_resume_and_compact_reinject(self) -> None:
        repo = make_repo(self.home / "work" / "alpha", "ALPHA_RESUME_READY")
        self.assertEqual(self.boss("scan", "--adopt").returncode, 0)
        self.boss(
            "hook",
            "session-start",
            payload={"session_id": "resume", "cwd": str(repo), "source": "startup"},
        )

        def prompt() -> subprocess.CompletedProcess[str]:
            return self.boss(
                "hook",
                "prompt-submit",
                payload={"session_id": "resume", "prompt": "查看 @alpha"},
            )

        self.assertIn("ALPHA_RESUME_READY", prompt().stdout)
        self.assertEqual(prompt().stdout, "")
        for source in ("resume", "compact"):
            self.boss(
                "hook",
                "session-start",
                payload={"session_id": "resume", "cwd": str(repo), "source": source},
            )
            self.assertIn("ALPHA_RESUME_READY", prompt().stdout)
            self.assertEqual(prompt().stdout, "")

    def test_task_ids_prevent_silent_task_drift_and_feed_explain_trace(self) -> None:
        repo = make_repo(self.home / "work" / "tasked", "TASKED_READY")
        tasks = repo / ".brain" / "TASKS.md"
        tasks.write_text(
            "# Tasks\n\n"
            "- [ ] [TASK-ALPHA] stabilize the importer\n"
            "- [ ] TASK-BETA: migrate the worker\n"
            "- [x] [TASK-DONE] already shipped\n",
            encoding="utf-8",
        )
        adopted = self.boss("adopt", str(repo), "--summary", "task drift")
        self.assertEqual(adopted.returncode, 0, adopted.stderr)
        self.boss(
            "hook",
            "session-start",
            payload={"session_id": "task-drift", "cwd": str(repo), "source": "startup"},
        )

        selected = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "task-drift", "prompt": "开始 @task:TASK-ALPHA"},
        )
        self.assertIn("TASK-ALPHA", selected.stdout)
        selected_trace = json.loads(self.boss("explain", "--json").stdout)
        self.assertEqual(selected_trace["mode"], "task")
        self.assertEqual(selected_trace["task"], "TASK-ALPHA")
        self.assertEqual(selected_trace["content_policy"], "selected-task")

        drift = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "task-drift", "prompt": "TASK-BETA 也需要看一下"},
        )
        self.assertIn("低置信度任务漂移提示", drift.stdout)
        self.assertIn("@task:ID", drift.stdout)
        drift_trace = json.loads(self.boss("explain", "--json").stdout)
        self.assertEqual(drift_trace["mode"], "task-drift")
        self.assertEqual(drift_trace["task"], "TASK-ALPHA")
        self.assertEqual(drift_trace["drift_task"], "TASK-BETA")

        switched = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "task-drift", "prompt": "确认切换 @task:TASK-BETA"},
        )
        self.assertIn("TASK-BETA", switched.stdout)
        switched_trace = json.loads(self.boss("explain", "--json").stdout)
        self.assertEqual(switched_trace["mode"], "task")
        self.assertEqual(switched_trace["task"], "TASK-BETA")

        completed = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "task-drift", "prompt": "@task:TASK-DONE"},
        )
        self.assertEqual(completed.stdout, "")

    def test_git_worktree_uses_the_checked_out_worktree_context(self) -> None:
        source = make_repo(self.home / "work" / "source", "SOURCE_READY")
        worktree = self.home / "worktrees" / "feature-view"
        worktree.parent.mkdir()
        added = git(source, "worktree", "add", "-b", "feature-view", str(worktree))
        self.assertEqual(added.returncode, 0, added.stderr)
        (worktree / ".brain" / "STATE.md").write_text(
            "# State\n\n## 现状\n\nWORKTREE_USER_READY\n",
            encoding="utf-8",
        )

        started = self.boss(
            "hook",
            "session-start",
            payload={"session_id": "worktree", "cwd": str(worktree), "source": "startup"},
        )
        context = json.loads(started.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("WORKTREE_USER_READY", context)
        self.assertNotIn("SOURCE_READY", context)
        registry = (self.boss_home / "registry.tsv").read_text(encoding="utf-8")
        self.assertIn(str(worktree), registry)

    def test_normal_hooks_finish_within_user_visible_latency_budget(self) -> None:
        repo = make_repo(self.home / "work" / "latency", "LATENCY_READY")
        self.assertEqual(self.boss("scan", "--adopt").returncode, 0)
        started_at = time.monotonic()
        started = self.boss(
            "hook",
            "session-start",
            payload={"session_id": "latency", "cwd": str(repo), "source": "startup"},
        )
        session_elapsed = time.monotonic() - started_at
        prompt_at = time.monotonic()
        prompted = self.boss(
            "hook",
            "prompt-submit",
            payload={"session_id": "latency", "prompt": "查看 @latency"},
        )
        prompt_elapsed = time.monotonic() - prompt_at
        self.assertEqual(started.returncode, 0, started.stderr)
        self.assertEqual(prompted.returncode, 0, prompted.stderr)
        self.assertLess(session_elapsed, 2.0, f"SessionStart took {session_elapsed:.3f}s")
        self.assertLess(prompt_elapsed, 2.0, f"UserPromptSubmit took {prompt_elapsed:.3f}s")

    def test_guarded_block_clears_after_user_pushes(self) -> None:
        remote = self.home / "remotes" / "guarded.git"
        remote.parent.mkdir()
        repo = make_repo(self.home / "work" / "guarded", "GUARDED_READY", remote=remote)
        self.assertEqual(self.boss("policy", "guarded").returncode, 0)
        self.boss(
            "hook",
            "session-start",
            payload={"session_id": "guarded", "cwd": str(repo), "source": "startup"},
        )
        (repo / "feature.txt").write_text("user change\n", encoding="utf-8")
        git(repo, "add", "feature.txt")
        git(repo, "commit", "-m", "user change")

        blocked = self.boss("hook", "stop", payload={"session_id": "guarded", "cwd": str(repo)})
        decision = json.loads(blocked.stdout)
        self.assertEqual(decision["decision"], "block")
        self.assertIn("尚未推送", decision["reason"])

        self.assertEqual(git(repo, "push").returncode, 0)
        cleared = self.boss("hook", "stop", payload={"session_id": "guarded", "cwd": str(repo)})
        self.assertEqual(json.loads(cleared.stdout), {})

    def test_strict_block_clears_after_continuity_records_are_complete(self) -> None:
        remote = self.home / "remotes" / "strict.git"
        remote.parent.mkdir()
        repo = make_repo(self.home / "work" / "strict", "STRICT_READY", remote=remote)
        self.assertEqual(self.boss("policy", "strict").returncode, 0)
        self.boss(
            "hook",
            "session-start",
            payload={"session_id": "strict", "cwd": str(repo), "source": "startup"},
        )
        (repo / "feature.txt").write_text("finished feature\n", encoding="utf-8")
        git(repo, "add", "feature.txt")
        git(repo, "commit", "-m", "finish feature")
        work_commit = git(repo, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(git(repo, "push").returncode, 0)

        blocked = self.boss("hook", "stop", payload={"session_id": "strict", "cwd": str(repo)})
        reason = json.loads(blocked.stdout)["reason"]
        self.assertIn("evidence", reason)
        self.assertIn("STATE.md", reason)
        self.assertIn("dev-log", reason)

        brain = repo / ".brain"
        (brain / "STATE.md").write_text(
            "# State\n\n## 现状\n\nSTRICT_COMPLETE\n\n## 下一步\n\nship\n",
            encoding="utf-8",
        )
        (brain / "dev-log").mkdir()
        (brain / "dev-log" / "journey.md").write_text("Verified the user journey.\n", encoding="utf-8")
        evidence = brain / "evidence.jsonl"
        evidence.write_text(json.dumps({"commit": work_commit, "result": "pass"}) + "\n", encoding="utf-8")
        git(repo, "add", ".brain")
        git(repo, "commit", "-m", "record continuity")
        self.assertEqual(git(repo, "push").returncode, 0)

        missing_judgment = self.boss("hook", "stop", payload={"session_id": "strict", "cwd": str(repo)})
        self.assertIn("wiki", json.loads(missing_judgment.stdout)["reason"])

        evidence.write_text(
            json.dumps({"commit": work_commit, "wiki": "no durable lesson", "result": "pass"}) + "\n",
            encoding="utf-8",
        )
        git(repo, "add", ".brain/evidence.jsonl")
        git(repo, "commit", "-m", "record wiki judgment")
        self.assertEqual(git(repo, "push").returncode, 0)

        cleared = self.boss("hook", "stop", payload={"session_id": "strict", "cwd": str(repo)})
        self.assertEqual(json.loads(cleared.stdout), {})

    def test_stale_evidence_and_preexisting_dev_log_do_not_satisfy_current_work(self) -> None:
        remote = self.home / "remotes" / "stale-records.git"
        remote.parent.mkdir()
        repo = make_repo(self.home / "work" / "stale-records", "STALE_RECORDS_READY", remote=remote)
        brain = repo / ".brain"
        (brain / "dev-log").mkdir()
        (brain / "dev-log" / "old.md").write_text("old work\n", encoding="utf-8")
        old_commit = git(repo, "rev-parse", "HEAD").stdout.strip()
        (brain / "evidence.jsonl").write_text(
            json.dumps({"commit": old_commit, "wiki": "none", "result": "old"}) + "\n",
            encoding="utf-8",
        )
        git(repo, "add", ".brain")
        git(repo, "commit", "-m", "old continuity records")
        self.assertEqual(git(repo, "push").returncode, 0)
        self.assertEqual(self.boss("policy", "strict").returncode, 0)
        self.boss(
            "hook",
            "session-start",
            payload={"session_id": "stale-records", "cwd": str(repo), "source": "startup"},
        )
        (repo / "new-work.txt").write_text("new work\n", encoding="utf-8")
        git(repo, "add", "new-work.txt")
        git(repo, "commit", "-m", "new work")
        self.assertEqual(git(repo, "push").returncode, 0)

        blocked = self.boss("hook", "stop", payload={"session_id": "stale-records", "cwd": str(repo)})
        reason = json.loads(blocked.stdout)["reason"]
        self.assertIn("evidence", reason)
        self.assertIn("dev-log", reason)
        self.assertIn("STATE.md", reason)

    def test_uncommitted_brain_records_remain_a_data_loss_block(self) -> None:
        remote = self.home / "remotes" / "dirty-brain.git"
        remote.parent.mkdir()
        repo = make_repo(self.home / "work" / "dirty-brain", "DIRTY_BRAIN_READY", remote=remote)
        self.assertEqual(self.boss("policy", "guarded").returncode, 0)
        self.boss(
            "hook",
            "session-start",
            payload={"session_id": "dirty-brain", "cwd": str(repo), "source": "startup"},
        )
        (repo / "work.txt").write_text("work\n", encoding="utf-8")
        git(repo, "add", "work.txt")
        git(repo, "commit", "-m", "work")
        self.assertEqual(git(repo, "push").returncode, 0)
        (repo / ".brain" / "dev-log").mkdir()
        (repo / ".brain" / "dev-log" / "pending.md").write_text("pending\n", encoding="utf-8")

        blocked = self.boss("hook", "stop", payload={"session_id": "dirty-brain", "cwd": str(repo)})
        reason = json.loads(blocked.stdout)["reason"]
        self.assertIn("未提交", reason)

    def test_machine_brain_push_and_clean_machine_restore_clone(self) -> None:
        project_remote = self.home / "remotes" / "project.git"
        machine_remote = self.home / "remotes" / "machine.git"
        project_remote.parent.mkdir()
        project = make_repo(self.home / "work" / "portable", "PORTABLE_READY", remote=project_remote)
        subprocess.run(
            ["git", "init", "--bare", "--initial-branch=main", str(machine_remote)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(self.boss("adopt", str(project), "--summary", "portable project").returncode, 0)

        machine = self.home / "boss-source"
        initialized = self.boss(
            "machine",
            "init",
            "--path",
            str(machine),
            "--remote",
            machine_remote.as_uri(),
            "--push",
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        self.assertTrue(git(machine, "rev-parse", "@{u}").stdout.strip())

        restored_home = self.home / "restored-home"
        restored_boss = restored_home / ".boss"
        restored_boss.mkdir(parents=True)
        restored_machine = restored_home / "machine-brain"
        self.assertEqual(
            subprocess.run(
                ["git", "clone", machine_remote.as_uri(), str(restored_machine)],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            ).returncode,
            0,
        )
        restored_env = {
            **self.env,
            "HOME": str(restored_home),
            "BOSS_HOME": str(restored_boss),
        }
        restored = self.boss(
            "machine",
            "restore",
            str(restored_machine),
            "--clone",
            "--destination",
            str(restored_home / "projects"),
            env=restored_env,
        )
        self.assertEqual(restored.returncode, 0, restored.stderr)
        cloned = restored_home / "projects" / "portable"
        self.assertTrue((cloned / ".git").exists())
        registry = (restored_boss / "registry.tsv").read_text(encoding="utf-8")
        self.assertIn(
            "portable",
            registry,
            f"restore={restored.stdout!r} origin={git(cloned, 'remote', 'get-url', 'origin').stdout!r} "
            f"owner={(restored_boss / 'owner').read_text(encoding='utf-8')!r}",
        )

    def test_machine_create_remote_uses_authenticated_gh_contract(self) -> None:
        remote = self.home / "remotes" / "created-machine.git"
        remote.parent.mkdir()
        subprocess.run(
            ["git", "init", "--bare", "--initial-branch=main", str(remote)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        fake_bin = self.home / "fake-bin"
        fake_bin.mkdir()
        gh = fake_bin / "gh"
        gh.write_text(
            "#!/bin/sh\n"
            "source=\nprev=\n"
            "for arg in \"$@\"; do\n"
            "  if [ \"$prev\" = \"--source\" ]; then source=\"$arg\"; fi\n"
            "  prev=\"$arg\"\n"
            "done\n"
            "printf '%s\\n' \"$*\" > \"$FAKE_GH_LOG\"\n"
            "git -C \"$source\" remote add origin \"$FAKE_REMOTE\"\n"
            "git -C \"$source\" push -u origin main >/dev/null 2>&1\n",
            encoding="utf-8",
        )
        gh.chmod(0o755)
        machine = self.home / "boss-created"
        env = {
            **self.env,
            "PATH": f"{fake_bin}:{self.env['PATH']}",
            "FAKE_REMOTE": remote.as_uri(),
            "FAKE_GH_LOG": str(self.home / "gh.log"),
        }
        created = self.boss(
            "machine",
            "init",
            "--path",
            str(machine),
            "--create-remote",
            env=env,
        )
        self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
        self.assertIn("repo create", (self.home / "gh.log").read_text(encoding="utf-8"))
        self.assertEqual(git(machine, "remote", "get-url", "origin").stdout.strip(), remote.as_uri())
        self.assertTrue(git(machine, "rev-parse", "@{u}").stdout.strip())

    def test_deleted_registered_project_is_reported_restored_and_idempotent(self) -> None:
        project_remote = self.home / "remotes" / "deleted-project.git"
        machine_remote = self.home / "remotes" / "deleted-machine.git"
        project_remote.parent.mkdir()
        project = make_repo(self.home / "work" / "deleted-project", "DELETED_PROJECT_RECOVERED", remote=project_remote)
        subprocess.run(
            ["git", "init", "--bare", "--initial-branch=main", str(machine_remote)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(self.boss("adopt", str(project), "--summary", "deletion recovery").returncode, 0)
        machine = self.home / "boss-delete-source"
        initialized = self.boss(
            "machine",
            "init",
            "--path",
            str(machine),
            "--remote",
            machine_remote.as_uri(),
            "--push",
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)

        shutil.rmtree(project)
        missing = self.boss("status")
        self.assertEqual(missing.returncode, 1)
        self.assertIn("MISSING deleted-project", missing.stdout)

        for _ in range(2):
            restored = self.boss(
                "machine",
                "restore",
                str(machine),
                "--clone",
                "--destination",
                str(self.home / "work"),
            )
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertTrue((project / ".git").exists())
            self.assertIn("DELETED_PROJECT_RECOVERED", (project / ".brain" / "STATE.md").read_text(encoding="utf-8"))
        registry_rows = [
            line
            for line in (self.boss_home / "registry.tsv").read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(len([line for line in registry_rows if "deleted-project" in line]), 1)

    def test_restore_reports_corrupt_inventory_and_unavailable_project_remote(self) -> None:
        corrupt = self.home / "corrupt-machine"
        corrupt.mkdir()
        missing_inventory = self.boss("machine", "restore", str(corrupt), "--clone")
        self.assertEqual(missing_inventory.returncode, 2)
        self.assertIn("no projects.tsv", missing_inventory.stderr)

        unavailable = self.home / "unavailable-machine"
        unavailable.mkdir()
        (unavailable / "projects.tsv").write_text(
            "name\taliases\tsummary\tkind\tlast_path\torigin\thas_brain\n"
            "lost\t\tmissing\tlocal\t/obsolete/lost\tfile:///definitely/missing/lost.git\tyes\n",
            encoding="utf-8",
        )
        failed = self.boss(
            "machine",
            "restore",
            str(unavailable),
            "--clone",
            "--destination",
            str(self.home / "restore-target"),
        )
        self.assertEqual(failed.returncode, 1)
        self.assertIn("UNRESOLVED lost", failed.stdout)
        self.assertFalse((self.home / "restore-target" / "lost").exists())

    def test_install_then_rollback_preserves_existing_user_configuration(self) -> None:
        codex = self.home / ".codex"
        claude = self.home / ".claude"
        codex.mkdir()
        claude.mkdir()
        original_codex = (
            '[projects."/keep"]\ntrust_level = "trusted"\n\n'
            '[[hooks.Stop]]\n[[hooks.Stop.hooks]]\ntype = "command"\ncommand = "/keep/custom-stop"\n'
        )
        original_claude = {
            "keep": True,
            "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "/keep/custom-stop"}]}]},
        }
        (codex / "config.toml").write_text(original_codex, encoding="utf-8")
        (claude / "settings.json").write_text(json.dumps(original_claude), encoding="utf-8")

        installed = run(["python3", str(INSTALLER), "install", "--owner", "me"], env=self.env)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        rolled_back = run(["python3", str(INSTALLER), "rollback"], env=self.env)
        self.assertEqual(rolled_back.returncode, 0, rolled_back.stderr)
        self.assertEqual((codex / "config.toml").read_text(encoding="utf-8"), original_codex)
        self.assertEqual(json.loads((claude / "settings.json").read_text(encoding="utf-8")), original_claude)
        self.assertFalse((self.home / ".local" / "bin" / "boss").exists())
        self.assertTrue(self.boss_home.exists())

    def test_handoff_and_index_checks_report_and_run_only_safe_acceptance(self) -> None:
        repo = make_repo(self.home / "work" / "checks", "CHECKS_READY")
        brain = repo / ".brain"
        (brain / "HANDOFF.md").write_text(
            "# Handoff\n\n## Purpose\nThis project.\n\n## Assets and access\nSee Vault.\n\n"
            "## Reading order\nRead STATE.\n\n## Verification\nRun acceptance.\n\n## Hazards\nNo secrets.\n",
            encoding="utf-8",
        )
        (brain / "HANDOFF_ACCEPTANCE.md").write_text(
            "# Acceptance\n\n- [ ] REQUIRED SAFE `git status` => On branch\n",
            encoding="utf-8",
        )
        self.assertEqual(self.boss("adopt", str(repo), "--summary", "checks").returncode, 0)
        not_run = self.boss("handoff", "check", str(repo), "--json")
        self.assertEqual(not_run.returncode, 1)
        not_run_value = json.loads(not_run.stdout)
        self.assertFalse(not_run_value["ready"])
        self.assertTrue(any(item["status"] == "NOT_RUN" for item in not_run_value["checks"]))
        ran = self.boss("handoff", "check", str(repo), "--run", "--json")
        self.assertEqual(ran.returncode, 0, ran.stdout + ran.stderr)
        ran_value = json.loads(ran.stdout)
        self.assertTrue(ran_value["ready"])
        self.assertTrue(all(item["status"] == "PASS" for item in ran_value["checks"]))

        wiki = brain / "wiki"
        wiki.mkdir()
        (wiki / "index.md").write_text(
            "# Wiki\n\n- [Broken](missing.md)\n- [Broken again](missing.md)\n- [Escape](../../README.md)\n",
            encoding="utf-8",
        )
        (wiki / "orphan.md").write_text("orphan\n", encoding="utf-8")
        checked = self.boss("wiki", "check", str(repo), "--json")
        self.assertEqual(checked.returncode, 1)
        diagnostics = json.loads(checked.stdout)
        self.assertEqual(diagnostics["broken"], ["missing.md"])
        self.assertEqual(diagnostics["duplicates"], ["missing.md"])
        self.assertEqual(diagnostics["unsafe"], ["../../README.md"])
        self.assertEqual(diagnostics["orphan"], ["orphan.md"])

        conventions = brain / "conventions"
        conventions.mkdir()
        (conventions / "rules.md").write_text("rules\n", encoding="utf-8")
        fixed = self.boss("conventions", "check", str(repo), "--fix", "--json")
        self.assertEqual(fixed.returncode, 0, fixed.stdout + fixed.stderr)
        self.assertIn("rules.md", (conventions / "index.md").read_text(encoding="utf-8"))

    def test_status_commands_return_actionable_user_output(self) -> None:
        repo = make_repo(self.home / "work" / "visible", "VISIBLE_READY")
        state = repo / ".brain" / "STATE.md"
        state.write_text(state.read_text(encoding="utf-8") + "\n## 阻塞\n\nwaiting for review\n", encoding="utf-8")
        self.assertEqual(self.boss("adopt", str(repo), "--summary", "visible project").returncode, 0)

        projects = self.boss("projects")
        self.assertIn("visible", projects.stdout)
        self.assertIn("continue safely", projects.stdout)
        self.assertIn("journey.visible", self.boss("caps").stdout)
        self.assertIn("waiting for review", self.boss("risk").stdout)
        doctor = self.boss("doctor", "--json")
        self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
        self.assertTrue(all(item["ok"] for item in json.loads(doctor.stdout)))


if __name__ == "__main__":
    unittest.main()
