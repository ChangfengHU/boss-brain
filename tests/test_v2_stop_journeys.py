"""Replay the existing user Stop journeys through real v2 work bindings.

The fixture keeps a synthetic GitHub origin for Brain identity and uses a separate
local bare upstream for every push; no network or real project writes occur.
"""
from pathlib import Path
import unittest

from tests import test_user_journeys as legacy


class V2StopJourney(unittest.TestCase):
    tearDown = legacy.UserJourneyTest.tearDown

    def setUp(self):
        legacy.UserJourneyTest.setUp(self)
        result = legacy.UserJourneyTest.boss(self, 'init', '--rules-only')
        self.assertEqual(result.returncode, 0, result.stderr)

    def boss(self, *args, **kwargs):
        if args[:2] == ('hook', 'session-start'):
            payload = kwargs['payload']
            root = Path(payload['cwd'])
            for command in [('remote', 'rename', 'origin', 'fixture-upstream'),
                            ('remote', 'add', 'origin', f'https://github.com/me/{root.name}.git')]:
                self.assertEqual(legacy.git(root, *command).returncode, 0)
            result = legacy.UserJourneyTest.boss(self, 'adopt', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            for command in [('add', '.brain/manifest.json'), ('commit', '-m', 'fixture Brain setup'), ('push',)]:
                self.assertEqual(legacy.git(root, *command).returncode, 0)
            result = legacy.UserJourneyTest.boss(self, 'session', 'bind', payload['session_id'],
                '--task-id', 'FIXTURE-WORK', '--project', root.name, '--access', 'work')
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        return legacy.UserJourneyTest.boss(self, *args, **kwargs)

    test_guarded_block_clears_after_user_pushes = legacy.UserJourneyTest.test_guarded_block_clears_after_user_pushes
    test_strict_block_clears_after_continuity_records_are_complete = legacy.UserJourneyTest.test_strict_block_clears_after_continuity_records_are_complete
    test_stale_evidence_and_preexisting_dev_log_do_not_satisfy_current_work = legacy.UserJourneyTest.test_stale_evidence_and_preexisting_dev_log_do_not_satisfy_current_work
    test_uncommitted_brain_records_remain_a_data_loss_block = legacy.UserJourneyTest.test_uncommitted_brain_records_remain_a_data_loss_block


if __name__ == '__main__':
    unittest.main()
