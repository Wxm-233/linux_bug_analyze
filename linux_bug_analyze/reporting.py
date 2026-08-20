"""Markdown 报告、断点状态与索引管理。"""

from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .models import AnalysisResult


SUCCESS_MARKER = "<!-- linux-bug-analyze-status: success -->"
FAILURE_MARKER = "<!-- linux-bug-analyze-status: failure -->"


def report_path(output_dir: Path, commit_hash: str) -> Path:
    return output_dir / f"{commit_hash}.md"


def is_successful_report(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if FAILURE_MARKER in content:
        return False
    if SUCCESS_MARKER in content:
        return True
    # 兼容旧版本报告。
    if "调用失败" in content or "处理异常" in content:
        return False
    heading = "## 模型分析"
    if heading not in content:
        return False
    analysis = content.split(heading, 1)[1].split("\n\n---", 1)[0].strip()
    return bool(analysis)


def read_existing_subject(path: Path) -> str:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    for line in lines:
        if line.startswith("- **标题**:"):
            return line.split(":", 1)[1].strip()
    return ""


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        text=True,
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


def write_report(output_dir: Path, result: AnalysisResult) -> Path:
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    marker = SUCCESS_MARKER if result.succeeded else FAILURE_MARKER
    body = result.analysis if result.succeeded else f"处理失败：{result.error}"
    content = (
        f"{marker}\n# {result.hash}\n\n"
        f"- **作者**: {result.author}\n"
        f"- **日期**: {result.date}\n"
        f"- **标题**: {result.subject}\n\n"
        f"## 模型分析\n\n{body}\n\n---\n*生成时间: {generated_at}*\n"
    )
    path = report_path(output_dir, result.hash)
    write_text_atomic(path, content)
    return path


def write_index(output_dir: Path, ordered_results: Iterable[AnalysisResult]) -> Path:
    lines = ["# 提交分析索引", ""]
    for result in ordered_results:
        status = "" if result.succeeded else "（失败，后续运行会重试）"
        lines.append(
            f"- [{result.hash}](./{result.hash}.md) — {result.subject}{status}"
        )
    path = output_dir / "index.md"
    write_text_atomic(path, "\n".join(lines) + "\n")
    return path
