"""Opt-in local event viewer. Never performs network calls or project writes."""
import hashlib
import itertools
import json
from pathlib import Path
import re
import time

MODES = ('off', 'summary', 'detail')


def redact(text):
    # The ordinary context redactor handles provider prefixes. This extra layer
    # protects arbitrary credentials and terminal control sequences in documents.
    text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?(?:-----END [^-]*PRIVATE KEY-----|\Z)',
                  '[REDACTED_PRIVATE_KEY]', text, flags=re.S)
    text = re.sub(r'(?i)\b(Bearer|Basic)\s+[A-Za-z0-9+/_.=:-]+', r'\1 [REDACTED]', text)
    text = re.sub(r'(?im)(["\']?(?:[\w-]*(?:token|secret|password|api[_-]?key|cookie|authorization))["\']?\s*[:=]\s*)[^\n,}]+',
                  r'\1[REDACTED]', text)
    text = re.sub(r'(https?://)[^/\s:@]+:[^/\s@]+@', r'\1[REDACTED]@', text)
    return ''.join(c for c in text if c in '\n\t' or ord(c) >= 32 and ord(c) != 127)


def settings(boss):
    path = boss.runtime_home() / 'display.json'
    if path.is_symlink():
        raise ValueError('显示配置不能是符号链接')
    value = json.loads(path.read_text()) if path.exists() else {}
    if not isinstance(value, dict) or any(k not in ('sessions', 'projects') for k in value):
        raise ValueError('显示配置损坏，未覆盖')
    for scope in ('sessions', 'projects'):
        items = value.get(scope, {})
        if not isinstance(items, dict) or any(not isinstance(k, str) or v not in MODES for k, v in items.items()):
            raise ValueError('显示配置损坏，未覆盖')
    return value


def sanitized(boss, value):
    if isinstance(value, str):
        return redact(boss.redact_secrets(value))
    if isinstance(value, list):
        return [sanitized(boss, item) for item in value]
    if isinstance(value, dict):
        return {sanitized(boss, key): sanitized(boss, item) for key, item in value.items()}
    return value


def level(boss, sid, paths):
    cfg = settings(boss)
    override = cfg.get('sessions', {}).get(sid)
    if override is not None:
        return override
    # Only grounded task/workspace projects select display policy; incidental
    # capability matches must not turn a user's detailed logging on.
    values = [cfg.get('projects', {}).get(str(Path(p).resolve()), 'off') for p in paths]
    return max(values, key=MODES.index, default='off')


def command_display(boss, args):
    cfg = settings(boss)
    scope, key = 'sessions', args.session
    if args.project:
        matches = [r for r in boss.read_registry() if args.project in boss.row_names(r)
                   or Path(args.project).resolve() == Path(r['path']).resolve()]
        if len(matches) != 1:
            raise ValueError('项目未知或有歧义；请先确认已登记的名称')
        scope, key = 'projects', str(Path(matches[0]['path']).resolve())
    if args.value:
        with boss.continuity.lock(boss.runtime_home() / 'locks/display.lock'):
            cfg = settings(boss)
            group = cfg.setdefault(scope, {})
            if args.value == 'inherit':
                group.pop(key, None)
            else:
                group[key] = args.value
            boss.write_json(boss.runtime_home() / 'display.json', cfg)
    print(json.dumps({'scope': scope, 'target': key, 'override': cfg.get(scope, {}).get(key, 'inherit'),
                      'default': 'off', 'viewer': 'boss events --session SESSION --follow',
                      'note': '仅控制执行观察；不改变上下文、旧 receipt 或审计策略'}, ensure_ascii=False))
    return 0


def snapshot(boss, paths):
    result = {}
    deadline = time.monotonic() + 2
    bytes_left = 1048576
    for raw in sorted(set(paths))[:8]:
        if time.monotonic() > deadline:
            result[raw] = {'unavailable': 'observation-time-budget'}
            continue
        root = Path(raw)
        if not (root / '.git').exists():
            result[raw] = {'unavailable': 'not-a-local-repository; remote work requires remote observer'}
            continue
        item = {'documents': {}, 'head': boss.git(root, 'rev-parse', 'HEAD', timeout=1)}
        for kind in ('dev_log', 'wiki', 'tasks', 'handoff'):
            path = boss.continuity.document(root, kind)
            files = sorted(itertools.islice(path.rglob('*.md'), 129)) if path.is_dir() else [path]
            values = {}
            for file in files[:128]:
                if not file.is_file() or file.is_symlink() or not file.resolve().is_relative_to(root.resolve()):
                    continue
                size = file.stat().st_size
                if size > 262144 or size > bytes_left or time.monotonic() > deadline:
                    values[str(file.relative_to(root))] = 'omitted:observation-budget'
                else:
                    values[str(file.relative_to(root))] = hashlib.sha256(file.read_bytes()).hexdigest()
                    bytes_left -= size
            item['documents'][kind] = {'files': values, 'limited': len(files) > 128}
        item['dirty'] = boss.git(root, 'status', '--porcelain', timeout=1)[:10000]
        upstream = boss.git(root, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}', timeout=1)
        item['upstream'] = upstream
        item['ahead'] = boss.git(root, 'rev-list', '--count', f'{upstream}..HEAD', timeout=1) if upstream else None
        result[raw] = item
    return result


def event_path(boss, sid):
    return boss.state_home() / 'events' / (boss.continuity.digest(sid) + '.json')


