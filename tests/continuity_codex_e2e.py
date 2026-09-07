#!/usr/bin/env python3
"""Real Codex acceptance, isolated HOME, two synthetic projects, no business writes.

Run explicitly with CODEX_AUTH_SOURCE pointing at existing auth. Credentials remain
in a permission-restricted temporary directory and are never included in output.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    auth = Path(os.environ.get('CODEX_AUTH_SOURCE', ''))
    codex = shutil.which('codex')
    if not auth.is_file() or not codex:
        raise RuntimeError('CODEX_AUTH_SOURCE and Codex CLI required')
    with tempfile.TemporaryDirectory(prefix='boss-v2-codex-') as directory:
        home = Path(directory)
        cfg = home / '.codex'
        cfg.mkdir(mode=0o700)
        shutil.copyfile(auth, cfg / 'auth.json')
        (cfg / 'auth.json').chmod(0o600)
        env = {**os.environ, 'HOME': str(home), 'CODEX_HOME': str(cfg),
               'BOSS_HOME': str(home / '.boss'), 'BOSSBRAIN_STATE_DIR': str(home / '.boss/state'),
               'BOSS_SKIP_PLUGIN_CLI': '1', 'PATH': str(home / '.local/bin') + os.pathsep + os.environ['PATH']}

        def run(args, cwd=home, timeout=90):
            result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
            if result.returncode:
                # Never echo subprocess streams: they can include host credentials/config.
                raise RuntimeError(f'{Path(args[0]).name} exited {result.returncode}')
            return result.stdout

        run([sys.executable, str(ROOT / 'scripts/install.py'), 'install', '--owner', 'fixture-owner'])
        boss = [sys.executable, str(home / '.boss/distribution/plugins/boss-brain/scripts/boss.py')]
        run([*boss, 'init', '--rules-only'])
        # This global instruction is deliberately outside the managed block.
        with (cfg / 'AGENTS.md').open('a') as stream:
            stream.write('\nUser test preference: global_marker is GLOBAL_K82Q.\n')
        projects = []
        for name, marker in [('workflow-fixture', 'WORKFLOW_N93R'), ('browser-fixture', 'BROWSER_F62P')]:
            repo = home / name
            repo.mkdir()
            for args in [('init', '-b', 'main'), ('config', 'user.name', 'Fixture'),
                         ('config', 'user.email', 'fixture@example.invalid')]:
                run(['git', '-C', str(repo), *args])
            (repo / 'README.md').write_text('Synthetic plugin acceptance fixture.\n')
            run(['git', '-C', str(repo), 'add', 'README.md'])
            run(['git', '-C', str(repo), 'commit', '-m', 'fixture'])
            run(['git', '-C', str(repo), 'remote', 'add', 'origin', f'https://github.com/fixture-owner/{name}.git'])
            run([*boss, 'adopt', str(repo)])
            (repo / '.brain/STATE.md').write_text('# State\n\n' + marker + '\n')
            projects.append(repo)
        # A registered but unrelated damaged Brain must not suppress healthy context.
        damaged = home / 'damaged-fixture'
        damaged.mkdir()
        run(['git', '-C', str(damaged), 'init', '-b', 'main'])
        run(['git', '-C', str(damaged), 'remote', 'add', 'origin', 'https://github.com/fixture-owner/damaged-fixture.git'])
        run([*boss, 'adopt', str(damaged)])
        (damaged / '.brain/manifest.json').write_text('{damaged fixture')
        schema = home / 'response.schema.json'
        schema.write_text(json.dumps({'type': 'object', 'properties': {
            'global_marker': {'type': 'string'}, 'markers': {'type': 'array', 'items': {'type': 'string'}},
            'constraint': {'type': 'string'}}, 'required': ['global_marker', 'markers', 'constraint'], 'additionalProperties': False}))
        output = home / 'answer.json'
        flags = ['--disable', 'apps', '--dangerously-bypass-hook-trust', '--skip-git-repo-check',
                 '-c', 'mcp_servers={}', '--json', '--output-schema', str(schema), '--output-last-message', str(output)]
        prompt = ('For @workflow-fixture and @browser-fixture, return the two opaque state markers and global_marker from '
                  'the already supplied project context and global user preference. Use constraint="". '
                  'This is a read-only fixture. Do not call tools, inspect files or guess markers.')
        events = run([codex, 'exec', '--sandbox', 'read-only', '--cd', str(projects[0]), *flags, prompt], timeout=180)
        result = json.loads(output.read_text())
        assert result['global_marker'] == 'GLOBAL_K82Q', 'global rule not loaded'
        assert set(result['markers']) == {'WORKFLOW_N93R', 'BROWSER_F62P'}, 'multi-project context not loaded'
        parsed = [json.loads(line) for line in events.splitlines() if line.startswith('{')]
        sid = next(item['thread_id'] for item in parsed if item.get('type') == 'thread.started')
        run([*boss, 'session', 'bind', sid, '--task-id', 'PUBLISH', '--project', 'workflow-fixture',
             '--project', 'browser-fixture', '--goal', 'publish fixture', '--constraint', 'WORKFLOW_EXECUTES_BROWSER_ONLY_ASSISTS'])
        resume = ('Return the same opaque state markers and global_marker, plus the exact current task constraint '
                  'from supplied context. Read-only; no tools, file reads or inferred values.')
        resumed_events = run([codex, 'exec', 'resume', sid, *flags, resume], cwd=projects[1], timeout=180)
        result = json.loads(output.read_text())
        assert result['constraint'] == 'WORKFLOW_EXECUTES_BROWSER_ONLY_ASSISTS', 'constraint lost on resume'
        assert set(result['markers']) == {'WORKFLOW_N93R', 'BROWSER_F62P'}, 'projects lost on resume'
        run([*boss, 'session', 'bind', sid, '--task-id', 'PUBLISH', '--replace-projects',
             '--project', 'workflow-fixture', '--access', 'read', '--replace-constraints',
             '--constraint', 'WORKFLOW_ONLY_READ_SCOPE'])
        revised_events = run([codex, 'exec', 'resume', sid, *flags,
                              'The task scope has been corrected. Return only the state marker for projects in '
                              'the latest focused task, the latest exact task constraint and global_marker. '
                              'Do not include markers just because they appeared in earlier conversation. '
                              'Read-only; no tools, file reads or guesses.'], cwd=home, timeout=180)
        result = json.loads(output.read_text())
        assert result['constraint'] == 'WORKFLOW_ONLY_READ_SCOPE', 'corrected constraint not loaded'
        assert result['markers'] == ['WORKFLOW_N93R'], 'retired project still treated as current scope'
        trace = home / '.boss/state/traces' / (sid + '.jsonl')
        entries = [json.loads(line) for line in trace.read_text().splitlines()]
        assert any(e.get('mode') == 'multi-project' for e in entries), 'no real hook trace'
        assert any('damaged-fixture' in e.get('unavailable_projects', []) for e in entries), 'damaged project not diagnosed'
        assert any(e.get('projects') == ['workflow-fixture'] for e in entries), 'revised scope not injected'
        for event_text in (events, resumed_events, revised_events):
            for line in event_text.splitlines():
                event = json.loads(line)
                assert event.get('item', {}).get('type') not in ('command_execution', 'mcp_tool_call'), 'context test unexpectedly used tools'
        audit = home / '.boss/state/audit.jsonl'
        assert any(json.loads(line).get('session') == sid for line in audit.read_text().splitlines()), 'Stop hook did not run'
        print('PASS real Codex: global rules, two projects, task constraint, resume, corrected scope, isolated damaged Brain, hook trace')
        if os.environ.get('BOSS_TEST_KNOWLEDGE') == '1':
            # A separately authorized disposable write fixture; never push its fake origin.
            instruction = (
                'Use the installed Boss Brain skill to preserve this confirmed important project decision: '
                'the workflow executes publishing; browser only provides transport. Its exact verification marker is DECISION_J47M. '
                'This is the owning workflow-fixture repository. Save the decision in .brain/conventions/execution.md '
                'and its index, track and resolve the knowledge review with the installed boss CLI. '
                'No business-code changes. This is a disposable acceptance fixture: do not commit, push, access external services '
                'or ask questions. Do not change global configuration. Final response should briefly report saved or failed.')
            run([codex, 'exec', '--sandbox', 'workspace-write', '--cd', str(projects[0]),
                 '--add-dir', str(home / '.boss'), '--disable', 'apps', '--dangerously-bypass-hook-trust',
                 '--skip-git-repo-check', '-c', 'mcp_servers={}', '--json', instruction], timeout=240)
            decision = projects[0] / '.brain/conventions/execution.md'
            assert 'DECISION_J47M' in decision.read_text(), 'confirmed knowledge was not saved'
            reviews = [json.loads(p.read_text()) for p in (home / '.boss/knowledge').glob('*/*.json')]
            assert any(r.get('status') == 'updated' and r.get('evidence', {}).get('file') == '.brain/conventions/execution.md'
                       for r in reviews), 'knowledge was not resolved with file evidence'
            assert run(['git', '-C', str(projects[0]), 'rev-list', '--count', 'HEAD']).strip() == '1', 'fixture unexpectedly committed'
            print('PASS real Codex: confirmed decision saved and review resolved without a business commit')


if __name__ == '__main__':
    main()
