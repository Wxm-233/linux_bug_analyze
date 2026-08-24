from unittest import TestCase

from linux_bug_analyze.analysis_protocol import (
    AnalysisFormatError,
    parse_model_output,
    render_classification,
)


def _output(metadata: str) -> str:
    return f"""<<<LBA_METADATA_V1>>>
{metadata}
<<<LBA_REPORT_V1>>>
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
    def test_parses_metadata_and_free_markdown_body(self) -> None:
        parsed = parse_model_output(
            _output(
                '{"schema_version":1,"relevance":"related",'
                '"categories":["implicit_semantic_assumption",'
                '"cross_arch_regression"],"confidence":"medium"}'
            )
        )
        self.assertEqual(parsed.classification.relevance, "related")
        self.assertEqual(
            parsed.classification.categories,
            ("implicit_semantic_assumption", "cross_arch_regression"),
        )
        self.assertIn("## 语义卡片", parsed.markdown)

    def test_rejects_markdown_only_classification(self) -> None:
        with self.assertRaisesRegex(AnalysisFormatError, "必须以"):
            parse_model_output("- **结论**：不相关- **类型**：不适用")

    def test_rejects_inconsistent_classification(self) -> None:
        with self.assertRaisesRegex(AnalysisFormatError, "必须为空"):
            parse_model_output(
                _output(
                    '{"schema_version":1,"relevance":"unrelated",'
                    '"categories":["cross_arch_regression"],"confidence":"high"}'
                )
            )

    def test_rejects_missing_required_heading(self) -> None:
        content = _output(
            '{"schema_version":1,"relevance":"uncertain",'
            '"categories":[],"confidence":"low"}'
        ).replace("## 证据审计", "## 其他")
        with self.assertRaisesRegex(AnalysisFormatError, "证据审计"):
            parse_model_output(content)

    def test_program_renders_plain_stable_classification(self) -> None:
        parsed = parse_model_output(
            _output(
                '{"schema_version":1,"relevance":"related",'
                '"categories":["cross_arch_regression"],"confidence":"high"}'
            )
        )
        rendered = render_classification(parsed.classification)
        self.assertIn("- 结论：相关", rendered)
        self.assertIn("- 类型：跨架构回归", rendered)
        self.assertNotIn("**", rendered)
