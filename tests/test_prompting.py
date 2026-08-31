from unittest import TestCase

from linux_bug_analyze.models import CommitInfo
from linux_bug_analyze.prompting import build_prompt


class PromptTests(TestCase):
    def test_prompt_requires_relevance_and_evidence_audit(self) -> None:
        commit = CommitInfo(
            requested_hash="abcd",
            hash="a" * 40,
            subject="fix something",
            author="Author",
            date="2026-01-01",
            body="commit claim",
            files=("arch/foo/file.c",),
            diff="diff fact",
            diff_truncated=True,
            original_diff_chars=60000,
        )
        prompt = build_prompt(commit, "research context")
        self.assertIn("<<<LBA_METADATA_V2>>>", prompt)
        self.assertIn('"relevance":"related"', prompt)
        self.assertIn("## 判定理由", prompt)
        self.assertIn("正文不要再次输出结论", prompt)
        self.assertIn("### 反证与替代解释", prompt)
        self.assertIn("应修改的层次", prompt)
        self.assertIn("原始 60000 字符", prompt)
        self.assertIn("不得声称看过邮件", prompt)
        self.assertIn('"related_architectures":["arm32"]', prompt)
        self.assertIn("arch/arm 对应 arm32", prompt)
        self.assertIn("不能只因某个", prompt)
