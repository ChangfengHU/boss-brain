"""Legacy user contracts must survive enabling multi-project continuity."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

from tests import test_boss as support
from tests.test_boss import ROOT, git, make_repo, command


class PreservationTest(unittest.TestCase):
    setUp = support.BossTest.setUp
    tearDown = support.BossTest.tearDown
    boss = support.BossTest.boss

    def repo(self, name='alpha'):
        root = make_repo(self.home / name)
        self.assertEqual(self.boss('adopt', str(root)).returncode, 0)
        return root

    def enable(self):
        result = self.boss('init', '--rules-only')
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def hook(self, root, prompt='', event='prompt-submit', sid='preserve'):
        result = self.boss('hook', event, payload={'session_id': sid, 'cwd': str(root), 'prompt': prompt})
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def session(self):
        return json.loads((self.home / '.boss/state/sessions/preserve.json').read_text())

    def test_all_original_core_rules_survive_global_migration(self):
        core = ROOT / 'plugins/boss-brain/assets/legacy-directives.md'
        self.assertEqual(hashlib.sha256(core.read_bytes()).hexdigest(), '1300c5e4dc6f9680b1f437054c81722fc870f7c9b24146be60fae43c53767f2a')
        legacy = core.read_text().strip()
        target = self.home / '.codex/AGENTS.md'
        target.parent.mkdir()
        target.write_text('USER PREFIX\n<!-- project-brains:begin (managed block, do not edit inside) -->\n'
                          + legacy + '\n<!-- project-brains:end -->\nUSER SUFFIX\n')
        self.enable()
        self.assertIn(legacy, target.read_text())
        self.assertIn('USER PREFIX', target.read_text())
        self.assertIn('USER SUFFIX', target.read_text())
        before = target.read_bytes()
        self.enable()
        self.assertEqual(target.read_bytes(), before)

    def test_initializer_refuses_a_template_that_drops_a_core_rule(self):
        spec = importlib.util.spec_from_file_location('preservation_continuity', ROOT / 'plugins/boss-brain/scripts/continuity.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        assets = self.home / 'assets'
        assets.mkdir()
        core = (ROOT / 'plugins/boss-brain/assets/legacy-directives.md').read_text()
        (assets / 'legacy-directives.md').write_text(core)
        (assets / 'global-directives.md').write_text('# New protocol without original requirements\n')
        with patch.object(module, 'ASSETS', assets):
            result = module.manage_rules(self.home, self.home / '.boss')
        self.assertEqual(result[0]['status'], 'blocked')
        self.assertFalse((self.home / '.codex/AGENTS.md').exists())

    def test_long_state_does_not_swallow_tasks_or_capability_relationships(self):
        self.enable()
        root = self.repo()
        peer = self.repo('beta')
        (root / '.brain/STATE.md').write_text('# State\n\n' + 'state filler ' * 160)
        (root / '.brain/TASKS.md').write_text('- [ ] [TASK-A] TASK_TAIL_CANARY\n')
        (root / '.brain/capabilities.tsv').write_text('consumes\ttransport.control\tREADME.md\ttransport\n')
        (peer / '.brain/capabilities.tsv').write_text('provides\ttransport.control\tREADME.md\ttransport\n')
        result = self.hook(root, '查看状态')
        self.assertIn('TASK_TAIL_CANARY', result)
        self.assertIn('transport.control', result)

    def test_wiki_and_convention_keep_legacy_topic_length(self):
        self.enable()
        root = self.repo()
        for folder, marker in [('wiki', 'WIKI_TAIL_CANARY'), ('conventions', 'RULE_TAIL_CANARY')]:
            directory = root / '.brain' / folder
            directory.mkdir()
            (directory / 'index.md').write_text('- [recovery](recovery.md)\n')
            (directory / 'recovery.md').write_text('x' * 1500 + '\n' + marker)
        result = self.hook(root, 'recovery')
        self.assertIn('WIKI_TAIL_CANARY', result)
        self.assertIn('RULE_TAIL_CANARY', result)

    def test_legacy_task_switch_and_drift_still_work_after_init(self):
        root = self.repo()
        (root / '.brain').mkdir()
        (root / '.brain/TASKS.md').write_text('- [ ] [TASK-A] importer\n- [ ] [TASK-B] worker\n- [x] [TASK-DONE] finished\n')
        self.hook(root, event='session-start')
        self.hook(root, '@task:TASK-A')
        self.enable()
        self.assertIn('低置信度任务漂移提示', self.hook(root, 'TASK-B 也需要看一下'))
        self.assertEqual(self.session()['focus_task'], 'TASK-A')
        self.hook(root, '@task:TASK-B')
        self.assertEqual(self.session()['focus_task'], 'TASK-B')
        self.hook(root, '@task:TASK-DONE')
        self.assertEqual(self.session()['focus_task'], 'TASK-B')

    def test_legacy_goal_drift_survives_init(self):
        root = self.repo()
        (root / '.brain').mkdir()
        (root / '.brain/TASKS.md').write_text('- [ ] stabilize importer parser\n- [ ] migrate worker deployment\n')
        self.hook(root, event='session-start')
        self.enable()
        result = self.hook(root, '请迁移 worker deployment 到新环境')
        self.assertIn('低置信度目标漂移提示', result)

    def test_work_binding_connects_the_confirmed_task_to_stop_audit(self):
        self.enable()
        root = self.repo()
        (root / '.brain/TASKS.md').write_text('- [ ] [TASK-A] importer\n- [ ] [TASK-B] worker\n')
        self.boss('session', 'bind', 'preserve', '--task-id', 'TASK-A', '--project', 'alpha', '--access', 'work')
        self.assertEqual(self.session()['roots'][str(root)].get('task_id'), 'TASK-A')

    def test_v2_without_work_binding_reports_audit_gap_not_a_clean_bill(self):
        self.enable()
        root = self.repo()
        self.hook(root, event='session-start')
        (root / 'change.txt').write_text('fixture\n')
        git(root, 'add', 'change.txt')
        git(root, 'commit', '-m', 'fixture change')
        self.hook(root, event='stop')
        audit = [json.loads(l) for l in (self.home / '.boss/state/audit.jsonl').read_text().splitlines()]
        self.assertIn('baseline-missing', {f['code'] for f in audit[-1]['findings']})

    def test_bare_at_keeps_project_roster_access_in_v2(self):
        self.enable()
        root = self.repo()
        self.repo('beta')
        result = self.hook(root, '@')
        self.assertIn('beta', result)

    def test_mapped_documents_are_used_by_diagnostics_not_just_injection(self):
        root = self.repo()
        (root / 'STATE.md').write_text('# State\n\n## 下一步\nMAPPED_NEXT\n\n## 雷区\nMAPPED_RISK\n')
        (root / 'wiki').mkdir()
        (root / 'wiki/index.md').write_text('- [topic](topic.md)\n')
        (root / 'wiki/topic.md').write_text('Existing authoritative topic\n')
        (root / 'HANDOFF.md').write_text('# Handoff\n\n## Purpose\nfixture\n## Access\nlocal\n## Reading order\nREADME\n## Verification\ntests\n## Hazards\nfixture\n')
        self.enable()
        self.assertEqual(self.boss('brain-init', str(root)).returncode, 0)
        self.assertIn('MAPPED_NEXT', self.boss('projects').stdout)
        self.assertIn('MAPPED_RISK', self.boss('risk').stdout)
        checked = self.boss('wiki', 'check', str(root), '--json')
        self.assertEqual(checked.returncode, 0, checked.stdout)
        checked = json.loads(self.boss('handoff', 'check', str(root), '--json').stdout)
        self.assertEqual(next(c for c in checked['checks'] if c['id'] == 'handoff-file')['status'], 'PASS')

    def test_readonly_stop_does_not_block_for_missing_work_baseline(self):
        self.enable()
        root = self.repo()
        self.boss('policy', 'strict')
        self.hook(root, '只读查看状态')
        result = json.loads(self.hook(root, event='stop'))
        self.assertNotEqual(result.get('decision'), 'block')

    def test_plain_explain_can_show_current_multi_project_preview(self):
        self.enable()
        root = self.repo()
        self.hook(root, '查看状态')
        result = self.boss('explain', '--show').stdout
        self.assertIn('alpha', result)
        self.assertNotIn('(preview unavailable)', result)

    def test_pending_knowledge_after_100_closed_reviews_is_not_lost(self):
        self.enable()
        root = self.repo()
        self.boss('session', 'bind', 'preserve', '--task-id', 'REVIEW', '--project', 'alpha')
        folder = self.home / '.boss/knowledge' / hashlib.sha256(str(root).encode()).hexdigest()
        folder.mkdir(parents=True)
        for index in range(101):
            rid = f'{index:016x}'
            (folder / (rid + '.json')).write_text(json.dumps({'id': rid, 'project': str(root),
                'status': 'pending' if index == 100 else 'updated', 'files': {}, 'summary': 'fixture'}))
        result = json.loads(self.boss('knowledge', 'list', '--session', 'preserve').stdout)
        self.assertEqual(sum(r['status'] == 'pending' for r in result), 1)
        self.assertIn(f'{100:016x}', self.hook(root, '继续'))

    def test_hook_skips_missing_internal_runtime_module(self):
        scripts = self.home / 'incomplete-plugin/scripts'
        scripts.mkdir(parents=True)
        target = scripts / 'boss.py'
        shutil.copyfile(ROOT / 'plugins/boss-brain/scripts/boss.py', target)
        result = command([sys.executable, str(target), 'hook', 'stop'], env=self.env, stdin='{}')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual(result.stderr, '')

    def test_context_budget_retains_task_metadata_and_reports_shortened_bodies(self):
        self.enable()
        roots = [self.repo(name) for name in ('alpha', 'beta', 'gamma')]
        args = []
        for root in roots:
            (root / '.brain/TASKS.md').write_text('- [ ] task for ' + root.name + '\n')
            (root / '.brain/STATE.md').write_text('long state ' * 1000)
            args.extend(['--project', root.name])
        self.boss('session', 'bind', 'preserve', '--task-id', 'CURRENT', '--constraint', 'CORE_CONSTRAINT', *args)
        cfg = self.home / '.boss/config.json'
        config = json.loads(cfg.read_text())
        config['continuity']['context_chars'] = 3000
        cfg.write_text(json.dumps(config))
        text = json.loads(self.hook(self.home, '继续'))['hookSpecificOutput']['additionalContext']
        self.assertLessEqual(len(text), 3000)
        for marker in ('CORE_CONSTRAINT', 'task for alpha', 'task for beta', 'task for gamma'):
            self.assertIn(marker, text)
        self.assertTrue(self.session()['last_context']['truncated_sections'])
        hooks = json.loads((ROOT / 'plugins/boss-brain/hooks/hooks.json').read_text())['hooks']
        self.assertTrue(all(hooks[e][0]['hooks'][0]['additionalContextLimit'] >= 20000
                            for e in ('SessionStart', 'UserPromptSubmit')))

    def test_ambiguous_task_id_does_not_reassign_another_projects_contract(self):
        self.enable()
        alpha, beta = self.repo(), self.repo('beta')
        for root in (alpha, beta):
            (root / '.brain/TASKS.md').write_text('- [ ] [TASK-A] task for ' + root.name + '\n')
        self.boss('session', 'bind', 'preserve', '--task-id', 'TASK-A', '--project', 'alpha')
        before = self.session()['contracts']['TASK-A']
        self.hook(beta, '@beta @task:TASK-A')
        self.assertEqual(self.session()['contracts']['TASK-A'], before)
        self.assertEqual(self.session()['last_context']['suppression_reason'], 'ambiguous-task-owner')
