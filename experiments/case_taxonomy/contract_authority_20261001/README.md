# 局部契约证据门控

本门控把“引用是否完整、是否指向提供的同版材料”与“审阅者认为这些材料支持什么语义”分开。它不从引文自动理解接口，也不建立新增样本真值。独立留出检测继续使用上一轮冻结生成器；契约卡不会更改其 candidate/matched 标签。

## API

```python
from authority_gate import evaluate
result = evaluate(generator_plan, contract_card, source_files)
```

`generator_plan` 是 `generator.build_plan(report, files)` 的完整输出。门控用卡的绑定选出唯一 program，并重新生成该 program 核对保存的源证据。精简摘要不能代替完整计划。

`source_files` 可以按下列方式提供；同一 plan 已保存的文件也可直接映射为原文字符串：

```json
{
  "net/bluetooth/hci_core.c": {
    "revision": "与 program.source_revision 完全相同",
    "text": "同版源文件原文",
    "sha256": "源文件 UTF-8 原文的 SHA256",
    "git_blob": "可选，按 Git blob 算法核对内容"
  }
}
```

原有 plan 文件必须字节一致；额外源文件必须提供同 revision 元数据和匹配哈希。门控能核对内容与版本元数据的一致性，不能单凭这些字段认证某个文件确实属于该 Git 提交；调用方仍需从对应版本读取材料。外部 URL 和未提供文件不在引用核对范围内。

## 精简契约卡

完整合成示例见 `schema_example.json`，仅用于 schema 和边界测试，不能当实际案例的审阅卡。核心结构如下：

```json
{
  "binding": {
    "revision": "program.source_revision",
    "source_file": "program.source_file",
    "function": "program.function",
    "variable": "program.variable",
    "payload_struct": "program.payload_struct"
  },
  "review": {
    "status": "reviewed",
    "reviewed_by": "可追踪的审阅者名称",
    "reviewer_kind": "human 或 assistant",
    "scope": "source_contract"
  },
  "fields": [
    {
      "name": "payload 字段名",
      "producer": {"struct": "来源结构", "field": "来源字段", "type": "来源声明类型"},
      "consumer": {"endian": "le 或 be", "bits": 16},
      "facts": [
        {
          "kind": "source_numeric_domain",
          "status": "supported",
          "origin": "source_review",
          "value": "host_numeric",
          "claim": "审阅者为什么认为来源是主机数值；类型名自身不足以证明",
          "evidence": [{"file": "提供的同版源文件", "line": 1, "quote": "精确原文", "sha256": "整文件哈希"}]
        }
      ]
    }
  ]
}
```

每个 payload 字段必须唯一出现，来源结构/字段/类型以及消费者端序/宽度均与选定 program 对应。每字段需三种事实：

- `source_numeric_domain`：value 为 `host_numeric`，支持的是明确审阅后的来源域声明，不自动继承生成器的 host 输入假设。
- `consumer_format`：value 为 `{"endian":"le 或 be","bits":16/32/64}`，与字段 schema 一致；格式是否应作为权威仍由审阅者给出 claim。
- `applicability`：value 为 `{"revision":"同版标识","scope":"source_contract"}`，只支持局部源码适用范围，不声明硬件或配置可达。

所有 fact 使用 `supported / conditional / insufficient / conflict` 状态，以及 `source_review / normative_review / assumption` origin，并必须保留 claim 和源引用。精确 quote 必须从指定行开始，允许省略行首空白，不会折叠内部空白、制表符或换行。已有提取器的归一化 evidence text 可能与原文空白不同，应从提供源文件实际行复制引用。

`normative_review` 还需保存：

```json
{
  "document_version": "明确的历史规范版本和日期",
  "historical_applicability": {
    "status": "reviewed",
    "claim": "该版本、设备或模式为什么适用于本历史提交"
  }
}
```

版本或历史适用性未知时不能升为 ready；`current / latest / HEAD` 等浮动标识也不算固定历史版本，不得把当前文档自动当成历史权威。本轮机器只核对提供源文件引用，外部规范本体与语义不由门控认证。冲突保留为未解决，不按架构数量、引文数量或 origin 自动选赢家。

## 状态与含义

| 状态 | 含义 |
|---|---|
| source_contract_ready | 每字段事实与引用完整，且来自已归属审阅者的 supported 非假设声明；仅是局部审阅门槛 |
| conditional | 引用可核对，但存在假设、条件性判断、未完成语义审阅或未知规范历史适用性 |
| insufficient | 缺卡、缺 program、缺字段、绑定/域不符、引用不完整或事实值未知 |
| conflict | 任意卡内已报告冲突优先保留，即使另有引用或绑定缺失；不是机器已经证实冲突 |

输出分别保存 `reference_integrity`、`semantic_review` 和逐字段事实。匹配引文只证明其引用完整性，不证明 claim 从 quote 逻辑推出；助手审阅也不是人类专家金标准。

所有状态下 `machine_contract_proven`、`runtime_reachability_proven`、`full_kernel_proven`、`external_protocol_proven` 均为 false。本轮未接入任何独立运行证据，因此即使 source_contract_ready 也不能改变这些值。

## 开发验证

```bash
cd experiments/case_taxonomy/contract_authority_20261001
python3 -m unittest authority_gate_test.py
```

17 项独立门控测试覆盖错误身份与字段绑定、不同版本与源字节、quote/line/hash、缺事实和部分引用、冲突优先、假设、规范历史版本未知或浮动、program 篡改，以及“引用匹配但没有语义审阅不能 ready”。这些是合成开发测试，不计新增案例或检测准确率。
