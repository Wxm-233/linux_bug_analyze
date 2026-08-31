"""把研究定义、提交事实和补充证据组装为可审计提示词。"""

from __future__ import annotations

from .analysis_protocol import METADATA_MARKER, REPORT_MARKER
from .models import CommitInfo


SYSTEM_PROMPT = (
    "你是熟悉 Linux 内核源码的资深研究者。严格区分已给证据、合理推断和未知信息；"
    "不得把常识或猜测伪装成提交证据，不得引用材料中不存在的函数或事实。"
    "必须严格遵守用户提供的输出协议，"
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
- 补充证据可能包含 Fixes 引入提交、CVE 公告、邮件讨论或人工材料；必须注明具体来源。
- 只根据下方材料判断。区分“证据直接表明”“由代码推断”“材料不足”。
- 必须寻找反证或替代解释。缺少证据时写“未知”，不要补造事实。
- 若不同来源看似冲突，先检查它们是否适用于不同版本、架构、配置或目标；不能只因某个
  方案更简单就选择支持它的语义。运行时反馈通常优先于代码，代码优先于一般性文档和
  其他架构类比，但代码本身可能正是缺陷，最终判断必须说明依据。
- 检查实际补丁是否修改了根因，是否只是绕开症状，以及在其他相关边界下是否仍正确。
- “实际修复”只能描述 diff 已做的事情；研究者建议必须另行标明，不能混为一谈。
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
{{"schema_version":2,"relevance":"related","categories":["implicit_semantic_assumption"],"confidence":"high","related_architectures":["arm32"]}}
{REPORT_MARKER}
## 提交概述
……

分类 JSON 规则：
- 只能包含 schema_version、relevance、categories、confidence、related_architectures 五个字段。
- schema_version 必须是 2。
- relevance 只能是 related、unrelated、uncertain。
- categories 只能从 implicit_semantic_assumption、cross_arch_regression 中选择，可多选。
- related 至少选择一个 category；unrelated 的 categories 必须为空数组；uncertain 可为空或列出疑似类型。
- confidence 只能是 high、medium、low。
- related_architectures 是与缺陷的触发、影响或修复直接相关的架构数组，不是正文中提到的
  所有架构。可多选，只能使用：alpha、arc、arm32、arm64、csky、h8300、hexagon、ia64、
  loongarch、m68k、microblaze、mips、nds32、nios2、openrisc、parisc、powerpc、riscv、
  s390、sh、sparc、um、x86、xtensa。
- arch/arm 对应 arm32，arch/arm64 对应 arm64；不要输出 arm、aarch64、x86_64、ppc
  等别名。仅作为对照实现而被提到的架构不要列入。
- related 的 related_architectures 至少包含一项；unrelated 必须为空数组；uncertain 可为空。
- JSON 之后必须原样输出 {REPORT_MARKER}，再输出 Markdown 正文。
- Markdown 正文不要再次输出结论、类型、置信度或“研究相关性判定”标题；该区块由程序根据 JSON 生成。

Markdown 正文必须严格包含以下结构，不要省略二级标题：

## 提交概述
用本科生能看懂的语言说明动机、主要改动、涉及的公共层/架构/子系统。

## 判定理由
引用具体的提交说明、diff 或补充证据解释分类 JSON 中的判断，不复制大段原文；同时说明
为什么 JSON 中列出的架构与缺陷直接相关。

## 语义卡片
| 字段 | 分析 |
|---|---|
| 缺失或冲突的语义 d | |
| 语义来源及冲突 | 分别列出支持、反驳或范围不同的来源；没有冲突也要说明 |
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
只列出当前材料确实尚未回答、且会影响判定或人工复核的内容。区分“未检索”“未找到”和
“材料中没有说明”；不要机械地为每篇报告列出所有可能的证据类型。
"""
