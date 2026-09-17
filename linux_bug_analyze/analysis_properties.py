"""缺陷性质的固定词表、证据判定与展示。"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


PROPERTY_LABELS = {
    "assumption_exceeds_guarantee": "调用者使用的假设强于实现者的保证",
    "representation_mismatch": "传递的数据类型含义、解释不一致",
    "default_config_invalid": "默认配置在特定架构下不成立",
    "intermediate_state_violation": "实现只保证最终状态，调用者假设中间态正确",
    "stale_state": "状态更新不及时",
    "repair_outcome": "修复历史",
    "impact_type": "问题影响",
}
PROPERTY_VALUES = {
    **{name: ("yes", "no") for name in list(PROPERTY_LABELS)[:5]},
    "repair_outcome": ("new_bug", "incomplete_fix", "neither"),
    "impact_type": ("correctness_security", "performance", "neither"),
}
VALUE_LABELS = {
    "yes": "是", "no": "否",
    "new_bug": "修复后引入新漏洞",
    "incomplete_fix": "修复不完全",
    "neither": "都不是",
    "correctness_security": "正确性/安全问题",
    "performance": "性能损失",
}


@dataclass(frozen=True, slots=True)
class PropertyAssessment:
    value: str
    reason: str
    needs_review: bool


def properties_from_mapping(data: Any) -> dict[str, PropertyAssessment]:
    """不把缺失、未知、布尔字符串或多选默认为有效判断。"""
    if not isinstance(data, dict) or set(data) != set(PROPERTY_VALUES):
        raise ValueError("properties 必须包含且仅包含规定的七项性质。")
    result = {}
    for name, values in PROPERTY_VALUES.items():
        item = data[name]
        if not isinstance(item, dict) or set(item) != {"value", "reason", "needs_review"}:
            raise ValueError(f"properties.{name} 必须包含 value、reason、needs_review。")
        value, reason, review = item["value"], item["reason"], item["needs_review"]
        if not isinstance(value, str) or value not in values:
            raise ValueError(f"properties.{name}.value 必须为 {' / '.join(values)}。")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 600:
            raise ValueError(f"properties.{name}.reason 必须为 1–600 字符的非空依据。")
        if not isinstance(review, bool):
            raise ValueError(f"properties.{name}.needs_review 必须是布尔值。")
        result[name] = PropertyAssessment(value, reason.strip(), review)
    return result


def properties_to_mapping(
    properties: Mapping[str, PropertyAssessment],
) -> dict[str, Any]:
    return {name: asdict(item) for name, item in properties.items()}


def pending_properties_example() -> dict[str, Any]:
    """仅用于提示词示例；实际输出必须逐项重新判断。"""
    return {
        name: {"value": values[-1], "reason": "材料不足，需逐项说明缺少的证据。", "needs_review": True}
        for name, values in PROPERTY_VALUES.items()
    }


def render_properties(properties: Mapping[str, PropertyAssessment]) -> str:
    lines = ["## 性质判定", "", "| 性质 | 判断 | 需复核 | 依据 |", "|---|---|---|---|"]
    for name, label in PROPERTY_LABELS.items():
        item = properties.get(name)
        if item is None:
            lines.append(f"| {label} | 未分析 | 是 | 缺少该字段 |")
            continue
        reason = " ".join(item.reason.splitlines()).replace("|", "&#124;").replace("<", "&lt;")
        value = VALUE_LABELS[item.value] + ("（暂定）" if item.needs_review else "")
        lines.append(f"| {label} | {value} | {'是' if item.needs_review else '否'} | {reason} |")
    return "\n".join(lines)
