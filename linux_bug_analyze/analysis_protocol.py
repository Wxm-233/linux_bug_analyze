"""模型分析输出协议及严格解析。"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping

from .models import AnalysisClassification, ModelAnalysis


METADATA_MARKER = "<<<LBA_METADATA_V3>>>"
REPORT_MARKER = "<<<LBA_REPORT_V3>>>"
SCHEMA_VERSION = 3

RELEVANCE_VALUES = {"related", "unrelated", "uncertain"}
CATEGORY_VALUES = {
    "implicit_semantic_assumption",
    "cross_arch_regression",
}
CONFIDENCE_VALUES = {"high", "medium", "low"}
COMMON_CODE_SCOPE_VALUES = {"overbroad", "appropriate", "not_applicable", "uncertain"}
ASSERTION_SUFFICIENCY_VALUES = {
    "sufficient", "partial", "insufficient", "not_applicable", "uncertain"
}
RECOMMENDED_MECHANISM_VALUES = {
    "assertion",
    "config_guard",
    "move_to_arch",
    "capability_interface",
    "type_or_api",
    "state_machine",
    "test",
    "other",
    "none",
}
ARCHITECTURE_VALUES = {
    "alpha",
    "arc",
    "arm32",
    "arm64",
    "csky",
    "h8300",
    "hexagon",
    "ia64",
    "loongarch",
    "m68k",
    "microblaze",
    "mips",
    "nds32",
    "nios2",
    "openrisc",
    "parisc",
    "powerpc",
    "riscv",
    "s390",
    "sh",
    "sparc",
    "um",
    "x86",
    "xtensa",
}

RELEVANCE_LABELS = {
    "related": "相关",
    "unrelated": "不相关",
    "uncertain": "不确定",
}
CATEGORY_LABELS = {
    "implicit_semantic_assumption": "隐式语义假设错误",
    "cross_arch_regression": "跨架构回归",
}
CONFIDENCE_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
}
COMMON_CODE_SCOPE_LABELS = {
    "overbroad": "公共层作用域过宽",
    "appropriate": "公共层放置合理",
    "not_applicable": "不适用",
    "uncertain": "不确定",
}
ASSERTION_SUFFICIENCY_LABELS = {
    "sufficient": "断言基本足够",
    "partial": "断言只能部分解决",
    "insufficient": "断言不足",
    "not_applicable": "不适用",
    "uncertain": "不确定",
}
RECOMMENDED_MECHANISM_LABELS = {
    "assertion": "断言",
    "config_guard": "条件编译或配置隔离",
    "move_to_arch": "迁移到架构目录",
    "capability_interface": "能力描述或接口扩展",
    "type_or_api": "类型或 API 重构",
    "state_machine": "状态机",
    "test": "测试",
    "other": "其他",
    "none": "无",
}

REQUIRED_REPORT_HEADINGS = (
    "提交概述",
    "判定理由",
    "语义卡片",
    "证据审计",
)


class AnalysisFormatError(ValueError):
    """模型输出不符合可机器解析的协议。"""


def classification_from_mapping(data: Mapping[str, Any]) -> AnalysisClassification:
    """验证分类对象的字段、类型、枚举及字段间约束。"""

    expected_keys = {
        "schema_version",
        "relevance",
        "categories",
        "confidence",
        "related_architectures",
        "semantic_origin_architectures",
        "common_code_scope",
        "assertion_sufficiency",
        "recommended_mechanisms",
    }
    actual_keys = set(data)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        details: list[str] = []
        if missing:
            details.append(f"缺少字段 {', '.join(missing)}")
        if extra:
            details.append(f"未知字段 {', '.join(extra)}")
        raise AnalysisFormatError("分类 JSON 字段错误：" + "；".join(details))

    if data["schema_version"] != SCHEMA_VERSION:
        raise AnalysisFormatError(
            f"不支持 schema_version={data['schema_version']!r}，预期 {SCHEMA_VERSION}。"
        )

    relevance = data["relevance"]
    confidence = data["confidence"]
    categories = data["categories"]
    architectures = data["related_architectures"]
    origin_architectures = data["semantic_origin_architectures"]
    common_code_scope = data["common_code_scope"]
    assertion_sufficiency = data["assertion_sufficiency"]
    mechanisms = data["recommended_mechanisms"]
    if not isinstance(relevance, str) or relevance not in RELEVANCE_VALUES:
        raise AnalysisFormatError(f"无效 relevance：{relevance!r}")
    if not isinstance(confidence, str) or confidence not in CONFIDENCE_VALUES:
        raise AnalysisFormatError(f"无效 confidence：{confidence!r}")
    if not isinstance(categories, list) or not all(
        isinstance(category, str) for category in categories
    ):
        raise AnalysisFormatError("categories 必须是字符串数组。")
    if len(categories) != len(set(categories)):
        raise AnalysisFormatError("categories 不能包含重复值。")
    invalid_categories = set(categories) - CATEGORY_VALUES
    if invalid_categories:
        raise AnalysisFormatError(
            f"无效 categories：{', '.join(sorted(invalid_categories))}"
        )
    if relevance == "related" and not categories:
        raise AnalysisFormatError("relevance=related 时 categories 不能为空。")
    if relevance == "unrelated" and categories:
        raise AnalysisFormatError("relevance=unrelated 时 categories 必须为空。")

    if not isinstance(architectures, list) or not all(
        isinstance(architecture, str) for architecture in architectures
    ):
        raise AnalysisFormatError("related_architectures 必须是字符串数组。")
    if len(architectures) != len(set(architectures)):
        raise AnalysisFormatError("related_architectures 不能包含重复值。")
    invalid_architectures = set(architectures) - ARCHITECTURE_VALUES
    if invalid_architectures:
        raise AnalysisFormatError(
            "无效 related_architectures："
            + ", ".join(sorted(invalid_architectures))
        )
    if relevance == "related" and not architectures:
        raise AnalysisFormatError(
            "relevance=related 时 related_architectures 不能为空。"
        )
    if relevance == "unrelated" and architectures:
        raise AnalysisFormatError(
            "relevance=unrelated 时 related_architectures 必须为空。"
        )

    if not isinstance(origin_architectures, list) or not all(
        isinstance(architecture, str) for architecture in origin_architectures
    ):
        raise AnalysisFormatError("semantic_origin_architectures 必须是字符串数组。")
    if len(origin_architectures) != len(set(origin_architectures)):
        raise AnalysisFormatError("semantic_origin_architectures 不能包含重复值。")
    invalid_origins = set(origin_architectures) - ARCHITECTURE_VALUES
    if invalid_origins:
        raise AnalysisFormatError(
            "无效 semantic_origin_architectures：" + ", ".join(sorted(invalid_origins))
        )
    if not set(origin_architectures).issubset(architectures):
        raise AnalysisFormatError(
            "semantic_origin_architectures 必须是 related_architectures 的子集。"
        )
    if common_code_scope not in COMMON_CODE_SCOPE_VALUES:
        raise AnalysisFormatError(f"无效 common_code_scope：{common_code_scope!r}")
    if assertion_sufficiency not in ASSERTION_SUFFICIENCY_VALUES:
        raise AnalysisFormatError(
            f"无效 assertion_sufficiency：{assertion_sufficiency!r}"
        )
    if not isinstance(mechanisms, list) or not all(
        isinstance(mechanism, str) for mechanism in mechanisms
    ):
        raise AnalysisFormatError("recommended_mechanisms 必须是字符串数组。")
    if len(mechanisms) != len(set(mechanisms)):
        raise AnalysisFormatError("recommended_mechanisms 不能包含重复值。")
    invalid_mechanisms = set(mechanisms) - RECOMMENDED_MECHANISM_VALUES
    if invalid_mechanisms:
        raise AnalysisFormatError(
            "无效 recommended_mechanisms：" + ", ".join(sorted(invalid_mechanisms))
        )
    if "none" in mechanisms and len(mechanisms) != 1:
        raise AnalysisFormatError("recommended_mechanisms 中 none 不能与其他值并存。")
    if relevance == "related" and not mechanisms:
        raise AnalysisFormatError(
            "relevance=related 时 recommended_mechanisms 不能为空。"
        )
    if relevance == "unrelated" and (
        origin_architectures
        or common_code_scope != "not_applicable"
        or assertion_sufficiency != "not_applicable"
        or mechanisms != ["none"]
    ):
        raise AnalysisFormatError("unrelated 的作用域、断言和机制字段必须为不适用。")

    return AnalysisClassification(
        relevance=relevance,
        categories=tuple(categories),
        confidence=confidence,
        related_architectures=tuple(architectures),
        semantic_origin_architectures=tuple(origin_architectures),
        common_code_scope=common_code_scope,
        assertion_sufficiency=assertion_sufficiency,
        recommended_mechanisms=tuple(mechanisms),
    )


def parse_model_output(content: str) -> ModelAnalysis:
    """把模型响应解析为分类元数据和 Markdown 正文。"""

    normalized = content.lstrip("\ufeff \t\r\n")
    if not normalized.startswith(METADATA_MARKER):
        raise AnalysisFormatError(f"响应必须以 {METADATA_MARKER} 开始。")
    remainder = normalized[len(METADATA_MARKER) :]
    if REPORT_MARKER not in remainder:
        raise AnalysisFormatError(f"响应缺少 {REPORT_MARKER}。")
    metadata_text, markdown = remainder.split(REPORT_MARKER, 1)
    metadata_text = metadata_text.strip()
    markdown = markdown.strip()
    try:
        metadata = json.loads(metadata_text)
    except json.JSONDecodeError as exc:
        raise AnalysisFormatError(f"分类 JSON 无法解析：{exc.msg}") from exc
    if not isinstance(metadata, dict):
        raise AnalysisFormatError("分类 JSON 顶层必须是对象。")
    classification = classification_from_mapping(metadata)

    if not markdown:
        raise AnalysisFormatError("Markdown 分析正文为空。")
    if METADATA_MARKER in markdown or REPORT_MARKER in markdown:
        raise AnalysisFormatError("Markdown 正文中不能重复输出协议标记。")
    if re.search(r"^##\s+研究相关性判定\s*$", markdown, re.MULTILINE):
        raise AnalysisFormatError("分类区块由程序生成，正文中不应重复输出。")
    missing_headings = [
        heading
        for heading in REQUIRED_REPORT_HEADINGS
        if not re.search(rf"^##\s+{re.escape(heading)}\s*$", markdown, re.MULTILINE)
    ]
    if missing_headings:
        raise AnalysisFormatError(
            "Markdown 正文缺少标题：" + "、".join(missing_headings)
        )
    return ModelAnalysis(classification, markdown)


def render_classification(classification: AnalysisClassification) -> str:
    """由程序生成稳定的人读分类区块。"""

    categories = (
        "、".join(CATEGORY_LABELS[value] for value in classification.categories)
        if classification.categories
        else "不适用"
    )
    architectures = (
        "、".join(classification.related_architectures)
        if classification.related_architectures
        else "不适用"
    )
    origins = (
        "、".join(classification.semantic_origin_architectures)
        if classification.semantic_origin_architectures
        else "未知或不适用"
    )
    mechanisms = (
        "、".join(
            RECOMMENDED_MECHANISM_LABELS[value]
            for value in classification.recommended_mechanisms
        )
        if classification.recommended_mechanisms
        else "未给出"
    )
    return "\n".join(
        (
            "## 研究相关性判定",
            "",
            f"- 结论：{RELEVANCE_LABELS[classification.relevance]}",
            f"- 类型：{categories}",
            f"- 相关架构：{architectures}",
            f"- 语义来源架构：{origins}",
            f"- 公共层作用域：{COMMON_CODE_SCOPE_LABELS[classification.common_code_scope]}",
            f"- 断言充分性：{ASSERTION_SUFFICIENCY_LABELS[classification.assertion_sufficiency]}",
            f"- 建议机制：{mechanisms}",
            f"- 置信度：{CONFIDENCE_LABELS[classification.confidence]}",
        )
    )
