"""Project receipt overrides must not become global or disable project work."""
import json
import unittest

from tests import test_boss as support
from tests.test_boss import make_repo, git


class ProjectReceiptTest(unittest.TestCase):
    setUp = support.BossTest.setUp
    tearDown = support.BossTest.tearDown
    boss = support.BossTest.boss

    def setup_projects(self):
        self.boss('init', '--rules-only')
        self.roots = [make_repo(self.home / name) for name in ('alpha', 'beta')]
        for root in self.roots:
            self.assertEqual(self.boss('adopt', str(root)).returncode, 0)
        return self.roots

    def hook(self, root, prompt='只读查看状态', sid='project-receipt'):
        result = self.boss('hook', 'prompt-submit', payload={'session_id': sid, 'cwd': str(root), 'prompt': prompt})
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['hookSpecificOutput']['additionalContext'] if result.stdout.strip() else ''

    def test_project_override_keeps_global_and_other_projects_unchanged(self):
        alpha, beta = self.setup_projects()
        before = (self.home / '.boss/config.json').read_bytes()
        query = self.boss('receipt', '--project', 'alpha')
        self.assertEqual(json.loads(query.stdout)['override'], 'inherit')
        self.assertFalse((self.home / '.boss/project-receipts.json').exists())
        result = self.boss('receipt', 'always', '--project', 'alpha')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.home / '.boss/config.json').read_bytes(), before)
        self.assertIn('↳ Boss：', self.hook(alpha))
        self.assertIn('↳ Boss：', self.hook(alpha))
        self.assertIn('↳ Boss：', self.hook(beta, sid='other'))
        self.assertEqual(self.hook(beta, sid='other'), '')
        self.assertIn('↳ Boss：', self.hook(alpha, sid='same-project-other-session'))
        self.boss('receipt', 'inherit', '--project', str(alpha))
        self.assertEqual(json.loads(self.boss('receipt', '--project', 'alpha').stdout)['effective'], 'changes')
        self.assertEqual(json.loads((self.home / '.boss/project-receipts.json').read_text()), {})

    def test_mixed_project_off_hides_only_receipt_not_context_or_authority(self):
        alpha, beta = self.setup_projects()
        (alpha / '.brain/STATE.md').write_text('# State\nALPHA_CONTEXT_STILL_AVAILABLE\n')
        self.boss('receipt', 'off', '--project', 'alpha')
        self.boss('receipt', 'always', '--project', 'beta')
        result = self.hook(alpha, '只读查看 @beta')
        self.assertIn('ALPHA_CONTEXT_STILL_AVAILABLE', result)
        line = result.split('否则在本轮最终答复末尾原样附加这一行：')[-1]
        self.assertNotIn('alpha', line)
        self.assertIn('参考项目 beta', line)
        value = json.loads((self.home / '.boss/state/sessions/project-receipt.json').read_text())
        self.assertFalse(value.get('roots'))
        self.boss('receipt', 'off', '--project', 'beta')
        self.assertNotIn('用户可见上下文回执', self.hook(alpha, '只读查看 @beta'))

    def test_unknown_ambiguous_and_malformed_settings_fail_without_overwrite(self):
        alpha, beta = self.setup_projects()
        before = (self.home / '.boss/config.json').read_bytes()
        for args in [('always', '--project', 'unknown'), ('inherit',)]:
            self.assertEqual(self.boss('receipt', *args).returncode, 2)
        registry = self.home / '.boss/registry.tsv'
        original = registry.read_text()
        registry.write_text(original.replace('\talpha\t\t', '\talpha\tshared\t').replace('\tbeta\t\t', '\tbeta\tshared\t'))
        self.assertEqual(self.boss('receipt', 'always', '--project', 'shared').returncode, 2)
        registry.write_text(original)
        self.assertEqual((self.home / '.boss/config.json').read_bytes(), before)
        path = self.home / '.boss/project-receipts.json'
        path.write_text('{invalid')
        self.assertEqual(self.boss('receipt', 'always', '--project', 'alpha').returncode, 2)
        self.assertEqual(path.read_text(), '{invalid')
        result = self.hook(alpha)
        self.assertIn('当前项目：alpha', result)
        self.assertNotIn('用户可见上下文回执', result)
        trace = json.loads((self.home / '.boss/state/sessions/project-receipt.json').read_text())['last_context']
        self.assertEqual(trace['receipt']['error'], 'invalid-project-receipts')

    def test_legacy_project_option_refused_and_disabled_session_wins(self):
        result = self.boss('receipt', 'always', '--project', 'alpha')
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.home / '.boss/project-receipts.json').exists())
        alpha, _ = self.setup_projects()
        self.boss('receipt', 'always', '--project', 'alpha')
        for mode in ('disabled', 'observe-only'):
            self.boss('session', 'mode', 'project-receipt', mode)
            self.assertEqual(self.hook(alpha), '')

    def test_project_receipt_off_does_not_disable_guarded_stop(self):
        alpha, _ = self.setup_projects()
        self.boss('receipt', 'off', '--project', 'alpha')
        self.boss('policy', 'guarded')
        result = self.boss('session', 'bind', 'work', '--task-id', 'TASK-WORK', '--project', 'alpha', '--access', 'work')
        self.assertEqual(result.returncode, 0, result.stderr)
        (alpha / 'feature.txt').write_text('fixture work\n')
        git(alpha, 'add', 'feature.txt')
        self.assertEqual(git(alpha, 'commit', '-m', 'fixture work').returncode, 0)
        result = self.boss('hook', 'stop', payload={'session_id': 'work', 'cwd': str(alpha)})
        self.assertEqual(json.loads(result.stdout)['decision'], 'block')


if __name__ == '__main__':
    unittest.main()
