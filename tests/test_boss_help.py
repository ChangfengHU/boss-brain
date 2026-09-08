"""Help is explanatory, discoverable and strictly separate from command execution."""
import hashlib
import json
import unittest

from tests import test_boss as support
from tests.test_boss import ROOT, make_repo


class HelpTest(unittest.TestCase):
    setUp = support.BossTest.setUp
    tearDown = support.BossTest.tearDown
    boss = support.BossTest.boss

    def snapshot(self):
        return {str(p.relative_to(self.home)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.home.rglob('*') if p.is_file()}

    def test_overview_and_detailed_help_do_not_execute_commands_or_write(self):
        before = self.snapshot()
        for args in [(), ('help',), ('--help',), ('help', 'receipt'), ('help', 'session', 'mode'),
                     ('help', 'init'), ('help', 'machine', 'restore'), ('help', 'knowledge', 'resolve')]:
            result = self.boss(*args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout)
        self.assertEqual(self.snapshot(), before)
        text = self.boss('help', 'receipt').stdout
        for concept in ('用途', '影响', '示例', '恢复', '--project', 'inherit', '其他项目和全局默认不变'):
            self.assertIn(concept, text)
        self.assertIn('--replace-projects', self.boss('help', 'session', 'bind').stdout)

    def test_every_catalog_topic_is_a_real_command_with_substantive_help(self):
        topics = json.loads((ROOT / 'plugins/boss-brain/assets/help-topics.json').read_text())
        before = self.snapshot()
        for topic in topics:
            result = self.boss('help', *topic.split())
            self.assertEqual(result.returncode, 0, topic + ': ' + result.stderr)
            self.assertIn('用途', result.stdout)
            self.assertGreater(len(result.stdout), 140)
            self.assertIn('usage:', result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_chat_help_is_readonly_in_both_modes_and_repeated_help_still_works(self):
        root = make_repo(self.home / 'repo')
        for v2 in (False, True):
            if v2:
                self.boss('init', '--rules-only')
            before = self.snapshot()
            for prompt in ('help boss', 'boss help', 'boss 帮助', 'help boss receipt', 'help boss'):
                result = self.boss('hook', 'prompt-submit', payload={'session_id': 'help', 'cwd': str(root), 'prompt': prompt})
                self.assertEqual(result.returncode, 0, result.stderr)
                text = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
                self.assertIn('不执行示例或修改设置', text)
                self.assertIn('全局', text)
            self.assertEqual(self.snapshot(), before)

    def test_unknown_help_reports_usage_without_running_and_modes_still_apply(self):
        before = self.snapshot()
        self.assertEqual(self.boss('help', 'not-a-command').returncode, 2)
        self.assertEqual(self.snapshot(), before)
        for mode in ('disabled', 'observe-only'):
            self.boss('session', 'mode', 'help', mode)
            before = self.snapshot()
            result = self.boss('hook', 'prompt-submit', payload={'session_id': 'help', 'prompt': 'help boss'})
            self.assertEqual(result.stdout, '')
            self.assertEqual(self.snapshot(), before)
        self.boss('session', 'mode', 'help', 'enabled')
        result = self.boss('hook', 'prompt-submit', payload={'session_id': 'help', 'prompt': 'help boss unknown'})
        self.assertIn('未知帮助主题', result.stdout)


if __name__ == '__main__':
    unittest.main()
