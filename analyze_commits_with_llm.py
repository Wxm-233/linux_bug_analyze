#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取一个 commit hash 文件（每行一个 hash），依次用 git 提取每个提交的信息，
再调用大模型（openai 库）分析该提交做了什么，并把结果写出来。

用法示例（并行）：
    python3 analyze_commits_with_llm.py /path/to/linux filtered_hashes.txt --outdir analysis_out
    python3 analyze_commits_with_llm.py /path/to/linux filtered_hashes.txt \
        --outdir analysis_out --workers 8 --start-index 0 --end-index 10

配置方式（三种，优先级从高到低）：
    1. 命令行参数 --api-key / --base-url / --model
    2. 环境变量 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL
    3. 下方常量 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL
"""

import argparse
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ============================================================
# TODO：请在此填写你的调用配置（也可用命令行参数或环境变量覆盖）
# ------------------------------------------------------------
# 1) API Key（必填）
OPENAI_API_KEY_FILE = "OPENAI_API_KEY"
try:
    with open(OPENAI_API_KEY_FILE, encoding="utf-8") as f:
        OPENAI_API_KEY = f.read().strip()
except OSError:
    sys.exit(f"[错误] 请在当前目录下创建 {OPENAI_API_KEY_FILE} 文件，写入你的 API Key。")

# 2) API 路径（base_url，一般指向 /v1 结尾，OpenAI 官方或各类代理/中转）
OPENAI_BASE_URL = "https://llmapi.isrc.ac.cn/v1"         # 例如: "https://api.openai.com/v1" 或 "https://your-proxy.com/v1"

# 3) 调用的大模型名称（必填）
OPENAI_MODEL = "DeepSeek-V4-Pro"            # 例如: "gpt-4o-mini" / "gpt-4o" / "deepseek-chat" / "qwen-plus"
# ============================================================


def run_git(cwd, args):
    """运行 git 命令，返回 stdout 文本；失败时打印错误并退出。"""
    try:
        proc = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return proc.stdout
    except subprocess.CalledProcessError as e:
        print(f"[错误] git 命令执行失败: git {' '.join(args)}", file=sys.stderr)
        print(e.stderr.strip(), file=sys.stderr)
        sys.exit(1)


def get_commit_info(linux_dir, commit_hash):
    """
    提取单个 commit 的信息。
    返回 dict: {hash, subject, author, date, body, files}
    """
    # 提交信息（hash、作者、日期、subject + body）
    log = run_git(linux_dir, [
        "log", "-1", "--format=%H%x1e%an%x1e%ad%x1e%B", "--date=short", commit_hash,
    ])
    parts = log.split("\x1e")
    commit_hash = parts[0].strip()
    author = parts[1].strip() if len(parts) > 1 else ""
    date = parts[2].strip() if len(parts) > 2 else ""
    full_message = parts[3].strip() if len(parts) > 3 else ""

    lines = full_message.splitlines()
    subject = lines[0].strip() if lines else ""
    body = "\n".join(lines[1:]).strip()

    # 变更文件列表
    files_raw = run_git(linux_dir, ["show", "--name-only", "--format=", commit_hash])
    files = [f for f in files_raw.splitlines() if f.strip()]

    # 代码变更（diff），截断避免超出模型上下文
    diff = run_git(linux_dir, ["show", "--format=", "--unified=3", commit_hash]).strip()
    MAX_DIFF_CHARS = 12000
    if len(diff) > MAX_DIFF_CHARS:
        diff = diff[:MAX_DIFF_CHARS] + f"\n...(diff 过长，已截断，原长 {len(diff)} 字符)"

    return {
        "hash": commit_hash,
        "subject": subject,
        "author": author,
        "date": date,
        "body": body,
        "files": files,
        "diff": diff,
    }


def build_prompt(info, context_md):
    """根据 commit 信息与语义卡片框架文档构造提示词。"""
    files_text = "\n".join(info["files"]) if info["files"] else "(无文件变更)"
    diff_text = info["diff"] if info["diff"] else "(无代码差异)"
    return f"""
你是熟悉 Linux 内核源码的资深内核开发者。

下面是关于“Linux 多架构兼容性与边界代码语义”的研究框架文档，请先阅读理解：
==================== 框架文档开始 ====================
{context_md}
==================== 框架文档结束 ====================

请针对下面的 Linux 内核提交完成两件事：

一、用朴实无华、本科生能看懂的语言解释这个提交做了什么
（包括动机、主要改动点、涉及子系统/架构等，避免堆砌术语）。

