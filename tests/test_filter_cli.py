import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from linux_bug_analyze.filter_cli import main


class FilterCliTests(TestCase):
    def test_filters_real_git_commit_using_only_settings(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "candidates.txt"
            output = root / "filtered.txt"
            audit = root / "audit.jsonl"
            source.write_text("3094eaa\n", encoding="utf-8")
            settings = root / "settings.toml"
            settings.write_text(
                f"""
linux_dir = "{project_root.as_posix()}"
hashes_file = "{output.as_posix()}"

[hash_filter]
source_file = "{source.as_posix()}"
audit_file = "{audit.as_posix()}"
include = ["init"]
fields = ["subject"]
""".strip(),
                encoding="utf-8",
            )

            self.assertEqual(main(["--settings", str(settings)]), 0)
            self.assertEqual(
                output.read_text(encoding="utf-8").strip(),
                "3094eaa058d2e3bf827dae8afd39b05182a2cb5b",
            )
            record = json.loads(audit.read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "selected")
            self.assertEqual(record["include_matches"][0]["pattern"], "init")
