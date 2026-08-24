"""汇总结构化分析结果，并兼容只读解析旧版 Markdown 报告。"""

from __future__ import annotations

import csv
import io
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .analysis_protocol import AnalysisFormatError, classification_from_mapping
from .models import AnalysisClassification
from .reporting import (
    FAILURE_MARKER,
    STRUCTURED_SUCCESS_MARKER,
    SUCCESS_MARKER,
    write_text_atomic,
)


META_SUFFIX = ".meta.json"


class ResultSummaryError(RuntimeError):
    """分析结果目录或元数据无法汇总。"""


@dataclass(frozen=True, slots=True)
class SummaryRecord:
    commit_hash: str
    status: str
    subject: str = ""
    classification: AnalysisClassification | None = None
    report_path: Path | None = None
    source_format: str = "structured_v1"
    error: str = ""

    def to_csv_row(self) -> dict[str, str]:
        classification = self.classification
        return {
            "commit_hash": self.commit_hash,
            "status": self.status,
            "relevance": classification.relevance if classification else "",
            "categories": (
                ";".join(classification.categories) if classification else ""
            ),
            "confidence": classification.confidence if classification else "",
            "subject": self.subject,
            "report_file": str(self.report_path or ""),
            "source_format": self.source_format,
            "error": self.error,
        }


def _classification_from_sidecar(data: Any) -> AnalysisClassification:
    if not isinstance(data, dict):
        raise AnalysisFormatError("classification 必须是对象。")
    payload = {"schema_version": 1, **data}
    return classification_from_mapping(payload)


def _read_sidecar(path: Path, input_dir: Path) -> SummaryRecord:
    commit_hash = path.name[: -len(META_SUFFIX)]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return SummaryRecord(
            commit_hash,
            "invalid_metadata",
            source_format="structured_v1",
            error=f"无法读取元数据：{exc}",
        )
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return SummaryRecord(
            commit_hash,
            "invalid_metadata",
            source_format="structured_v1",
            error="元数据顶层无效或 schema_version 不是 1。",
        )
    status = data.get("status")
    stored_hash = data.get("commit_hash")
    if status not in {"success", "failure"} or not isinstance(stored_hash, str):
        return SummaryRecord(
            commit_hash,
            "invalid_metadata",
            source_format="structured_v1",
            error="元数据缺少有效 status 或 commit_hash。",
        )
    if stored_hash != commit_hash:
        return SummaryRecord(
            commit_hash,
            "invalid_metadata",
            source_format="structured_v1",
            error=f"文件名 hash 与元数据 commit_hash 不一致：{stored_hash}",
        )

    report_name = data.get("report_file")
    report_path = (
        input_dir / report_name if isinstance(report_name, str) and report_name else None
    )
    if status == "failure":
        return SummaryRecord(
            commit_hash,
            status,
            subject=str(data.get("subject", "")),
            report_path=report_path,
            error=str(data.get("error", "")),
        )
    try:
        classification = _classification_from_sidecar(data.get("classification"))
    except AnalysisFormatError as exc:
        return SummaryRecord(
            commit_hash,
            "invalid_metadata",
            subject=str(data.get("subject", "")),
            report_path=report_path,
            source_format="structured_v1",
            error=str(exc),
        )
    if report_path is None or not report_path.is_file():
        return SummaryRecord(
            commit_hash,
            "invalid_metadata",
            subject=str(data.get("subject", "")),
            classification=classification,
            report_path=report_path,
            source_format="structured_v1",
            error="找不到元数据引用的 Markdown 报告。",
        )
    return SummaryRecord(
        commit_hash,
        "success",
        subject=str(data.get("subject", "")),
        classification=classification,
        report_path=report_path,
    )


def parse_legacy_classification(content: str) -> AnalysisClassification:
    """只用于迁移/汇总旧报告；新报告不依赖 Markdown 正则。"""

    heading = re.search(r"^##\s+研究相关性判定\s*$", content, re.MULTILINE)
    if not heading:
        raise AnalysisFormatError("旧报告缺少“研究相关性判定”标题。")
    following = content[heading.end() :]
    next_heading = re.search(r"^##\s+", following, re.MULTILINE)
    section = following[: next_heading.start()] if next_heading else following
    section = section.replace("**", "")

    relevance_match = re.search(
        r"结论\s*[：:]\s*(不相关|不确定|相关)", section
    )
    category_match = re.search(
        r"类型\s*[：:]\s*(隐式语义假设错误|跨架构回归|两者|不适用)",
        section,
    )
    confidence_match = re.search(r"置信度\s*[：:]\s*(高|中|低)", section)
    if not relevance_match or not category_match or not confidence_match:
        raise AnalysisFormatError("旧报告的结论、类型或置信度无法唯一识别。")

    relevance = {
        "相关": "related",
        "不相关": "unrelated",
        "不确定": "uncertain",
    }[relevance_match.group(1)]
    category_value = category_match.group(1)
    categories = {
        "隐式语义假设错误": ["implicit_semantic_assumption"],
        "跨架构回归": ["cross_arch_regression"],
        "两者": ["implicit_semantic_assumption", "cross_arch_regression"],
        "不适用": [],
    }[category_value]
    confidence = {"高": "high", "中": "medium", "低": "low"}[
        confidence_match.group(1)
    ]
    return classification_from_mapping(
        {
            "schema_version": 1,
            "relevance": relevance,
            "categories": categories,
            "confidence": confidence,
        }
    )


