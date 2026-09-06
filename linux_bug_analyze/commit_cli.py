"""从 Linux 主线提交历史生成跨架构候选 hash。"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from .commit_source import CommitSourceError, iter_mainline_commits
from .config import DEFAULT_SETTINGS_PATH, ConfigurationError, FileSettings, load_settings
from .git_repository import GitRepository, GitRepositoryError
from .hash_filter import HashFilterError, compile_rules, evaluate_commit
from .reporting import write_text_atomic


def build_commit_parser(settings: FileSettings | None = None) -> argparse.ArgumentParser:
    settings = settings or FileSettings()
    source = settings.commit_source
    filter_settings = settings.hash_filter
    parser = argparse.ArgumentParser(
        description="直接扫描 Linux 主线 Git 历史并筛选跨架构候选提交。"
    )
    parser.add_argument(
        "linux_dir", nargs="?", type=Path, default=settings.linux_dir,
        help="Linux 主线 Git 仓库；可从 settings 的 linux_dir 读取",
    )
    parser.add_argument(
        "output_file", nargs="?", type=Path,
        default=source.output_file or settings.hashes_file,
        help="候选 hash 输出；默认使用 [commit_source].output_file 或 hashes_file",
    )
    parser.add_argument(
        "--settings", type=Path, default=settings.source or DEFAULT_SETTINGS_PATH,
        help=f"TOML 配置文件（默认 {DEFAULT_SETTINGS_PATH}，不存在时忽略）",
    )
    parser.add_argument("--ref", default=source.ref, help="扫描的主线 ref（默认 HEAD）")
    parser.add_argument("--since", default=source.since, help="git log --since 时间")
    parser.add_argument("--until", default=source.until, help="git log --until 时间")
    merge_group = parser.add_mutually_exclusive_group()
    merge_group.add_argument(
        "--no-merges", dest="no_merges", action="store_true",
        help="排除 merge commit",
    )
    merge_group.add_argument(
        "--include-merges", dest="no_merges", action="store_false",
        help="同时扫描 merge commit",
    )
    parser.set_defaults(no_merges=source.no_merges)
    parser.add_argument(
        "--reverse", action=argparse.BooleanOptionalAction,
        default=source.reverse, help="是否按时间从旧到新输出",
    )
    parser.add_argument(
        "--max-count", type=int, default=source.max_count,
        help="最多扫描的提交数；0 表示不限",
    )
    parser.add_argument(
        "--shuffle", action=argparse.BooleanOptionalAction,
        default=source.shuffle, help="是否用固定种子打乱候选顺序",
    )
    parser.add_argument("--random-seed", type=int, default=source.random_seed)
    parser.add_argument("--audit-file", type=Path, default=source.audit_file)
    parser.add_argument(
        "--include", action="append", default=None, metavar="REGEX",
        help="候选保留规则；命令行提供时替换 [hash_filter].include",
    )
    parser.add_argument(
        "--exclude", action="append", default=None, metavar="REGEX",
        help="候选排除规则；命令行提供时替换 [hash_filter].exclude",
    )
    parser.add_argument(
        "--fields", nargs="+", choices=("subject", "body", "files"),
        default=tuple(field for field in filter_settings.fields if field != "diff"),
        help="匹配字段；主线流式扫描不读取 diff",
    )
    parser.add_argument(
        "--match", choices=("any", "all"), default=filter_settings.match,
    )
    parser.add_argument(
        "--case-sensitive", action=argparse.BooleanOptionalAction,
        default=filter_settings.case_sensitive,
    )
    parser.set_defaults(
        settings_include=filter_settings.include,
        settings_exclude=filter_settings.exclude,
    )
    return parser


def _settings_argument(argv: list[str] | None) -> tuple[Path, bool]:
    values = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--settings", type=Path, default=DEFAULT_SETTINGS_PATH)
    known, _ = parser.parse_known_args(values)
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
    parser = build_commit_parser(settings)
    args = parser.parse_args(argv)
    if args.linux_dir is None:
        parser.error("缺少 linux_dir：请使用位置参数或 settings")
    if args.output_file is None:
        parser.error("缺少 output_file：请设置 hashes_file 或 [commit_source].output_file")
    if args.max_count < 0:
        parser.error("--max-count 不能为负数")
    if not args.fields:
        parser.error("--fields 至少包含一个字段，且不能只配置 diff")
    audit_file = args.audit_file or Path(f"{args.output_file}.audit.jsonl")
    if args.output_file.resolve() == audit_file.resolve():
        parser.error("输出 hash 文件和审计文件不能是同一路径")

    include = args.include if args.include is not None else args.settings_include
    exclude = args.exclude if args.exclude is not None else args.settings_exclude
    try:
        repository = GitRepository(args.linux_dir)
        repository.validate()
        rules = compile_rules(
            include, exclude, args.fields,
            match=args.match, case_sensitive=args.case_sensitive,
        )
    except (GitRepositoryError, HashFilterError) as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2

    selected = []
    scanned = 0
    try:
        for commit in iter_mainline_commits(
            args.linux_dir,
            args.ref,
            since=args.since,
            until=args.until,
            no_merges=args.no_merges,
            reverse=args.reverse,
            max_count=args.max_count,
        ):
            decision = evaluate_commit(scanned, commit, rules)
            scanned += 1
            if decision.selected:
                selected.append(decision)
            if scanned % 10_000 == 0:
                print(f"[进度] 已扫描 {scanned}，候选 {len(selected)}", flush=True)
    except CommitSourceError as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2

    if args.shuffle:
        random.Random(args.random_seed).shuffle(selected)
    hashes_text = "".join(f"{decision.hash}\n" for decision in selected)
    summary = {
        "record_type": "summary",
        "source": "linux-mainline-git",
        "ref": args.ref,
        "since": args.since,
        "until": args.until,
        "no_merges": args.no_merges,
        "reverse": args.reverse,
        "shuffle": args.shuffle,
        "random_seed": args.random_seed if args.shuffle else None,
        "scanned": scanned,
        "selected": len(selected),
        "include": list(include),
        "exclude": list(exclude),
        "fields": list(args.fields),
        "match": args.match,
    }
    audit_text = json.dumps(summary, ensure_ascii=False) + "\n" + "".join(
        json.dumps(
            {"record_type": "selected", **decision.to_dict()},
            ensure_ascii=False,
        ) + "\n"
        for decision in selected
    )
    try:
        write_text_atomic(args.output_file, hashes_text)
        write_text_atomic(audit_file, audit_text)
    except OSError as exc:
        print(f"[错误] 无法写入候选结果：{exc}", file=sys.stderr)
        return 2
    print(
        f"[完成] 扫描 {scanned}，候选 {len(selected)}；"
        f"结果：{args.output_file}；审计：{audit_file}"
    )
    return 0
