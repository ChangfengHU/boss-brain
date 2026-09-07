"""Corrected project scope and partial failures in multi-project sessions."""
import json
import unittest

from tests import test_boss as support
from tests.test_boss import make_repo


class ContinuityRefinementTest(unittest.TestCase):
    setUp = support.BossTest.setUp
    tearDown = support.BossTest.tearDown
    boss = support.BossTest.boss

    def prepare(self):
        self.assertEqual(self.boss('init', '--rules-only').returncode, 0)
        projects = []
        for name in ('alpha', 'beta', 'gamma'):
            root = make_repo(self.home / name)
            self.assertEqual(self.boss('adopt', str(root)).returncode, 0)
            (root / '.brain/STATE.md').write_text('# State\n\n' + name.upper() + '_MARKER\n')
            projects.append(root)
        return projects

    def bind(self, task, *args):
        return self.boss('session', 'bind', 'refine', '--task-id', task, *args)

    def session(self):
        return json.loads((self.home / '.boss/state/sessions/refine.json').read_text())

    def hook(self, cwd, prompt='继续'):
        return self.boss('hook', 'prompt-submit', payload={'session_id': 'refine', 'cwd': str(cwd), 'prompt': prompt})

    def test_replacing_scope_removes_old_work_associations_not_other_tasks_or_audit(self):
        alpha, beta, gamma = self.prepare()
        self.bind('OTHER', '--project', 'gamma', '--constraint', 'OTHER_CONSTRAINT')
        self.bind('CURRENT', '--project', 'alpha', '--project', 'beta', '--access', 'work',
                  '--constraint', 'OLD_CONSTRAINT')
        other = self.session()['contracts']['OTHER']
        before_roots = self.session()['roots']
        updated = self.bind('CURRENT', '--replace-projects', '--project', 'beta', '--access', 'read',
                            '--replace-constraints', '--constraint', 'NEW_CONSTRAINT')
        self.assertEqual(updated.returncode, 0, updated.stderr)
        state = self.session()
        self.assertEqual(state['contracts']['CURRENT']['projects'], [str(beta)])
        self.assertEqual(state['contracts']['CURRENT']['work_projects'], [])
        self.assertEqual(state['contracts']['OTHER'], other)
        self.assertEqual(state['roots'], before_roots)  # Past work still needs audit.
        response = self.hook(self.home)
        self.assertIn('BETA_MARKER', response.stdout)
        self.assertIn('NEW_CONSTRAINT', response.stdout)
        self.assertNotIn('ALPHA_MARKER', response.stdout)
        self.assertNotIn('OLD_CONSTRAINT', response.stdout)
        self.assertNotIn('GAMMA_MARKER', response.stdout)

    def test_invalid_scope_replacement_preserves_contract(self):
        self.prepare()
        self.bind('CURRENT', '--project', 'alpha')
        before = self.session()
        result = self.bind('CURRENT', '--replace-projects', '--project', 'unknown')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.session(), before)

    def test_damaged_unrelated_project_does_not_remove_good_context(self):
        alpha, beta, gamma = self.prepare()
        (beta / '.brain/manifest.json').write_text('{damaged')
        self.bind('CURRENT', '--project', 'alpha', '--constraint', 'KEEP_GOAL')
        response = self.hook(alpha)
        self.assertEqual(response.returncode, 0)
        self.assertIn('ALPHA_MARKER', response.stdout)
        self.assertIn('KEEP_GOAL', response.stdout)
        self.assertNotIn('GAMMA_MARKER', response.stdout)
        trace = self.session()['last_context']
        self.assertIn('beta', trace['unavailable_projects'])

    def test_damaged_selected_project_isolated_and_never_reads_external_file(self):
        alpha, beta, gamma = self.prepare()
        secret = self.home / 'outside.md'
        secret.write_text('OUTSIDE_CANARY')
        manifest = beta / '.brain/manifest.json'
        data = json.loads(manifest.read_text())
        data['documents']['state'] = '../outside.md'
        manifest.write_text(json.dumps(data))
        self.bind('CURRENT', '--project', 'alpha', '--project', 'beta')
        response = self.hook(alpha)
        self.assertEqual(response.returncode, 0)
        self.assertIn('ALPHA_MARKER', response.stdout)
        self.assertIn('Context unavailable', response.stdout)
        self.assertNotIn('OUTSIDE_CANARY', response.stdout)

    def test_work_initialization_reports_each_result_without_aborting_other_projects(self):
        alpha, beta, gamma = self.prepare()
        (alpha / '.brain/manifest.json').write_text('{damaged')
        (beta / '.brain/manifest.json').unlink()
        result = self.bind('CURRENT', '--project', 'alpha', '--project', 'beta', '--access', 'work')
        self.assertEqual(result.returncode, 1, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data['status'], 'partial')
        self.assertEqual([r['status'] for r in data['initialization']], ['blocked', 'initialized'])
        self.assertTrue((beta / '.brain/manifest.json').is_file())

    def test_unknown_init_selection_does_not_install_global_rules(self):
        result = self.boss('init', '--project', str(self.home / 'unknown'))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.home / '.codex/AGENTS.md').exists())

    def test_nonobject_manifest_refused_without_overwriting_it(self):
        alpha, beta, gamma = self.prepare()
        manifest = alpha / '.brain/manifest.json'
        for malformed in ('[]', '["unexpected"]', 'null'):
            manifest.write_text(malformed)
            result = self.boss('brain-init', str(alpha))
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'blocked')
            self.assertEqual(manifest.read_text(), malformed)

    def test_repaired_project_reinjects_without_changing_task_scope(self):
        alpha, beta, gamma = self.prepare()
        manifest = beta / '.brain/manifest.json'
        original = manifest.read_text()
        manifest.write_text('{damaged')
        self.bind('CURRENT', '--project', 'alpha', '--project', 'beta')
        first = self.hook(alpha)
        self.assertIn('ALPHA_MARKER', first.stdout)
        self.assertNotIn('BETA_MARKER', first.stdout)
        manifest.write_text(original)
        repaired = self.hook(alpha)
        self.assertIn('ALPHA_MARKER', repaired.stdout)
        self.assertIn('BETA_MARKER', repaired.stdout)
        self.assertEqual(self.session()['last_context']['unavailable_projects'], [])
        self.assertEqual(self.session()['contracts']['CURRENT']['projects'], [str(alpha), str(beta)])
