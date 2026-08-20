from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from linux_bug_analyze.models import AnalysisResult
from linux_bug_analyze.reporting import is_successful_report, write_index, write_report


class ReportingTests(TestCase):
    def test_empty_or_incomplete_legacy_report_is_not_success(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "report.md"
            path.write_text("", encoding="utf-8")
            self.assertFalse(is_successful_report(path))
            path.write_text("# hash\n\n## 模型分析\n", encoding="utf-8")
            self.assertFalse(is_successful_report(path))

    def test_failure_report_is_retryable_and_index_uses_same_name(self) -> None:
        result = AnalysisResult.failure("abcd", "git failed")
        with TemporaryDirectory() as directory:
            output_dir = Path(directory)
            report = write_report(output_dir, result)
            self.assertFalse(is_successful_report(report))
            index = write_index(output_dir, [result]).read_text(encoding="utf-8")
            self.assertIn("[abcd](./abcd.md)", index)

    def test_success_report_is_recognized(self) -> None:
        result = AnalysisResult(
            requested_hash="abcd",
            hash="a" * 40,
            subject="subject",
            author="author",
            date="date",
            analysis="analysis",
        )
        with TemporaryDirectory() as directory:
            report = write_report(Path(directory), result)
            self.assertTrue(is_successful_report(report))
