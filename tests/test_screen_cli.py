import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
from types import SimpleNamespace as NS

from linux_bug_analyze.config import FileSettings
from linux_bug_analyze.models import CommitInfo
from linux_bug_analyze.screen_cli import main
from tests.test_screening import response


class ScreenCliTests(TestCase):
    def test_small_batch_exports_only_review_items_and_resumes_without_calls(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            hashes = root / "hashes.txt"
            hashes.write_text("aaaa\nbbbb\ncccc\n", encoding="utf-8")
            settings = FileSettings(linux_dir=root, hashes_file=hashes, api_key_file=root / "outside-key")
            output = root / "out"
            with patch("linux_bug_analyze.screen_cli.load_settings", return_value=settings), \
                 patch("linux_bug_analyze.screen_cli.resolve_api_key", return_value="test-placeholder"), \
                 patch("linux_bug_analyze.screen_cli.create_openai_client") as client, \
                 patch("linux_bug_analyze.screen_cli.GitRepository") as repo:
                repo.return_value.get_commit.side_effect = lambda h, _: CommitInfo(h, h, "fix dma", "a", "d", "", (), "diff")
                create = client.return_value.chat.completions.create
                create.side_effect = [response(), response("related")]
                args = ["--outdir", str(output), "--max-items", "2"]
                self.assertEqual(main(args), 0)
                self.assertEqual(create.call_count, 2)
                self.assertEqual((output / "selected_hashes.txt").read_text(), "bbbb\n")
                self.assertEqual(main(args), 0)
                self.assertEqual(create.call_count, 2)
                self.assertEqual(len(list((output / "runs").glob("*/usage.json"))), 2)
                self.assertEqual(json.loads((output / "usage.json").read_text())["requests"], 0)

    def test_invalid_budget_rejected_before_loading_key(self):
        with patch("linux_bug_analyze.screen_cli.resolve_api_key") as key:
            with self.assertRaises(SystemExit):
                main(["--max-requests", "0"])
            key.assert_not_called()
