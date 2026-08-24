from unittest import TestCase

from linux_bug_analyze.models import AnalysisClassification, CommitInfo, ModelAnalysis
from linux_bug_analyze.pipeline import analyze_commits


class _Repository:
    def get_commit(self, commit_hash, _max_diff_chars):
        if commit_hash == "bad0":
            raise RuntimeError("bad commit")
        return CommitInfo(
            requested_hash=commit_hash,
            hash=commit_hash * 10,
            subject="subject",
            author="author",
            date="date",
            body="body",
            files=("file.c",),
            diff="diff",
        )


class _Analyzer:
    def analyze(self, _prompt):
        return ModelAnalysis(
            AnalysisClassification(
                relevance="related",
                categories=("implicit_semantic_assumption",),
                confidence="medium",
            ),
            "analysis",
        )


class PipelineTests(TestCase):
    def test_one_commit_failure_does_not_abort_batch(self) -> None:
        results = list(
            analyze_commits(
                _Repository(),
                ["good", "bad0"],
                "context",
                _Analyzer(),
                workers=2,
                max_diff_chars=1000,
            )
        )
        by_hash = {result.requested_hash: result for result in results}
        self.assertTrue(by_hash["good"].succeeded)
        self.assertFalse(by_hash["bad0"].succeeded)
