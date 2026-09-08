"""Legacy local startup services must run in enabled v2, not just legacy tests."""
import importlib.util
import json
import unittest
from unittest.mock import patch

from tests import test_boss as support
from tests.test_boss import ROOT, make_repo, git


class StartupTest(unittest.TestCase):
    setUp = support.BossTest.setUp
    tearDown = support.BossTest.tearDown
    boss = support.BossTest.boss

    def test_v2_daily_patrol_and_local_machine_init_without_project_writes(self):
        first = make_repo(self.home / 'work/first')
        peer = make_repo(self.home / 'work/peer')
        foreign = make_repo(self.home / 'work/foreign', owner='not-me')
        self.assertEqual(self.boss('init', '--rules-only').returncode, 0)
        payload = {'session_id': 'startup', 'cwd': str(first), 'source': 'startup'}
        result = self.boss('hook', 'session-start', payload=payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        registry = (self.home / '.boss/registry.tsv').read_text()
        self.assertIn(str(first), registry)
        self.assertIn(str(peer), registry)
        self.assertNotIn(str(foreign), registry)
        for root in (first, peer, foreign):
            self.assertFalse((root / '.brain').exists())
            self.assertEqual(git(root, 'status', '--porcelain').stdout, '')
        cfg = json.loads((self.home / '.boss/config.json').read_text())
        machine = self.home / cfg['machine']['path']
        self.assertTrue((machine / '.git').exists())
        head = git(machine, 'rev-parse', 'HEAD').stdout
        stamp = (self.home / '.boss/.last-patrol').stat().st_mtime_ns
        make_repo(self.home / 'work/after-patrol')
        payload['source'] = 'resume'
        self.assertEqual(self.boss('hook', 'session-start', payload=payload).returncode, 0)
        self.assertEqual((self.home / '.boss/.last-patrol').stat().st_mtime_ns, stamp)
        self.assertNotIn('after-patrol', (self.home / '.boss/registry.tsv').read_text())
        self.assertEqual(git(machine, 'rev-parse', 'HEAD').stdout, head)
        state = json.loads((self.home / '.boss/state/sessions/startup.json').read_text())
        self.assertFalse(state.get('roots'))  # Discovery never authorizes development.

    def test_disabled_session_skips_startup_and_machine_opt_out_is_preserved(self):
        first = make_repo(self.home / 'first')
        self.boss('init', '--rules-only')
        self.boss('session', 'mode', 'startup', 'disabled')
        payload = {'session_id': 'startup', 'cwd': str(first)}
        self.assertEqual(self.boss('hook', 'session-start', payload=payload).stdout, '')
        self.assertFalse((self.home / '.boss/.last-patrol').exists())
        path = self.home / '.boss/config.json'
        cfg = json.loads(path.read_text())
        cfg['machine'] = {'auto_init': False}
        path.write_text(json.dumps(cfg))
        self.boss('session', 'mode', 'startup', 'enabled')
        result = self.boss('hook', 'session-start', payload=payload)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(path.read_text())['machine'], {'auto_init': False})

    def test_startup_failure_does_not_bypass_healthy_context_or_other_services(self):
        spec = importlib.util.spec_from_file_location('boss_startup_test', ROOT / 'plugins/boss-brain/scripts/boss.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with patch.object(module, 'session_mode', return_value='enabled'), \
             patch.object(module, 'continuity_enabled', return_value=True), \
             patch.object(module, 'patrol', side_effect=OSError('fixture')), \
             patch.object(module, 'ensure_machine_initialized') as machine, \
             patch.object(module, 'load_session', return_value={}), \
             patch.object(module, 'save_session') as save, \
             patch.object(module, 'hook_multi_context', return_value=0) as context:
            self.assertEqual(module.hook_session_start({'session_id': 's'}), 0)
            machine.assert_called_once()
            context.assert_called_once()
            self.assertEqual(save.call_args.args[1]['startup_unavailable'], ['patrol'])


if __name__ == '__main__':
    unittest.main()
