#!/usr/bin/env python3
# C14 FIX: Crash recovery tests
import os, sys, tempfile, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'coordinator'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'plugins' / 'agent-coordination' / 'utils'))

from event_log import EventLog
from blackboard import Blackboard

class TestEventLogCrashRecovery(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.event_log = EventLog(self.test_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_recovery_from_empty_log(self):
        log_file = Path(self.test_dir) / '.coordination' / 'events.jsonl'
        log_file.parent.mkdir(parents=True, exist_ok=True)
        log_file.touch()
        state = self.event_log.get_current_state()
        self.assertIsNotNone(state)
        self.assertEqual(len(state['agents']), 0)

    def test_state_reconstruction_after_crash(self):
        self.event_log.append_event('agent.registered', {'agent_id': 'agent-1', 'task': 'test'})
        self.event_log.append_event('finding.added', {'agent_id': 'agent-1', 'finding_type': 'fact', 'content': 'Test'})
        new_log = EventLog(self.test_dir)
        state = new_log.get_current_state()
        self.assertIn('agent-1', state['agents'])
        self.assertEqual(len(state['findings']), 1)

class TestBlackboardCrashRecovery(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.blackboard = Blackboard(self.test_dir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_recovery_from_missing_blackboard(self):
        state = self.blackboard.get_full_state()
        self.assertIsNotNone(state)
        self.assertEqual(len(state['agents']), 0)

    def test_state_persistence_after_crash(self):
        self.blackboard.register_agent('agent-1', 'test task')
        self.blackboard.add_finding('agent-1', 'fact', 'Test finding')
        new_bb = Blackboard(self.test_dir)
        state = new_bb.get_full_state()
        self.assertIn('agent-1', state['agents'])
        self.assertEqual(len(state['findings']), 1)

if __name__ == '__main__':
    unittest.main()
