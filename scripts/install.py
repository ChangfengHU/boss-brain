#!/usr/bin/env python3
"""Install, uninstall, or roll back Boss Brain without touching project data."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any


LEGACY_MARKERS = ("/.boss/hooks/", "/.project-brains/hooks/")
UNIFIED_MARKER = "boss-brain:hooks"


def home() -> Path:
    return Path.home()


def boss_home() -> Path:
    return Path(os.environ.get("BOSS_HOME", str(home() / ".boss"))).expanduser()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run(command: list[str], timeout: int = 90) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 127, "", str(exc))


def write(path: Path, text: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def copy_distribution(backup: Path) -> Path:
    source = repo_root()
    required = source / "plugins" / "boss-brain" / "scripts" / "boss.py"
    if not required.exists():
        raise RuntimeError(f"invalid source tree: missing {required}")
    target = boss_home() / "distribution"
    temporary = boss_home() / f".distribution-{os.getpid()}"
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    for relative in (Path(".agents"), Path(".claude-plugin"), Path("plugins/boss-brain"), Path("scripts")):
        shutil.copytree(
            source / relative,
            temporary / relative,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
    if target.exists():
        shutil.move(str(target), str(backup / "distribution"))
    os.replace(temporary, target)
    return target


def backup_file(path: Path, backup: Path) -> None:
    if path.exists():
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup / path.name)


def strip_codex_hooks(text: str, include_legacy: bool) -> str:
    patterns = [UNIFIED_MARKER]
    if include_legacy:
        patterns.extend(LEGACY_MARKERS)
    lines = text.splitlines(keepends=True)
    output: list[str] = []
    top = re.compile(r"^\[\[hooks\.([A-Za-z]+)\]\]\s*$")
    header = re.compile(r"^\[")
    i = 0
    while i < len(lines):
        match = top.match(lines[i].strip())
        if match:
            event = match.group(1)
            j = i + 1
            nested = f"[[hooks.{event}.hooks]]"
            while j < len(lines):
                stripped = lines[j].strip()
                if top.match(stripped) or (header.match(stripped) and stripped != nested):
                    break
                j += 1
            block = "".join(lines[i:j])
            if any(pattern in block for pattern in patterns):
                i = j
                continue
        line = lines[i]
        if "boss:hooks:" in line or "project-brains:hooks:" in line or UNIFIED_MARKER in line:
            i += 1
            continue
        output.append(line)
        i += 1
    return "".join(output).rstrip() + "\n"


def manual_codex_hooks(script: Path) -> str:
    commands = {
        "UserPromptSubmit": "prompt-submit",
        "SessionStart": "session-start",
        "Stop": "stop",
    }
    values = ["# boss-brain:hooks:begin (managed)\n"]
    for event, command in commands.items():
        value = f'{sys.executable} "{script}" hook {command}'
        values.extend([
            f"[[hooks.{event}]]\n",
            f"[[hooks.{event}.hooks]]\n",
            'type = "command"\n',
            f"command = {json.dumps(value)}\n",
        ])
    values.append("# boss-brain:hooks:end\n")
    return "".join(values)


def command_in(value: Any, patterns: tuple[str, ...]) -> bool:
    if isinstance(value, dict):
        return any(command_in(item, patterns) for item in value.values())
    if isinstance(value, list):
        return any(command_in(item, patterns) for item in value)
    return isinstance(value, str) and any(pattern in value for pattern in patterns)


def configure_claude_fallback(script: Path, skill: Path, include_legacy: bool) -> None:
    settings = home() / ".claude" / "settings.json"
    try:
        value = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        value = {}
    hooks = value.setdefault("hooks", {})
    patterns = (UNIFIED_MARKER, str(script), *(LEGACY_MARKERS if include_legacy else ()))
    for event in ("SessionStart", "UserPromptSubmit", "Stop"):
        entries = hooks.get(event, [])
        if not isinstance(entries, list):
            entries = []
        hooks[event] = [entry for entry in entries if not command_in(entry, patterns)]
    event_command = {"SessionStart": "session-start", "UserPromptSubmit": "prompt-submit", "Stop": "stop"}
    for event, command in event_command.items():
        hooks[event].append({
            "matcher": "*",
            "hooks": [{
                "type": "command",
                "command": f'{sys.executable} "{script}" hook {command} # {UNIFIED_MARKER}',
                "timeout": 20 if event == "Stop" else 10,
            }],
        })
    write(settings, json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    target = home() / ".claude" / "skills" / "boss-brain"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(skill, target)


def plugin_cli_install(name: str, distribution: Path) -> bool:
    if os.environ.get("BOSS_SKIP_PLUGIN_CLI") == "1" or not shutil.which(name):
        return False
    if name == "codex":
        add_market = run([name, "plugin", "marketplace", "add", str(distribution), "--json"])
        if add_market.returncode != 0 and "already" not in (add_market.stdout + add_market.stderr).lower():
            return False
        run([name, "plugin", "remove", "boss-brain@boss-brain", "--json"])
        return run([name, "plugin", "add", "boss-brain@boss-brain", "--json"]).returncode == 0
    help_result = run([name, "plugin", "--help"], timeout=15)
    if help_result.returncode != 0:
        return False
    add_market = run([name, "plugin", "marketplace", "add", str(distribution)])
    if add_market.returncode != 0 and "already" not in (add_market.stdout + add_market.stderr).lower():
        return False
    run([name, "plugin", "uninstall", "boss-brain@boss-brain"])
    return run([name, "plugin", "install", "boss-brain@boss-brain"]).returncode == 0


def install(args: argparse.Namespace) -> int:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = boss_home() / "backups" / f"install-{stamp}"
    boss_home().mkdir(parents=True, exist_ok=True)
    codex_config = home() / ".codex" / "config.toml"
    claude_settings = home() / ".claude" / "settings.json"
    backup_file(codex_config, backup)
    backup_file(claude_settings, backup)
    distribution = copy_distribution(backup)
    script = distribution / "plugins" / "boss-brain" / "scripts" / "boss.py"
    skill = distribution / "plugins" / "boss-brain" / "skills" / "boss-brain"
    wrapper = home() / ".local" / "bin" / "boss"
    write(wrapper, f'#!/bin/sh\nexec {sys.executable} "{script}" "$@"\n', 0o755)

    current = codex_config.read_text(encoding="utf-8") if codex_config.exists() else ""
    cleaned = strip_codex_hooks(current, include_legacy=True)
    if cleaned != current:
        write(codex_config, cleaned)
    codex_plugin = plugin_cli_install("codex", distribution)
    if not codex_plugin:
        current_after_cli = codex_config.read_text(encoding="utf-8") if codex_config.exists() else ""
        fallback_base = strip_codex_hooks(current_after_cli, include_legacy=False)
        write(codex_config, fallback_base + "\n" + manual_codex_hooks(script))
        target = home() / ".codex" / "skills" / "boss-brain"
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(skill, target)

    claude_plugin = plugin_cli_install("claude", distribution)
    if not claude_plugin:
        configure_claude_fallback(script, skill, include_legacy=True)

    migrate = run([sys.executable, str(script), "migrate", "--policy", args.policy])
    if migrate.returncode != 0:
        print("migration failed", file=sys.stderr)
        return 1
    if args.owner:
        write(boss_home() / "owner", args.owner.strip() + "\n")
    print(f"installed Boss Brain 0.1.0; backup={backup}")
    print(f"codex={'plugin' if codex_plugin else 'fallback'} claude={'plugin' if claude_plugin else 'fallback'}")
    print("existing ~/.boss data and all project .brain directories were preserved")
    return 0


def strip_claude_unified() -> None:
    settings = home() / ".claude" / "settings.json"
    try:
        value = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    hooks = value.get("hooks")
    if not isinstance(hooks, dict):
        return
    for event, entries in list(hooks.items()):
        if isinstance(entries, list):
            hooks[event] = [entry for entry in entries if not command_in(entry, (UNIFIED_MARKER, "/.boss/distribution/"))]
    write(settings, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def uninstall(_args: argparse.Namespace) -> int:
    run(["codex", "plugin", "remove", "boss-brain@boss-brain", "--json"])
    run(["claude", "plugin", "uninstall", "boss-brain@boss-brain"])
    codex_config = home() / ".codex" / "config.toml"
    if codex_config.exists():
        write(codex_config, strip_codex_hooks(codex_config.read_text(encoding="utf-8"), include_legacy=False))
    strip_claude_unified()
    for path in (home() / ".codex" / "skills" / "boss-brain", home() / ".claude" / "skills" / "boss-brain", boss_home() / "distribution"):
        if path.exists():
            shutil.rmtree(path)
    wrapper = home() / ".local" / "bin" / "boss"
    with contextlib.suppress(OSError):
        if wrapper.exists() and "/.boss/distribution/" in wrapper.read_text(encoding="utf-8"):
            wrapper.unlink()
    print("Boss Brain code and hooks removed; ~/.boss data and project .brain directories preserved")
    return 0


def rollback(_args: argparse.Namespace) -> int:
    backups = sorted((boss_home() / "backups").glob("install-*"), reverse=True)
    if not backups:
        print("no install backup found", file=sys.stderr)
        return 2
    backup = backups[0]
    uninstall(_args)
    for name, target in (("config.toml", home() / ".codex" / "config.toml"), ("settings.json", home() / ".claude" / "settings.json")):
        source = backup / name
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    print(f"configuration restored from {backup}; ~/.boss data preserved")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    subs = result.add_subparsers(dest="command", required=True)
    add = subs.add_parser("install")
    add.add_argument("--policy", choices=("quiet", "guarded", "strict"), default="quiet")
    add.add_argument("--owner")
    add.set_defaults(func=install)
    remove = subs.add_parser("uninstall")
    remove.set_defaults(func=uninstall)
    restore = subs.add_parser("rollback")
    restore.set_defaults(func=rollback)
    return result


def main() -> int:
    args = parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
