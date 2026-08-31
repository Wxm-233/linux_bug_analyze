"""Markdown 报告、断点状态与索引管理。"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Iterable

from .analysis_protocol import (
    AnalysisFormatError,
    classification_from_mapping,
    render_classification,
)
from .models import AnalysisResult


SUCCESS_MARKER = "<!-- linux-bug-analyze-status: success -->"
STRUCTURED_SUCCESS_MARKER = (
    "<!-- linux-bug-analyze-status: success; report-format: 3 -->"
)
FAILURE_MARKER = "<!-- linux-bug-analyze-status: failure -->"


def report_path(output_dir: Path, commit_hash: str) -> Path:
    return output_dir / f"{commit_hash}.md"


def metadata_path(output_dir: Path, commit_hash: str) -> Path:
    return output_dir / f"{commit_hash}.meta.json"


def _is_successful_metadata(path: Path) -> bool:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return False
        classification = data.get("classification")
        if not isinstance(classification, dict):
            return False
        classification_from_mapping({"schema_version": 2, **classification})
    except (OSError, json.JSONDecodeError, AnalysisFormatError):
        return False
    return (
        data.get("schema_version") == 2
        and data.get("status") == "success"
        and data.get("commit_hash") == path.name[: -len(".meta.json")]
    )


def is_successful_report(path: Path) -> bool:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    if FAILURE_MARKER in content:
        return False
    if STRUCTURED_SUCCESS_MARKER in content:
        return _is_successful_metadata(
            metadata_path(path.parent, path.name.removesuffix(".md"))
        )
    # 旧报告不会作为本轮 schema v2 的断点继续使用。
    return False


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
    if result.succeeded and result.classification is None:
        raise ValueError("成功分析缺少结构化 classification。")
    marker = STRUCTURED_SUCCESS_MARKER if result.succeeded else FAILURE_MARKER
    if result.succeeded:
        assert result.classification is not None
        body = f"{render_classification(result.classification)}\n\n{result.analysis}"
    else:
        body = f"处理失败：{result.error}"
    content = (
        f"{marker}\n# {result.hash}\n\n"
        f"- **作者**: {result.author}\n"
        f"- **日期**: {result.date}\n"
        f"- **标题**: {result.subject}\n\n"
        f"## 模型分析\n\n{body}\n\n---\n*生成时间: {generated_at}*\n"
    )
    path = report_path(output_dir, result.hash)
    write_text_atomic(path, content)
    classification = result.classification
    metadata = {
        "schema_version": 2,
        "status": "success" if result.succeeded else "failure",
        "commit_hash": result.hash,
        "requested_hash": result.requested_hash,
        "subject": result.subject,
        "author": result.author,
        "date": result.date,
        "model": result.model,
        "classification": (
            {
                "relevance": classification.relevance,
                "categories": list(classification.categories),
                "confidence": classification.confidence,
                "related_architectures": list(
                    classification.related_architectures
                ),
            }
            if classification is not None
            else None
        ),
        "report_file": path.name,
        "generated_at": generated_at,
        "error": result.error,
    }
    write_text_atomic(
        metadata_path(output_dir, result.hash),
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
    )
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
