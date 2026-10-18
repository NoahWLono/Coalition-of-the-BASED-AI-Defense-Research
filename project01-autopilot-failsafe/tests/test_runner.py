import unittest
import tempfile
from pathlib import Path
try:
    from failsafelab.runner import validate_scenario, isolation_ok
except ImportError:
    validate_scenario = isolation_ok = None

class RunnerContract(unittest.TestCase):
    def test_rejects_external_action_and_unsorted_events(self):
        self.assertIsNotNone(validate_scenario, 'runner validation not implemented')
        for events in [[{'id':'a','at_s':1,'kind':'shell','command':'x'}], [{'id':'a','at_s':2,'kind':'heartbeat','enabled':False},{'id':'b','at_s':1,'kind':'heartbeat','enabled':True}], [{'id':'a','at_s':1,'kind':'parameter','name':'SERIAL0_PROTOCOL','value':1}]]:
            with self.assertRaises(ValueError):
                validate_scenario({'id':'test','duration_s':10,'events':events})
    def test_requires_private_loopback_only_network(self):
        self.assertIsNotNone(isolation_ok, 'isolation check not implemented')
        self.assertFalse(isolation_ok(['lo','eth0'], 'net:[1]', 'net:[2]'))
        self.assertFalse(isolation_ok(['lo'], 'net:[1]', 'net:[1]'))
        self.assertTrue(isolation_ok(['lo'], 'net:[1]', 'net:[2]'))

class OutputScope(unittest.TestCase):
    def test_rejects_output_outside_project_evidence(self):
        from failsafelab import runner
        self.assertTrue(hasattr(runner,'validated_output'),'output scoping missing')
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): runner.validated_output(Path(d)/'outside')
    def test_accepts_fresh_evidence_subdirectory(self):
        from failsafelab import runner
        self.assertTrue(hasattr(runner,'validated_output'),'output scoping missing')
        self.assertEqual(runner.validated_output(runner.ROOT/'evidence'/'future-case'),runner.ROOT/'evidence'/'future-case')

if __name__=='__main__': unittest.main()
