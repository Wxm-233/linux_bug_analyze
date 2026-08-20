"""命令行默认值与 API 配置解析。"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - 仅 Python 3.10 使用
    import tomli as tomllib


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API_KEY_FILE = PROJECT_ROOT / "OPENAI_API_KEY"
DEFAULT_CONTEXT_PATH = PROJECT_ROOT / "documents" / "新·论文思路梳理.md"
DEFAULT_BASE_URL = "https://llmapi.isrc.ac.cn/v1"
DEFAULT_MODEL = "DeepSeek-V4-Pro"
DEFAULT_SETTINGS_PATH = Path("settings.toml")


class ConfigurationError(ValueError):
    """配置缺失或无效。"""


@dataclass(frozen=True, slots=True)
class FileSettings:
    """从 TOML 文件读取的可选命令行默认值。"""

    source: Path | None = None
    linux_dir: Path | None = None
    hashes_file: Path | None = None
    outdir: Path | None = None
    context_md: Path | None = None
    evidence_dir: Path | None = None
    workers: int | None = None
    force: bool | None = None
    max_tokens: int | None = None
    max_diff_chars: int | None = None
    start_index: int | None = None
    end_index: int | None = None
    api_key_file: Path | None = None
    base_url: str | None = None
    model: str | None = None


_ROOT_KEYS = {
    "linux_dir",
    "hashes_file",
    "outdir",
    "context_md",
    "evidence_dir",
    "workers",
    "force",
    "max_tokens",
    "max_diff_chars",
    "start_index",
    "end_index",
    "openai",
}
_OPENAI_KEYS = {"api_key_file", "base_url", "model"}


def _read_path(data: Mapping[str, Any], key: str, base_dir: Path) -> Path | None:
    value = data.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ConfigurationError(f"settings 中的 {key} 必须是字符串路径。")
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path.resolve()


def _read_int(data: Mapping[str, Any], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"settings 中的 {key} 必须是整数。")
    return value


def _read_bool(data: Mapping[str, Any], key: str) -> bool | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ConfigurationError(f"settings 中的 {key} 必须是 true 或 false。")
    return value


def _read_string(data: Mapping[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise ConfigurationError(f"settings 中的 {key} 必须是字符串。")
    return value.strip() or None


def load_settings(path: Path, *, required: bool = False) -> FileSettings:
    """读取 TOML settings；其中的相对路径以 settings 所在目录为基准。"""

    source = path.expanduser().resolve()
    if not source.is_file():
        if required:
            raise ConfigurationError(f"找不到 settings 文件：{source}")
        return FileSettings(source=source)
    try:
        with source.open("rb") as stream:
            data = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"无法读取 settings 文件 {source}: {exc}") from exc

    unknown = set(data) - _ROOT_KEYS
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigurationError(f"settings 包含未知字段：{names}")
    openai = data.get("openai", {})
    if not isinstance(openai, dict):
        raise ConfigurationError("settings 中的 openai 必须是 TOML 表。")
    unknown_openai = set(openai) - _OPENAI_KEYS
    if unknown_openai:
        names = ", ".join(sorted(unknown_openai))
        raise ConfigurationError(f"settings 的 [openai] 包含未知字段：{names}")

    base_dir = source.parent
    return FileSettings(
        source=source,
        linux_dir=_read_path(data, "linux_dir", base_dir),
        hashes_file=_read_path(data, "hashes_file", base_dir),
        outdir=_read_path(data, "outdir", base_dir),
        context_md=_read_path(data, "context_md", base_dir),
        evidence_dir=_read_path(data, "evidence_dir", base_dir),
        workers=_read_int(data, "workers"),
        force=_read_bool(data, "force"),
        max_tokens=_read_int(data, "max_tokens"),
        max_diff_chars=_read_int(data, "max_diff_chars"),
        start_index=_read_int(data, "start_index"),
        end_index=_read_int(data, "end_index"),
        api_key_file=_read_path(openai, "api_key_file", base_dir),
        base_url=_read_string(openai, "base_url"),
        model=_read_string(openai, "model"),
    )


def resolve_api_key(
    cli_value: str | None,
    key_file: Path,
    environ: Mapping[str, str] | None = None,
) -> str:
    """按命令行、环境变量、密钥文件的顺序解析 API Key。"""

    env = os.environ if environ is None else environ
    if cli_value and cli_value.strip():
        return cli_value.strip()
    if env.get("OPENAI_API_KEY", "").strip():
        return env["OPENAI_API_KEY"].strip()
    try:
        value = key_file.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ConfigurationError(
            "缺少 API Key：请使用 --api-key、OPENAI_API_KEY 环境变量，"
            f"或密钥文件 {key_file}。"
        ) from exc
    if not value:
        raise ConfigurationError(f"API Key 文件为空：{key_file}")
    return value


def resolve_setting(
    cli_value: str | None,
    env_name: str,
    default: str,
    environ: Mapping[str, str] | None = None,
) -> str:
    """按命令行、环境变量、默认值的顺序解析普通配置。"""

    env = os.environ if environ is None else environ
    return (cli_value or env.get(env_name) or default).strip()
