from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from linux_bug_analyze.cli import build_parser, main
from linux_bug_analyze.config import FileSettings


class SettingsArgumentTests(TestCase):
    def test_positionals_can_come_from_settings(self) -> None:
        settings = FileSettings(
            linux_dir=Path("settings-linux"),
            hashes_file=Path("settings-hashes"),
            workers=3,
            force=True,
        )
        args = build_parser(settings).parse_args([])
        self.assertEqual(args.linux_dir, Path("settings-linux"))
        self.assertEqual(args.hashes_file, Path("settings-hashes"))
        self.assertEqual(args.workers, 3)
        self.assertTrue(args.force)

    def test_command_line_overrides_settings(self) -> None:
        settings = FileSettings(
            linux_dir=Path("settings-linux"),
            hashes_file=Path("settings-hashes"),
            workers=3,
            force=True,
        )
        args = build_parser(settings).parse_args(
            ["cli-linux", "cli-hashes", "--workers", "2", "--no-force"]
        )
        self.assertEqual(args.linux_dir, Path("cli-linux"))
        self.assertEqual(args.hashes_file, Path("cli-hashes"))
        self.assertEqual(args.workers, 2)
        self.assertFalse(args.force)

    def test_main_can_run_with_only_settings_argument(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        with TemporaryDirectory() as directory:
            root = Path(directory)
            hashes_file = root / "hashes.txt"
            hashes_file.write_text("3094eaa\n", encoding="utf-8")
            settings_file = root / "settings.toml"
            settings_file.write_text(
                (
                    f'linux_dir = "{project_root.as_posix()}"\n'
                    f'hashes_file = "{hashes_file.as_posix()}"\n'
                    "end_index = 0\n"
                ),
                encoding="utf-8",
            )
            self.assertEqual(main(["--settings", str(settings_file)]), 0)
