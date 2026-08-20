"""候选 commit hash 筛选器命令行入口。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import (
    DEFAULT_SETTINGS_PATH,
    ConfigurationError,
    FileSettings,
    load_settings,
)
from .git_repository import GitRepository, GitRepositoryError, read_hashes
from .hash_filter import HashFilterError, compile_rules, iter_filter_candidates
from .reporting import write_text_atomic


def build_filter_parser(settings: FileSettings | None = None) -> argparse.ArgumentParser:
    settings = settings or FileSettings()
    filter_settings = settings.hash_filter
    parser = argparse.ArgumentParser(
        description="基于提交标题、说明、文件路径或 diff 筛选 commit hash。"
    )
    parser.add_argument(
        "linux_dir",
        nargs="?",
        type=Path,
        default=settings.linux_dir,
        help="Git 仓库；可从 settings 的 linux_dir 读取",
    )
    parser.add_argument(
        "source_hashes_file",
        nargs="?",
        type=Path,
        default=filter_settings.source_file,
        help="待筛选 hash 文件；可从 [hash_filter].source_file 读取",
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        type=Path,
        default=filter_settings.output_file or settings.hashes_file,
        help="筛选结果；默认使用 [hash_filter].output_file 或根级 hashes_file",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=settings.source or DEFAULT_SETTINGS_PATH,
        help=f"TOML 配置文件（默认 {DEFAULT_SETTINGS_PATH}，不存在时忽略）",
    )
    parser.add_argument(
        "--audit-file",
        type=Path,
        default=filter_settings.audit_file,
        help="JSONL 审计文件；默认在输出文件名后添加 .audit.jsonl",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=None,
        metavar="REGEX",
        help="保留规则，可重复；命令行提供时替换 settings 中的 include",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=None,
        metavar="REGEX",
        help="排除规则，可重复；命令行提供时替换 settings 中的 exclude",
    )
    parser.add_argument(
        "--fields",
        nargs="+",
        choices=("subject", "body", "files", "diff"),
        default=filter_settings.fields,
        help="匹配字段（默认 subject body files）",
    )
    parser.add_argument(
        "--match",
        choices=("any", "all"),
        default=filter_settings.match,
        help="include 规则命中任一还是全部（默认 any）",
    )
    parser.add_argument(
        "--case-sensitive",
        action=argparse.BooleanOptionalAction,
        default=filter_settings.case_sensitive,
        help="是否区分大小写",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=(
            filter_settings.workers
            if filter_settings.workers is not None
            else settings.workers if settings.workers is not None else 8
        ),
        help="并行 Git 读取数",
    )
    parser.add_argument(
        "--max-diff-chars",
        type=int,
        default=(
            filter_settings.max_diff_chars
            if filter_settings.max_diff_chars is not None
            else 0
        ),
        help="筛选 diff 时最多读取到规则匹配文本的字符数；0 表示不截断",
    )
    parser.set_defaults(
        settings_include=filter_settings.include,
        settings_exclude=filter_settings.exclude,
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


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.linux_dir is None:
        parser.error("缺少 linux_dir：请使用位置参数或 settings")
    if args.source_hashes_file is None:
        parser.error("缺少 source_hashes_file：请使用位置参数或 [hash_filter].source_file")
    if args.output_file is None:
        parser.error("缺少 output_file：请使用位置参数、hashes_file 或 [hash_filter].output_file")
    if args.workers < 1:
        parser.error("--workers 必须大于 0")
    if args.max_diff_chars < 0:
        parser.error("--max-diff-chars 不能为负数")


def main(argv: list[str] | None = None) -> int:
    settings_path, settings_required = _settings_argument(argv)
    try:
        settings = load_settings(settings_path, required=settings_required)
    except ConfigurationError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2

    parser = build_filter_parser(settings)
    args = parser.parse_args(argv)
    _validate_args(parser, args)
    audit_file = args.audit_file or Path(f"{args.output_file}.audit.jsonl")
    if args.output_file.resolve() == audit_file.resolve():
        parser.error("输出 hash 文件和 --audit-file 不能是同一路径")
    include = args.include if args.include is not None else args.settings_include
    exclude = args.exclude if args.exclude is not None else args.settings_exclude

    try:
        rules = compile_rules(
            include,
            exclude,
            args.fields,
            match=args.match,
            case_sensitive=args.case_sensitive,
        )
        repository = GitRepository(args.linux_dir)
        repository.validate()
        hashes = read_hashes(args.source_hashes_file)
    except (HashFilterError, GitRepositoryError) as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2

    if settings.source is not None and settings.source.is_file():
        print(f"[信息] 已加载 settings：{settings.source}")
    if not include and not exclude:
        print("[警告] 未配置 include/exclude，所有可读取提交都会被保留。", file=sys.stderr)

    decisions = {}
    completed = 0
    for decision in iter_filter_candidates(
        repository,
        hashes,
        rules,
        workers=args.workers,
        max_diff_chars=args.max_diff_chars,
    ):
        decisions[decision.index] = decision
        completed += 1
        print(
            f"[{completed}/{len(hashes)}] {decision.status}: "
            f"{decision.requested_hash} {decision.subject}",
            flush=True,
        )

    ordered = [decisions[index] for index in range(len(hashes))]
    selected = [decision.hash for decision in ordered if decision.selected]
    output_content = "".join(f"{commit_hash}\n" for commit_hash in selected)
    audit_content = "".join(
        json.dumps(decision.to_dict(), ensure_ascii=False) + "\n"
        for decision in ordered
    )
    try:
        write_text_atomic(args.output_file, output_content)
        write_text_atomic(audit_file, audit_content)
    except OSError as exc:
        print(f"[错误] 无法写入筛选结果：{exc}", file=sys.stderr)
        return 2

    errors = sum(decision.status == "error" for decision in ordered)
    print(
        f"[完成] 输入 {len(hashes)}，保留 {len(selected)}，错误 {errors}；"
        f"结果：{args.output_file}；审计：{audit_file}"
    )
    return 1 if errors else 0
