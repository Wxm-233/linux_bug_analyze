"""小批短判定命令行。"""
import argparse
from datetime import datetime
from pathlib import Path

from .config import load_settings, resolve_api_key, DEFAULT_MODEL
from .git_repository import GitRepository, read_hashes
from .llm import create_openai_client
from .reporting import write_text_atomic
from .screening import ScreenRunner, StopRun


def main(argv=None):
    parser = argparse.ArgumentParser(description="有预算的短判定；不会自动生成详细报告")
    parser.add_argument("--settings", type=Path, default=Path("settings.toml"))
    parser.add_argument("--hashes-file", type=Path)
    parser.add_argument("--outdir", type=Path)
    parser.add_argument("--max-items", type=int, default=50)
    parser.add_argument("--max-requests", type=int, default=60)
    parser.add_argument("--token-budget", type=int, default=200000)
    parser.add_argument("--max-tokens", type=int, default=1200)
    args = parser.parse_args(argv)
    if min(args.max_items, args.max_requests, args.token_budget, args.max_tokens) < 1:
        parser.error("所有运行上限必须为正整数")
    settings = load_settings(args.settings, required=True)
    if not settings.linux_dir or not (args.hashes_file or settings.hashes_file):
        parser.error("需要 linux_dir 和 hashes_file")
    if not settings.api_key_file:
        parser.error("请在 [openai] 中配置仓库外的 api_key_file")
    repo = GitRepository(settings.linux_dir)
    repo.validate()
    hashes = read_hashes(args.hashes_file or settings.hashes_file)[:args.max_items]
    context = settings.context_md.read_text(encoding="utf-8") if settings.context_md else ""
    output = args.outdir or Path("analysis_out") / ("screen-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
    # 同目录恢复复用结果，但每次预算账本独立保留，避免覆盖历史支出。
    ledger = output / "runs" / datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    client = create_openai_client(resolve_api_key(None, settings.api_key_file), settings.base_url or "https://api.deepseek.com")
    runner = ScreenRunner(client, output, model=settings.model or DEFAULT_MODEL,
        max_requests=args.max_requests, token_budget=args.token_budget, max_tokens=args.max_tokens, ledger=ledger)
    selected = []
    status, code = "completed", 0
    write_text_atomic(output / "selected_hashes.txt", "")
    try:
        for value in hashes:
            commit = repo.get_commit(value, settings.max_diff_chars if settings.max_diff_chars is not None else 20000)
            decision = runner.screen(commit, context)
            if decision["relevance"] != "unrelated" or decision["needs_review"]:
                selected.append(commit.hash)
            write_text_atomic(output / "selected_hashes.txt", "".join(h + "\n" for h in selected))
            print(f"{commit.hash}: {decision['relevance']}", flush=True)
    except StopRun as exc:
        status, code = str(exc), 3
        print(f"[已停止] {status}")
    except KeyboardInterrupt:
        status, code = "用户中断", 130
    except Exception as exc:
        status, code = "本地处理错误：" + type(exc).__name__, 2
        print(status)
    finally:
        runner.save_usage(status)
    print(f"短判定结果：{output}；进入复核队列 {len(selected)} 条；未启动详细分析。")
    return code
