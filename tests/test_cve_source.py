import json
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from linux_bug_analyze.cve_cli import main
from linux_bug_analyze.cve_source import parse_cve_message
from linux_bug_analyze.public_inbox import (
    InboxMessage,
    discover_epoch_repositories,
    iter_inbox_messages,
)


FAKE_STABLE_HASH = "b" * 40


def _git(*args: str, cwd: Path | None = None) -> str:
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


def _message(mainline_hash: str) -> bytes:
    return (
        "From: Linux CVE Announcements <cve@kernel.org>\n"
        "To: linux-cve-announce@vger.kernel.org\n"
        "Subject: CVE-2026-12345: test issue\n"
        "Message-ID: <20260821-CVE-2026-12345@example.test>\n"
        "Date: Fri, 21 Aug 2026 10:00:00 +0800\n"
        "Content-Type: text/plain; charset=utf-8\n"
        "\n"
        f"Issue introduced in 6.1 with commit {'d' * 40} and fixed in "
        f"6.1.1 with commit {FAKE_STABLE_HASH}\n"
        f"Issue introduced in 6.8 with commit {'e' * 40} and fixed in "
        f"6.9 with commit {mainline_hash}\n"
        f"https://git.kernel.org/stable/c/{FAKE_STABLE_HASH}\n"
        f"https://git.kernel.org/linus/{mainline_hash}\n"
    ).encode()


def _create_inbox(root: Path, raw_message: bytes) -> Path:
    worktree = root / "mail-worktree"
    worktree.mkdir()
    _git("init", cwd=worktree)
    _git("config", "user.email", "tests@example.test", cwd=worktree)
    _git("config", "user.name", "Tests", cwd=worktree)
    (worktree / "m").write_bytes(raw_message)
    _git("add", "m", cwd=worktree)
    _git("commit", "-m", "add message", cwd=worktree)

    inbox = root / "linux-cve-announce"
    epoch = inbox / "git" / "0.git"
    epoch.parent.mkdir(parents=True)
    _git("clone", "--bare", str(worktree), str(epoch))
    return inbox


class CveSourceTests(TestCase):
    def test_reads_public_inbox_epoch_and_parses_fix_references(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        mainline_hash = _git("rev-parse", "HEAD", cwd=project_root)
        raw_message = _message(mainline_hash)

        with TemporaryDirectory() as directory:
            inbox = _create_inbox(Path(directory), raw_message)

            epochs = discover_epoch_repositories(inbox)
            self.assertEqual(epochs[0][0], 0)
            messages = list(iter_inbox_messages(inbox))
            self.assertEqual(len(messages), 1)
            self.assertEqual(messages[0].raw_message, raw_message)

            record = parse_cve_message(messages[0])
            self.assertEqual(record.cve_ids, ["CVE-2026-12345"])
            self.assertEqual(
                [reference.reported_hash for reference in record.fixes],
                [FAKE_STABLE_HASH, mainline_hash],
            )
            self.assertEqual(
                record.fixes[0].sources,
                ["fixed-line", "git.kernel.org-url"],
            )

    def test_cli_uses_settings_and_keeps_only_mainline_commit(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        mainline_hash = _git("rev-parse", "HEAD", cwd=project_root)

        with TemporaryDirectory() as directory:
            root = Path(directory)
            inbox = _create_inbox(root, _message(mainline_hash))
            output = root / "candidate_hashes.txt"
            audit = root / "cve-audit.jsonl"
            settings = root / "settings.toml"
            settings.write_text(
                f"""
linux_dir = "{project_root.as_posix()}"

[hash_filter]
source_file = "{output.as_posix()}"

[cve_source]
inbox_dir = "{inbox.as_posix()}"
audit_file = "{audit.as_posix()}"
prefer_mainline = true
fallback_to_all = false
""".strip(),
                encoding="utf-8",
            )

            self.assertEqual(main(["--settings", str(settings)]), 0)
            self.assertEqual(output.read_text(encoding="utf-8").strip(), mainline_hash)

            record = json.loads(audit.read_text(encoding="utf-8"))
            self.assertEqual(record["status"], "selected")
            self.assertEqual(record["cve_ids"], ["CVE-2026-12345"])
            fixes = {fix["reported_hash"]: fix for fix in record["fixes"]}
            self.assertFalse(fixes[FAKE_STABLE_HASH]["in_linux_repo"])
            self.assertTrue(fixes[mainline_hash]["in_linux_repo"])
            self.assertTrue(fixes[mainline_hash]["emitted"])

    def test_parser_accepts_mbox_from_line(self) -> None:
        raw = b"From sender@example.test Sat Jan 01 00:00:00 2022\n" + _message("a" * 40)
        record = parse_cve_message(InboxMessage(0, "c" * 40, raw))
        self.assertEqual(record.cve_ids, ["CVE-2026-12345"])
        self.assertEqual(record.message_id, "<20260821-CVE-2026-12345@example.test>")
