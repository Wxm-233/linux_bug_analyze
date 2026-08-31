from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from linux_bug_analyze.evidence import EvidenceCollector, linked_message_ids
from linux_bug_analyze.models import CommitInfo
from linux_bug_analyze.public_inbox import InboxMessage


class _Repository:
    def get_commit(self, commit_hash, _max_diff_chars, *, include_diff=True):
        if commit_hash.startswith("1234567"):
            return CommitInfo(
                requested_hash=commit_hash,
                hash="1" * 40,
                subject="introduce boundary behavior",
                author="author",
                date="date",
                body="old semantic assumption",
                files=("kernel/common.c",),
                diff="old diff" if include_diff else "",
            )
        return CommitInfo(
            requested_hash=commit_hash,
            hash="a" * 40,
            subject="fix",
            author="author",
            date="date",
            body=(
                "Fixes: 1234567890ab (\"introduce\")\n"
                "Link: https://lore.kernel.org/all/20260825-fix-v1@example.test/"
            ),
            files=("arch/arm/mm/fault.c",),
            diff="fix diff" if include_diff else "",
        )


class EvidenceTests(TestCase):
    def test_extracts_lore_message_id(self) -> None:
        body = (
            "Link: https://lore.kernel.org/r/ABC@example.test\n"
            "Closes: https://lore.kernel.org/all/second%40example.test/raw/\n"
        )
        self.assertEqual(
            linked_message_ids(body),
            ("abc@example.test", "second@example.test"),
        )

    def test_combines_fixes_commit_and_manual_evidence(self) -> None:
        repository = _Repository()
        commit = repository.get_commit("a" * 40, 1000)
        with TemporaryDirectory() as directory:
            evidence_dir = Path(directory)
            (evidence_dir / f"{commit.hash}.md").write_text(
                "manual bug report", encoding="utf-8"
            )
            collector = EvidenceCollector(repository, evidence_dir=evidence_dir)
            evidence = collector.collect(commit)

        self.assertIn("===== Fixes 引入提交 =====", evidence)
        self.assertIn("old semantic assumption", evidence)
        self.assertIn("===== 人工补充材料 =====", evidence)
        self.assertIn("manual bug report", evidence)

    def test_matches_linked_discussion_from_local_inbox_once(self) -> None:
        repository = _Repository()
        raw = (
            "From: reviewer@example.test\n"
            "Subject: Re: fix\n"
            "Message-ID: <20260825-fix-v1@example.test>\n"
            "Content-Type: text/plain; charset=utf-8\n\n"
            "runtime reproduction and review discussion\n"
        ).encode()
        collector = EvidenceCollector(
            repository,
            mail_inbox_dirs=(Path("local-inbox"),),
            include_fixes_commit=False,
        )
        with patch(
            "linux_bug_analyze.evidence.iter_inbox_messages",
            return_value=iter((InboxMessage(0, "b" * 40, raw),)),
        ) as iterator:
            collector.prepare(("a" * 40,))
        evidence = collector.collect(repository.get_commit("a" * 40, 1000))

        iterator.assert_called_once()
        self.assertIn("===== 本地邮件讨论 =====", evidence)
        self.assertIn("runtime reproduction", evidence)
