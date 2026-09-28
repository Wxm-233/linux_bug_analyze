import tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from experiments.holdout_review.stratified_pilot import restore_budget
from linux_bug_analyze.screening import ScreenRunner,StopRun

class PilotBudgetTests(unittest.TestCase):
    def runner(self,path):
        return ScreenRunner(None,Path(path),model='offline',max_requests=600,token_budget=4000000)
    def test_inflight_reservation_not_refunded(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=self.runner(folder)
            restore_budget(runner,{'max_requests':600,'token_budget':4000000,'requests':4,'charged_tokens':3999999,'reported_tokens':20,'records':[{'status':'request_in_flight'}]})
            commit=SimpleNamespace(hash='a'*40,subject='cleanup',body='',files=[],diff='',diff_truncated=False)
            with self.assertRaises(StopRun):runner.screen(commit,'')
            self.assertEqual(runner.requests,4)
            self.assertEqual(runner.charged_tokens,3999999)
    def test_request_cap_persists(self):
        with tempfile.TemporaryDirectory() as folder:
            runner=self.runner(folder)
            restore_budget(runner,{'max_requests':600,'token_budget':4000000,'requests':600,'charged_tokens':20,'reported_tokens':20,'records':[]})
            commit=SimpleNamespace(hash='a'*40,subject='cleanup',body='',files=[],diff='',diff_truncated=False)
            with self.assertRaises(StopRun):runner.screen(commit,'')
            self.assertEqual(runner.requests,600)
    def test_reject_different_budget(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(AssertionError):restore_budget(self.runner(folder),{'max_requests':601,'token_budget':4000000})