def _read_legacy_report(path: Path) -> SummaryRecord | None:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return SummaryRecord(
            path.stem,
            "legacy_ambiguous",
            report_path=path,
            source_format="legacy_markdown",
            error=f"无法读取旧报告：{exc}",
        )
    if not any(
        marker in content
        for marker in (SUCCESS_MARKER, STRUCTURED_SUCCESS_MARKER, FAILURE_MARKER)
    ):
        return None
    if FAILURE_MARKER in content:
        return SummaryRecord(
            path.stem,
            "failure",
            report_path=path,
            source_format="legacy_markdown",
        )
    if STRUCTURED_SUCCESS_MARKER in content:
        return SummaryRecord(
            path.stem,
            "invalid_metadata",
            report_path=path,
            source_format="structured_v1",
            error="结构化报告缺少 sidecar 元数据。",
        )
    try:
        classification = parse_legacy_classification(content)
    except AnalysisFormatError as exc:
        return SummaryRecord(
            path.stem,
            "legacy_ambiguous",
            report_path=path,
            source_format="legacy_markdown",
            error=str(exc),
        )
    subject_match = re.search(r"^- \*\*标题\*\*:\s*(.*)$", content, re.MULTILINE)
    return SummaryRecord(
        path.stem,
        "success",
        subject=subject_match.group(1).strip() if subject_match else "",
        classification=classification,
        report_path=path,
        source_format="legacy_markdown",
    )


def collect_results(input_dir: Path) -> list[SummaryRecord]:
    """收集 sidecar；仅在不存在 sidecar 时兼容读取旧 Markdown。"""

    root = input_dir.expanduser().resolve()
    if not root.is_dir():
        raise ResultSummaryError(f"分析结果目录不存在：{root}")
    records: list[SummaryRecord] = []
    handled_hashes: set[str] = set()
    for path in sorted(root.glob(f"*{META_SUFFIX}")):
        record = _read_sidecar(path, root)
        records.append(record)
        handled_hashes.add(record.commit_hash)
    for path in sorted(root.glob("*.md")):
        if path.stem in handled_hashes:
            continue
        record = _read_legacy_report(path)
        if record is not None:
            records.append(record)
    return sorted(records, key=lambda record: record.commit_hash)


def _counts(records: list[SummaryRecord]) -> dict[str, Any]:
    statuses = {
        status: sum(record.status == status for record in records)
        for status in (
            "success",
            "failure",
            "invalid_metadata",
            "legacy_ambiguous",
        )
    }
    relevance = {
        value: sum(
            record.status == "success"
            and record.classification is not None
            and record.classification.relevance == value
            for record in records
        )
        for value in ("related", "unrelated", "uncertain")
    }
    confidence = {
        value: sum(
            record.status == "success"
            and record.classification is not None
            and record.classification.confidence == value
            for record in records
        )
        for value in ("high", "medium", "low")
    }
    categories = {
        value: sum(
            record.status == "success"
            and record.classification is not None
            and value in record.classification.categories
            for record in records
        )
        for value in (
            "implicit_semantic_assumption",
            "cross_arch_regression",
        )
    }
    success = statuses["success"]
    decisive = relevance["related"] + relevance["unrelated"]
    return {
        "total": len(records),
        "by_status": statuses,
        "by_relevance": relevance,
        "by_confidence": confidence,
        "by_category": categories,
        "related_rate_among_success": relevance["related"] / success if success else None,
        "related_rate_among_decisive": (
            relevance["related"] / decisive if decisive else None
        ),
    }


def write_summary(
    input_dir: Path,
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, Path]]:
    """生成 JSON、CSV、相关 hash 列表和相关报告索引。"""

    records = collect_results(input_dir)
    output_root = output_dir.expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    counts = _counts(records)
    summary = {
        "schema_version": 1,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "input_dir": str(input_dir.expanduser().resolve()),
        "counts": counts,
    }

    summary_path = output_root / "summary.json"
    csv_path = output_root / "results.csv"
    related_hashes_path = output_root / "related_hashes.txt"
    related_index_path = output_root / "related_index.md"
    write_text_atomic(
        summary_path,
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
    )

    csv_stream = io.StringIO(newline="")
    fieldnames = [
        "commit_hash",
        "status",
        "relevance",
        "categories",
        "confidence",
        "subject",
        "report_file",
        "source_format",
        "error",
    ]
    writer = csv.DictWriter(csv_stream, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(record.to_csv_row() for record in records)
    write_text_atomic(csv_path, csv_stream.getvalue())

    related = [
        record
        for record in records
        if record.status == "success"
        and record.classification is not None
        and record.classification.relevance == "related"
    ]
    write_text_atomic(
        related_hashes_path,
        "".join(f"{record.commit_hash}\n" for record in related),
    )
    index_lines = ["# 相关提交分析索引", ""]
    for record in related:
        if record.report_path is None:
            continue
        try:
            relative = Path(os.path.relpath(record.report_path, output_root)).as_posix()
        except ValueError:  # Windows 上跨盘符时无法构造相对路径
            relative = record.report_path.resolve().as_posix()
        link_target = f"<{relative}>" if " " in relative else relative
        index_lines.append(
            f"- [{record.commit_hash}]({link_target}) — {record.subject or '（无标题）'}"
        )
    write_text_atomic(related_index_path, "\n".join(index_lines) + "\n")
    return summary, {
        "summary": summary_path,
        "csv": csv_path,
        "related_hashes": related_hashes_path,
        "related_index": related_index_path,
    }
