"""把研究定义、提交事实和补充证据组装为可审计提示词。"""

from __future__ import annotations

import json

from .analysis_protocol import METADATA_MARKER, REPORT_MARKER, SCHEMA_VERSION
from .analysis_properties import pending_properties_example
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
    properties_example = json.dumps(pending_properties_example(), ensure_ascii=False, separators=(",", ":"))

    return f"""请先理解研究框架，再分析来自 Linux 主线提交历史的提交。候选集合不是 CVE 样本；
是否有 CVE 编号不影响相关性判断。研究对象不是所有内核 bug，而是：
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
- 重点检查公共代码是否无条件承担了只源于部分架构的语义。若是，判断真正必要的
  architecture-scope，以及条件编译、移动到 arch/、能力接口、类型/API、状态机、测试或
  断言中哪种机制更适合。不要预设断言一定足够。
- 分析“为何最初进入公共层”时只能使用提交历史或材料中的依据；没有证据就写未知，
  不得把“为未来复用”当成默认事实。
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
{{"schema_version":{SCHEMA_VERSION},"relevance":"related","categories":["cross_arch_regression"],"confidence":"medium","related_architectures":["arm32","riscv"],"semantic_origin_architectures":["arm32"],"common_code_scope":"overbroad","assertion_sufficiency":"partial","recommended_mechanisms":["config_guard","move_to_arch","test"],"properties":{properties_example}}}
{REPORT_MARKER}
## 提交概述
……

分类 JSON 规则：
- 只能包含示例中出现的十个顶层字段，不得添加字段。schema_version 必须是 {SCHEMA_VERSION}。
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
- semantic_origin_architectures 表示材料能够支持的“语义需求来源架构”，使用相同架构枚举；
  无法确定时为空，并且它必须是 related_architectures 的子集。
- common_code_scope 只能是 overbroad、appropriate、not_applicable、uncertain：overbroad 表示
  公共层无条件承担了实际只对部分架构必要的语义；appropriate 表示共享位置合理。
- assertion_sufficiency 只能是 sufficient、partial、insufficient、not_applicable、uncertain。
  判断的是断言能否覆盖根因和必要作用域，不是“能否增加一条检查”。
- recommended_mechanisms 可多选，只能是 assertion、config_guard、move_to_arch、
  capability_interface、type_or_api、state_machine、test、other、none；none 不能与其他值并存。
- unrelated 时 semantic_origin_architectures=[]、common_code_scope=not_applicable、
  assertion_sufficiency=not_applicable、recommended_mechanisms=["none"]。
- properties 必须逐项包含下面七项，每项只包含 value、reason、needs_review。
  reason 是 1–600 字符的简短依据，注明提交说明、具体函数/diff 或补充证据来源；
  needs_review 是 JSON 布尔值。示例值只是格式占位，不能机械照抄。
- properties 判断当前提交所修复的缺陷（修复前），不把补丁新增的保护措施当成缺陷。
  即使 relevance=unrelated，也要独立判断这些性质；研究不相关不等于没有正确性或性能问题。

七项性质的判定口径：
1. assumption_exceeds_guarantee（yes/no）：调用者使用的假设强于实现者的保证。
   需指出调用者、实现者、所依赖的保证及差距；不能仅凭出现接口调用判 yes。
2. representation_mismatch（yes/no）：传递的数据类型含义、解释不一致。
   包括单位、位宽、符号、字节序、地址空间、标志位含义等。说明谁传递、谁解释及差异；
   仅类型不同但有正确转换不算。
3. default_config_invalid（yes/no）：默认配置在特定架构下不成立。
   需说明哪个默认值/默认配置、哪个架构以及为何无效；只在非默认配置触发不算。
4. intermediate_state_violation（yes/no）：实现只保证最终状态，调用者假设中间态正确。
   需说明状态转换过程、中间态被谁观察/使用以及违反的假设；不是所有竞态都属于此项。
5. stale_state（yes/no）：状态更新不及时。
   说明什么状态、应在哪个时点更新/失效/同步，以及陈旧状态如何造成问题；
   不要把一般执行缓慢当作状态更新不及时。它与第 4 项可同时成立，但需分别给出依据。
6. repair_outcome 只能三选一：new_bug（修复后引入新漏洞）、
   incomplete_fix（修复不完全）、neither（都不是）。判断本次修复对象的历史成因：
   前次修复引入新的缺陷选 new_bug；前次修复未覆盖原问题的路径/架构/配置选 incomplete_fix。
   需指出前次修复与当前缺陷的因果关系，仅有 Fixes 标签不代表它是前次修复。
   普通功能改动引入缺陷不自动算“修复后引入”。new_bug 泛指新的缺陷，不自动证明安全可利用性。
   若两种现象都有证据，优先 new_bug，并在 reason 写明不完全修复这一附带情况。
   不能无证据断言当前补丁未来会引入新漏洞或仍不完整。
7. impact_type 只能三选一：correctness_security（正确性/安全问题）、
   performance（性能损失）、neither（都不是）。崩溃、错误结果、安全边界失效等属于前者；
   功能正确但吞吐、延迟、资源开销恶化属于后者。两者并存优先 correctness_security，
   在 reason 中补充性能影响。perf 等性能工具本身崩溃不等于“性能损失”；
   正确性问题也不自动代表存在可利用安全漏洞。
- 前五项独立判断，可多项 yes；后两项各自单选。每项的 no/neither 同样需要依据。
- 证据不足或互相冲突无法消解时，needs_review=true，并在 reason 明确缺少什么证据。
  无法选择时 value 暂填 no/neither；已有倾向但不确定可保留倾向值并标需复核。
  这些暂定值不会计入已确认性质统计。证据足以作出肯定/否定判断时 needs_review=false。
- JSON 之后必须原样输出 {REPORT_MARKER}，再输出 Markdown 正文。
- Markdown 正文不要再次输出结论、类型、置信度、“研究相关性判定”或“性质判定”标题；
  这两个区块由程序根据 JSON 生成。可在判定理由中展开性质的证据链，但不得与 JSON 矛盾。

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
| 语义来源架构 | 哪个架构的需求引入或要求该语义；未知则说明 |
| 语义的提供者与消费者 | |
| 当前边界 | 具体函数、ops 回调、对象或资源描述；未知则直说 |
| 原边界可见信息 | 参数、返回值、状态、能力位、DT/ACPI 对象等 |
| 触发条件 | |
| 架构/设备/配置范围 | |
| 公共层实际承担范围 | 哪些架构无条件经过或承担这段语义 |
| 最小必要 architecture-scope | 应只适用于哪些架构、能力或配置 |
| 最初进入公共层的原因 | 只写有证据的原因；否则写未知及需要查阅的历史 |
| 原边界可检查性 | 能否精确检查，以及理由 |
| 实际修复 | 只描述补丁实际做法 |
| 应修改的层次 | 公共层 / 架构层 / 两者 / 不适用，并说明依据 |
| 隔离或重构方案 | 说明为何选择条件编译、移动到 arch/、能力接口、类型/API、状态机等 |
| 断言是否足够 | 足够 / 部分足够 / 不足 / 不适用 / 未知，并说明断言覆盖不了什么 |
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
