from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from linux_bug_analyze.git_repository import GitRepositoryError, read_hashes, truncate_diff


class HashFileTests(TestCase):
    def test_reads_comments_and_deduplicates(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "hashes.txt"
            path.write_text("# comment\nAbCd\n\nabcd\n1234\n", encoding="utf-8")
            self.assertEqual(read_hashes(path), ["AbCd", "1234"])

    def test_rejects_non_hash_revision(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "hashes.txt"
            path.write_text("HEAD\n", encoding="utf-8")
            with self.assertRaises(GitRepositoryError):
                read_hashes(path)


class TruncateDiffTests(TestCase):
    def test_zero_keeps_complete_diff(self) -> None:
        self.assertEqual(truncate_diff("abcdef", 0), ("abcdef", False))

    def test_truncation_keeps_both_ends_and_limit(self) -> None:
        diff = "A" * 500 + "B" * 500
        result, truncated = truncate_diff(diff, 200)
        self.assertTrue(truncated)
        self.assertLessEqual(len(result), 200)
        self.assertTrue(result.startswith("A"))
        self.assertTrue(result.endswith("B"))
        self.assertIn("diff 已截断", result)
