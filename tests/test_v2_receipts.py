"""User-visible project routing survives the enabled v2 hook path."""
import json
import unittest

from tests import test_boss as support
from tests.test_boss import make_repo


class ReceiptTest(unittest.TestCase):
    setUp = support.BossTest.setUp
    tearDown = support.BossTest.tearDown
    boss = support.BossTest.boss

    def setup_projects(self):
        self.assertEqual(self.boss('init', '--rules-only').returncode, 0)
        roots = [make_repo(self.home / name) for name in ('alpha', 'beta')]
        for root in roots:
            self.assertEqual(self.boss('adopt', str(root)).returncode, 0)
        return roots

    def hook(self, root, prompt='查看状态', event='prompt-submit', sid='receipt'):
        result = self.boss('hook', event, payload={'session_id': sid, 'cwd': str(root), 'prompt': prompt})
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['hookSpecificOutput']['additionalContext'] if result.stdout.strip() else ''

    def state(self, sid='receipt'):
        return json.loads((self.home / '.boss/state/sessions' / (sid + '.json')).read_text())

    def test_changes_first_prompt_after_start_then_only_routing_change(self):
        alpha, beta = self.setup_projects()
        self.assertNotIn('用户可见上下文回执', self.hook(alpha, event='session-start'))
        first = self.hook(alpha)
        self.assertIn('↳ Boss：工作目录项目 alpha', first)
        self.assertNotIn(str(alpha), first)  # Receipt only: body was already injected.
        self.assertEqual(self.hook(alpha), '')
        (alpha / '.brain/STATE.md').write_text('# State\nChanged body\n')
        self.assertNotIn('用户可见上下文回执', self.hook(alpha))
        changed = self.hook(beta)
        self.assertIn('↳ Boss：工作目录项目 beta', changed)

    def test_always_survives_duplicate_context_and_off_really_suppresses(self):
        alpha, _ = self.setup_projects()
        self.boss('receipt', 'always')
        self.hook(alpha)
        duplicate = self.hook(alpha)
        self.assertIn('↳ Boss：工作目录项目 alpha', duplicate)
        self.assertNotIn(str(alpha), duplicate)
        trace = self.state()['last_context']
        self.assertEqual(trace['injection']['reason'], 'duplicate')
        self.assertTrue(trace['receipt']['required'])
        self.assertEqual(trace['chars'], len(duplicate))
        self.boss('receipt', 'off')
        self.assertEqual(self.hook(alpha), '')
        self.assertFalse(self.state()['last_context']['receipt']['required'])

    def test_task_projects_and_candidates_are_distinct_without_work_claims(self):
        alpha, beta = self.setup_projects()
        result = self.boss('session', 'bind', 'receipt', '--task-id', 'TASK-A', '--project', 'alpha')
        self.assertEqual(result.returncode, 0, result.stderr)
        text = self.hook(alpha, '只读查看 @beta')
        line = text.split('否则在本轮最终答复末尾原样附加这一行：')[-1]
        self.assertEqual(line, '↳ Boss：任务项目 alpha；参考项目 beta · TASK-A')
        self.assertNotIn(str(beta), line)
        state = self.state()
        self.assertEqual(state['contracts']['TASK-A']['work_projects'], [])
        self.assertFalse(state.get('roots'))
        result = self.boss('session', 'bind', 'receipt', '--task-id', 'TASK-A',
                           '--project', 'beta', '--replace-projects')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('↳ Boss：任务项目 beta；参考项目 alpha · TASK-A', self.hook(alpha))

    def test_disabled_observe_only_and_sessions_remain_isolated(self):
        alpha, _ = self.setup_projects()
        self.boss('receipt', 'always')
        for mode in ('disabled', 'observe-only'):
            self.boss('session', 'mode', 'receipt', mode)
            self.assertEqual(self.hook(alpha), '')
        self.assertNotIn('last_multi_receipt', self.state())
        self.assertIn('↳ Boss：', self.hook(alpha, sid='separate'))
        self.boss('session', 'mode', 'receipt', 'enabled')
        self.assertIn('↳ Boss：', self.hook(alpha))

    def test_task_switch_and_drift_are_visible_without_switching_on_mentions(self):
        alpha, _ = self.setup_projects()
        (alpha / '.brain/TASKS.md').write_text('- [ ] [TASK-A] importer\n- [ ] [TASK-B] worker\n')
        self.assertIn(' · TASK-A', self.hook(alpha, '@task:TASK-A'))
        drift = self.hook(alpha, 'TASK-B 也需要看看')
        self.assertIn('检测到目标偏离，未切换', drift)
        self.assertEqual(self.state()['focus_task'], 'TASK-A')
        self.assertIn(' · TASK-B', self.hook(alpha, '@task:TASK-B'))
        self.assertEqual(self.state()['focus_task'], 'TASK-B')

    def test_receipt_fits_budget_and_does_not_override_strict_user_formats(self):
        alpha, _ = self.setup_projects()
        path = self.home / '.boss/config.json'
        cfg = json.loads(path.read_text())
        cfg['continuity']['context_chars'] = 2000
        cfg['receipt'] = 'always'
        path.write_text(json.dumps(cfg))
        (alpha / '.brain/STATE.md').write_text('# State\n' + 'Long state. ' * 1000)
        text = self.hook(alpha)
        self.assertLessEqual(len(text), 2000)
        self.assertIn('↳ Boss：工作目录项目 alpha', text)
        self.assertIn('若用户要求严格输出格式或不附加说明，遵循用户要求', text)
        self.assertTrue(self.state()['last_context']['truncated_sections'])

    def test_changes_reports_selected_knowledge_without_leaking_its_body(self):
        alpha, _ = self.setup_projects()
        directory = alpha / '.brain/wiki'
        directory.mkdir()
        (directory / 'index.md').write_text('- [recovery](recovery.md)\n')
        (directory / 'recovery.md').write_text('PRIVATE_LESSON_BODY\n')
        self.hook(alpha)
        text = self.hook(alpha, 'recovery')
        line = text.split('否则在本轮最终答复末尾原样附加这一行：')[-1]
        self.assertIn('相关知识 wiki', line)
        self.assertNotIn('PRIVATE_LESSON_BODY', line)
        self.assertNotIn(str(alpha), line)
        self.assertEqual(self.hook(alpha, 'recovery'), '')


if __name__ == '__main__':
    unittest.main()
