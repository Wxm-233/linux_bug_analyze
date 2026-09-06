import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from linux_bug_analyze.commit_cli import main
from linux_bug_analyze.commit_source import iter_mainline_commits


def _git(*args: str, cwd: Path) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return process.stdout.strip()


def _commit(root: Path, relative: str, content: str, message: str) -> str:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git("add", relative, cwd=root)
    _git("commit", "-m", message, cwd=root)
    return _git("rev-parse", "HEAD", cwd=root)


class CommitSourceTests(TestCase):
    def test_streams_commit_metadata_and_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            _git("init", cwd=root)
            _git("config", "user.email", "tests@example.test", cwd=root)
            _git("config", "user.name", "Tests", cwd=root)
            first = _commit(root, "drivers/test.c", "one", "generic fix")
            second = _commit(root, "arch/riscv/mm/test.c", "two", "RISC-V fix")

            commits = list(
                iter_mainline_commits(
                    root,
                    since="2000-01-01",
                    until="2030-01-01",
                )
            )

            self.assertEqual([commit.hash for commit in commits], [first, second])
            self.assertEqual(commits[1].subject, "RISC-V fix")
            self.assertEqual(commits[1].files, ("arch/riscv/mm/test.c",))

    def test_cli_scans_mainline_and_writes_only_matching_candidates(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            repo = root / "linux"
            repo.mkdir()
            _git("init", cwd=repo)
            _git("config", "user.email", "tests@example.test", cwd=repo)
            _git("config", "user.name", "Tests", cwd=repo)
            _commit(repo, "drivers/test.c", "one", "generic cleanup")
            riscv = _commit(repo, "arch/riscv/mm/test.c", "two", "RISC-V fix")
            ordering = _commit(
                repo,
                "kernel/common.c",
                "three",
                "fix memory ordering across architectures",
            )
            output = root / "candidate_hashes.txt"
            audit = root / "candidate-audit.jsonl"
            settings = root / "settings.toml"
            settings.write_text(
                f"""
linux_dir = "{repo.as_posix()}"
hashes_file = "{output.as_posix()}"

[commit_source]
since = "2000-01-01"
until = "2030-01-01"
audit_file = "{audit.as_posix()}"

[hash_filter]
include = ['risc-?v', 'memory ordering']
fields = ["subject", "body", "files"]
match = "any"
""".strip(),
                encoding="utf-8",
            )

            self.assertEqual(main(["--settings", str(settings)]), 0)
            self.assertEqual(
                output.read_text(encoding="utf-8").splitlines(),
                [riscv, ordering],
            )
            records = [
                json.loads(line)
                for line in audit.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(records[0]["source"], "linux-mainline-git")
            self.assertEqual(records[0]["scanned"], 3)
            self.assertEqual(records[0]["selected"], 2)
            self.assertTrue(all(record["record_type"] == "selected" for record in records[1:]))
