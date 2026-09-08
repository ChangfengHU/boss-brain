#!/usr/bin/env python3
"""Check actual installed files/retired entrypoints using disposable routing state.

No credential reads, network calls, live session writes or project initialization.
The installation itself must be performed explicitly before running this probe.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from tests.test_boss import ROOT, make_repo


def main():
    live = Path.home()
    distribution = live / '.boss/distribution/plugins/boss-brain'
    source = ROOT / 'plugins/boss-brain'
    version = json.loads((source / '.codex-plugin/plugin.json').read_text())['version']
    cache_root = live / '.codex/plugins/cache/boss-brain/boss-brain'
    for relative in ('scripts/boss.py', 'scripts/continuity.py', 'hooks/hooks.json',
                     'assets/global-directives.md', 'assets/legacy-directives.md', 'skills/boss-brain/SKILL.md'):
        expected = (source / relative).read_bytes()
        assert (distribution / relative).read_bytes() == expected, f'distribution mismatch: {relative}'
        assert (cache_root / version / relative).read_bytes() == expected, f'cache mismatch: {relative}'
    core = (source / 'assets/legacy-directives.md').read_text().strip()
    for path in (live / '.codex/AGENTS.md', live / '.claude/CLAUDE.md'):
        assert core in path.read_text(), 'original global core missing'
    versions = json.loads((live / '.boss/compatibility/codex-hook-versions.json').read_text())
    versions = sorted(set([version, *versions]))
    assert versions, 'no retained entries to check'
    with tempfile.TemporaryDirectory(prefix='boss-installed-probe-') as folder:
        home = Path(folder)
        env = {**os.environ, 'HOME': str(home), 'BOSS_HOME': str(home / '.boss'),
               'BOSSBRAIN_STATE_DIR': str(home / '.boss/state'), 'CODEX_HOME': str(home / '.codex')}
        root = make_repo(home / 'fixture')

        def run(script, *args, payload=None):
            result = subprocess.run([sys.executable, str(script), *args], env=env, cwd=root,
                                    input=json.dumps(payload) if payload is not None else '',
                                    text=True, capture_output=True, timeout=15)
            assert result.returncode == 0, 'installed entrypoint failed'
            return result.stdout

        script = distribution / 'scripts/boss.py'
        run(script, 'init', '--rules-only')
        run(script, 'receipt', 'always')
        # Registry metadata only: do not create a Brain for this read-only fixture.
        (home / '.boss/registry.tsv').write_text(f'{root}\tfixture\t\tfixture\tlocal\n')
        for index, entry in enumerate(versions):
            script = cache_root / entry / 'scripts/boss.py'
            assert script.is_file(), 'retired entrypoint missing'
            payload = {'session_id': f'probe-{index}', 'cwd': str(root), 'prompt': '只读查看项目'}
            result = json.loads(run(script, 'hook', 'prompt-submit', payload=payload))
            assert '↳ Boss：工作目录项目 fixture' in result['hookSpecificOutput']['additionalContext'], 'entrypoint did not forward repaired receipt'
            stopped = json.loads(run(script, 'hook', 'stop', payload=payload))
            assert stopped.get('decision') != 'block', 'read-only Stop unexpectedly blocked'
        assert not (root / '.brain').exists(), 'probe created project memory'
    print(f'PASS installed source/cache equality, original rules and {len(versions)} live/retired prompt+Stop entrypoints')


if __name__ == '__main__':
    main()
