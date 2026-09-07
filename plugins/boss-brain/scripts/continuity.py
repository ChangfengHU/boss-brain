"""Versioned continuity storage. No network calls and no generated business facts."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlsplit

PROTOCOL = 2
BEGIN = '<!-- boss-brain:begin (managed block, do not edit inside) -->'
END = '<!-- boss-brain:end -->'
LEGACY_BEGIN = '<!-- project-brains:begin (managed block, do not edit inside) -->'
LEGACY_END = '<!-- project-brains:end -->'
ASSETS = Path(__file__).resolve().parents[1] / 'assets'
DOCUMENTS = {
    'state': 'STATE.md', 'tasks': 'TASKS.md', 'handoff': 'HANDOFF.md',
    'evidence': 'evidence.jsonl', 'dev_log': 'dev-log', 'wiki': 'wiki',
    'conventions': 'conventions', 'capabilities': 'capabilities.tsv',
}


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    if path.stat().st_size > 1024 * 1024:
        raise ValueError('metadata exceeds 1 MiB limit')
    value = json.loads(path.read_text(encoding='utf-8'))
    return value


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError('refusing symlink write')
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temporary)


def write_json(path: Path, value) -> None:
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + '\n')


@contextlib.contextmanager
def lock(path: Path):
    # Linux is the tested target. Keep a stable inode; never unlink lock files.
    import fcntl
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(fd)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                            text=True, timeout=5, check=False)
    return result.stdout.strip() if result.returncode == 0 else ''


def github_identity(remote: str) -> str:
    if remote.startswith('git@github.com:'):
        path = remote[len('git@github.com:'):]
    else:
        parsed = urlsplit(remote)
        if parsed.hostname != 'github.com' or parsed.scheme not in ('https', 'ssh'):
            return ''
        path = parsed.path.lstrip('/')
    path = path.removesuffix('.git').rstrip('/')
    return path if re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', path) else ''


def document(root: Path, key: str) -> Path:
    """Resolve declared documents inside the repo; malformed manifests fail closed."""
    root = root.resolve()
    manifest_path = root / '.brain/manifest.json'
    if not manifest_path.resolve().is_relative_to(root):
        raise ValueError('Brain manifest escapes owning repository')
    manifest = read_json(manifest_path, {})
    if not isinstance(manifest, dict):
        raise ValueError('invalid Brain manifest')
    if not isinstance(manifest.get('documents', {}), dict):
        raise ValueError('invalid document map')
    relative = manifest.get('documents', {}).get(key, '.brain/' + DOCUMENTS[key])
    if not isinstance(relative, str) or Path(relative).is_absolute():
        raise ValueError('document path must be relative')
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError('document path escapes owning repository')
    return path


def brain_init(root: Path, runtime: Path, *, dry_run=False) -> dict:
    root = root.resolve()
    if git(root, 'rev-parse', '--show-toplevel') != str(root):
        raise ValueError('project is not a Git root')
    identity = github_identity(git(root, 'remote', 'get-url', 'origin'))
    if not identity:
        return {'project': str(root), 'status': 'skipped', 'reason': 'no-github-origin'}
    if (root / '.brain-home').exists():
        return {'project': str(root), 'status': 'delegated', 'reason': 'preserved-brain-home; verify owner before initialization'}
    if (root / '.brain').is_symlink():
        raise ValueError('Brain symlink needs explicit owner review')
    if git(root, 'check-ignore', '.brain/manifest.json'):
        raise ValueError('Brain is Git-ignored; cannot promise portable memory')
    manifest_path = root / '.brain/manifest.json'
    if manifest_path.is_symlink():
        raise ValueError('Brain manifest symlink needs explicit owner review')
    existing = read_json(manifest_path, {})
    if existing:
        if existing.get('schema') != PROTOCOL or not isinstance(existing.get('documents'), dict):
            raise ValueError('unsupported Brain manifest; migration required')
        for key in DOCUMENTS:
            document(root, key)
        if existing.get('repository') != identity:
            raise ValueError('repository identity changed; review before rebinding')
        return {'project': str(root), 'status': 'existing', 'content': existing.get('content_status', 'needs-review')}
    documents = {}
    for key, filename in DOCUMENTS.items():
        candidates = [root / '.brain' / filename, root / filename]
        found = next((path for path in candidates if path.exists()), candidates[0])
        if not found.resolve().is_relative_to(root):
            raise ValueError('existing document points outside repository')
        documents[key] = str(found.relative_to(root))
    if not (root / documents['conventions']).exists() and (root / 'CONVENTIONS.md').is_file():
        documents['conventions'] = 'CONVENTIONS.md'
    manifest = {'schema': PROTOCOL, 'repository': identity, 'content_status': 'needs-review',
                'documents': documents,
                'pending': ['Verify goals, decisions, tasks and runtime; do not infer completion from initialization.']}
    if not dry_run:
        with lock(runtime / 'locks' / (digest(str(root)) + '.lock')):
            if manifest_path.exists():
                return brain_init(root, runtime, dry_run=True)
            write_json(manifest_path, manifest)
            state = root / documents['state']
            if not state.exists():
                atomic_write(state, '# Project state\n\n## Verified inventory\n\n'
                             f'- GitHub repository: `{identity}`\n'
                             '- Brain entry initialized; business state has not been verified.\n\n'
                             '## Next action\n\nReview existing documentation and the user-confirmed task before development.\n')
    return {'project': str(root), 'status': 'would-initialize' if dry_run else 'initialized', 'content': 'needs-review'}


def block_in(text: str) -> tuple[str, str]:
    found = []
    for begin, end in ((BEGIN, END), (LEGACY_BEGIN, LEGACY_END)):
        if text.count(begin) != text.count(end) or text.count(begin) > 1:
            raise ValueError('malformed or duplicate global directive markers')
        if begin in text:
            start, stop = text.index(begin), text.index(end)
            if stop < start:
                raise ValueError('reversed global directive markers')
            found.append((text[start:stop + len(end)], begin))
    if len(found) > 1:
        raise ValueError('both legacy and current blocks exist; review required')
    return found[0] if found else ('', '')


def manage_rules(home: Path, runtime: Path, *, dry_run=False, restore=False) -> list[dict]:
    template = (ASSETS / 'global-directives.md').read_text(encoding='utf-8').strip()
    desired = BEGIN + '\n' + template + '\n' + END
    codex = Path(os.environ.get('CODEX_HOME', str(home / '.codex')))
    targets = [codex / 'AGENTS.md']
    if (home / '.claude').exists():
        targets.append(home / '.claude/CLAUDE.md')
    results = []
    for target in targets:
        try:
            if target.is_symlink():
                raise ValueError('global directives symlink needs explicit review')
            original = target.read_text(encoding='utf-8') if target.exists() else ''
            old, marker = block_in(original)
            record = runtime / 'directives' / (digest(str(target)) + '.json')
            saved = read_json(record, {})
            if saved and old != saved['installed_block']:
                raise ValueError('managed block changed by user; refusing overwrite')
            if restore:
                if not saved:
                    results.append({'target': str(target), 'status': 'unmanaged'})
                    continue
                replacement = saved['original_block']
            else:
                if old and not saved and marker == LEGACY_BEGIN:
                    legacy = (ASSETS / 'legacy-directives.md').read_text(encoding='utf-8').strip()
                    body = old[len(LEGACY_BEGIN):-len(LEGACY_END)].strip()
                    if body != legacy:
                        raise ValueError('unknown or edited legacy rules; review required')
                elif old and not saved and old != desired:
                    raise ValueError('unrecognized managed block; review required')
                replacement = desired
            updated = original.replace(old, replacement, 1) if old else original + ('\n' if original and not original.endswith('\n') else '') + replacement + '\n'
            if not dry_run:
                with lock(runtime / 'locks' / 'directives.lock'):
                    current = target.read_text(encoding='utf-8') if target.exists() else ''
                    if current != original:
                        raise ValueError('global directives changed concurrently')
                    if not restore:
                        if not saved:
                            saved = {'target': str(target), 'original_block': old, 'original_file': original}
                        saved['installed_block'] = desired
                        # Backup is written first. An interrupted update fails closed on retry.
                        write_json(record, saved)
                    if updated != original:
                        atomic_write(target, updated)
                    if restore:
                        record.unlink()
            results.append({'target': str(target), 'status': 'unchanged' if updated == original else ('planned' if dry_run else 'restored' if restore else 'installed')})
        except (OSError, ValueError, KeyError) as exc:
            results.append({'target': str(target), 'status': 'blocked', 'reason': str(exc)})
    return results
