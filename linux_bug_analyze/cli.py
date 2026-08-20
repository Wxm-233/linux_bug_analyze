"""命令行解析与各模块编排。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import (
    DEFAULT_API_KEY_FILE,
    DEFAULT_BASE_URL,
    DEFAULT_CONTEXT_PATH,
    DEFAULT_MODEL,
    ConfigurationError,
    resolve_api_key,
    resolve_setting,
)
from .git_repository import GitRepository, GitRepositoryError, read_hashes
from .llm import ChatAnalyzer, LLMError, create_openai_client
from .models import AnalysisResult
from .pipeline import analyze_commits
from .reporting import (
    is_successful_report,
    read_existing_subject,
    report_path,
    write_index,
    write_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="按论文研究框架分析 Linux 内核提交中的多架构语义缺陷。"
    )
    parser.add_argument("linux_dir", type=Path, help="Linux 内核源码 Git 仓库")
    parser.add_argument("hashes_file", type=Path, help="commit hash 文件，每行一个 hash")
    parser.add_argument("--outdir", type=Path, default=Path("analysis_out"), help="输出目录")
    parser.add_argument(
        "--context-md",
        type=Path,
        default=DEFAULT_CONTEXT_PATH,
        help=f"研究框架文档（默认 {DEFAULT_CONTEXT_PATH}）",
    )
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        help="可选补充证据目录，文件名须为完整 hash 加 .md 或 .txt",
    )
    parser.add_argument("--workers", type=int, default=8, help="并行线程数（默认 8）")
    parser.add_argument("--force", action="store_true", help="忽略成功报告并重新分析")
    parser.add_argument("--max-tokens", type=int, default=8192, help="单次最大输出 token 数")
    parser.add_argument(
        "--max-diff-chars",
        type=int,
        default=50_000,
        help="送入模型的最大 diff 字符数；0 表示不截断（默认 50000）",
    )
    parser.add_argument("--start-index", type=int, default=0, help="起始下标，含该位置")
    parser.add_argument("--end-index", type=int, default=-1, help="结束下标，不含；-1 表示末尾")
    parser.add_argument("--api-key", help="API Key；优先级高于环境变量和密钥文件")
    parser.add_argument(
        "--api-key-file",
        type=Path,
        default=DEFAULT_API_KEY_FILE,
        help=f"API Key 文件（默认 {DEFAULT_API_KEY_FILE}）",
    )
    parser.add_argument("--base-url", help="OpenAI 兼容 API 的 base URL")
    parser.add_argument("--model", help="模型名")
    return parser


def _validate_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.workers < 1:
        parser.error("--workers 必须大于 0")
    if args.max_tokens < 1:
        parser.error("--max-tokens 必须大于 0")
    if args.max_diff_chars < 0:
        parser.error("--max-diff-chars 不能为负数")
    if args.start_index < 0:
        parser.error("--start-index 不能为负数")
    if args.end_index < -1:
        parser.error("--end-index 只能是 -1 或非负数")
    if args.end_index != -1 and args.end_index < args.start_index:
        parser.error("--end-index 不能小于 --start-index")
    if args.evidence_dir is not None and not args.evidence_dir.is_dir():
        parser.error(f"--evidence-dir 不是目录：{args.evidence_dir}")


def _load_context(path: Path) -> str:
    try:
        content = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise ConfigurationError(f"无法读取研究框架文档 {path}: {exc}") from exc
    if not content:
        raise ConfigurationError(f"研究框架文档为空：{path}")
    return content


def _existing_result(commit_hash: str, path: Path) -> AnalysisResult:
    return AnalysisResult(
        requested_hash=commit_hash,
        hash=commit_hash,
        subject=read_existing_subject(path),
        author="",
        date="",
        analysis="（沿用已有成功报告）",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_args(parser, args)

    try:
        repository = GitRepository(args.linux_dir)
        repository.validate()
        all_hashes = read_hashes(args.hashes_file)
        end = len(all_hashes) if args.end_index == -1 else min(args.end_index, len(all_hashes))
        selected = all_hashes[args.start_index:end]
        context = _load_context(args.context_md)
    except (ConfigurationError, GitRepositoryError) as exc:
        print(f"[错误] {exc}", file=sys.stderr)
        return 2

    if not selected:
        print("[信息] 选择范围内没有提交；未调用模型。")
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    ordered: dict[str, AnalysisResult] = {}
    pending: list[str] = []

    # 先解析完整 hash，确保短 hash 的断点文件名和索引稳定。
    for requested_hash in selected:
        try:
            canonical_hash = repository.resolve_hash(requested_hash)
        except GitRepositoryError as exc:
            result = AnalysisResult.failure(requested_hash, exc)
            write_report(args.outdir, result)
            ordered[requested_hash] = result
            continue
        path = report_path(args.outdir, canonical_hash)
        if not args.force and is_successful_report(path):
            ordered[requested_hash] = _existing_result(canonical_hash, path)
        else:
            pending.append(requested_hash)

    failed_before_analysis = sum(not result.succeeded for result in ordered.values())
    reused = len(selected) - len(pending) - failed_before_analysis
    print(
        f"[信息] 共读取 {len(all_hashes)} 个 hash，本次选择 {len(selected)} 个；"
        f"待分析 {len(pending)} 个，沿用成功报告 {reused} 个。"
    )

    if pending:
        try:
            api_key = resolve_api_key(args.api_key, args.api_key_file)
            base_url = resolve_setting(args.base_url, "OPENAI_BASE_URL", DEFAULT_BASE_URL)
            model = resolve_setting(args.model, "OPENAI_MODEL", DEFAULT_MODEL)
            analyzer = ChatAnalyzer(
                create_openai_client(api_key, base_url),
                model,
                max_tokens=args.max_tokens,
            )
        except (ConfigurationError, LLMError) as exc:
            print(f"[错误] {exc}", file=sys.stderr)
            return 2

        completed = 0
        for result in analyze_commits(
            repository,
            pending,
            context,
            analyzer,
            workers=args.workers,
            max_diff_chars=args.max_diff_chars,
            evidence_dir=args.evidence_dir,
        ):
            completed += 1
            ordered[result.requested_hash] = result
            path = write_report(args.outdir, result)
            state = "完成" if result.succeeded else "失败"
            print(f"[{completed}/{len(pending)}] {state}: {result.hash} -> {path}", flush=True)

    ordered_results = [ordered[commit_hash] for commit_hash in selected]
    index_path = write_index(args.outdir, ordered_results)
    failures = sum(not result.succeeded for result in ordered_results)
    print(f"[完成] 索引已更新：{index_path}；失败 {failures} 个。")
    return 1 if failures else 0