二、基于上面框架文档中的“语义卡片”方法论，为这个提交填写一张语义卡片，表格字段如下：

| 字段 | 要记录的问题 |
|------|--------------|
| 缺失语义(d) | 例如设备归属、父域关系、锁状态、同步范围、能力限制 |
| 谁知道(d) | 公共层、架构层、平台描述，还是仅存在于邮件讨论/硬件规范中 |
| 当前边界 | 哪个函数、`ops` 回调、全局对象或资源描述承担交接 |
| 原边界可见信息 | 参数、返回值、状态、能力位、DeviceTree/ACPI 对象 |
| 可检查性 | 能否在原边界写出精确检查 |
| 实际修复 | 加能力字段、改参数、建立新对象、移动代码、单独实现、增加测试等 |
| 错误表现 | 架构特定触发，还是跨架构回归 |

若某字段对该提交不适用，请写“不适用”并简要说明原因。

提交哈希: {info['hash']}
作者: {info['author']}
日期: {info['date']}
标题: {info['subject']}

提交说明:
{info['body'] if info['body'] else '(无)'}

变更文件:
{files_text}

代码变更（diff，便于你看到实际改动）:
{diff_text}
"""


def _is_retryable_error(e):
    """判断错误是否值得重试（限流 429 或服务端 5xx）。"""
    status = getattr(e, "status_code", None)
    if status is not None:
        return status in (429, 500, 502, 503, 504)
    text = str(e).lower()
    return "429" in text or "rate limit" in text or "http 5" in text


def call_llm(client, model, prompt, max_retries=4, max_tokens=8192):
    """调用模型，遇限流/服务端错误时指数退避重试。"""
    for attempt in range(max_retries + 1):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一位熟悉 Linux 内核源码的资深内核开发者。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            if attempt < max_retries and _is_retryable_error(e):
                wait = 2 ** attempt
                print(f"[重试] 限流/服务端错误，{wait}s 后重试（第 {attempt+1} 次）...",
                      file=sys.stderr, flush=True)
                time.sleep(wait)
                continue
            return f"(调用失败: {e})"


def process_one(linux_dir, commit_hash, context_md, client, model, max_tokens=8192):
    """单个 commit 的完整处理：提取信息 -> 构造提示词 -> 调用模型。"""
    info = get_commit_info(linux_dir, commit_hash)
    prompt = build_prompt(info, context_md)
    analysis = call_llm(client, model, prompt, max_tokens=max_tokens)
    return {
        "hash": info["hash"],
        "subject": info["subject"],
        "author": info["author"],
        "date": info["date"],
        "analysis": analysis,
    }


def _is_failed_analysis(path):
    """判断某个已生成的分析文件是否属于失败结果（失败的需要重新处理）。"""
    try:
        with open(path, encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return True
    return "调用失败" in content or "处理异常" in content


def _read_existing_subject(path):
    """从已生成的分析文件里读取标题（用于索引）。"""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("- **标题**:"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return ""


def main():
    parser = argparse.ArgumentParser(
        description="读取 commit hash 文件，用大模型分析每个提交做了什么。"
    )
    parser.add_argument("linux_dir", help="Linux 内核源码目录（git 仓库）")
    parser.add_argument("hashes_file", help="commit hash 文件，每行一个 hash")
    parser.add_argument("--outdir", default="analysis_out",
                        help="输出目录，每个 commit 生成一个 md 文件（默认 analysis_out）")
    parser.add_argument("--context-md", default="analysis.md",
                        help="语义卡片框架文档路径（默认 analysis.md）")
    parser.add_argument("--workers", type=int, default=8,
                        help="并行线程数（默认 8；越大越快，但更容易触发 API 限流）")
    parser.add_argument("--force", action="store_true",
                        help="强制重新分析（忽略已存在的分析文件，默认断点续跑）")
    parser.add_argument("--max-tokens", type=int, default=8192,
                        help="模型单次最大输出 token 数（默认 8192；输出被截断时调大）")
    parser.add_argument("--start-index", type=int, default=0,
                        help="从第几个 hash 开始（0 起，默认 0）")
    parser.add_argument("--end-index", type=int, default=-1,
                        help="到第几个 hash 结束（不含，默认全部）")
    parser.add_argument("--api-key", default=os.environ.get("OPENAI_API_KEY", OPENAI_API_KEY),
                        help="API Key（默认取环境变量 OPENAI_API_KEY 或脚本内常量）")
    parser.add_argument("--base-url", default=os.environ.get("OPENAI_BASE_URL", OPENAI_BASE_URL),
                        help="API 路径（默认取环境变量 OPENAI_BASE_URL 或脚本内常量）")
    parser.add_argument("--model", default=os.environ.get("OPENAI_MODEL", OPENAI_MODEL),
                        help="模型名（默认取环境变量 OPENAI_MODEL 或脚本内常量）")
    args = parser.parse_args()

    # 检查必填配置
    if not args.api_key or not args.model or not args.base_url:
        print("[错误] 缺少 API 配置。请通过 --api-key / --base-url / --model、"
              "环境变量或脚本内常量提供。", file=sys.stderr)
        sys.exit(1)

    # 读取 commit hash 列表
    with open(args.hashes_file, encoding="utf-8") as f:
        hashes = [line.strip() for line in f if line.strip()]
    if not hashes:
        print("[错误] hash 文件为空。", file=sys.stderr)
        sys.exit(1)

    # 应用起止范围
    start = max(0, args.start_index)
    end = len(hashes) if args.end_index < 0 else min(args.end_index, len(hashes))
    selected = hashes[start:end]
    print(f"[信息] 共读取 {len(hashes)} 个 hash，本次处理第 {start}~{end} 个，共 {len(selected)} 个。")

    # 读取语义卡片框架文档（如 analysis.md）
    context_md = ""
    if os.path.isfile(args.context_md):
        with open(args.context_md, encoding="utf-8") as f:
            context_md = f.read()
        print(f"[信息] 已读取语义卡片框架文档: {args.context_md}（{len(context_md)} 字符）")
    else:
        print(f"[警告] 未找到语义卡片框架文档: {args.context_md}，将不带框架运行。", file=sys.stderr)

    # 创建输出目录
    os.makedirs(args.outdir, exist_ok=True)
    print(f"[信息] 输出目录: {args.outdir}")

    # 初始化 openai 客户端
    try:
        from openai import OpenAI
    except ImportError:
        print("[错误] 未安装 openai 库，请先执行: pip install openai", file=sys.stderr)
        sys.exit(1)
    client = OpenAI(api_key=args.api_key, base_url=args.base_url)

    # 断点续跑：跳过已生成且成功分析的 commit（失败或不存在才重新处理）
    pending = []   # (原索引, hash)
    skipped = 0
    for idx, h in enumerate(selected):
        out_path = os.path.join(args.outdir, f"{h}.md")
        if not args.force and os.path.isfile(out_path) and not _is_failed_analysis(out_path):
            skipped += 1
            continue
        pending.append((idx, h))
    print(f"[信息] 断点续跑：已存在成功分析 {skipped} 个（跳过），本次待处理 {len(pending)} 个。")
    if args.force:
        print("[信息] --force 已启用，将忽略已存在文件并全部重新分析。")

    # 并行分析：每条 commit 一个任务，线程池并发调用模型与 git
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[信息] 并行线程数: {args.workers}")

    results = {}   # 原索引 -> result，用于按原顺序生成索引
    done = 0
    total = len(pending)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_to_idx = {
            executor.submit(process_one, args.linux_dir, h, context_md, client,
                           args.model, args.max_tokens): idx
            for idx, h in pending
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                r = future.result()
            except Exception as e:
                r = {"hash": selected[idx], "subject": "(处理异常)",
                     "author": "", "date": "", "analysis": f"(处理异常: {e})"}
            done += 1
            results[idx] = r

            # 单独写入该 commit 的分析文件（失败结果也写入，下次运行会自动重试）
            out_path = os.path.join(args.outdir, f"{r['hash']}.md")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(f"# {r['hash']}\n\n")
                f.write(f"- **作者**: {r['author']}\n")
                f.write(f"- **日期**: {r['date']}\n")
                f.write(f"- **标题**: {r['subject']}\n\n")
                f.write(f"## 模型分析\n\n{r['analysis']}\n\n---\n*生成时间: {now}*\n")
            print(f"[{done}/{total}] {r['subject']} -> {r['analysis'][:60]}...", flush=True)

    # 按原输入顺序生成索引（本次新生成 + 之前已完成的）
    index_path = os.path.join(args.outdir, "index.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("# 提交分析索引\n\n")
        for idx, h in enumerate(selected):
            if idx in results:
                r = results[idx]
                f.write(f"- [{r['hash']}](./{r['hash']}.md) — {r['subject']}\n")
            else:
                subject = _read_existing_subject(os.path.join(args.outdir, f"{h}.md"))
                f.write(f"- [{h}](./{h}.md) — {subject}\n")
    print(f"\n[完成] 本次新生成 {len(results)} 个，索引已更新: {args.outdir}/")


if __name__ == "__main__":
    main()
