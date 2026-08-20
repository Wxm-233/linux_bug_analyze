"""命令行默认值与 API 配置解析。"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_API_KEY_FILE = PROJECT_ROOT / "OPENAI_API_KEY"
DEFAULT_CONTEXT_PATH = PROJECT_ROOT / "documents" / "新·论文思路梳理.md"
DEFAULT_BASE_URL = "https://llmapi.isrc.ac.cn/v1"
DEFAULT_MODEL = "DeepSeek-V4-Pro"


class ConfigurationError(ValueError):
    """配置缺失或无效。"""


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
