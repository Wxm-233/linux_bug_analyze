"""命令行默认值与 API 配置解析。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .hash_filter import DEFAULT_CROSS_ARCH_INCLUDE

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
class HashFilterSettings:
    """候选提交筛选器的可选默认值。"""

    source_file: Path | None = None
    output_file: Path | None = None
    audit_file: Path | None = None
    include: tuple[str, ...] = DEFAULT_CROSS_ARCH_INCLUDE
    exclude: tuple[str, ...] = ()
    fields: tuple[str, ...] = ("subject", "body", "files")
    match: str = "any"
    case_sensitive: bool = False
    workers: int | None = None
    max_diff_chars: int | None = None


@dataclass(frozen=True, slots=True)
class CveSourceSettings:
    """linux-cve-announce 本地镜像提取器的可选默认值。"""

    inbox_dir: Path | None = None
    output_file: Path | None = None
    audit_file: Path | None = None
    prefer_mainline: bool = True
    fallback_to_all: bool = False


@dataclass(frozen=True, slots=True)
class ResultSummarySettings:
    """分析结果汇总器的可选默认值。"""

    input_dir: Path | None = None
    output_dir: Path | None = None


@dataclass(frozen=True, slots=True)
class EvidenceSettings:
    """自动补充证据的可选默认值。"""

    mail_inbox_dirs: tuple[Path, ...] = ()
    include_fixes_commit: bool = True
    max_chars_per_source: int = 12_000
    max_total_chars: int = 36_000


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
    hash_filter: HashFilterSettings = field(default_factory=HashFilterSettings)
    cve_source: CveSourceSettings = field(default_factory=CveSourceSettings)
    evidence: EvidenceSettings = field(default_factory=EvidenceSettings)
    result_summary: ResultSummarySettings = field(default_factory=ResultSummarySettings)


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
    "hash_filter",
    "cve_source",
    "evidence",
    "result_summary",
}
_OPENAI_KEYS = {"api_key_file", "base_url", "model"}
_HASH_FILTER_KEYS = {
    "source_file",
    "output_file",
    "audit_file",
    "include",
    "exclude",
    "fields",
    "match",
    "case_sensitive",
    "workers",
    "max_diff_chars",
}
_CVE_SOURCE_KEYS = {
    "inbox_dir",
    "output_file",
    "audit_file",
    "prefer_mainline",
    "fallback_to_all",
}
_EVIDENCE_KEYS = {
    "mail_inbox_dirs",
    "include_fixes_commit",
    "max_chars_per_source",
    "max_total_chars",
}
_RESULT_SUMMARY_KEYS = {"input_dir", "output_dir"}


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


def _read_string_list(
    data: Mapping[str, Any],
    key: str,
    default: tuple[str, ...] = (),
) -> tuple[str, ...]:
    value = data.get(key)
    if value is None:
        return default
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigurationError(f"settings 中的 {key} 必须是字符串数组。")
    return tuple(item for item in (entry.strip() for entry in value) if item)


def _read_path_list(
    data: Mapping[str, Any], key: str, base_dir: Path
) -> tuple[Path, ...]:
    values = _read_string_list(data, key)
    paths: list[Path] = []
    for value in values:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = base_dir / path
        paths.append(path.resolve())
    return tuple(paths)


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
    hash_filter = data.get("hash_filter", {})
    if not isinstance(hash_filter, dict):
        raise ConfigurationError("settings 中的 hash_filter 必须是 TOML 表。")
    unknown_filter = set(hash_filter) - _HASH_FILTER_KEYS
    if unknown_filter:
        names = ", ".join(sorted(unknown_filter))
        raise ConfigurationError(f"settings 的 [hash_filter] 包含未知字段：{names}")

    match = _read_string(hash_filter, "match") or "any"
    if match not in {"any", "all"}:
        raise ConfigurationError("settings 中 hash_filter.match 必须是 any 或 all。")
    fields = _read_string_list(
        hash_filter,
        "fields",
        ("subject", "body", "files"),
    )
    valid_fields = {"subject", "body", "files", "diff"}
    invalid_fields = set(fields) - valid_fields
    if invalid_fields or not fields:
        names = ", ".join(sorted(invalid_fields)) or "（空）"
        raise ConfigurationError(
            "settings 中 hash_filter.fields 只能包含 subject、body、files、diff；"
            f"当前无效值：{names}"
        )
    cve_source = data.get("cve_source", {})
    if not isinstance(cve_source, dict):
        raise ConfigurationError("settings 中的 cve_source 必须是 TOML 表。")
    unknown_cve_source = set(cve_source) - _CVE_SOURCE_KEYS
    if unknown_cve_source:
        names = ", ".join(sorted(unknown_cve_source))
        raise ConfigurationError(f"settings 的 [cve_source] 包含未知字段：{names}")
    prefer_mainline = _read_bool(cve_source, "prefer_mainline")
    fallback_to_all = _read_bool(cve_source, "fallback_to_all")
    evidence = data.get("evidence", {})
    if not isinstance(evidence, dict):
        raise ConfigurationError("settings 中的 evidence 必须是 TOML 表。")
    unknown_evidence = set(evidence) - _EVIDENCE_KEYS
    if unknown_evidence:
        names = ", ".join(sorted(unknown_evidence))
        raise ConfigurationError(f"settings 的 [evidence] 包含未知字段：{names}")
    include_fixes_commit = _read_bool(evidence, "include_fixes_commit")
    max_chars_per_source = _read_int(evidence, "max_chars_per_source")
    max_total_chars = _read_int(evidence, "max_total_chars")
    if max_chars_per_source is not None and max_chars_per_source < 1:
        raise ConfigurationError("evidence.max_chars_per_source 必须大于 0。")
    if max_total_chars is not None and max_total_chars < 1:
        raise ConfigurationError("evidence.max_total_chars 必须大于 0。")
    result_summary = data.get("result_summary", {})
    if not isinstance(result_summary, dict):
        raise ConfigurationError("settings 中的 result_summary 必须是 TOML 表。")
    unknown_result_summary = set(result_summary) - _RESULT_SUMMARY_KEYS
    if unknown_result_summary:
        names = ", ".join(sorted(unknown_result_summary))
        raise ConfigurationError(
            f"settings 的 [result_summary] 包含未知字段：{names}"
        )

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
        hash_filter=HashFilterSettings(
            source_file=_read_path(hash_filter, "source_file", base_dir),
            output_file=_read_path(hash_filter, "output_file", base_dir),
            audit_file=_read_path(hash_filter, "audit_file", base_dir),
            include=_read_string_list(
                hash_filter,
                "include",
                DEFAULT_CROSS_ARCH_INCLUDE,
            ),
            exclude=_read_string_list(hash_filter, "exclude"),
            fields=fields,
            match=match,
            case_sensitive=_read_bool(hash_filter, "case_sensitive") or False,
            workers=_read_int(hash_filter, "workers"),
            max_diff_chars=_read_int(hash_filter, "max_diff_chars"),
        ),
        cve_source=CveSourceSettings(
            inbox_dir=_read_path(cve_source, "inbox_dir", base_dir),
            output_file=_read_path(cve_source, "output_file", base_dir),
            audit_file=_read_path(cve_source, "audit_file", base_dir),
            prefer_mainline=True if prefer_mainline is None else prefer_mainline,
            fallback_to_all=False if fallback_to_all is None else fallback_to_all,
        ),
        evidence=EvidenceSettings(
            mail_inbox_dirs=_read_path_list(evidence, "mail_inbox_dirs", base_dir),
            include_fixes_commit=(
                True if include_fixes_commit is None else include_fixes_commit
            ),
            max_chars_per_source=(
                12_000 if max_chars_per_source is None else max_chars_per_source
            ),
            max_total_chars=36_000 if max_total_chars is None else max_total_chars,
        ),
        result_summary=ResultSummarySettings(
            input_dir=_read_path(result_summary, "input_dir", base_dir),
            output_dir=_read_path(result_summary, "output_dir", base_dir),
        ),
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
