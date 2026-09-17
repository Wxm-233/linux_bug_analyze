import json
from unittest import TestCase
from tests.property_fixtures import property_mapping

from linux_bug_analyze.analysis_protocol import (
    AnalysisFormatError,
    parse_model_output,
    render_classification,
)


def _metadata(**overrides) -> str:
    data = {
        "schema_version": 4,
        "relevance": "related",
        "categories": ["implicit_semantic_assumption"],
        "confidence": "medium",
        "related_architectures": ["arm32"],
        "semantic_origin_architectures": ["arm32"],
        "common_code_scope": "overbroad",
        "assertion_sufficiency": "partial",
        "recommended_mechanisms": ["config_guard", "test"],
        "properties": property_mapping(),
    }
    data.update(overrides)
    return json.dumps(data)


def _output(metadata: str) -> str:
    return f"""<<<LBA_METADATA_V4>>>
{metadata}
<<<LBA_REPORT_V4>>>
## 提交概述
overview

## 判定理由
reason

## 语义卡片
card

## 证据审计
audit
"""


class AnalysisProtocolTests(TestCase):
    def test_accepts_each_property_choice(self) -> None:
        choices = {
            "assumption_exceeds_guarantee": ("yes", "no"),
            "representation_mismatch": ("yes", "no"),
            "default_config_invalid": ("yes", "no"),
            "intermediate_state_violation": ("yes", "no"),
            "stale_state": ("yes", "no"),
            "repair_outcome": ("new_bug", "incomplete_fix", "neither"),
            "impact_type": ("correctness_security", "performance", "neither"),
        }
        for name, values in choices.items():
            for value in values:
                with self.subTest(name=name, value=value):
                    properties = property_mapping()
                    properties[name]["value"] = value
                    parsed = parse_model_output(_output(_metadata(properties=properties)))
                    self.assertEqual(parsed.classification.properties[name].value, value)

    def test_properties_roundtrip_and_rendering(self) -> None:
        properties = property_mapping()
        properties["stale_state"]["reason"] = "调用 a|b\n缺少 <同步> 证据"
        parsed = parse_model_output(_output(_metadata(properties=properties)))
        self.assertEqual(parsed.classification.properties["repair_outcome"].value, "incomplete_fix")
        self.assertTrue(parsed.classification.properties["stale_state"].needs_review)
        rendered = render_classification(parsed.classification)
        self.assertIn("## 性质判定", rendered)
        self.assertIn("否（暂定）", rendered)
        self.assertIn("a&#124;b 缺少 &lt;同步>", rendered)
        self.assertIn("修复不完全", rendered)

    def test_rejects_invalid_properties(self) -> None:
        invalid_items = [
            {"value": True, "reason": "依据", "needs_review": False},
            {"value": "unknown", "reason": "依据", "needs_review": False},
            {"value": ["yes", "no"], "reason": "依据", "needs_review": False},
            {"value": "yes", "reason": " ", "needs_review": False},
            {"value": "yes", "reason": "x" * 601, "needs_review": False},
            {"value": "yes", "reason": "依据", "needs_review": "false"},
            {"value": "yes", "reason": "依据"},
            {"value": "yes", "reason": "依据", "needs_review": False, "extra": 1},
        ]
        for item in invalid_items:
            with self.subTest(item=item), self.assertRaises(AnalysisFormatError):
                properties = property_mapping()
                properties["stale_state"] = item
                parse_model_output(_output(_metadata(properties=properties)))
        for properties in ({}, None, [], {**property_mapping(), "extra": {}}):
            with self.subTest(properties=properties), self.assertRaises(AnalysisFormatError):
                parse_model_output(_output(_metadata(properties=properties)))
        for name in ("repair_outcome", "impact_type"):
            with self.subTest(name=name), self.assertRaises(AnalysisFormatError):
                properties = property_mapping()
                properties[name]["value"] = "both"
                parse_model_output(_output(_metadata(properties=properties)))

    def test_rejects_missing_properties_and_old_schema(self) -> None:
        metadata = json.loads(_metadata())
        del metadata["properties"]
        with self.assertRaisesRegex(AnalysisFormatError, "缺少字段 properties"):
            parse_model_output(_output(json.dumps(metadata)))
        with self.assertRaisesRegex(AnalysisFormatError, "schema_version"):
            parse_model_output(_output(_metadata(schema_version=3)))

    def test_rejects_duplicate_property_section(self) -> None:
        with self.assertRaisesRegex(AnalysisFormatError, "不应重复"):
            parse_model_output(_output(_metadata()) + "\n## 性质判定\n")

    def test_parses_metadata_and_scope_fields(self) -> None:
        parsed = parse_model_output(
            _output(
                _metadata(
                    categories=[
                        "implicit_semantic_assumption",
                        "cross_arch_regression",
                    ],
                    related_architectures=["arm32", "riscv"],
                    semantic_origin_architectures=["arm32"],
                )
            )
        )
        self.assertEqual(parsed.classification.relevance, "related")
        self.assertEqual(
            parsed.classification.categories,
            ("implicit_semantic_assumption", "cross_arch_regression"),
        )
        self.assertEqual(
            parsed.classification.related_architectures, ("arm32", "riscv")
        )
        self.assertEqual(
            parsed.classification.semantic_origin_architectures, ("arm32",)
        )
        self.assertEqual(parsed.classification.common_code_scope, "overbroad")
        self.assertIn("## 语义卡片", parsed.markdown)

    def test_rejects_markdown_only_classification(self) -> None:
        with self.assertRaisesRegex(AnalysisFormatError, "必须以"):
            parse_model_output("- **结论**：不相关- **类型**：不适用")

    def test_rejects_inconsistent_classification(self) -> None:
        with self.assertRaisesRegex(AnalysisFormatError, "必须为空"):
            parse_model_output(
                _output(
                    _metadata(
                        relevance="unrelated",
                        categories=["cross_arch_regression"],
                        related_architectures=[],
                        semantic_origin_architectures=[],
                        common_code_scope="not_applicable",
                        assertion_sufficiency="not_applicable",
                        recommended_mechanisms=["none"],
                    )
                )
            )

    def test_rejects_missing_required_heading(self) -> None:
        content = _output(
            _metadata(
                relevance="uncertain",
                categories=[],
                related_architectures=[],
                semantic_origin_architectures=[],
                common_code_scope="uncertain",
                assertion_sufficiency="uncertain",
                recommended_mechanisms=[],
            )
        ).replace("## 证据审计", "## 其他")
        with self.assertRaisesRegex(AnalysisFormatError, "证据审计"):
            parse_model_output(content)

    def test_program_renders_scope_and_mechanisms(self) -> None:
        parsed = parse_model_output(
            _output(
                _metadata(
                    categories=["cross_arch_regression"],
                    confidence="high",
                    related_architectures=["x86"],
                    semantic_origin_architectures=["x86"],
                    assertion_sufficiency="insufficient",
                    recommended_mechanisms=["state_machine", "test"],
                )
            )
        )
        rendered = render_classification(parsed.classification)
        self.assertIn("- 结论：相关", rendered)
        self.assertIn("- 相关架构：x86", rendered)
        self.assertIn("- 公共层作用域：公共层作用域过宽", rendered)
        self.assertIn("- 断言充分性：断言不足", rendered)
        self.assertIn("状态机", rendered)
        self.assertNotIn("**", rendered)

    def test_rejects_alias_origin_outside_related_and_mixed_none(self) -> None:
        with self.assertRaisesRegex(AnalysisFormatError, "无效 related_architectures"):
            parse_model_output(
                _output(_metadata(related_architectures=["aarch64"]))
            )
        with self.assertRaisesRegex(AnalysisFormatError, "子集"):
            parse_model_output(
                _output(
                    _metadata(
                        related_architectures=["riscv"],
                        semantic_origin_architectures=["arm32"],
                    )
                )
            )
        with self.assertRaisesRegex(AnalysisFormatError, "none 不能"):
            parse_model_output(
                _output(_metadata(recommended_mechanisms=["none", "test"]))
            )
