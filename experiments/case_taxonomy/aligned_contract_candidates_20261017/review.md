# N2.5 独立方法审查（2026-10-17）

## 输入与身份

我在模型任务启动附近核对了已生成的输入，**这不是调用前的独立批准**。重新计算 `protocol_pre.json`、`packet_schema.json`、`documents.json`、`prompt.md` 及登记的 8 份输入 SHA-256，均与 `packet_manifest.json` 相符。12 个函数文档的文本、profile、revision、配置、镜像与预处理摘要逐项匹配登记 region 的函数文本；2 个配置摘录逐行匹配原配置中的已选键。14 段编号文档在 prompt 中各出现一次，prompt 为 46,230 UTF-8 字节。两架构函数同属 revision `88b604263f3d6eedae0b1c2c3bbd602d1e2e8775`，各自配置摘要不同。x86 摘录未出现 `CONFIG_SCHED_TOPOLOGY`，s390 摘录未出现 `CONFIG_X86_64`；缺失不能解释为 `n`。

登记及 prompt 限定为已读案例的带观测代码源码区域和配置选行，包含事先披露的 x86 `smp_callin` 补充区域。没有把旧运行值、修复材料、手填 provider 特征或独立 oracle 放进模型输入；也没有以文字预填 `self` 要求。不过观测代码本身含 `o->self`、`cpumask_test_cpu` 等显著线索，因此不能把模型提出类似要求称为无提示的独立发现。函数区域并非完整内核或独立留出样本。模型没有看到 SHA 或完整 artifact 绑定字段；这些由 `documents.json` 和后续程序核对，而非模型自行验证。

## 检查器和真实输出

初审发现 `architecture_paths.profile` 缺失或为 null 时，引用核对会失去跨 profile 限制；用 D01（s390）和 D07（x86）的同一候选已复现。正式检查前已修正为只接受显式 `old_s390` 或 `old_x86`，独立再试 null、s390、x86 配混合引用均为 `insufficient`。检查器现在还限制架构路径至多 6 项。原始回答只接受完整单个 JSON 或单个外层 JSON 代码块，重复 JSON 键拒绝；文档、原文行段、同 profile 和模型交付元数据均有门控。引用通过后的状态明确为 `source_bound_candidate`，其 `check_scope` 仅为引用身份与行段，要求语义复核，且不写入 N2 正式特征。

首轮真实检查保留在 `candidate_checks.json`：14/14 文档绑定，3 项要求、6 条架构路径及 3 项建议检查仅完成引用绑定；L1 为 `not_established`（原文顺序是 `update_cpu_masks` 在 `notify_cpu_starting` 之后），L2 为 `verified_lexical_order`，L3 为 `insufficient`。L3 的 D12:31 是外层独立 `set_cpu_sibling_map(...)` 调用语句，但其展开实参含 GNU statement-expression 和 `void` 等类型词，旧过滤把嵌套词误作外层声明依据。此项是检查器保守漏判，不能计作模型语义错误。原回答的 L1 方向与原文相反，也不能单凭这条词法逆序判断真实故障。

获授权的局部修订仅让类型词过滤跳过已配对的嵌套 `()`、`{}`、`[]`，保留外层独立调用语句、函数体、唯一锚点和证据覆盖限制；原程序及首轮结果另存。`candidate_checks.revised.json` 与首轮使用同一 `documents.json` 和原样 final 摘要（`e7eec298c551107f8e3ed687d83596a63fb127a18af26ae8c151b801ae232b0b`），二轮 L1 仍不成立、L2/L3 为已核词法先后。独立运行修订后 11 项方法测试通过；程序 SHA-256 为 `a65c41ee2fa43b4cb73982c603b66b8288e6f0ef5439cf15b378d7a58e3fc78d`，测试 SHA-256 为 `dd7b1b40957f545b34ae9007b7df6e3638c916f5d338a78d330661fcb69c5b94`，与保存的修订执行记录一致。交付 receipt 报告 `complete_final_received`、退出码 0、success、单一 `AWS-Claude-Opus-5.5`、`end_turn`、未见拒绝；call plan 的 prompt 摘要与登记 manifest 相同。它们证明本次可见 CLI 交付条件，不能证明内部只发生一次上游推理或模型内容正确。

词法检查只证明指定编号文档内的受支持调用形态及字符位置关系。它不解析完整 C 语义、宏/函数指针身份、控制流、可达性、被调函数效果、对象准备或写后稳定性；修订后二轮结果的 `formal_features_updated` 与 `semantic_or_effect_proof` 仍为 false。配置缺键和自然语言要求是否成立也不由引用匹配自动认证。本审查没有读取独立 `source_oracle.md`、旧运行真值、修复材料或新 Git 源码；语义裁定由主流程另行完成。
