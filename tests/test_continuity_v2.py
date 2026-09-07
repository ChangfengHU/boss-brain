"""Observable v2 contracts in isolated homes; never initialize real projects."""
import concurrent.futures
import json
from pathlib import Path
import subprocess
import unittest

from tests import test_boss as support
from tests.test_boss import make_repo, git, command, INSTALLER, ROOT


class ContinuityV2Test(unittest.TestCase):
    setUp = support.BossTest.setUp
    tearDown = support.BossTest.tearDown
    boss = support.BossTest.boss

    def enable(self):
        result = self.boss('init', '--rules-only')
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def registered(self, name):
        repo = make_repo(self.home / name)
        self.assertEqual(self.boss('adopt', str(repo)).returncode, 0)
        return repo

    def hook(self, repo, prompt, sid='multi'):
        return self.boss('hook', 'prompt-submit', payload={'session_id': sid, 'cwd': str(repo), 'prompt': prompt})

    def test_init_dry_run_is_write_free_then_idempotent(self):
        repo = self.registered('alpha')
        preview = self.boss('init', '--dry-run')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertFalse((self.home / '.codex/AGENTS.md').exists())
        self.assertFalse((repo / '.brain').exists())
        first = self.boss('init')
        self.assertEqual(first.returncode, 0, first.stderr)
        manifest = repo / '.brain/manifest.json'
        before = manifest.read_bytes()
        self.assertEqual(self.boss('init').returncode, 0)
        self.assertEqual(manifest.read_bytes(), before)
        rules = (self.home / '.codex/AGENTS.md').read_text()
        self.assertEqual(rules.count('<!-- boss-brain:begin'), 1)
        self.assertEqual(json.loads(before)['content_status'], 'needs-review')

    def test_legacy_rules_migrate_preserving_custom_text(self):
        path = self.home / '.codex/AGENTS.md'
        path.parent.mkdir()
        legacy = (ROOT / 'plugins/boss-brain/assets/legacy-directives.md').read_text().strip()
        path.write_text('USER PREFIX\n<!-- project-brains:begin (managed block, do not edit inside) -->\n'
                        + legacy + '\n<!-- project-brains:end -->\nUSER SUFFIX\n')
        self.enable()
        self.assertIn('USER PREFIX', path.read_text())
        self.assertIn('USER SUFFIX', path.read_text())
        self.assertNotIn('project-brains:begin', path.read_text())
        # User changes outside the block are allowed; inside are not overwritten.
        path.write_text(path.read_text() + 'LATER USER RULE\n')
        self.enable()
        changed = path.read_text().replace('development protocol v2', 'MY EDIT')
        path.write_text(changed)
        self.assertNotEqual(self.boss('init', '--rules-only').returncode, 0)
        self.assertEqual(path.read_text(), changed)

    def test_malformed_global_rules_fail_before_project_writes(self):
        repo = self.registered('alpha')
        target = self.home / '.codex/AGENTS.md'
        target.parent.mkdir()
        target.write_text('<!-- boss-brain:begin (managed block, do not edit inside) -->\n')
        self.assertNotEqual(self.boss('init').returncode, 0)
        self.assertFalse((repo / '.brain').exists())

    def test_adopt_initializes_and_reuses_existing_documents(self):
        self.enable()
        repo = make_repo(self.home / 'existing')
        (repo / 'TASKS.md').write_text('- [ ] [TASK-1] preserve original task\n')
        (repo / 'HANDOFF.md').write_text('user receiving protocol\n')
        (repo / 'dev-log').mkdir()
        result = self.boss('adopt', str(repo))
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads((repo / '.brain/manifest.json').read_text())
        self.assertEqual(manifest['documents']['tasks'], 'TASKS.md')
        self.assertEqual(manifest['documents']['dev_log'], 'dev-log')
        self.assertFalse((repo / '.brain/TASKS.md').exists())
        response = self.hook(repo, '查看当前任务')
        self.assertIn('preserve original task', response.stdout)
        self.assertEqual((repo / 'HANDOFF.md').read_text(), 'user receiving protocol\n')

    def test_ignored_brain_and_external_symlink_are_refused(self):
        repo = self.registered('alpha')
        (repo / '.gitignore').write_text('.brain/\n')
        self.assertNotEqual(self.boss('brain-init', str(repo)).returncode, 0)
        self.assertFalse((repo / '.brain').exists())
        (repo / '.gitignore').write_text('')
        outside = self.home / 'outside'
        outside.mkdir()
        (repo / '.brain').symlink_to(outside)
        self.assertNotEqual(self.boss('brain-init', str(repo)).returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_readonly_and_scanning_do_not_initialize_projects(self):
        repo = self.registered('alpha')
        self.enable()
        self.boss('scan', '--adopt')
        self.hook(repo, '只读讨论如何修改和优化项目')
        self.assertFalse((repo / '.brain').exists())
        self.boss('session', 'bind', 'work', '--task-id', 'TASK-1', '--project', 'alpha', '--access', 'work')
        self.assertTrue((repo / '.brain/manifest.json').exists())

    def test_multi_project_binding_preserves_constraints_on_auxiliary_workspace(self):
        first = self.registered('workflow')
        second = self.registered('fleet')
        self.enable()
        bind = self.boss('session', 'bind', 'multi', '--task-id', 'PUBLISH', '--goal', 'publish approved video',
                         '--project', 'workflow', '--project', 'fleet', '--constraint', 'workflow executes; fleet only supplies browser')
        self.assertEqual(bind.returncode, 0, bind.stderr)
        response = self.hook(second, '继续检查浏览器')
        text = json.loads(response.stdout)['hookSpecificOutput']['additionalContext']
        self.assertIn('workflow executes; fleet only supplies browser', text)
        trace = json.loads(self.boss('explain', '--session', 'multi', '--json').stdout)
        self.assertEqual(set(trace['projects']), {'workflow', 'fleet'})
        self.assertFalse((first / '.brain').exists())
        self.assertFalse((second / '.brain').exists())

    def test_mentions_do_not_become_write_claims(self):
        a = self.registered('workflow')
        self.registered('fleet')
        self.enable()
        result = self.hook(a, 'workflow 和 fleet 是什么关系')
        self.assertIn('fleet', result.stdout)
        state = json.loads((self.home / '.boss/state/sessions/multi.json').read_text())
        self.assertNotIn(str(self.home / 'fleet'), state.get('roots', {}))
        self.assertNotIn('疑似涉及项目', result.stdout)

    def test_context_content_change_and_resume_reinject(self):
        self.enable()
        repo = self.registered('alpha')
        self.assertTrue(self.hook(repo, '查看状态').stdout)
        self.assertEqual(self.hook(repo, '查看状态').stdout, '')
        state = repo / '.brain/STATE.md'
        state.write_text(state.read_text() + '\nNEW VERIFIED STATE\n')
        self.assertIn('NEW VERIFIED STATE', self.hook(repo, '查看状态').stdout)
        resumed = self.boss('hook', 'session-start', payload={'session_id': 'multi', 'cwd': str(repo), 'source': 'resume'})
        self.assertIn('NEW VERIFIED STATE', resumed.stdout)

    def test_knowledge_survives_session_and_can_resolve_from_new_session(self):
        self.enable()
        repo = self.registered('alpha')
        flagged = self.boss('knowledge', 'flag', '--session', 'one', '--path', str(repo), '--key', 'execution-owner',
                            '--kind', 'decision', '--summary', 'workflow executes publishing', '--source', 'README.md')
        self.assertEqual(flagged.returncode, 0, flagged.stderr)
        rid = json.loads(flagged.stdout)[0]['id']
        self.boss('session', 'bind', 'two', '--task-id', 'T1', '--project', 'alpha')
        pending = json.loads(self.boss('knowledge', 'list', '--session', 'two').stdout)
        self.assertEqual(pending[0]['summary'], 'workflow executes publishing')
        self.assertEqual(pending[0]['id'], rid)
        unchanged = self.boss('knowledge', 'resolve', '--session', 'two', '--id', rid, '--status', 'updated', '--file', 'README.md')
        self.assertNotEqual(unchanged.returncode, 0)
        (repo / 'README.md').write_text('workflow executes publishing\n')
        updated = self.boss('knowledge', 'resolve', '--session', 'two', '--id', rid, '--status', 'updated', '--file', 'README.md')
        self.assertEqual(updated.returncode, 0, updated.stderr)
        self.assertEqual(json.loads(self.boss('knowledge', 'list', '--session', 'one').stdout)[0]['status'], 'updated')

    def test_readonly_knowledge_capture_and_secret_metadata_refused(self):
        self.enable()
        repo = self.registered('alpha')
        self.hook(repo, '不要记录，这个架构不对', 'readonly')
        result = self.boss('knowledge', 'flag', '--session', 'readonly', '--path', str(repo), '--key', 'test')
        self.assertNotEqual(result.returncode, 0)
        secret = 'ghp_' + 'X' * 30
        result = self.boss('knowledge', 'flag', '--session', 'safe', '--path', str(repo), '--key', 'test', '--summary', secret)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(secret, result.stdout + result.stderr)

    def test_concurrent_initialization_never_overwrites_state(self):
        repo = self.registered('alpha')
        (repo / 'STATE.md').write_text('preserve user state\n')
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: self.boss('brain-init', str(repo)), range(4)))
        self.assertTrue(any(r.returncode == 0 for r in results))
        manifest = json.loads((repo / '.brain/manifest.json').read_text())
        self.assertEqual(manifest['documents']['state'], 'STATE.md')
        self.assertEqual((repo / 'STATE.md').read_text(), 'preserve user state\n')

    def test_capability_dependency_and_both_knowledge_sections(self):
        self.enable()
        a, b = self.registered('workflow'), self.registered('browser')
        for repo, direction in [(a, 'consumes'), (b, 'provides')]:
            (repo / '.brain/capabilities.tsv').write_text(direction + '\tbrowser.control\tREADME.md\tbrowser connection\n')
        for folder, marker in [('wiki', 'LESSON_MARKER'), ('conventions', 'RULE_MARKER')]:
            path = b / '.brain' / folder
            path.mkdir()
            (path / 'index.md').write_text('- [recovery](recovery.md)\n')
            (path / 'recovery.md').write_text(marker)
        response = self.hook(a, 'explain recovery for browser.control')
        self.assertIn('LESSON_MARKER', response.stdout)
        self.assertIn('RULE_MARKER', response.stdout)
        state = json.loads((self.home / '.boss/state/sessions/multi.json').read_text())
        self.assertNotIn(str(b), state.get('roots', {}))

    def test_damaged_manifest_degrades_without_external_read(self):
        self.enable()
        repo = self.registered('alpha')
        outside = self.home / 'outside.md'
        outside.write_text('MUST_NOT_LEAK')
        manifest = repo / '.brain/manifest.json'
        value = json.loads(manifest.read_text())
        value['documents']['state'] = '../outside.md'
        manifest.write_text(json.dumps(value))
        result = self.hook(repo, 'show state')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('MUST_NOT_LEAK', result.stdout)
        self.assertIn('Context unavailable', result.stdout)

    def test_rule_restore_preserves_later_unmanaged_changes(self):
        self.enable()
        target = self.home / '.codex/AGENTS.md'
        target.write_text(target.read_text() + '\nUSER LATER RULE\n')
        # Import the module only for this unit-level restore operation.
        import importlib.util
        path = ROOT / 'plugins/boss-brain/scripts/continuity.py'
        spec = importlib.util.spec_from_file_location('fixture_continuity', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Test environment has no CODEX_HOME override; pass explicit isolated home.
        from unittest.mock import patch
        with patch.dict('os.environ', {'CODEX_HOME': str(self.home / '.codex')}):
            results = module.manage_rules(self.home, self.home / '.boss', restore=True)
        self.assertTrue(all(r['status'] != 'blocked' for r in results))
        self.assertIn('USER LATER RULE', target.read_text())
        self.assertNotIn('boss-brain:begin', target.read_text())

    def test_installer_updates_legacy_skill_and_rollback_refuses_later_config(self):
        old = self.home / '.codex/skills/brain-init'
        old.mkdir(parents=True)
        (old / 'SKILL.md').write_text('legacy entry using .project-brains/vault.sh')
        installed = command(['python3', str(INSTALLER), 'install'], env=self.env)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        self.assertNotIn('.project-brains/vault.sh', (old / 'SKILL.md').read_text())
        config = self.home / '.codex/config.toml'
        config.write_text(config.read_text() + '\n# LATER USER CONFIG\n')
        expected = config.read_bytes()
        rolled = command(['python3', str(INSTALLER), 'rollback'], env=self.env)
        self.assertNotEqual(rolled.returncode, 0)
        self.assertEqual(config.read_bytes(), expected)

    def test_hook_cleanup_preserves_native_trust_tables_and_removes_fallback(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('fixture_installer', INSTALLER)
        installer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer)
        trusted = '[hooks.state."boss-brain@boss-brain:hooks/hooks.json:session_start:0:0"]\ntrusted_hash = "canary-one"\n\n'
        trusted += '[hooks.state."boss-brain@boss-brain:hooks/hooks.json:stop:0:0"]\ntrusted_hash = "canary-two"\n\n'
        fallback = installer.manual_codex_hooks(Path('/home/test/.boss/distribution/plugins/boss-brain/scripts/boss.py'))
        cleaned = installer.strip_codex_hooks(trusted + fallback, True)
        self.assertIn(trusted.rstrip(), cleaned)
        self.assertNotIn('[[hooks.', cleaned)
        self.assertEqual(cleaned.count('trusted_hash'), 2)
        # Partial migration can leave unmarked runtime entries. Remove these too.
        bare = fallback.replace('# boss-brain:hooks:begin (managed)\n', '').replace('# boss-brain:hooks:end\n', '')
        self.assertNotIn('[[hooks.', installer.strip_codex_hooks(trusted + bare, True))


if __name__ == '__main__':
    unittest.main()
