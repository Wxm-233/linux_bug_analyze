"""linux-cve-announce 本地镜像候选 hash 提取命令行。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import DEFAULT_SETTINGS_PATH, ConfigurationError, FileSettings, load_settings
from .cve_source import CveSourceError, read_cve_records, select_candidates
from .git_repository import GitRepository, GitRepositoryError
from .public_inbox import PublicInboxError
from .reporting import write_text_atomic


def build_cve_parser(settings: FileSettings | None = None) -> argparse.ArgumentParser:
    settings = settings or FileSettings()
    cve_settings = settings.cve_source
    parser = argparse.ArgumentParser(
        description="从本地 linux-cve-announce public-inbox v2 镜像提取修复 commit。"
    )
    parser.add_argument(
        "inbox_dir",
        nargs="?",
        type=Path,
        default=cve_settings.inbox_dir,
        help="public-inbox 根目录、git 目录或单个 N.git epoch",
    )
    parser.add_argument(
        "output_file",
        nargs="?",
        type=Path,
        default=cve_settings.output_file or settings.hash_filter.source_file,
        help="候选 hash 输出；默认使用 [cve_source].output_file 或 [hash_filter].source_file",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=settings.source or DEFAULT_SETTINGS_PATH,
        help=f"TOML 配置文件（默认 {DEFAULT_SETTINGS_PATH}，不存在时忽略）",
    )
    parser.add_argument(
        "--linux-dir",
        type=Path,
        default=settings.linux_dir,
        help="用于识别主线提交的 Linux Git 仓库",
    )
    parser.add_argument(
        "--audit-file",
        type=Path,
        default=cve_settings.audit_file,
        help="JSONL 审计文件；默认在输出文件名后添加 .audit.jsonl",
    )
    parser.add_argument(
        "--prefer-mainline",
        action=argparse.BooleanOptionalAction,
        default=cve_settings.prefer_mainline,
        help="只选择 linux_dir 中存在的提交（默认启用）",
    )
    parser.add_argument(
        "--fallback-to-all",
        action=argparse.BooleanOptionalAction,
        default=cve_settings.fallback_to_all,
        help="找不到主线提交时是否回退到邮件中的全部修复引用",
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


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> Path:
    if args.inbox_dir is None:
        parser.error("缺少 inbox_dir：请使用位置参数或 [cve_source].inbox_dir")
    if args.output_file is None:
        parser.error(
            "缺少 output_file：请使用位置参数、[cve_source].output_file "
            "或 [hash_filter].source_file"
        )
    if args.prefer_mainline and args.linux_dir is None:
        parser.error("启用 --prefer-mainline 时必须提供 linux_dir")
    audit_file = args.audit_file or Path(f"{args.output_file}.audit.jsonl")
    if args.output_file.resolve() == audit_file.resolve():
        parser.error("输出 hash 文件和 --audit-file 不能是同一路径")
    return audit_file


def main(argv: list[str] | None = None) -> int:
    settings_path, settings_required = _settings_argument(argv)
    try:
        settings = load_settings(settings_path, required=settings_required)
    except ConfigurationError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2

    parser = build_cve_parser(settings)
    args = parser.parse_args(argv)
    audit_file = _validate_args(parser, args)

    try:
        if args.prefer_mainline:
            repository = GitRepository(args.linux_dir)
            repository.validate()
        records = read_cve_records(args.inbox_dir)
        candidates = select_candidates(
            records,
            args.linux_dir,
            prefer_mainline=args.prefer_mainline,
            fallback_to_all=args.fallback_to_all,
        )
    except (CveSourceError, GitRepositoryError, PublicInboxError) as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2

    output_content = "".join(f"{commit_hash}\n" for commit_hash in candidates)
    audit_content = "".join(
        json.dumps(record.to_dict(), ensure_ascii=False) + "\n" for record in records
    )
    try:
        write_text_atomic(args.output_file, output_content)
        write_text_atomic(audit_file, audit_content)
    except OSError as exc:
        print(f"[错误] 无法写入 CVE 提取结果：{exc}", file=sys.stderr)
        return 2

    selected_messages = sum(record.status == "selected" for record in records)
    unresolved = sum(record.status == "unresolved" for record in records)
    print(
        f"[完成] 邮件 {len(records)}，产生候选 {len(candidates)}，"
        f"命中邮件 {selected_messages}，未解析主线 {unresolved}；"
        f"结果：{args.output_file}；审计：{audit_file}"
    )
    return 0
