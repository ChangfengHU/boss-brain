from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
BOSS = ROOT / "plugins" / "boss-brain" / "scripts" / "boss.py"


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


def make_repo(path: Path, *, owner: str = "me", remote_name: str | None = None) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-b", "main")
    git(path, "config", "user.name", "Test")
    git(path, "config", "user.email", "test@example.invalid")
    git(path, "commit", "--allow-empty", "-m", "initial")
    git(path, "remote", "add", "origin", f"https://github.com/{owner}/{remote_name or path.name}.git")
    return path


class ResilienceTest(unittest.TestCase):
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
        stdin: str = "",
        env: dict[str, str] | None = None,
        timeout: int = 30,
    ) -> subprocess.CompletedProcess[str]:
        if payload is not None:
            stdin = json.dumps(payload)
        return run(
            ["python3", str(BOSS), *args],
            env=env or self.env,
            cwd=cwd,
            stdin=stdin,
            timeout=timeout,
        )

    def test_invalid_scan_config_types_fall_back_without_traceback(self) -> None:
        (self.boss_home / "config.json").write_text(
            json.dumps({"scan": {"max_depth": {"bad": True}, "max_age_days": "never"}}),
            encoding="utf-8",
        )
        make_repo(self.home / "work" / "valid")
        result = self.boss("scan", "--adopt", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["added"]), 1)

    def test_concurrent_scans_keep_registry_complete_and_deduplicated(self) -> None:
        repositories = [make_repo(self.home / "work" / f"repo-{index}") for index in range(8)]
        processes = [
            subprocess.Popen(
                ["python3", str(BOSS), "scan", "--adopt", "--json"],
                env=self.env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            for _ in range(12)
        ]
        for process in processes:
            stdout, stderr = process.communicate(timeout=30)
            self.assertEqual(process.returncode, 0, stderr)
            json.loads(stdout)
        rows = [
            line.split("\t")
            for line in (self.boss_home / "registry.tsv").read_text(encoding="utf-8").splitlines()
            if line and not line.startswith("#")
        ]
        self.assertEqual(len(rows), len(repositories))
        self.assertEqual(len({row[0] for row in rows}), len(repositories))

    def test_stale_registry_lock_is_recovered(self) -> None:
        repo = make_repo(self.home / "work" / "stale-lock")
        lock = self.boss_home / ".registry.lock"
        lock.mkdir()
        old = time.time() - 60
        os.utime(lock, (old, old))
        result = self.boss("scan", "--adopt", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(repo), json.loads(result.stdout)["added"])
        self.assertFalse(lock.exists())

    def test_live_registry_lock_fails_bounded_and_reports_busy(self) -> None:
        repo = make_repo(self.home / "work" / "busy-lock")
        (self.boss_home / ".registry.lock").mkdir()
        started = time.monotonic()
        result = self.boss("scan", "--adopt", "--json", timeout=10)
        elapsed = time.monotonic() - started
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertLess(elapsed, 4)
        self.assertIn({"path": str(repo), "reasons": ["registry-busy"]}, value["candidates"])

    def test_unicode_and_space_paths_are_registered(self) -> None:
        repo = make_repo(self.home / "工作 项目" / "示例 repo")
        result = self.boss("scan", "--adopt", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(str(repo), json.loads(result.stdout)["added"])

    def test_case_insensitive_name_collision_is_not_silently_adopted(self) -> None:
        first = make_repo(self.home / "one" / "Alpha")
        second = make_repo(self.home / "two" / "alpha")
        result = self.boss("scan", "--adopt", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(len(value["added"]), 1)
        skipped = {item["path"]: item["reasons"] for item in value["candidates"]}
        rejected = second if str(first) in value["added"] else first
        self.assertIn("name-conflict", skipped[str(rejected)])

    def test_hook_redacts_secret_shaped_brain_content(self) -> None:
        repo = make_repo(self.home / "work" / "redaction")
        brain = repo / ".brain"
        brain.mkdir()
        secret = "ghp_" + "A" * 24
        (brain / "STATE.md").write_text(f"# State\n\n## 现状\n\naccidental {secret}\n", encoding="utf-8")
        result = self.boss(
            "hook",
            "session-start",
            payload={"session_id": "redact", "cwd": str(repo), "source": "startup"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(secret, result.stdout)
        self.assertIn("[REDACTED_SECRET]", result.stdout)

    def test_adopt_rejects_secret_or_tsv_injection_metadata(self) -> None:
        repo = make_repo(self.home / "work" / "manual")
        secret = "ghp_" + "B" * 24
        rejected_secret = self.boss("adopt", str(repo), "--summary", secret)
        rejected_tab = self.boss("adopt", str(repo), "--aliases", "good\tforged")
        self.assertEqual(rejected_secret.returncode, 2)
        self.assertEqual(rejected_tab.returncode, 2)
        self.assertNotIn(secret, rejected_secret.stderr)
        self.assertFalse((self.boss_home / "registry.tsv").exists())

    def test_vault_reference_rejects_secret_in_non_key_fields(self) -> None:
        secret = "github_pat_" + "C" * 24
        result = self.boss("vault-ref", "service:github", "--purpose", secret)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(secret, result.stderr)
        self.assertFalse((self.boss_home / "vault-refs.tsv").exists())

    def test_machine_snapshot_refuses_contaminated_registry_without_traceback(self) -> None:
        repo = make_repo(self.home / "work" / "contaminated")
        secret = "ghp_" + "D" * 24
        (self.boss_home / "registry.tsv").write_text(
            "# path\tname\taliases\tsummary\tkind(local|remote|ref)\n"
            f"{repo}\tcontaminated\t\t{secret}\tlocal\n",
            encoding="utf-8",
        )
        result = self.boss("machine", "init", "--path", str(self.home / "machine"))
        self.assertEqual(result.returncode, 2)
        self.assertNotIn(secret, result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("secret-like", result.stderr)

    def test_machine_snapshot_sanitizes_credentialed_origin(self) -> None:
        repo = make_repo(self.home / "work" / "credential-origin")
        git(repo, "remote", "set-url", "origin", "https://user:password@github.com/me/credential-origin.git")
        self.assertEqual(self.boss("scan", "--adopt").returncode, 0)
        machine = self.home / "machine-safe"
        result = self.boss("machine", "init", "--path", str(machine))
        self.assertEqual(result.returncode, 0, result.stderr)
        snapshot = (machine / "projects.tsv").read_text(encoding="utf-8")
        self.assertNotIn("password", snapshot)
        self.assertIn("https://github.com/me/credential-origin.git", snapshot)

    def test_failed_machine_push_is_safe_and_actionable(self) -> None:
        machine = self.home / "machine-offline"
        missing_remote = self.home / "missing" / "remote.git"
        init = self.boss("machine", "init", "--path", str(machine), "--remote", missing_remote.as_uri())
        self.assertEqual(init.returncode, 0, init.stderr)
        result = self.boss("machine", "sync", "--push")
        self.assertEqual(result.returncode, 1)
        self.assertIn("push failed", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_malformed_hook_input_and_stop_recursion_do_not_crash(self) -> None:
        malformed = self.boss("hook", "session-start", stdin="{broken")
        recursion = self.boss("hook", "stop", payload={"stop_hook_active": True})
        self.assertEqual(malformed.returncode, 0, malformed.stderr)
        self.assertNotIn("Traceback", malformed.stderr)
        self.assertEqual(recursion.returncode, 0, recursion.stderr)
        self.assertEqual(json.loads(recursion.stdout), {})

    def test_systemd_failure_is_reported_without_touching_real_user_units(self) -> None:
        fake_bin = self.home / "fake-bin"
        fake_bin.mkdir()
        systemctl = fake_bin / "systemctl"
        systemctl.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        systemctl.chmod(0o755)
        env = {**self.env, "PATH": f"{fake_bin}:{self.env['PATH']}"}
        result = self.boss("machine", "timer-install", "--interval", "5", env=env)
        self.assertEqual(result.returncode, 1)
        self.assertIn("could not be enabled", result.stderr)
        units = self.home / ".config" / "systemd" / "user"
        self.assertTrue((units / "boss-machine-sync.service").exists())
        self.assertTrue((units / "boss-machine-sync.timer").exists())


if __name__ == "__main__":
    unittest.main()
