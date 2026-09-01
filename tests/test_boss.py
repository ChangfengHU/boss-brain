from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOSS = ROOT / "plugins" / "boss-brain" / "scripts" / "boss.py"
INSTALLER = ROOT / "scripts" / "install.py"


def command(args: list[str], *, env: dict[str, str], cwd: Path | None = None, stdin: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd or ROOT,
        env=env,
        input=stdin,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def make_repo(path: Path, owner: str = "me", remote_name: str | None = None) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "main")
    git(path, "config", "user.name", "Test")
    git(path, "config", "user.email", "test@example.invalid")
    (path / "README.md").write_text("test\n", encoding="utf-8")
    git(path, "add", "README.md")
    git(path, "commit", "-m", "initial")
    git(path, "remote", "add", "origin", f"https://github.com/{owner}/{remote_name or path.name}.git")
    return path


class BossTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.env = os.environ.copy()
        self.env.update({"HOME": str(self.home), "BOSS_HOME": str(self.home / ".boss"), "BOSS_SKIP_PLUGIN_CLI": "1"})
        (self.home / ".boss").mkdir()
        (self.home / ".boss" / "owner").write_text("me\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def boss(self, *args: str, cwd: Path | None = None, payload: dict | None = None) -> subprocess.CompletedProcess[str]:
        return command(
            ["python3", str(BOSS), *args],
            env=self.env,
            cwd=cwd,
            stdin=json.dumps(payload) if payload is not None else "",
        )

    def test_scan_adopts_only_owned_active_repo_without_creating_brain(self) -> None:
        mine = make_repo(self.home / "work" / "mine")
        foreign = make_repo(self.home / "work" / "foreign", owner="someone-else")
        result = self.boss("scan", "--adopt", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertIn(str(mine), value["added"])
        self.assertNotIn(str(foreign), value["added"])
        self.assertFalse((mine / ".brain").exists())
        registry = (self.home / ".boss" / "registry.tsv").read_text(encoding="utf-8")
        self.assertIn(str(mine), registry)
        self.assertNotIn(str(foreign), registry)

    def test_session_start_registers_current_repo_and_returns_private_context(self) -> None:
        repo = make_repo(self.home / "current")
        result = self.boss("hook", "session-start", payload={"session_id": "s1", "cwd": str(repo), "source": "startup"})
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        context = value["hookSpecificOutput"]["additionalContext"]
        self.assertIn("Boss Brain", context)
        self.assertIn(str(repo), (self.home / ".boss" / "registry.tsv").read_text(encoding="utf-8"))
        machine = json.loads((self.home / ".boss" / "config.json").read_text(encoding="utf-8"))["machine"]
        self.assertTrue((Path(machine["path"]) / ".git").exists())

    def test_explicit_project_at_end_of_prompt_matches(self) -> None:
        repo = make_repo(self.home / "alpha")
        self.boss("scan", "--adopt")
        result = self.boss("hook", "prompt-submit", payload={"session_id": "s2", "prompt": "看看 @alpha"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"], "UserPromptSubmit")

    def test_quiet_records_but_guarded_blocks_unpushed_commit(self) -> None:
        repo = make_repo(self.home / "work" / "guarded")
        self.boss("hook", "session-start", payload={"session_id": "s3", "cwd": str(repo), "source": "startup"})
        (repo / "work.txt").write_text("change\n", encoding="utf-8")
        git(repo, "add", "work.txt")
        git(repo, "commit", "-m", "work")
        quiet = self.boss("hook", "stop", payload={"session_id": "s3", "cwd": str(repo)})
        self.assertEqual(json.loads(quiet.stdout), {})
        audit = (self.home / ".boss" / "state" / "audit.jsonl").read_text(encoding="utf-8")
        self.assertIn("no-upstream", audit)
        policy = self.boss("policy", "guarded")
        self.assertEqual(policy.returncode, 0)
        guarded = self.boss("hook", "stop", payload={"session_id": "s3", "cwd": str(repo)})
        self.assertEqual(json.loads(guarded.stdout)["decision"], "block")

    def test_machine_brain_is_portable_and_sync_is_stable(self) -> None:
        repo = make_repo(self.home / "work" / "portable")
        (repo / ".brain").mkdir()
        (repo / ".brain" / "capabilities.tsv").write_text(
            "provides\ttest.cap\tREADME.md\tTest capability\n", encoding="utf-8"
        )
        self.boss("scan", "--adopt")
        init = self.boss("machine", "init", "--name", "boss-test-node")
        self.assertEqual(init.returncode, 0, init.stderr)
        machine = self.home / "boss-test-node"
        self.assertTrue((machine / ".git").exists())
        self.assertIn("portable", (machine / "projects.tsv").read_text(encoding="utf-8"))
        self.assertIn("test.cap", (machine / "capabilities.tsv").read_text(encoding="utf-8"))
        second = self.boss("machine", "sync")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("snapshot=unchanged", second.stdout)

    def test_vault_reference_never_accepts_secret_value_shape(self) -> None:
        good = self.boss("vault-ref", "service:github", "--purpose", "repository access")
        self.assertEqual(good.returncode, 0, good.stderr)
        bad = self.boss("vault-ref", "password=value")
        self.assertEqual(bad.returncode, 2)
        value = (self.home / ".boss" / "vault-refs.tsv").read_text(encoding="utf-8")
        self.assertIn("service:github", value)
        self.assertNotIn("password=value", value)

    def test_strict_policy_checks_project_continuity(self) -> None:
        repo = make_repo(self.home / "work" / "strict")
        (repo / ".brain").mkdir()
        (repo / ".brain" / "STATE.md").write_text("# State\n", encoding="utf-8")
        git(repo, "add", ".brain/STATE.md")
        git(repo, "commit", "-m", "add brain")
        self.boss("hook", "session-start", payload={"session_id": "strict", "cwd": str(repo), "source": "startup"})
        (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
        git(repo, "add", "feature.txt")
        git(repo, "commit", "-m", "feature")
        self.boss("policy", "strict")
        result = self.boss("hook", "stop", payload={"session_id": "strict", "cwd": str(repo)})
        value = json.loads(result.stdout)
        self.assertEqual(value["decision"], "block")
        self.assertIn("evidence", value["reason"])

    def test_machine_restore_recovers_owner_identity(self) -> None:
        make_repo(self.home / "work" / "source")
        self.boss("scan", "--adopt")
        self.assertEqual(self.boss("machine", "init", "--name", "boss-origin").returncode, 0)
        machine_repo = self.home / "boss-origin"
        (self.home / ".boss" / "owner").unlink()
        result = self.boss("machine", "restore", str(machine_repo))
        self.assertIn(result.returncode, (0, 1))
        self.assertEqual((self.home / ".boss" / "owner").read_text(encoding="utf-8").strip(), "me")

    def test_timer_rejects_overly_aggressive_interval(self) -> None:
        result = self.boss("machine", "timer-install", "--interval", "1", "--dry-run")
        self.assertEqual(result.returncode, 2)

    def test_machine_sync_discovers_repo_created_after_session(self) -> None:
        self.assertEqual(self.boss("machine", "init", "--name", "boss-later").returncode, 0)
        repo = make_repo(self.home / "work" / "later")
        result = self.boss("machine", "sync")
        self.assertEqual(result.returncode, 0, result.stderr)
        registry = (self.home / ".boss" / "registry.tsv").read_text(encoding="utf-8")
        self.assertIn(str(repo), registry)
        self.assertIn("later", (self.home / "boss-later" / "projects.tsv").read_text(encoding="utf-8"))


class InstallerTest(unittest.TestCase):
    def test_install_update_uninstall_in_fake_home(self) -> None:
        with tempfile.TemporaryDirectory() as value:
            fake = Path(value)
            env = os.environ.copy()
            env.update({"HOME": str(fake), "BOSS_HOME": str(fake / ".boss"), "BOSS_SKIP_PLUGIN_CLI": "1"})
            (fake / ".boss").mkdir()
            (fake / ".boss" / "registry.tsv").write_text("# path\\tname\\taliases\\tsummary\\tkind\n", encoding="utf-8")
            (fake / ".project-brains").mkdir()
            (fake / ".project-brains" / "registry.tsv").write_text(
                f"{ROOT}\tboss-brain\t\tplugin source\tlocal\n", encoding="utf-8"
            )
            (fake / ".codex").mkdir()
            (fake / ".codex" / "config.toml").write_text(
                '[[hooks.SessionStart]]\n[[hooks.SessionStart.hooks]]\ntype = "command"\ncommand = "/x/.boss/hooks/old.sh"\n\n[projects."/keep"]\ntrust_level = "trusted"\n',
                encoding="utf-8",
            )
            (fake / ".claude").mkdir()
            (fake / ".claude" / "settings.json").write_text(json.dumps({
                "keep": True,
                "hooks": {"Stop": [{"hooks": [{"type": "command", "command": "/x/.project-brains/hooks/old.sh"}]}]},
            }), encoding="utf-8")

            first = command(["python3", str(INSTALLER), "install", "--owner", "me"], env=env)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = command(["python3", str(INSTALLER), "install", "--owner", "me"], env=env)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertTrue((fake / ".local" / "bin" / "boss").exists())
            self.assertTrue((fake / ".boss" / "distribution" / "plugins" / "boss-brain" / "scripts" / "boss.py").exists())
            codex = (fake / ".codex" / "config.toml").read_text(encoding="utf-8")
            self.assertNotIn("/old.sh", codex)
            self.assertEqual(codex.count("boss-brain:hooks:begin"), 1)
            self.assertIn('[projects."/keep"]', codex)
            claude = json.loads((fake / ".claude" / "settings.json").read_text(encoding="utf-8"))
            self.assertTrue(claude["keep"])
            self.assertNotIn("old.sh", json.dumps(claude))
            self.assertIn("boss-brain", (fake / ".boss" / "registry.tsv").read_text(encoding="utf-8"))

            remove = command(["python3", str(INSTALLER), "uninstall"], env=env)
            self.assertEqual(remove.returncode, 0, remove.stderr)
            self.assertFalse((fake / ".boss" / "distribution").exists())
            self.assertTrue((fake / ".boss" / "registry.tsv").exists())
            self.assertNotIn("boss-brain:hooks", (fake / ".codex" / "config.toml").read_text(encoding="utf-8"))


class PackagingTest(unittest.TestCase):
    def test_manifests_and_hooks_are_consistent(self) -> None:
        codex = json.loads((ROOT / "plugins" / "boss-brain" / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        claude = json.loads((ROOT / "plugins" / "boss-brain" / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        market = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        hooks = json.loads((ROOT / "plugins" / "boss-brain" / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        self.assertEqual(codex["name"], "boss-brain")
        self.assertEqual(codex["version"].split("+", 1)[0], claude["version"])
        self.assertEqual(market["plugins"][0]["policy"]["authentication"], "ON_INSTALL")
        self.assertEqual(set(hooks["hooks"]), {"SessionStart", "UserPromptSubmit", "Stop"})
        self.assertNotIn("hooks", codex)
        for event in hooks["hooks"].values():
            self.assertIn("scripts/boss.py", event[0]["hooks"][0]["command"])

    def test_old_runtime_name_is_absent_from_release_files(self) -> None:
        forbidden = ".boss" + "brain"
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            self.assertNotIn(forbidden, path.read_text(encoding="utf-8", errors="ignore"), str(path))


if __name__ == "__main__":
    unittest.main()
