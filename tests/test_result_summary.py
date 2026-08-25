import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from linux_bug_analyze.models import AnalysisClassification, AnalysisResult
from linux_bug_analyze.reporting import SUCCESS_MARKER, write_report
from linux_bug_analyze.result_summary import (
    parse_legacy_classification,
    write_summary,
)
from linux_bug_analyze.summary_cli import main


def _success(commit_hash: str, relevance: str) -> AnalysisResult:
    categories = ("implicit_semantic_assumption",) if relevance == "related" else ()
    return AnalysisResult(
        requested_hash=commit_hash,
        hash=commit_hash,
        subject=f"subject-{commit_hash[0]}",
        author="author",
        date="date",
        analysis="## 提交概述\noverview",
        classification=AnalysisClassification(relevance, categories, "high"),
        model="test-model",
    )


class ResultSummaryTests(TestCase):
    def test_legacy_parser_accepts_bold_fields_on_one_line(self) -> None:
        classification = parse_legacy_classification(
            """## 研究相关性判定
- **结论**：不相关- **类型**：不适用- **置信度**：高

## 语义卡片
..."""
        )
        self.assertEqual(classification.relevance, "unrelated")
        self.assertEqual(classification.categories, ())
        self.assertEqual(classification.confidence, "high")

    def test_writes_statistics_and_related_outputs(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            related_hash = "a" * 40
            unrelated_hash = "b" * 40
            legacy_hash = "c" * 40
            missing_meta_hash = "d" * 40
            failure_hash = "e" * 40
            write_report(root, _success(related_hash, "related"))
            write_report(root, _success(unrelated_hash, "unrelated"))
            write_report(root, AnalysisResult.failure(failure_hash, "failed"))
            (root / f"{legacy_hash}.md").write_text(
                f"""{SUCCESS_MARKER}
# {legacy_hash}

- **标题**: legacy subject

## 模型分析

## 研究相关性判定
- **结论**：不相关- **类型**：不适用- **置信度**：高

## 语义卡片
...
""",
                encoding="utf-8",
            )
            (root / f"{missing_meta_hash}.md").write_text(
                "<!-- linux-bug-analyze-status: success; report-format: 2 -->\n",
                encoding="utf-8",
            )

            summary, paths = write_summary(root, root)

            counts = summary["counts"]
            self.assertEqual(counts["total"], 5)
            self.assertEqual(counts["by_status"]["success"], 3)
            self.assertEqual(counts["by_status"]["failure"], 1)
            self.assertEqual(counts["by_status"]["invalid_metadata"], 1)
            self.assertEqual(counts["by_relevance"]["related"], 1)
            self.assertEqual(counts["by_relevance"]["unrelated"], 2)
            self.assertEqual(counts["related_rate_among_success"], 1 / 3)
            self.assertEqual(
                paths["related_hashes"].read_text(encoding="utf-8"),
                f"{related_hash}\n",
            )
            related_reports = paths["related_reports"]
            self.assertTrue((related_reports / f"{related_hash}.md").is_file())
            self.assertTrue(
                (related_reports / f"{related_hash}.meta.json").is_file()
            )
            self.assertFalse((related_reports / f"{unrelated_hash}.md").exists())
            related_index = paths["related_index"].read_text(encoding="utf-8")
            self.assertIn(related_hash, related_index)
            self.assertIn(f"related_reports/{related_hash}.md", related_index)
            rows = list(
                csv.DictReader(paths["csv"].read_text(encoding="utf-8").splitlines())
            )
            legacy = next(row for row in rows if row["commit_hash"] == legacy_hash)
            self.assertEqual(legacy["source_format"], "legacy_markdown")
            self.assertEqual(legacy["relevance"], "unrelated")
            persisted = json.loads(paths["summary"].read_text(encoding="utf-8"))
            self.assertEqual(persisted["counts"]["by_relevance"]["related"], 1)

    def test_cli_uses_root_outdir_from_settings(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            reports = root / "reports"
            reports.mkdir()
            write_report(reports, _success("a" * 40, "related"))
            settings = root / "settings.toml"
            settings.write_text(
                f'outdir = "{reports.as_posix()}"\n',
                encoding="utf-8",
            )
            self.assertEqual(main(["--settings", str(settings)]), 0)
            self.assertTrue((reports / "summary.json").is_file())
            self.assertTrue((reports / "related_hashes.txt").is_file())
            self.assertTrue(
                (reports / "related_reports" / f"{'a' * 40}.md").is_file()
            )

    def test_removes_only_stale_managed_files_from_related_folder(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            commit_hash = "a" * 40
            write_report(root, _success(commit_hash, "related"))
            _, paths = write_summary(root, root)
            related_root = paths["related_reports"]
            user_file = related_root / "notes.txt"
            user_file.write_text("keep", encoding="utf-8")

            metadata_file = root / f"{commit_hash}.meta.json"
            metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
            metadata["classification"]["relevance"] = "unrelated"
            metadata["classification"]["categories"] = []
            metadata_file.write_text(
                json.dumps(metadata, ensure_ascii=False),
                encoding="utf-8",
            )
            write_summary(root, root)

            self.assertFalse((related_root / f"{commit_hash}.md").exists())
            self.assertFalse((related_root / f"{commit_hash}.meta.json").exists())
            self.assertEqual(user_file.read_text(encoding="utf-8"), "keep")
