"""分析结果统计与相关提交筛选命令行。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import DEFAULT_SETTINGS_PATH, ConfigurationError, FileSettings, load_settings
from .result_summary import ResultSummaryError, write_summary


def build_summary_parser(settings: FileSettings | None = None) -> argparse.ArgumentParser:
    settings = settings or FileSettings()
    summary_settings = settings.result_summary
    parser = argparse.ArgumentParser(
        description="统计分析结论并生成相关提交 hash、CSV 和索引。"
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        type=Path,
        default=summary_settings.input_dir or settings.outdir or Path("analysis_out"),
        help="分析报告目录；默认使用 [result_summary].input_dir 或 outdir",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=summary_settings.output_dir,
        help="汇总文件目录；默认与 input_dir 相同",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=settings.source or DEFAULT_SETTINGS_PATH,
        help=f"TOML 配置文件（默认 {DEFAULT_SETTINGS_PATH}，不存在时忽略）",
    )
    return parser


def _settings_argument(argv: list[str] | None) -> tuple[Path, bool]:
    values = sys.argv[1:] if argv is None else argv
    pre_parser = argparse.ArgumentParser(add_help=False)
    pre_parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS_PATH)
    known, _ = pre_parser.parse_known_args(values)
    explicit = any(
        value == "--settings" or value.startswith("--settings=") for value in values
    )
    return known.settings, explicit


def main(argv: list[str] | None = None) -> int:
    settings_path, settings_required = _settings_argument(argv)
    try:
        settings = load_settings(settings_path, required=settings_required)
    except ConfigurationError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2

    parser = build_summary_parser(settings)
    args = parser.parse_args(argv)
    output_dir = args.output_dir or args.input_dir
    try:
        summary, paths = write_summary(args.input_dir, output_dir)
    except (OSError, ResultSummaryError) as exc:
        print(f"[错误] 无法汇总分析结果：{exc}", file=sys.stderr)
        return 2

    counts = summary["counts"]
    relevance = counts["by_relevance"]
    statuses = counts["by_status"]
    print(
        f"[完成] 总记录 {counts['total']}，成功 {statuses['success']}，"
        f"相关 {relevance['related']}，不相关 {relevance['unrelated']}，"
        f"不确定 {relevance['uncertain']}，无效元数据 {statuses['invalid_metadata']}，"
        f"旧格式不明确 {statuses['legacy_ambiguous']}；汇总：{paths['summary']}"
    )
    format_problems = statuses["invalid_metadata"] + statuses["legacy_ambiguous"]
    return 1 if format_problems else 0
