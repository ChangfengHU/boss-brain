"""Visible events must come from actual hooks/files, not an assistant receipt."""
import json
from pathlib import Path
import subprocess
import unittest

from tests import test_boss as support


class ObservabilityTest(unittest.TestCase):
    setUp = support.BossTest.setUp
    tearDown = support.BossTest.tearDown
    boss = support.BossTest.boss

    def setup_project(self):
        self.boss('init', '--rules-only')
        root = support.make_repo(self.home / 'alpha')
        self.boss('adopt', str(root))
        self.root = root
        self.sid = 'visible-session'
        return root

    def hook(self, event='prompt-submit', sid=None):
        result = self.boss('hook', event, payload={'session_id': sid or self.sid,
                          'cwd': str(self.root), 'prompt': '只读查看状态'})
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    def events(self, sid=None):
        result = self.boss('events', '--session', sid or self.sid, '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        return [json.loads(line) for line in result.stdout.splitlines()]

    def test_opt_in_scopes_inherit_off_and_no_cross_session_changes(self):
        self.setup_project()
        self.hook()
        self.assertEqual(self.events(), [])
        cfg = (self.home / '.boss/config.json').read_bytes()
        self.boss('display', 'detail', '--project', 'alpha')
        self.boss('display', 'off', '--session', self.sid)
        self.hook()
        self.assertEqual(self.events(), [])
        self.hook(sid='other')
        self.assertEqual(self.events('other')[-1]['mode'], 'detail')
        self.boss('display', 'inherit', '--session', self.sid)
        self.assertIn('systemMessage', self.hook())
        self.assertEqual((self.home / '.boss/config.json').read_bytes(), cfg)

    def test_actual_context_and_duplicate_body_not_replayed_as_new_injection(self):
        root = self.setup_project()
        (root / '.brain/STATE.md').write_text('# State\nVISIBLE_MARKER\n')
        self.boss('display', 'detail', '--session', self.sid)
        first = self.hook()
        entry = self.events()[-1]
        self.assertEqual(entry['context_body'], first['hookSpecificOutput']['additionalContext'])
        self.assertIn('VISIBLE_MARKER', entry['context_body'])
        self.assertEqual(entry['host_display'], 'requested-not-confirmed')
        self.hook()
        entry = self.events()[-1]
        self.assertEqual(entry['context_body'], '')
        self.assertEqual(entry['context']['injection']['reason'], 'duplicate')

    def test_actual_write_evidence_without_business_commit_and_no_auto_writing(self):
        root = self.setup_project()
        self.boss('display', 'summary', '--session', self.sid)
        self.hook()
        log = root / '.brain/dev-log/verified.md'
        log.parent.mkdir(exist_ok=True)
        log.write_text('# Verified local edit\n')
        self.hook('stop')
        entry = self.events()[-1]
        record = next(d for d in entry['documents'] if d['kind'] == 'dev_log')
        self.assertEqual(record['status'], 'observed-change')
        self.assertIn('.brain/dev-log/verified.md', record['changed_files'])
        self.assertEqual(entry['context_body'], '')
        self.hook('stop')
        self.assertTrue(all(d['status'] == 'no-change' for d in self.events()[-1]['documents']))

    def test_secrets_redacted_from_disk_host_and_viewer(self):
        root = self.setup_project()
        secret = 'ghp_' + 'a' * 24
        bearer = 'opaquecredential0123456789'
        (root / '.brain/STATE.md').write_text(f'# State\nToken: {secret}\nAuthorization: Bearer {bearer}\n')
        self.boss('display', 'detail', '--session', self.sid)
        self.hook()
        entries = json.dumps(self.events())
        self.assertNotIn(secret, entries)
        self.assertNotIn(bearer, entries)
        output = self.boss('events', '--session', self.sid, '--detail').stdout
        self.assertNotIn(secret, output)
        self.assertNotIn(bearer, output)

    def test_corrupt_display_config_preserves_original_hook_and_file(self):
        self.setup_project()
        path = self.home / '.boss/display.json'
        path.write_text('{invalid')
        result = self.boss('display', 'detail', '--session', self.sid)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(path.read_text(), '{invalid')
        self.assertIn('hookSpecificOutput', self.hook())

    def test_disabled_session_wins_and_help_is_readonly(self):
        self.setup_project()
        self.boss('display', 'detail', '--session', self.sid)
        self.boss('session', 'mode', self.sid, 'disabled')
        self.assertEqual(self.hook(), {})
        self.assertEqual(self.events(), [])
        before = (self.home / '.boss/display.json').read_bytes()
        self.assertEqual(self.boss('help', 'display').returncode, 0)
        self.assertEqual((self.home / '.boss/display.json').read_bytes(), before)

    def test_guarded_stop_and_git_evidence_preserved(self):
        root = self.setup_project()
        self.boss('session', 'bind', self.sid, '--task-id', 'WORK', '--project', 'alpha', '--access', 'work')
        self.boss('display', 'detail', '--session', self.sid)
        self.boss('policy', 'guarded')
        self.hook()
        (root / 'feature.txt').write_text('feature\n')
        support.git(root, 'add', 'feature.txt')
        support.git(root, 'commit', '-m', 'feature')
        output = self.hook('stop')
        self.assertEqual(output['decision'], 'block')
        entry = self.events()[-1]
        self.assertIn('no-upstream', [f['code'] for f in entry['audit']['findings']])
        self.assertEqual(entry['repositories'][str(root)]['head'], support.git(root, 'rev-parse', 'HEAD').stdout.strip())

    def test_remote_missing_path_is_not_local_initialization_instruction(self):
        self.setup_project()
        registry = self.home / '.boss/registry.tsv'
        registry.write_text(registry.read_text().replace(str(self.root), '/missing-remote-test/alpha').replace('\tlocal\n', '\tremote\n'))
        result = self.boss('hook', 'prompt-submit', payload={'session_id': self.sid, 'prompt': '@alpha'})
        text = result.stdout
        self.assertIn('远程 Brain 未在本机加载', text)
        self.assertNotIn('Brain 基础入口待初始化', text)
        self.assertFalse(Path('/missing-remote-test/alpha').exists())

    def test_cli_follower_prints_hook_event_without_assistant(self):
        self.setup_project()
        self.boss('display', 'detail', '--session', self.sid)
        command = ['python3', str(support.BOSS), 'events', '--session', self.sid, '--follow', '--json']
        viewer = subprocess.Popen(command, env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            self.hook()
            import select
            ready, _, _ = select.select([viewer.stdout], [], [], 5)
            self.assertTrue(ready, 'real CLI follower did not print Hook event')
            entry = json.loads(viewer.stdout.readline())
            self.assertEqual(entry['event'], 'prompt-submit')
        finally:
            viewer.terminate()
            viewer.communicate(timeout=5)


if __name__ == '__main__':
    unittest.main()
