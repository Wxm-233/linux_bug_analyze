from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from linux_bug_analyze.config import ConfigurationError, resolve_api_key


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