def observe(boss, payload, event, raw):
    sid = str(payload.get('session_id') or 'nosid')
    if boss.session_mode(sid) != 'enabled' or payload.get('stop_hook_active'):
        return raw
    session = boss.load_session(sid)
    paths = set(session.get('roots', {}))
    paths.update(session.get('contracts', {}).get(session.get('focus_task'), {}).get('projects', []))
    root = boss.git_root(Path(str(payload.get('cwd') or '.')))
    if root:
        paths.add(str(root))
    mode = level(boss, sid, paths)
    if mode == 'off':
        return raw
    output = json.loads(raw) if raw.strip() else {}
    body = output.get('hookSpecificOutput', {}).get('additionalContext', '')
    context = session.get('last_context', {}) if event != 'stop' else {}
    current = snapshot(boss, paths)
    previous = session.get('observation_snapshot', {})
    documents = []
    for path, project in current.items():
        for kind, record in project.get('documents', {}).items():
            before = previous.get(path, {}).get('documents', {}).get(kind)
            changed = [] if before is None else sorted(k for k in set(before['files']) | set(record['files'])
                                                    if before['files'].get(k) != record['files'].get(k))
            documents.append({'project': path, 'kind': kind, 'changed_files': changed,
                              'status': 'observed-change' if changed else 'baseline-established' if before is None else 'no-change',
                              'reason': '字节差异证据，不证明作者或语义正确' if changed else
                                        '首次观察，不能推断此前是否写入' if before is None else
                                        '两次观察间无变化；Hook 不自动撰写文档',
                              'limited': record['limited'], 'hashes': record['files']})
    entry = {'at': boss.now_iso(), 'event': event, 'session': sid, 'mode': mode,
             'context': context, 'context_body': body if mode == 'detail' else '',
             'context_chars': len(body), 'documents': documents, 'repositories': current,
             'knowledge': [{'id': i['id'], 'status': i['status'], 'kind': i.get('kind')}
                           for i in boss.knowledge_reviews(sid)],
             'decision': output.get('decision', 'no-block'), 'reason': output.get('reason', ''),
             'host_display': 'requested-not-confirmed', 'push_evidence': 'local-tracking-ref-only; no network in hooks'}
    if event == 'stop':
        audit = boss.state_home() / 'audit.jsonl'
        if audit.is_file():
            with audit.open('rb') as handle:
                handle.seek(max(0, audit.stat().st_size - 65536))
                lines = handle.read().decode('utf-8', errors='replace').splitlines()
            for line in reversed(lines):
                try:
                    finding = json.loads(line)
                except ValueError:
                    continue
                if finding.get('session') == sid:
                    entry['audit'] = finding
                    break
    # Redact before both persistence and terminal/host output.
    entry = sanitized(boss, entry)
    path = event_path(boss, sid)
    with boss.continuity.lock(boss.runtime_home() / 'locks' / ('events-' + boss.continuity.digest(sid) + '.lock')):
        entries = boss.read_json(path, [])
        entry['sequence'] = entries[-1]['sequence'] + 1 if entries else 1
        entries.append(entry)
        boss.write_json(path, entries[-40:])
    session['observation_snapshot'] = sanitized(boss, current)
    boss.save_session(sid, session)
    notice = render(entry, detail=mode == 'detail')
    output['systemMessage'] = (output.get('systemMessage', '') + '\n' + notice).strip()
    return json.dumps(output, ensure_ascii=False)


def render(entry, detail=False):
    context = entry.get('context', {})
    lines = [f"Boss #{entry.get('sequence', '-')} {entry['at']} {entry['event']} ({entry['mode']})",
             f"上下文输出 {entry['context_chars']} 字符；{context.get('injection', {}).get('reason', 'not-a-context-event')}",
             '截断：' + ', '.join(context.get('truncated_sections', [])),
             '宿主显示：仅请求，未确认；本 events 查看器直接输出真实记录。']
    for doc in entry['documents']:
        lines.append(f"{doc['project']} {doc['kind']}: {doc['status']} — {doc['reason']}")
        lines.extend('  ' + name for name in doc['changed_files'])
    for path, repo in entry['repositories'].items():
        lines.append(f"Git {path}: HEAD={repo.get('head', '-')} upstream={repo.get('upstream') or '-'} ahead={repo.get('ahead', '-')} (仅本地引用，未联网确认 push)")
        if repo.get('unavailable'):
            lines.append(repo['unavailable'])
    for finding in entry.get('audit', {}).get('findings', []):
        lines.append(f"审计 {finding['code']}: {finding['message']}")
    lines.append('结束决策：' + entry['decision'])
    lines.extend(f"知识审阅 {i['id']}: {i['status']}" for i in entry['knowledge'])
    if detail:
        lines.extend(['实际 Hook 上下文正文（脱敏）：', entry['context_body'],
                      '上下文来源/路由元数据：', json.dumps(context, ensure_ascii=False)])
    return '\n'.join(lines)


def command_events(boss, args):
    seen = 0
    try:
        while True:
            entries = boss.read_json(event_path(boss, args.session), [])
            fresh = [e for e in entries[-args.limit:] if e['sequence'] > seen]
            for entry in fresh:
                print(json.dumps(entry, ensure_ascii=False) if args.json else render(entry, args.detail), flush=True)
                seen = entry['sequence']
            if not args.follow:
                if not entries and not args.json:
                    print('暂无执行记录；需要先为会话或项目开启 boss display。历史事件不会追造。')
                return 0
            time.sleep(1)
    except KeyboardInterrupt:
        return 0
