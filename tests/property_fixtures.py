"""明确的测试判定，不使用生产提示词示例作为测试预期。"""

from linux_bug_analyze.analysis_properties import properties_from_mapping


def property_mapping():
    result = {
        name: {"value": "no", "reason": "diff 中未涉及此性质，测试依据。", "needs_review": False}
        for name in (
            "assumption_exceeds_guarantee", "representation_mismatch",
            "default_config_invalid", "intermediate_state_violation", "stale_state",
        )
    }
    result["assumption_exceeds_guarantee"]["value"] = "yes"
    result["stale_state"]["needs_review"] = True
    result["stale_state"]["reason"] = "缺少同步调用路径，暂不能排除陈旧状态。"
    result["repair_outcome"] = {"value": "incomplete_fix", "reason": "前次修复遗漏 arm32 路径。", "needs_review": False}
    result["impact_type"] = {"value": "correctness_security", "reason": "提交说明报告了崩溃。", "needs_review": False}
    return result


def property_assessments():
    return properties_from_mapping(property_mapping())
