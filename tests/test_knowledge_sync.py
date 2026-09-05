import json
import unittest

from tests import test_boss as support
from tests.test_boss import make_repo


class KnowledgeSyncTest(unittest.TestCase):
    setUp = support.BossTest.setUp
    tearDown = support.BossTest.tearDown
    boss = support.BossTest.boss
    def test_correction_survives_no_context_match_and_stop(self):
        repo = make_repo(self.home / 'tripstar-control')
        result = self.boss('hook', 'prompt-submit', cwd=repo, payload={
            'session_id': 'k1', 'cwd': str(repo),
            'prompt': '你没有弄清架构，/app 和 /release-app 的版本关系不对'})
        self.assertIn('Brain 知识同步检查', result.stdout)
        pending = json.loads(self.boss('knowledge', 'list', '--session', 'k1').stdout)
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]['project'], str(repo))
        stop = self.boss('hook', 'stop', cwd=repo, payload={'session_id': 'k1', 'cwd': str(repo)})
        self.assertIn('systemMessage', json.loads(stop.stdout))
        self.assertFalse((repo / '.brain').exists())
        # Another turn still reminds even though it contains no trigger.
        again = self.boss('hook', 'prompt-submit', cwd=repo, payload={'session_id': 'k1', 'cwd': str(repo), 'prompt': '继续'})
        self.assertIn(pending[0]['id'], again.stdout)

    def test_resolution_requires_changed_document_in_owning_project(self):
        repo = make_repo(self.home / 'control')
        args = ['knowledge', 'flag', '--session', 'k2', '--path', str(repo), '--key', 'release-channel']
        rid = json.loads(self.boss(*args).stdout)[0]['id']
        self.assertEqual(len(json.loads(self.boss(*args).stdout)), 1)
        resolve = ['knowledge', 'resolve', '--session', 'k2', '--id', rid, '--status', 'updated', '--file']
        self.assertNotEqual(self.boss(*resolve, 'README.md').returncode, 0)
        outside = self.home / 'other.md'
        outside.write_text('unrelated')
        self.assertNotEqual(self.boss(*resolve, str(outside)).returncode, 0)
        (repo / 'README.md').write_text('Verified development and release channels\n')
        self.assertEqual(self.boss(*resolve, 'README.md').returncode, 0)
        self.assertEqual(json.loads(self.boss('knowledge', 'list', '--session', 'k2').stdout)[0]['status'], 'updated')
        self.assertEqual(json.loads(self.boss('knowledge', 'list', '--session', 'other').stdout), [])

    def test_no_write_request_is_candidate_not_authorization(self):
        repo = make_repo(self.home / 'control')
        result = self.boss('hook', 'prompt-submit', cwd=repo, payload={
            'session_id': 'k3', 'cwd': str(repo), 'prompt': '架构不对，只讨论，不要修改文件'})
        self.assertIn('不是已确认事实或写入授权', result.stdout)
        rid = json.loads(self.boss('knowledge', 'list', '--session', 'k3').stdout)[0]['id']
        self.boss('knowledge', 'resolve', '--session', 'k3', '--id', rid, '--status', 'deferred')
        self.assertFalse((repo / '.brain').exists())
        self.assertEqual((repo / 'README.md').read_text(), 'test\n')

    def test_modes_and_no_prompt_storage(self):
        repo = make_repo(self.home / 'control')
        for mode in ('disabled', 'observe-only'):
            self.boss('session', 'mode', mode, mode)
            r = self.boss('hook', 'prompt-submit', cwd=repo, payload={
                'session_id': mode, 'cwd': str(repo), 'prompt': '架构不对 unique-private-user-text'})
            self.assertNotIn('Brain 知识同步检查', r.stdout)
            entries = json.loads(self.boss('knowledge', 'list', '--session', mode).stdout)
            self.assertEqual(len(entries), 0 if mode == 'disabled' else 1)
            self.assertNotIn('unique-private-user-text', json.dumps(entries))

    def test_ordinary_question_and_ambiguous_workspace_do_not_flag(self):
        repo = make_repo(self.home / 'control')
        for cwd, prompt in ((repo, '你好'), (self.home, '小程序架构不对')):
            self.boss('hook', 'prompt-submit', cwd=cwd, payload={'session_id': 'k4', 'cwd': str(cwd), 'prompt': prompt})
        self.assertEqual(json.loads(self.boss('knowledge', 'list', '--session', 'k4').stdout), [])
