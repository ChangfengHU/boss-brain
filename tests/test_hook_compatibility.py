"""Missing hook infrastructure must not block an already-running conversation."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tests.test_boss import ROOT, INSTALLER, command

spec = importlib.util.spec_from_file_location('compat_installer', INSTALLER)
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class HookCompatibilityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, HOME=str(self.root), BOSS_HOME=str(self.root / '.boss'),
                        CODEX_HOME=str(self.root / '.codex'))
        self.environment = patch.dict(os.environ, self.env)
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.hooks = json.loads((ROOT / 'plugins/boss-brain/hooks/hooks.json').read_text())['hooks']

    def invoke(self, value, **env):
        return command(['/bin/sh', '-c', value], env=dict(self.env, **env), stdin='{}')

    def assertSkipped(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertEqual(result.stderr, '')

    def test_native_missing_script_skips_all_events_without_writes(self):
        for entries in self.hooks.values():
            self.assertSkipped(self.invoke(entries[0]['hooks'][0]['command'],
                                           CLAUDE_PLUGIN_ROOT=str(self.root / 'absent')))
        self.assertEqual(list(self.root.iterdir()), [])

    def test_native_missing_python_skips_all_events(self):
        for entries in self.hooks.values():
            self.assertSkipped(self.invoke(entries[0]['hooks'][0]['command'], PATH=str(self.root),
                                           CLAUDE_PLUGIN_ROOT=str(ROOT / 'plugins/boss-brain')))

    def test_healthy_handler_output_and_failure_are_not_swallowed(self):
        script = self.root / 'scripts/boss.py'
        script.parent.mkdir()
        script.write_text('import sys\nprint(\'{"decision":"block","reason":"fixture"}\')\nsys.exit(2)\n')
        result = self.invoke(self.hooks['Stop'][0]['hooks'][0]['command'],
                             CLAUDE_PLUGIN_ROOT=str(self.root))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stdout)['decision'], 'block')

    def test_fallback_missing_file_and_interpreter_skip(self):
        script = self.root / "quoted ' script.py"
        self.assertSkipped(self.invoke(installer.guarded_hook_command(script, 'stop')))
        script.write_text('raise AssertionError("must not execute")\n')
        with patch.object(installer.sys, 'executable', str(self.root / 'missing-python')):
            self.assertSkipped(self.invoke(installer.guarded_hook_command(script, 'stop')))

    def test_retired_cache_restored_after_pruning_forwards_then_skips_missing_runtime(self):
        version = '0.1.0+codex.fixture'
        cache = installer.hook_cache_root() / version
        manifest = cache / '.codex-plugin/plugin.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'name': 'boss-brain', 'version': version}))
        versions = installer.remember_hook_versions()
        self.assertEqual(versions, [version])
        shutil.rmtree(cache)
        self.assertEqual(installer.restore_hook_entries(versions), versions)
        self.assertFalse(manifest.exists())
        bridge = cache / 'scripts/boss.py'
        self.assertSkipped(command([sys.executable, str(bridge), 'hook', 'stop'], env=self.env))
        runtime = installer.boss_home() / 'distribution/plugins/boss-brain/scripts/boss.py'
        runtime.parent.mkdir(parents=True)
        runtime.write_text('import json, sys\nprint(json.dumps({"args":sys.argv[1:]}))\n')
        result = command([sys.executable, str(bridge), 'hook', 'stop'], env=self.env)
        self.assertEqual(json.loads(result.stdout), {'args': ['hook', 'stop']})
        self.assertEqual(installer.remember_hook_versions(), versions)

    def test_existing_module_is_preserved_and_unsafe_targets_refused(self):
        version = '0.1.0+codex.fixture'
        target = installer.hook_cache_root() / version / 'scripts/boss.py'
        target.parent.mkdir(parents=True)
        target.write_text('original module\n')
        self.assertEqual(installer.restore_hook_entries([version]), [])
        self.assertEqual(target.read_text(), 'original module\n')
        target.unlink()
        target.symlink_to(self.root / 'outside')
        with self.assertRaises(RuntimeError):
            installer.restore_hook_entries([version])
        with self.assertRaises(RuntimeError):
            installer.restore_hook_entries(['../outside'])

    def test_partial_native_install_failure_still_restores_old_entry(self):
        version = '0.1.0+codex.fixture'
        cache = installer.hook_cache_root() / version
        manifest = cache / '.codex-plugin/plugin.json'
        manifest.parent.mkdir(parents=True)
        manifest.write_text(json.dumps({'name': 'boss-brain', 'version': version}))

        def failed_install(name, distribution):
            self.assertEqual(name, 'codex')
            shutil.rmtree(cache)
            raise RuntimeError('simulated CLI failure after pruning')

        with patch.object(installer, 'plugin_cli_install', side_effect=failed_install):
            with self.assertRaisesRegex(RuntimeError, 'simulated CLI failure'):
                installer.install(SimpleNamespace(policy=None, owner=None))
        self.assertTrue((cache / 'scripts/boss.py').is_file())
        self.assertFalse(manifest.exists())
