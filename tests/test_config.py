from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from linux_bug_analyze.config import (
    ConfigurationError,
    load_settings,
    resolve_api_key,
    resolve_setting,
)


class LoadSettingsTests(TestCase):
    def test_loads_values_and_resolves_paths_from_settings_directory(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "settings.toml"
            path.write_text(
                """
linux_dir = "repos/linux"
hashes_file = "input/hashes.txt"
outdir = "results"
workers = 3
force = true

[openai]
api_key_file = "secrets/key"
base_url = "https://example.test/v1"
model = "test-model"

[hash_filter]
source_file = "input/candidates.txt"
include = ["riscv", "(^|/)arch/"]
fields = ["subject", "files"]
match = "all"
case_sensitive = true
""".strip(),
                encoding="utf-8",
            )

            settings = load_settings(path, required=True)

            self.assertEqual(settings.linux_dir, (root / "repos/linux").resolve())
            self.assertEqual(settings.hashes_file, (root / "input/hashes.txt").resolve())
            self.assertEqual(settings.outdir, (root / "results").resolve())
            self.assertEqual(settings.api_key_file, (root / "secrets/key").resolve())
            self.assertEqual(settings.workers, 3)
            self.assertTrue(settings.force)
            self.assertEqual(settings.base_url, "https://example.test/v1")
            self.assertEqual(settings.model, "test-model")
            self.assertEqual(
                settings.hash_filter.source_file,
                (root / "input/candidates.txt").resolve(),
            )
            self.assertEqual(settings.hash_filter.include, ("riscv", "(^|/)arch/"))
            self.assertEqual(settings.hash_filter.fields, ("subject", "files"))
            self.assertEqual(settings.hash_filter.match, "all")
            self.assertTrue(settings.hash_filter.case_sensitive)

    def test_rejects_unknown_field(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "settings.toml"
            path.write_text("workres = 3\n", encoding="utf-8")
            with self.assertRaises(ConfigurationError):
                load_settings(path, required=True)

    def test_missing_default_is_allowed_but_explicit_file_is_required(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "missing.toml"
            self.assertIsNone(load_settings(path).linux_dir)
            with self.assertRaises(ConfigurationError):
                load_settings(path, required=True)


class ResolveApiKeyTests(TestCase):
    def test_priority_is_cli_then_environment_then_file(self) -> None:
        with TemporaryDirectory() as directory:
            key_file = Path(directory) / "key"
            key_file.write_text("from-file\n", encoding="utf-8")
            self.assertEqual(
                resolve_api_key("from-cli", key_file, {"OPENAI_API_KEY": "from-env"}),
                "from-cli",
            )
            self.assertEqual(
                resolve_api_key(None, key_file, {"OPENAI_API_KEY": "from-env"}),
                "from-env",
            )
            self.assertEqual(resolve_api_key(None, key_file, {}), "from-file")

    def test_missing_key_is_reported_only_when_resolved(self) -> None:
        with TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            with self.assertRaises(ConfigurationError):
                resolve_api_key(None, missing, {})

    def test_normal_setting_priority_is_cli_then_environment_then_default(self) -> None:
        self.assertEqual(
            resolve_setting("cli", "OPENAI_MODEL", "settings", {"OPENAI_MODEL": "env"}),
            "cli",
        )
        self.assertEqual(
            resolve_setting(None, "OPENAI_MODEL", "settings", {"OPENAI_MODEL": "env"}),
            "env",
        )
        self.assertEqual(resolve_setting(None, "OPENAI_MODEL", "settings", {}), "settings")
