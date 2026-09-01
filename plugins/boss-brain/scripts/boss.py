#!/usr/bin/env python3
"""Boss Brain: ambient project continuity for coding agents.

The lifecycle path is intentionally local-only and dependency-free.  Hooks read
stdin, inspect Git and small text files, and emit either developer context or a
policy decision.  Network sync belongs in optional adapters, never in hooks.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from typing import Any, Iterable


VERSION = "0.1.0"
SCHEMA_VERSION = 1
POLICIES = ("quiet", "guarded", "strict")
TOKEN_RE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20,}|"
    r"xox[baprs]-[A-Za-z0-9-]{20,}|AKIA[A-Z0-9]{16}|AIza[A-Za-z0-9_-]{30,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----)"
)
AT_TOKEN_RE = re.compile(r"@([A-Za-z0-9_\-\u4e00-\u9fff]+)")


def bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(maximum, max(minimum, parsed))


def redact_secrets(value: str) -> str:
    return TOKEN_RE.sub("[REDACTED_SECRET]", value)


def safe_record_field(value: str) -> bool:
    return not TOKEN_RE.search(value) and not any(character in value for character in "\t\r\n")


def runtime_home() -> Path:
    override = os.environ.get("BOSS_HOME")
    return Path(override).expanduser() if override else Path.home() / ".boss"


def state_home() -> Path:
    override = os.environ.get("BOSSBRAIN_STATE_DIR")
    return Path(override).expanduser() if override else runtime_home() / "state"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def atomic_write(path: Path, value: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, mode)
        os.replace(tmp_name, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_name)


def read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, value: Any, mode: int = 0o600) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n", mode)


def config() -> dict[str, Any]:
    value = read_json(runtime_home() / "config.json", {})
    policy = value.get("policy", "quiet")
    if policy not in POLICIES:
        policy = "quiet"
    scan = value.get("scan") if isinstance(value.get("scan"), dict) else {}
    scan = {"max_depth": 3, "max_age_days": 180, **scan}
    scan["max_depth"] = bounded_int(scan.get("max_depth"), 3, 0, 32)
    scan["max_age_days"] = bounded_int(scan.get("max_age_days"), 180, 0, 36500)
    return {
        **value,
        "schema": SCHEMA_VERSION,
        "policy": policy,
        "scan": scan,
    }


def registry_path() -> Path:
    return runtime_home() / "registry.tsv"


def run(command: list[str], cwd: Path | None = None, timeout: int = 10) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(command, 127, "", str(exc))


def git(root: Path, *args: str, timeout: int = 10) -> str:
    result = run(["git", "-C", str(root), *args], timeout=timeout)
    return result.stdout.strip() if result.returncode == 0 else ""


def git_root(cwd: str | Path) -> Path | None:
    value = git(Path(cwd), "rev-parse", "--show-toplevel")
    return Path(value).resolve() if value else None


def read_registry() -> list[dict[str, str]]:
    path = registry_path()
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    rows: list[dict[str, str]] = []
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        parts.extend([""] * (5 - len(parts)))
        rows.append(
            {
                "path": parts[0].strip(),
                "name": parts[1].strip(),
                "aliases": parts[2].strip(),
                "summary": parts[3].strip(),
                "kind": parts[4].strip() or "local",
            }
        )
    return [row for row in rows if row["path"] and row["name"]]


def owner_name() -> str:
    value = os.environ.get("BOSS_OWNER", "").strip()
    if value:
        return value
    try:
        return (runtime_home() / "owner").read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def origin_url(root: Path) -> str:
    return git(root, "remote", "get-url", "origin")


def remote_owner(url: str) -> str:
    match = re.search(r"github\.com[:/]+(?:[^/@]+@)?([^/]+)/", url)
    return match.group(1) if match else ""


def repo_age_days(root: Path) -> float:
    stamp = git(root, "log", "-1", "--format=%ct")
    if not stamp.isdigit():
        return float("inf")
    return max(0.0, (time.time() - int(stamp)) / 86400)


def repo_qualification(root: Path) -> tuple[bool, list[str]]:
    """Return whether Boss may silently adopt a repository and why not."""
    reasons: list[str] = []
    remote = origin_url(root)
    owner = owner_name()
    actual_owner = remote_owner(remote)
    max_age = int(config().get("scan", {}).get("max_age_days", 180))
    if not remote:
        reasons.append("no-origin")
    elif not owner:
        reasons.append("owner-unknown")
    elif actual_owner.lower() != owner.lower():
        reasons.append("foreign-owner")
    if not git(root, "rev-parse", "HEAD"):
        reasons.append("empty")
    if repo_age_days(root) > max_age:
        reasons.append("stale")
    return not reasons, reasons


def scan_roots() -> list[Path]:
    configured = config().get("scan", {}).get("roots")
    values = configured if isinstance(configured, list) and configured else [str(Path.home())]
    roots: list[Path] = []
    for value in values:
        path = Path(str(value)).expanduser()
        if path.is_dir():
            roots.append(path.resolve())
    return roots


def discover_repositories() -> list[Path]:
    max_depth = int(config().get("scan", {}).get("max_depth", 3))
    excluded = {
        ".cache", ".cargo", ".git", ".local", ".npm", ".nvm", ".rustup",
        "build", "dist", "node_modules", "vendor", "venv", ".venv",
    }
    found: set[Path] = set()
    for scan_root in scan_roots():
        for current, dirs, _files in os.walk(scan_root):
            path = Path(current)
            try:
                depth = len(path.relative_to(scan_root).parts)
            except ValueError:
                continue
            dirs[:] = [name for name in dirs if name not in excluded and not name.startswith(".")]
            if (path / ".git").exists():
                found.add(path.resolve())
                dirs[:] = []
                continue
            if depth >= max_depth:
                dirs[:] = []
    return sorted(found)


def registry_text(rows: Iterable[dict[str, str]]) -> str:
    header = "# path\tname\taliases\tsummary\tkind(local|remote|ref)"
    values = [header]
    for row in rows:
        values.append("\t".join(row.get(key, "") for key in ("path", "name", "aliases", "summary", "kind")))
    return "\n".join(values) + "\n"


def register_rows(
    candidates: Iterable[Path], *, require_qualification: bool = True
) -> tuple[list[dict[str, str]], list[tuple[Path, list[str]]]]:
    """Atomically register repositories without creating .brain.

    Silent discovery requires owner qualification; explicit machine restore has
    already been authorized by the user and may include non-GitHub remotes.
    """
    runtime_home().mkdir(parents=True, exist_ok=True)
    lock = runtime_home() / ".registry.lock"
    acquired = False
    for _ in range(100):
        try:
            lock.mkdir()
            acquired = True
            break
        except FileExistsError:
            with contextlib.suppress(OSError):
                if time.time() - lock.stat().st_mtime > 30:
                    lock.rmdir()
            time.sleep(0.02)
    if not acquired:
        return [], [(path, ["registry-busy"]) for path in candidates]
    try:
        rows = read_registry()
        known_paths = {str(Path(row["path"]).resolve()) for row in rows}
        known_names = {row["name"].lower() for row in rows}
        added: list[dict[str, str]] = []
        skipped: list[tuple[Path, list[str]]] = []
        for root in candidates:
            root = root.resolve()
            if str(root) in known_paths:
                continue
            qualified, reasons = repo_qualification(root) if require_qualification else (True, [])
            name = root.name
            if not safe_record_field(str(root)) or not safe_record_field(name):
                reasons = [*reasons, "unsafe-metadata"]
                qualified = False
            if name.lower() in known_names:
                reasons = [*reasons, "name-conflict"]
                qualified = False
            if not qualified:
                skipped.append((root, reasons))
                continue
            row = {
                "path": str(root),
                "name": name,
                "aliases": "",
                "summary": "(Boss 自动登记，定位待项目工作自然补齐)",
                "kind": "local",
            }
            rows.append(row)
            added.append(row)
            known_paths.add(str(root))
            known_names.add(name.lower())
        if added:
            atomic_write(registry_path(), registry_text(rows))
        elif not registry_path().exists():
            atomic_write(registry_path(), registry_text(rows))
        return added, skipped
    finally:
        with contextlib.suppress(OSError):
            lock.rmdir()


def patrol(force: bool = False) -> tuple[list[dict[str, str]], list[tuple[Path, list[str]]]]:
    stamp = runtime_home() / ".last-patrol"
    today = dt.date.today().isoformat()
    if not force:
        with contextlib.suppress(OSError):
            if stamp.read_text(encoding="utf-8").strip() == today:
                return [], []
    added, skipped = register_rows(discover_repositories())
    atomic_write(stamp, today + "\n")
    return added, skipped


def row_names(row: dict[str, str]) -> list[str]:
    return [row["name"], *[item.strip() for item in row["aliases"].split(",") if item.strip()]]


def row_map(rows: Iterable[dict[str, str]]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in rows:
        for name in row_names(row):
            if len(name) >= 2:
                result.setdefault(name.lower(), row)
    return result


def explicit_project(prompt: str, rows: list[dict[str, str]]) -> dict[str, str] | None:
    names = row_map(rows)
    for match in AT_TOKEN_RE.finditer(prompt):
        start, end, token = match.start(), match.end(), match.group(1)
        previous = prompt[start - 1] if start else ""
        if previous and previous.isascii() and (previous.isalnum() or previous in "_./-"):
            continue
        following = prompt[end] if end < len(prompt) else ""
        following2 = prompt[end + 1] if end + 1 < len(prompt) else ""
        if (following and following in "/@") or (
            following and following in ":." and following2.isascii() and following2.isalnum()
        ):
            continue
        direct = names.get(token.lower())
        if direct:
            return direct
        best = ""
        for name in names:
            if token.lower().startswith(name) and name[-1].isascii():
                boundary = token[len(name) : len(name) + 1]
                if boundary and not (boundary.isascii() and (boundary.isalnum() or boundary in "_-")):
                    if len(name) > len(best):
                        best = name
        if best:
            return names[best]
    return None


def alias_project(prompt: str, rows: list[dict[str, str]]) -> dict[str, str] | None:
    best: dict[str, str] | None = None
    best_len = 0
    for row in rows:
        for name in row_names(row):
            if not re.search(r"[A-Za-z0-9_-]", name) and len(name) < 3:
                continue
            if re.search(r"[A-Za-z0-9_-]", name):
                pattern = rf"(?<![A-Za-z0-9_-]){re.escape(name)}(?![A-Za-z0-9_-])"
            else:
                pattern = re.escape(name)
            if re.search(pattern, prompt, re.IGNORECASE) and len(name) > best_len:
                best, best_len = row, len(name)
    return best


def cap_text(text: str, limit: int = 4200) -> str:
    if len(text) <= limit:
        return text
    sections = re.split(r"(?m)(?=^## )", text)
    selected = [part for part in sections if any(key in part[:80] for key in ("现状", "下一步", "阻塞", "雷区"))]
    value = "\n".join(selected)
    if not value:
        value = text[:limit]
    return value[:limit].rstrip() + f"\n[状态卡过长，已节选；全文 {len(text)} 字]"


def active_tasks(brain: Path) -> list[str]:
    path = brain / "TASKS.md"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    checkbox = any(line.startswith("- [ ]") for line in lines)
    if checkbox:
        return [line for line in lines if line.startswith("- [ ]")][:10]
    return [line for line in lines if line.rstrip().endswith(" active")][:10]


def project_context(row: dict[str, str], explicit: bool = True) -> str:
    root = Path(row["path"])
    if not root.is_dir():
        return f"[Boss Brain 内部上下文，请勿向用户复述]\n项目 {row['name']} 的登记路径不存在：{root}。不要在该路径写入。"
    brain = root / ".brain"
    lines = [
        "[Boss Brain 内部上下文，请静默使用，不要向用户复述]",
        f"当前项目：{row['name']} ({row['kind']})",
        f"工作目录：{root}",
    ]
    if row["summary"]:
        lines.append(f"定位：{row['summary']}")
    state = brain / "STATE.md"
    if state.exists():
        try:
            text = state.read_text(encoding="utf-8", errors="replace")
            lines.extend(["--- .brain/STATE.md ---", cap_text(text)])
        except OSError:
            pass
    elif explicit:
        lines.append("该项目尚无 STATE.md；不要因此打断用户当前任务。")
    tasks = active_tasks(brain)
    if tasks:
        lines.append("活跃任务：")
        lines.extend(tasks)
    wiki_index = brain / "wiki" / "index.md"
    if wiki_index.is_file():
        lines.append(
            f"Wiki 索引可用：{wiki_index}。仅在当前问题困难或反复出现时，用本地只读命令先读取索引，"
            "再只加载相关条目；普通问题不要读取，也不要把本地路径交给网页或 MCP 工具。"
        )
    lines.extend(relation_context(row))
    lines.extend(capability_context(row))
    return "\n".join(lines)


def relevant_wiki_context(row: dict[str, str], prompt: str) -> tuple[str, str] | None:
    wiki = Path(row["path"]) / ".brain" / "wiki"
    index = wiki / "index.md"
    try:
        index_text = index.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    prompt_lower = prompt.lower()
    ignored = {"brain", "index", "memory", "project", "wiki"}
    prompt_tokens = set(re.findall(r"[a-z0-9]{3,}|[\u4e00-\u9fff]{2,}", prompt_lower)) - ignored
    candidates: list[tuple[int, str, Path]] = []
    for label, relative in re.findall(r"\[([^\]]+)\]\(([^)]+\.md)\)", index_text, re.IGNORECASE):
        candidate = (wiki / relative).resolve()
        try:
            if os.path.commonpath((str(wiki.resolve()), str(candidate))) != str(wiki.resolve()):
                continue
        except ValueError:
            continue
        topic_text = f"{label} {Path(relative).stem}".lower()
        topic_tokens = set(re.findall(r"[a-z0-9]{3,}|[\u4e00-\u9fff]{2,}", topic_text)) - ignored
        score = len(prompt_tokens & topic_tokens)
        if label.lower() in prompt_lower:
            score += 10
        if score and candidate.is_file():
            candidates.append((score, relative, candidate))
    if not candidates:
        return None
    _score, relative, candidate = max(candidates, key=lambda item: (item[0], item[1]))
    try:
        content = candidate.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if len(content) > 2400:
        content = content[:2400].rstrip() + f"\n[Wiki 条目过长，已节选；全文 {len(content)} 字]"
    text = (
        "[Boss Brain 相关 Wiki 条目，请静默使用，不要向用户复述本段]\n"
        f"当前项目：{row['name']}\n"
        f"命中条目：.brain/wiki/{relative}\n"
        "--- 相关 Wiki 正文 ---\n"
        f"{content}"
    )
    return text, relative


def relation_context(row: dict[str, str]) -> list[str]:
    path = runtime_home() / "relations.md"
    if not path.exists():
        legacy = Path.home() / ".boss" / "relations.md"
        path = legacy if legacy.exists() else path
    try:
        content = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    names = [item.lower() for item in row_names(row) if len(item) >= 3]
    matches = [line for line in content if line.startswith("|") and any(name in line.lower() for name in names)]
    return ["--- 跨项目关系 ---", *matches[:6]] if matches else []


def read_capabilities(row: dict[str, str]) -> list[dict[str, str]]:
    path = Path(row["path"]) / ".brain" / "capabilities.tsv"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    values: list[dict[str, str]] = []
    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.split("\t")
        parts.extend([""] * (4 - len(parts)))
        if parts[0] in ("provides", "consumes") and parts[1]:
            values.append({"direction": parts[0], "id": parts[1], "at": parts[2], "summary": parts[3]})
    return values


def capability_context(target: dict[str, str]) -> list[str]:
    rows = read_registry()
    all_caps = [(row, cap) for row in rows for cap in read_capabilities(row)]
    mine = read_capabilities(target)
    lines: list[str] = []
    for cap in mine:
        opposite = "consumes" if cap["direction"] == "provides" else "provides"
        peers = sorted({row["name"] for row, other in all_caps if other["direction"] == opposite and other["id"] == cap["id"]})
        if peers:
            verb = "被使用" if cap["direction"] == "provides" else "由其提供"
            lines.append(f"{cap['id']} {verb}：{', '.join(peers)}")
    return ["--- 能力关系 ---", *lines[:8]] if lines else []


def cleanup_state() -> None:
    root = state_home()
    root.mkdir(parents=True, exist_ok=True)
    cutoff = time.time() - 14 * 86400
    for path in root.glob("**/*"):
        with contextlib.suppress(OSError):
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()


def session_file(session_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "nosid")
    return state_home() / "sessions" / f"{safe}.json"


def load_session(session_id: str) -> dict[str, Any]:
    return read_json(session_file(session_id), {"schema": SCHEMA_VERSION, "roots": {}, "last_injection": ""})


def save_session(session_id: str, value: dict[str, Any]) -> None:
    write_json(session_file(session_id), value)


def claim_root(session_id: str, root: Path) -> None:
    value = load_session(session_id)
    roots = value.setdefault("roots", {})
    key = str(root.resolve())
    if key not in roots:
        roots[key] = {"baseline": git(root, "rev-parse", "HEAD"), "claimed_at": now_iso()}
    save_session(session_id, value)


def context_sections(mode: str, text: str) -> list[str]:
    if mode == "alias":
        return ["pointer"]
    if mode == "roster":
        return ["project-index"]
    if mode == "wiki":
        return ["wiki"]
    checks = (
        ("state", "--- .brain/STATE.md ---"),
        ("tasks", "活跃任务："),
        ("wiki-index", "Wiki 索引可用："),
        ("relations", "--- 跨项目关系 ---"),
        ("capabilities", "--- 能力关系 ---"),
    )
    return [name for name, marker in checks if marker in text]


def remember_context(
    session_id: str,
    mode: str,
    row: dict[str, str] | None,
    text: str,
    event: str,
    identity: str = "",
) -> None:
    value = load_session(session_id)
    key = f"{mode}:{row['name'] if row else '-'}:{identity}"
    value["last_injection"] = key
    redacted = redact_secrets(text)
    value["last_context"] = {
        "at": now_iso(),
        "event": event,
        "mode": mode,
        "confidence": {"workspace": "workspace", "explicit": "high", "alias": "low", "roster": "index", "wiki": "matched"}.get(mode, "unknown"),
        "content_policy": {
            "workspace": "full-project",
            "explicit": "full-project",
            "alias": "pointer-only",
            "roster": "project-index",
            "wiki": "selected-wiki-entry",
        }.get(mode, "unknown"),
        "project": row["name"] if row else None,
        "chars": len(redacted),
        "sections": context_sections(mode, redacted),
    }
    save_session(session_id, value)
    write_json(state_home() / "last-context.json", value["last_context"])
    atomic_write(state_home() / "last-context-preview.txt", redacted.rstrip() + "\n", 0o600)


def roster_context(rows: list[dict[str, str]]) -> str:
    lines = ["[Boss Brain 项目索引，仅供 Agent 内部路由，请勿向用户复述]"]
    for row in rows[:30]:
        suffix = f"：{row['summary']}" if row["summary"] else ""
        aliases = f"；别名 {row['aliases']}" if row["aliases"] else ""
        lines.append(f"- {row['name']} [{row['kind']}] {row['path']}{aliases}{suffix}")
    return "\n".join(lines)


def hook_output(event: str, context: str) -> None:
    if not context:
        if event == "Stop":
            print("{}")
        return
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": redact_secrets(context)}}, ensure_ascii=False))


def hook_session_start(payload: dict[str, Any]) -> int:
    cleanup_state()
    added, _skipped = patrol()
    session_id = str(payload.get("session_id") or "nosid")
    source = str(payload.get("source") or "startup")
    value = load_session(session_id)
    if source in ("compact", "resume"):
        value["last_injection"] = ""
        save_session(session_id, value)
    cwd = Path(str(payload.get("cwd") or os.getcwd()))
    root = git_root(cwd)
    rows = read_registry()
    if root:
        if not any(Path(row["path"]).resolve() == root for row in rows):
            just_added, _ = register_rows([root])
            added.extend(just_added)
            rows = read_registry()
        claim_root(session_id, root)
        match = next((row for row in rows if Path(row["path"]).resolve() == root), None)
        if match:
            text = project_context(match)
        elif (root / ".brain").is_dir():
            synthetic = {"path": str(root), "name": root.name, "aliases": "", "summary": "", "kind": "local"}
            text = project_context(synthetic)
        else:
            text = (
                "[Boss Brain 内部上下文，请勿向用户复述]\n"
                f"当前 Git 工作区尚未纳管：{root}。普通任务照常执行；只有用户明确要求纳管时才写入 .brain。"
            )
        if added:
            names = ", ".join(row["name"] for row in added)
            text += f"\nBoss 本轮静默登记了项目：{names}。不要为补元数据打断用户当前任务。"
        ensure_machine_initialized()
        remember_context(session_id, "workspace", match, text, "SessionStart")
        hook_output("SessionStart", text)
        return 0
    if rows:
        text = roster_context(rows)
        if added:
            names = ", ".join(row["name"] for row in added)
            text += f"\n本轮巡航静默登记：{names}。不要主动要求用户补资料。"
        ensure_machine_initialized()
        remember_context(session_id, "roster", None, text, "SessionStart")
        hook_output("SessionStart", text)
    else:
        ensure_machine_initialized()
    return 0


def hook_prompt(payload: dict[str, Any]) -> int:
    prompt = str(payload.get("prompt") or "")
    if not prompt:
        return 0
    session_id = str(payload.get("session_id") or "nosid")
    rows = read_registry()
    if not rows:
        return 0
    session = load_session(session_id)
    explicit = explicit_project(prompt, rows)
    at_context = bool(re.search(r"@(?=\s|$)", prompt))
    identity = ""
    if explicit:
        root = Path(explicit["path"])
        if root.is_dir():
            claim_root(session_id, root)
        wiki_match = relevant_wiki_context(explicit, prompt)
        if wiki_match:
            text, identity = wiki_match
            mode, row = "wiki", explicit
        else:
            mode, row, text = "explicit", explicit, project_context(explicit)
    elif at_context:
        mode, row, text = "roster", None, roster_context(rows)
    elif "@" not in prompt:
        alias = alias_project(prompt, rows)
        claimed = session.get("roots", {})
        if alias and str(Path(alias["path"]).resolve()) not in claimed:
            mode, row = "alias", alias
            text = (
                "[Boss Brain 低置信度项目指针，请勿向用户复述]\n"
                f"提示词可能涉及 {alias['name']}，路径 {alias['path']}。"
                "没有加载项目正文；写操作前必须确认目标确实是该项目。"
            )
        else:
            target = alias
            if not target:
                target = next(
                    (row for row in rows if str(Path(row["path"]).resolve()) in claimed),
                    None,
                )
            wiki_match = relevant_wiki_context(target, prompt) if target else None
            if not wiki_match:
                return 0
            text, identity = wiki_match
            mode, row = "wiki", target
    else:
        return 0
    key = f"{mode}:{row['name'] if row else '-'}:{identity}"
    if session.get("last_injection") == key:
        return 0
    remember_context(session_id, mode, row, text, "UserPromptSubmit", identity)
    hook_output("UserPromptSubmit", text)
    return 0


def changed_commits(root: Path, baseline: str) -> list[str]:
    if not baseline:
        return []
    value = git(root, "rev-list", "--reverse", f"{baseline}..HEAD")
    return value.splitlines() if value else []


def work_commits(root: Path, commits: list[str]) -> list[str]:
    result: list[str] = []
    for commit in commits:
        names = git(root, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", commit).splitlines()
        if any(not name.startswith(".brain/") for name in names if name):
            result.append(commit)
    return result


def newest_evidence(brain: Path) -> tuple[dict[str, Any] | None, set[str]]:
    files = [brain / "evidence.jsonl", *sorted((brain / "tasks").glob("*/evidence.jsonl"))]
    newest: tuple[float, dict[str, Any]] | None = None
    commits: set[str] = set()
    for path in files:
        try:
            mtime = path.stat().st_mtime
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            commit = str(item.get("commit") or "")
            if commit and commit != "pending":
                commits.add(commit)
            newest = max(newest, (mtime, item), key=lambda value: value[0]) if newest else (mtime, item)
    return (newest[1] if newest else None, commits)


def commit_is_recorded(commit: str, recorded: set[str]) -> bool:
    return any(commit.startswith(value) or value.startswith(commit) for value in recorded if len(value) >= 7)


def audit_repo(root: Path, baseline: str, policy: str) -> list[dict[str, str]]:
    commits = changed_commits(root, baseline)
    if not commits:
        return []
    findings: list[dict[str, str]] = []
    work = work_commits(root, commits)
    upstream = git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    if not upstream:
        findings.append({"code": "no-upstream", "level": "data-loss", "message": f"{root} 本会话有提交但当前分支没有远端上游。"})
    else:
        ahead = git(root, "rev-list", "--count", f"{upstream}..HEAD")
        if ahead and int(ahead) > 0:
            findings.append({"code": "unpushed", "level": "data-loss", "message": f"{root} 有 {ahead} 个提交尚未推送到 {upstream}。"})
    brain = root / ".brain"
    if not brain.is_dir():
        return findings
    dirty = git(root, "status", "--porcelain", "--", ".brain")
    if dirty:
        findings.append({"code": "brain-dirty", "level": "data-loss", "message": f"{root}/.brain 有未提交写入。"})
    if not work:
        return findings
    evidence, recorded = newest_evidence(brain)
    latest = work[-1]
    if not commit_is_recorded(latest, recorded):
        findings.append({"code": "evidence", "level": "continuity", "message": f"{root} 最新工作提交尚未被 evidence.jsonl 记录。"})
    if not evidence or "wiki" not in evidence:
        findings.append({"code": "wiki-judgment", "level": "continuity", "message": f"{root} 最新证据缺少 wiki 判断字段。"})
    changed = set(git(root, "diff", "--name-only", f"{baseline}..HEAD", "--", ".brain").splitlines())
    if ".brain/STATE.md" not in changed:
        findings.append({"code": "state", "level": "continuity", "message": f"{root} 有新工作提交，但 STATE.md 未随本会话更新。"})
    if not any(name.startswith(".brain/dev-log/") for name in changed):
        findings.append({"code": "dev-log", "level": "continuity", "message": f"{root} 有新工作提交，但没有本会话 dev-log。"})
    if policy == "strict":
        caps = brain / "capabilities.tsv"
        if not caps.exists():
            findings.append({"code": "capabilities", "level": "strict", "message": f"{root} 缺少 .brain/capabilities.tsv。"})
        else:
            with contextlib.suppress(OSError):
                if "这里换成真的" in caps.read_text(encoding="utf-8", errors="replace"):
                    findings.append({"code": "capabilities-template", "level": "strict", "message": f"{root} 的 capabilities.tsv 仍是模板。"})
    return findings


def append_audit(session_id: str, findings: list[dict[str, str]]) -> None:
    path = state_home() / "audit.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    safe_findings = [
        {key: redact_secrets(value) if isinstance(value, str) else value for key, value in finding.items()}
        for finding in findings
    ]
    entry = {"at": now_iso(), "session": session_id, "findings": safe_findings}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    os.chmod(path, 0o600)


def hook_stop(payload: dict[str, Any]) -> int:
    if payload.get("stop_hook_active"):
        print("{}")
        return 0
    session_id = str(payload.get("session_id") or "nosid")
    session = load_session(session_id)
    cwd = Path(str(payload.get("cwd") or os.getcwd()))
    root = git_root(cwd)
    if root:
        register_rows([root])
        claim_root(session_id, root)
        session = load_session(session_id)
    policy = config()["policy"]
    findings: list[dict[str, str]] = []
    for path, info in session.get("roots", {}).items():
        repo = Path(path)
        if repo.is_dir() and (repo / ".git").exists():
            findings.extend(audit_repo(repo, str(info.get("baseline") or ""), policy))
    append_audit(session_id, findings)
    if policy == "quiet":
        print("{}")
        return 0
    selected = findings if policy == "strict" else [item for item in findings if item["level"] == "data-loss"]
    if not selected:
        print("{}")
        return 0
    reason = "Boss Brain 收工检查：\n" + "\n".join(f"- {item['message']}" for item in selected[:8])
    reason += "\n请只处理本会话产生的改动；若属于其他并发会话，不要代为提交或推送。"
    print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
    return 0


def read_payload() -> dict[str, Any]:
    try:
        value = json.load(sys.stdin)
        return value if isinstance(value, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def cmd_hook(args: argparse.Namespace) -> int:
    payload = read_payload()
    if args.event == "session-start":
        return hook_session_start(payload)
    if args.event == "prompt-submit":
        return hook_prompt(payload)
    return hook_stop(payload)


def state_summary(path: Path) -> str:
    state = path / ".brain" / "STATE.md"
    if not state.exists():
        return "-"
    try:
        lines = state.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "?"
    in_next = False
    for line in lines:
        if line.startswith("## "):
            in_next = "下一步" in line
            continue
        if in_next and line.strip():
            return line.strip()[:70]
    return "-"


def cmd_projects(_: argparse.Namespace) -> int:
    rows = read_registry()
    print(f"{'PROJECT':24} {'KIND':8} {'GIT':8} NEXT")
    for row in rows:
        path = Path(row["path"])
        git_state = "missing" if not path.is_dir() else ("dirty" if git(path, "status", "--porcelain") else "clean")
        print(f"{row['name'][:24]:24} {row['kind'][:8]:8} {git_state:8} {state_summary(path)}")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    failed = False
    for row in read_registry():
        root = Path(row["path"])
        if not root.is_dir():
            print(f"MISSING {row['name']}: {root}")
            failed = True
            continue
        dirty = len(git(root, "status", "--porcelain").splitlines())
        upstream = git(root, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
        ahead = git(root, "rev-list", "--count", f"{upstream}..HEAD") if upstream else "?"
        behind = git(root, "rev-list", "--count", f"HEAD..{upstream}") if upstream else "?"
        label = "OK" if dirty == 0 and ahead in ("0", "?") else "CHECK"
        print(f"{label:5} {row['name']}: dirty={dirty} ahead={ahead or '?'} behind={behind or '?'}")
    return 1 if failed else 0


def cmd_caps(_: argparse.Namespace) -> int:
    rows = read_registry()
    mapping: dict[str, dict[str, list[str]]] = {}
    for row in rows:
        for cap in read_capabilities(row):
            mapping.setdefault(cap["id"], {"provides": [], "consumes": []})[cap["direction"]].append(row["name"])
    for cap_id in sorted(mapping):
        value = mapping[cap_id]
        providers = ", ".join(sorted(set(value["provides"]))) or "MISSING"
        consumers = ", ".join(sorted(set(value["consumes"]))) or "-"
        print(f"{cap_id}\n  provides: {providers}\n  consumes: {consumers}")
    return 0


def cmd_risk(_: argparse.Namespace) -> int:
    for row in read_registry():
        state = Path(row["path"]) / ".brain" / "STATE.md"
        try:
            text = state.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parts = re.split(r"(?m)(?=^## )", text)
        risk = [part.strip() for part in parts if part.startswith("## 阻塞") or part.startswith("## 雷区")]
        if risk:
            print(f"== {row['name']}\n" + "\n".join(risk))
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    found = discover_repositories()
    rows = read_registry()
    known = {str(Path(row["path"]).resolve()) for row in rows}
    candidates = [path for path in found if str(path) not in known]
    added: list[dict[str, str]] = []
    skipped: list[tuple[Path, list[str]]] = []
    if args.adopt:
        added, skipped = register_rows(candidates)
    else:
        for path in candidates:
            qualified, reasons = repo_qualification(path)
            skipped.append((path, [] if qualified else reasons))
    if args.json:
        print(json.dumps({
            "found": len(found),
            "known": len(found) - len(candidates),
            "added": [row["path"] for row in added],
            "candidates": [{"path": str(path), "reasons": reasons} for path, reasons in skipped],
        }, ensure_ascii=False, indent=2))
        return 0
    print(f"found={len(found)} known={len(found) - len(candidates)} added={len(added)}")
    for row in added:
        print(f"ADDED {row['name']}: {row['path']}")
    for path, reasons in skipped:
        label = "QUALIFIED" if not reasons else "CANDIDATE"
        detail = ",".join(reasons) if reasons else "use --adopt"
        print(f"{label} {path}: {detail}")
    return 0


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9.-]+", "-", value.strip()).strip("-.").lower()
    return slug[:63] or "machine"


def machine_defaults() -> dict[str, str]:
    cfg = config().get("machine") if isinstance(config().get("machine"), dict) else {}
    try:
        machine_id = Path("/etc/machine-id").read_text(encoding="utf-8").strip()[:8]
    except OSError:
        machine_id = "unknown"
    hostname = socket.gethostname().split(".", 1)[0]
    name = str(cfg.get("name") or os.environ.get("BOSS_MACHINE_NAME") or f"boss-{safe_slug(hostname)}-{machine_id}")
    path = str(cfg.get("path") or (Path.home() / name))
    remote = str(cfg.get("remote") or "")
    return {"name": safe_slug(name), "path": path, "remote": remote, "id": machine_id, "hostname": hostname}


def safe_remote(url: str) -> str:
    if not url:
        return ""
    match = re.search(r"github\.com[:/]+(?:[^/@]+@)?([^/]+)/([^/#]+?)(?:\.git)?$", url)
    if match:
        return f"https://github.com/{match.group(1)}/{match.group(2)}.git"
    return re.sub(r"//[^/@]+@", "//***@", url)


def local_addresses() -> list[str]:
    result = run(["hostname", "-I"])
    if result.returncode != 0:
        return []
    return [value for value in result.stdout.split() if re.fullmatch(r"[0-9A-Fa-f:.]+", value)][:8]


def machine_project_rows() -> list[list[str]]:
    values: list[list[str]] = []
    for row in read_registry():
        root = Path(row["path"])
        values.append([
            row["name"], row["aliases"], row["summary"], row["kind"],
            str(root), safe_remote(origin_url(root)) if root.is_dir() else "",
            "yes" if (root / ".brain").is_dir() else "no",
        ])
    return values


def machine_capability_rows() -> list[list[str]]:
    values: list[list[str]] = []
    for project in read_registry():
        for cap in read_capabilities(project):
            values.append([project["name"], cap["direction"], cap["id"], cap["at"], cap["summary"]])
    return values


def table_text(header: list[str], rows: Iterable[Iterable[str]]) -> str:
    return "\t".join(header) + "\n" + "\n".join("\t".join(str(item).replace("\t", " ").replace("\n", " ") for item in row) for row in rows) + "\n"


def write_machine_snapshot(repo: Path, machine: dict[str, str]) -> list[Path]:
    repo.mkdir(parents=True, exist_ok=True)
    projects = machine_project_rows()
    caps = machine_capability_rows()
    system = {
        "schema": 1,
        "machine_id": machine["id"],
        "name": machine["name"],
        "hostname": machine["hostname"],
        "addresses": local_addresses(),
        "platform": platform.platform(),
        "architecture": platform.machine(),
        "project_owner": owner_name(),
    }
    managed: dict[Path, str] = {
        repo / ".gitignore": "secrets/\n*.key\n*.pem\n.env*\n",
        repo / "README.md": (
            f"# {machine['name']}\n\n"
            "This repository is a portable Boss machine brain. It contains project and capability indexes, "
            "recovery instructions, and Vault key references only. It must never contain credential values.\n"
        ),
        repo / "machine.json": json.dumps(system, ensure_ascii=False, indent=2) + "\n",
        repo / "projects.tsv": table_text(
            ["name", "aliases", "summary", "kind", "last_path", "origin", "has_brain"], projects
        ),
        repo / "capabilities.tsv": table_text(
            ["project", "direction", "capability", "interface", "summary"], caps
        ),
        repo / ".brain" / "STATE.md": (
            "# Machine state\n\n"
            f"## 现状\n\nBoss manages {len(projects)} registered projects on this machine.\n\n"
            "## 下一步\n\nRun `boss machine sync --push` after machine structure changes.\n\n"
            "## 阻塞\n\nSee `boss status` and the latest timer result.\n\n"
            "## 雷区\n\nCredential values belong in Vault, never in this repository.\n"
        ),
        repo / ".brain" / "HANDOFF.md": (
            "# Machine takeover\n\n"
            "## 这是什么\n\nA machine-level Boss index. Project truth remains in each project's `.brain/`.\n\n"
            "## 资产与访问\n\nVault key names are in `vault-refs.tsv` when configured; values remain in Vault.\n\n"
            "## 阅读顺序\n\nRead `machine.json`, `projects.tsv`, `capabilities.tsv`, then project brains.\n\n"
            "## 如何验证\n\nRun `boss doctor`, `boss scan`, and `boss status`.\n\n"
            "## 雷区\n\nDo not restore obsolete absolute paths blindly; match projects by origin URL first.\n"
        ),
        repo / ".brain" / "capabilities.tsv": (
            "# direction\tcapability-id\tinterface\tsummary\n"
            "provides\tboss.machine.inventory\tprojects.tsv\tPortable project inventory for this machine\n"
            "provides\tboss.machine.recovery\t.brain/HANDOFF.md\tMachine recovery procedure\n"
        ),
    }
    refs = runtime_home() / "vault-refs.tsv"
    if refs.exists():
        try:
            refs_text = refs.read_text(encoding="utf-8", errors="replace")
        except OSError:
            refs_text = ""
        if refs_text and not TOKEN_RE.search(refs_text):
            managed[repo / "vault-refs.tsv"] = refs_text
    for path, content in managed.items():
        if TOKEN_RE.search(content):
            raise RuntimeError(f"refusing to write secret-like value to {path.name}")
        atomic_write(path, content, 0o644)
    return list(managed)


def ensure_git_repo(repo: Path) -> bool:
    if (repo / ".git").exists():
        return True
    if repo.exists() and any(repo.iterdir()):
        return False
    repo.mkdir(parents=True, exist_ok=True)
    result = run(["git", "init", "-b", "main", str(repo)])
    if result.returncode != 0:
        result = run(["git", "init", str(repo)])
    return result.returncode == 0


def commit_machine_snapshot(repo: Path, paths: list[Path]) -> tuple[bool, str]:
    relative = [str(path.relative_to(repo)) for path in paths]
    add = run(["git", "-C", str(repo), "add", "--", *relative])
    if add.returncode != 0:
        return False, "git-add-failed"
    if not git(repo, "status", "--porcelain", "--", *relative):
        return False, "unchanged"
    commit = run([
        "git", "-C", str(repo), "-c", "user.name=Boss", "-c", "user.email=boss@localhost",
        "commit", "-m", "chore(boss): refresh machine brain",
    ])
    return commit.returncode == 0, "committed" if commit.returncode == 0 else "git-commit-failed"


def save_machine_config(machine: dict[str, str]) -> None:
    cfg = config()
    previous = cfg.get("machine") if isinstance(cfg.get("machine"), dict) else {}
    cfg["machine"] = {**previous, **{key: machine[key] for key in ("name", "path", "remote")}}
    write_json(runtime_home() / "config.json", cfg)


def ensure_machine_initialized() -> None:
    cfg = config().get("machine") if isinstance(config().get("machine"), dict) else {}
    if cfg.get("auto_init", True) is False:
        return
    machine = machine_defaults()
    repo = Path(machine["path"])
    if (repo / ".git").exists():
        return
    if not ensure_git_repo(repo):
        return
    save_machine_config(machine)
    with contextlib.suppress(OSError, RuntimeError):
        paths = write_machine_snapshot(repo, machine)
        commit_machine_snapshot(repo, paths)


def cmd_machine_init(args: argparse.Namespace) -> int:
    machine = machine_defaults()
    if args.name:
        machine["name"] = safe_slug(args.name)
    if args.path:
        machine["path"] = str(Path(args.path).expanduser().resolve())
    elif args.name:
        machine["path"] = str(Path.home() / machine["name"])
    if args.remote:
        machine["remote"] = safe_remote(args.remote)
    repo = Path(machine["path"])
    if not ensure_git_repo(repo):
        print(f"refusing to initialize non-empty non-Git directory: {repo}", file=sys.stderr)
        return 2
    if machine["remote"]:
        current = origin_url(repo)
        if not current:
            result = run(["git", "-C", str(repo), "remote", "add", "origin", machine["remote"]])
            if result.returncode != 0:
                print("failed to add remote", file=sys.stderr)
                return 2
    patrol(force=True)
    save_machine_config(machine)
    try:
        paths = write_machine_snapshot(repo, machine)
    except RuntimeError:
        print("machine snapshot refused because secret-like content was detected", file=sys.stderr)
        return 2
    committed, status = commit_machine_snapshot(repo, paths)
    print(f"machine={machine['name']} path={repo} snapshot={status}")
    if args.create_remote:
        owner = owner_name()
        if not owner or not shutil.which("gh"):
            print("remote creation requires ~/.boss/owner and an authenticated gh CLI", file=sys.stderr)
            return 2
        created = run(["gh", "repo", "create", f"{owner}/{machine['name']}", "--private", "--source", str(repo), "--remote", "origin", "--push"], timeout=120)
        if created.returncode != 0:
            print("GitHub machine repository creation failed", file=sys.stderr)
            return 1
        machine["remote"] = safe_remote(origin_url(repo))
        save_machine_config(machine)
    if args.timer:
        timer_result = install_machine_timer(args.interval)
        if timer_result != 0:
            return timer_result
    if args.push:
        return push_machine(repo)
    return 0 if committed or status == "unchanged" else 1


def push_machine(repo: Path) -> int:
    remote = origin_url(repo)
    if not remote:
        print("machine brain is local; configure a remote before push")
        return 1
    upstream = git(repo, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}")
    branch = git(repo, "branch", "--show-current") or "main"
    command = ["git", "-C", str(repo), "push"] if upstream else ["git", "-C", str(repo), "push", "-u", "origin", branch]
    result = run(command, timeout=60)
    if result.returncode != 0:
        print("machine brain push failed; credentials or remote permissions need attention", file=sys.stderr)
        return 1
    print("machine brain pushed")
    return 0


def cmd_machine_sync(args: argparse.Namespace) -> int:
    machine = machine_defaults()
    repo = Path(machine["path"])
    if not (repo / ".git").exists():
        print("machine brain is not initialized; run boss machine init", file=sys.stderr)
        return 2
    patrol(force=True)
    try:
        paths = write_machine_snapshot(repo, machine)
    except RuntimeError:
        print("machine snapshot refused because secret-like content was detected", file=sys.stderr)
        return 2
    _committed, status = commit_machine_snapshot(repo, paths)
    print(f"snapshot={status}")
    return push_machine(repo) if args.push else (0 if status in ("committed", "unchanged") else 1)


def install_machine_timer(interval: int, dry_run: bool = False) -> int:
    if interval < 5:
        print("timer interval must be at least 5 minutes", file=sys.stderr)
        return 2
    unit_dir = Path.home() / ".config" / "systemd" / "user"
    service = unit_dir / "boss-machine-sync.service"
    timer = unit_dir / "boss-machine-sync.timer"
    command = f'{sys.executable} "{Path(__file__).resolve()}" machine sync --push'
    service_text = (
        "[Unit]\nDescription=Refresh and push the Boss machine brain\n\n"
        "[Service]\nType=oneshot\n"
        f"ExecStart={command}\n"
    )
    timer_text = (
        "[Unit]\nDescription=Periodic Boss machine brain sync\n\n"
        "[Timer]\nOnBootSec=5m\n"
        f"OnUnitActiveSec={interval}m\nPersistent=true\n\n"
        "[Install]\nWantedBy=timers.target\n"
    )
    if dry_run:
        print(f"would write {service} and {timer}")
        return 0
    atomic_write(service, service_text, 0o644)
    atomic_write(timer, timer_text, 0o644)
    daemon = run(["systemctl", "--user", "daemon-reload"])
    enable = run(["systemctl", "--user", "enable", "--now", timer.name])
    if daemon.returncode or enable.returncode:
        print("timer files installed but systemd user timer could not be enabled", file=sys.stderr)
        return 1
    print(f"machine sync timer enabled every {interval} minutes")
    return 0


def cmd_machine_timer(args: argparse.Namespace) -> int:
    return install_machine_timer(args.interval, args.dry_run)


def read_machine_projects(repo: Path) -> list[dict[str, str]]:
    path = repo / "projects.tsv"
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    if not lines:
        return []
    header = lines[0].split("\t")
    values: list[dict[str, str]] = []
    for line in lines[1:]:
        parts = line.split("\t")
        parts.extend([""] * (len(header) - len(parts)))
        values.append(dict(zip(header, parts)))
    return values


def cmd_machine_restore(args: argparse.Namespace) -> int:
    repo = Path(args.repository).expanduser().resolve()
    metadata = read_json(repo / "machine.json", {})
    restored_owner = str(metadata.get("project_owner") or "").strip()
    if restored_owner and not owner_name():
        atomic_write(runtime_home() / "owner", restored_owner + "\n")
    projects = read_machine_projects(repo)
    if not projects:
        print("no projects.tsv found in machine brain", file=sys.stderr)
        return 2
    restored: list[Path] = []
    unresolved: list[str] = []
    existing_by_remote = {safe_remote(origin_url(Path(row["path"]))): Path(row["path"]) for row in read_registry() if Path(row["path"]).is_dir()}
    for item in projects:
        remote = safe_remote(item.get("origin", ""))
        current = existing_by_remote.get(remote) if remote else None
        if current:
            restored.append(current)
            continue
        target = Path(args.destination).expanduser() / safe_slug(item.get("name", "project"))
        if args.clone and remote and not target.exists():
            result = run(["git", "clone", remote, str(target)], timeout=120)
            if result.returncode == 0:
                restored.append(target.resolve())
                continue
        unresolved.append(item.get("name", "unknown"))
    if restored:
        register_rows(restored, require_qualification=False)
    print(f"restored={len(restored)} unresolved={len(unresolved)}")
    for name in unresolved:
        print(f"UNRESOLVED {name}")
    return 0 if not unresolved else 1


def cmd_vault_ref(args: argparse.Namespace) -> int:
    path = runtime_home() / "vault-refs.tsv"
    if not args.key:
        try:
            print(path.read_text(encoding="utf-8"), end="")
        except OSError:
            print("# project\tkey\tpurpose")
        return 0
    fields = [args.key, args.project or "machine", args.purpose or ""]
    if (
        TOKEN_RE.search(args.key)
        or any(char.isspace() for char in args.key)
        or "=" in args.key
        or any(not safe_record_field(field) for field in fields)
    ):
        print("refusing secret-like or malformed key name", file=sys.stderr)
        return 2
    rows: list[list[str]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        lines = []
    for line in lines:
        if line and not line.startswith("#"):
            parts = line.split("\t")
            parts.extend([""] * (3 - len(parts)))
            rows.append(parts[:3])
    value = [args.project or "machine", args.key, args.purpose or ""]
    if not any(row[0] == value[0] and row[1] == value[1] for row in rows):
        rows.append(value)
    atomic_write(path, table_text(["# project", "key", "purpose"], rows))
    print(f"recorded Vault reference {args.key}; no credential value stored")
    return 0


def merge_registry(sources: list[Path]) -> str:
    ordered: dict[str, list[str]] = {}
    for source in sources:
        try:
            lines = source.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.split("\t")
            parts.extend([""] * (5 - len(parts)))
            if parts[0] and parts[1]:
                ordered.setdefault(parts[0], parts[:5])
    header = "# path\tname\taliases\tsummary\tkind(local|remote|ref)"
    return "\n".join([header, *["\t".join(parts) for parts in ordered.values()]]) + "\n"


def migration_plan(home: Path) -> list[tuple[Path, Path]]:
    target = runtime_home()
    old_brain = home / ".project-brains"
    pairs: list[tuple[Path, Path]] = []
    if (old_brain / "registry.tsv").exists():
        pairs.append((old_brain / "registry.tsv", target / "registry.tsv"))
    return pairs


def cmd_migrate(args: argparse.Namespace) -> int:
    home = Path.home()
    target = runtime_home()
    pairs = migration_plan(home)
    if args.dry_run:
        print(f"target: {target}")
        for source, dest in pairs:
            print(f"copy: {source} -> {dest}")
        print("preserve: existing ~/.boss data and all project .brain directories")
        print("skip: token and credential values are never copied")
        return 0
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = target / "backups" / f"migration-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    target.mkdir(parents=True, exist_ok=True)
    for name in ("registry.tsv", "config.json"):
        source = target / name
        if source.exists():
            shutil.copy2(source, backup / name)
    sources = [target / "registry.tsv", home / ".project-brains" / "registry.tsv"]
    registry = merge_registry(sources)
    if registry.count("\n") > 1:
        atomic_write(target / "registry.tsv", registry)
    cfg = config()
    if (home / ".boss").exists() or (home / ".project-brains").exists():
        cfg["policy"] = args.policy or "strict"
    write_json(target / "config.json", cfg)
    write_json(target / "migration.json", {"at": now_iso(), "from": [".project-brains"], "backup": str(backup)})
    print(f"migrated in place at {target}; project brains preserved; credentials skipped")
    return 0


def cmd_policy(args: argparse.Namespace) -> int:
    cfg = config()
    if args.value:
        cfg["policy"] = args.value
        write_json(runtime_home() / "config.json", cfg)
    print(cfg["policy"])
    return 0


def cmd_explain(args: argparse.Namespace) -> int:
    value = read_json(state_home() / "last-context.json", {})
    if args.json:
        print(json.dumps(value, ensure_ascii=False, indent=2))
        return 0
    if not value:
        print("No Boss context has been injected yet.")
        return 0
    print(f"EVENT    {value.get('event') or '-'}")
    print(f"MODE     {value.get('mode') or '-'} ({value.get('confidence') or 'unknown'} confidence)")
    print(f"PROJECT  {value.get('project') or '-'}")
    print(f"CONTENT  {value.get('content_policy') or '-'}")
    print(f"SECTIONS {', '.join(value.get('sections') or []) or '-'}")
    print(f"CHARS    {value.get('chars') or 0}")
    print(f"AT       {value.get('at') or '-'}")
    if args.show:
        preview = state_home() / "last-context-preview.txt"
        print("--- redacted context preview ---")
        try:
            print(preview.read_text(encoding="utf-8"), end="")
        except OSError:
            print("(preview unavailable)")
    return 0


def scan_secrets(root: Path) -> list[Path]:
    matches: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if TOKEN_RE.search(text):
            matches.append(path)
    return matches


def cmd_doctor(args: argparse.Namespace) -> int:
    checks: list[dict[str, Any]] = []
    home = runtime_home()
    checks.append({"name": "runtime-home", "ok": home.is_dir(), "detail": str(home)})
    checks.append({"name": "policy", "ok": config()["policy"] in POLICIES, "detail": config()["policy"]})
    rows = read_registry()
    checks.append({"name": "registry", "ok": bool(rows), "detail": f"{len(rows)} projects"})
    plugin_root = Path(os.environ.get("PLUGIN_ROOT") or os.environ.get("CLAUDE_PLUGIN_ROOT") or Path(__file__).resolve().parents[1])
    secret_matches = scan_secrets(plugin_root)
    checks.append({"name": "secret-scan", "ok": not secret_matches, "detail": f"{len(secret_matches)} matching files"})
    checks.append({"name": "git", "ok": bool(shutil.which("git")), "detail": shutil.which("git") or "missing"})
    if args.json:
        print(json.dumps(checks, ensure_ascii=False, indent=2))
    else:
        for check in checks:
            print(f"{'PASS' if check['ok'] else 'FAIL'} {check['name']}: {check['detail']}")
    return 0 if all(check["ok"] for check in checks) else 1


def cmd_adopt(args: argparse.Namespace) -> int:
    root = git_root(args.path)
    if not root:
        print("not a Git repository", file=sys.stderr)
        return 2
    rows = read_registry()
    if any(Path(row["path"]).resolve() == root for row in rows):
        print(f"already managed: {root}")
        return 0
    name = args.name or root.name
    fields = [str(root), name, args.aliases or "", args.summary or "", args.kind]
    if any(not safe_record_field(field) for field in fields):
        print("refusing secret-like or malformed project metadata", file=sys.stderr)
        return 2
    line = "\t".join([str(root), name, args.aliases or "", args.summary or "", args.kind])
    path = runtime_home() / "registry.tsv"
    existing = merge_registry([registry_path()]).rstrip("\n")
    atomic_write(path, existing + "\n" + line + "\n")
    print(f"adopted {name}: {root}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="boss", description="Machine control and portable project continuity")
    result.add_argument("--version", action="version", version=f"boss {VERSION}")
    subs = result.add_subparsers(dest="command", required=True)
    hook = subs.add_parser("hook")
    hook.add_argument("event", choices=("session-start", "prompt-submit", "stop"))
    hook.set_defaults(func=cmd_hook)
    for name, func in (("projects", cmd_projects), ("status", cmd_status), ("caps", cmd_caps), ("risk", cmd_risk)):
        item = subs.add_parser(name)
        item.set_defaults(func=func)
    explain = subs.add_parser("explain")
    explain_output = explain.add_mutually_exclusive_group()
    explain_output.add_argument("--json", action="store_true")
    explain_output.add_argument("--show", action="store_true")
    explain.set_defaults(func=cmd_explain)
    scan = subs.add_parser("scan")
    scan.add_argument("--adopt", action="store_true")
    scan.add_argument("--json", action="store_true")
    scan.set_defaults(func=cmd_scan)
    machine = subs.add_parser("machine")
    machine_subs = machine.add_subparsers(dest="machine_command", required=True)
    machine_init = machine_subs.add_parser("init")
    machine_init.add_argument("--name")
    machine_init.add_argument("--path")
    machine_init.add_argument("--remote")
    machine_init.add_argument("--create-remote", action="store_true")
    machine_init.add_argument("--push", action="store_true")
    machine_init.add_argument("--timer", action="store_true")
    machine_init.add_argument("--interval", type=int, default=15)
    machine_init.set_defaults(func=cmd_machine_init)
    machine_sync = machine_subs.add_parser("sync")
    machine_sync.add_argument("--push", action="store_true")
    machine_sync.set_defaults(func=cmd_machine_sync)
    machine_timer = machine_subs.add_parser("timer-install")
    machine_timer.add_argument("--interval", type=int, default=15)
    machine_timer.add_argument("--dry-run", action="store_true")
    machine_timer.set_defaults(func=cmd_machine_timer)
    machine_restore = machine_subs.add_parser("restore")
    machine_restore.add_argument("repository")
    machine_restore.add_argument("--clone", action="store_true")
    machine_restore.add_argument("--destination", default=str(Path.home()))
    machine_restore.set_defaults(func=cmd_machine_restore)
    vault_ref = subs.add_parser("vault-ref")
    vault_ref.add_argument("key", nargs="?")
    vault_ref.add_argument("--project")
    vault_ref.add_argument("--purpose")
    vault_ref.set_defaults(func=cmd_vault_ref)
    migrate = subs.add_parser("migrate")
    migrate.add_argument("--dry-run", action="store_true")
    migrate.add_argument("--policy", choices=POLICIES)
    migrate.set_defaults(func=cmd_migrate)
    policy = subs.add_parser("policy")
    policy.add_argument("value", nargs="?", choices=POLICIES)
    policy.set_defaults(func=cmd_policy)
    doctor = subs.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=cmd_doctor)
    adopt = subs.add_parser("adopt")
    adopt.add_argument("path", nargs="?", default=".")
    adopt.add_argument("--name")
    adopt.add_argument("--aliases")
    adopt.add_argument("--summary")
    adopt.add_argument("--kind", choices=("local", "remote", "ref"), default="local")
    adopt.set_defaults(func=cmd_adopt)
    return result


def main() -> int:
    args = parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
