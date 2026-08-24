"""把研究定义、提交事实和补充证据组装为可审计提示词。"""

from __future__ import annotations

from .analysis_protocol import METADATA_MARKER, REPORT_MARKER
from .models import CommitInfo


SYSTEM_PROMPT = (
    "你是熟悉 Linux 内核源码的资深研究者。严格区分已给证据、合理推断和未知信息；"
    "不得把常识或猜测伪装成提交证据。必须严格遵守用户提供的输出协议，"
    "不能自行改用其他格式。"
)


def build_prompt(commit: CommitInfo, research_context: str, evidence: str = "") -> str:
    """构造与论文当前研究问题一致的固定结构分析任务。"""

    files_text = "\n".join(commit.files) if commit.files else "（无文件变更）"
    diff_text = commit.diff or "（无文本差异，可能仅包含二进制变更）"
    truncation_note = (
        f"是（原始 {commit.original_diff_chars} 字符，结论必须降低置信度并指出可能遗漏）"
        if commit.diff_truncated
        else "否"
    )
    supplemental = evidence.strip() or "（未提供；不得声称看过邮件、缺陷报告或硬件手册）"

    return f"""请先理解研究框架，再分析提交。研究对象不是所有内核 bug，而是：
1. 公共层与架构层对硬件语义理解不一致造成的“隐式语义假设错误”；
2. 为架构 A 修改公共/边界代码后影响架构 B 的“跨架构回归”。

==================== 研究框架开始 ====================
{research_context}
==================== 研究框架结束 ====================

证据使用规则：
- “提交说明”和“代码差异”是不同证据源；前者表达作者意图，后者表达实际修改。
- 只根据下方材料判断。区分“证据直接表明”“由代码推断”“材料不足”。
- 必须寻找反证或替代解释。缺少证据时写“未知”，不要补造事实。
- 若 diff 被截断，必须在局限性中说明可能遗漏关键改动。

提交哈希：{commit.hash}
作者：{commit.author}
日期：{commit.date}
标题：{commit.subject}
diff 是否截断：{truncation_note}

==================== 提交说明 ====================
{commit.body or '（无）'}

==================== 变更文件 ====================
{files_text}

==================== 代码差异 ====================
{diff_text}

==================== 补充证据 ====================
{supplemental}

输出是程序接口。必须从响应的第一个字符开始严格使用以下协议；不要添加代码围栏、前言或结尾标记：

{METADATA_MARKER}
{{"schema_version":1,"relevance":"related","categories":["implicit_semantic_assumption"],"confidence":"high"}}
{REPORT_MARKER}
## 提交概述
……

分类 JSON 规则：
- 只能包含 schema_version、relevance、categories、confidence 四个字段。
- schema_version 必须是 1。
- relevance 只能是 related、unrelated、uncertain。
- categories 只能从 implicit_semantic_assumption、cross_arch_regression 中选择，可多选。
- related 至少选择一个 category；unrelated 的 categories 必须为空数组；uncertain 可为空或列出疑似类型。
- confidence 只能是 high、medium、low。
- JSON 之后必须原样输出 {REPORT_MARKER}，再输出 Markdown 正文。
- Markdown 正文不要再次输出结论、类型、置信度或“研究相关性判定”标题；该区块由程序根据 JSON 生成。

Markdown 正文必须严格包含以下结构，不要省略二级标题：

## 提交概述
用本科生能看懂的语言说明动机、主要改动、涉及的公共层/架构/子系统。

## 判定理由
引用具体的提交说明或 diff 事实解释分类 JSON 中的判断，不复制大段原文。

## 语义卡片
| 字段 | 分析 |
|---|---|
| 缺失或冲突的语义 d | |
| 语义的提供者与消费者 | |
| 当前边界 | 具体函数、ops 回调、对象或资源描述；未知则直说 |
| 原边界可见信息 | 参数、返回值、状态、能力位、DT/ACPI 对象等 |
| 触发条件 | |
| 架构/设备/配置范围 | |
| 原边界可检查性 | 能否精确检查，以及理由 |
| 实际修复 | 只描述补丁实际做法 |
| 应修改的层次 | 公共层 / 架构层 / 两者 / 不适用，并说明依据 |
| 建议验证手段 | 静态检查、运行期断言、构建、测试或人工审查 |
| 错误表现 | 架构特定触发 / 跨架构回归 / 其他 / 不适用 |

若 relevance 为 unrelated，语义卡片仍须保留，各字段写“不适用”并简述原因。

## 证据审计
### 支持结论的证据
逐条注明来源为“提交说明”“代码差异”或“补充证据”。

### 反证与替代解释
列出材料中的反证；若没有，写“当前材料未见”，但不得等同于不存在。

### 未知信息与局限性
列出仍需从邮件讨论、缺陷报告、硬件规范、其他架构实现或运行结果确认的内容。
"""
